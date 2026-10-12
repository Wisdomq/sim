from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from simcards_backend.core.database import SessionLocal
from simcards_backend.models import SimCard, SimStatus
from simcards_backend.services.stock import mark_expired_sim_cards
from simcards_backend.tasks.pdf_parser import parse_pick_list_text


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _setup_accounts(client):
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Dealer Two",
            "safaricom_dealer_shortcode": "D002",
            "hq_email": "hq2@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "hq2@example.com", "supersecret")
    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Branch B",
            "type": "VAN",
            "id_number": "BR-010",
            "photo_url": "https://example.com/branch-b.jpg",
            "email": "branch2@example.com",
            "password": "branchsecret",
        },
    )
    assert branch.status_code == 201
    branch_token = _login(client, "branch2@example.com", "branchsecret")
    ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "BA Two",
            "email": "ba2@example.com",
            "password": "basecret123",
            "phone_msisdn": "254700000002",
            "id_number": "BA-010",
            "photo_url": "https://example.com/ba-two.jpg",
        },
    )
    assert ba.status_code == 201
    return hq_token, branch_token, branch.json(), ba.json()


def test_parse_pick_list_text_extracts_lots_and_serials():
    lots = parse_pick_list_text(
        """
        <<Lot>>
        787561_GD0014656
        Serial No 123456789012345
        Serial No 123456789012346
        <<Lot>> LOT_TWO
        223456789012345
        """
    )
    assert [lot.source_reference for lot in lots] == ["787561_GD0014656", "LOT_TWO"]
    assert lots[0].serials == ["123456789012345", "123456789012346"]
    assert lots[1].serials == ["223456789012345"]


def test_stock_intake_distribution_assignment_returns_and_expiry(client):
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "box_barcode": "BOX-001",
            "first_serial": "1000000000000000001",
            "quantity": 100,
            "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert intake.status_code == 201
    assert intake.json()["inserted_count"] == 100
    assert intake.json()["duplicate_count"] == 0

    duplicate_intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "box_barcode": "BOX-001",
            "first_serial": "1000000000000000001",
            "quantity": 100,
        },
    )
    assert duplicate_intake.status_code == 201
    assert duplicate_intake.json()["inserted_count"] == 0
    assert duplicate_intake.json()["duplicate_count"] == 100

    serials = ["1000000000000000001", "1000000000000000002"]
    distributed = client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "serial_numbers": serials},
    )
    assert distributed.status_code == 200
    assert {row["status"] for row in distributed.json()} == {"WITH_BRANCH"}

    assigned = client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"], "serial_numbers": [serials[0]]},
    )
    assert assigned.status_code == 200
    assert assigned.json()[0]["status"] == "WITH_BA"
    assert assigned.json()[0]["current_ba_id"] == ba["id"]

    returned_to_branch = client.post(
        "/api/v1/stock/return-to-branch",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"serial_numbers": [serials[0]], "reason": "BA offboarded"},
    )
    assert returned_to_branch.status_code == 200
    assert returned_to_branch.json()["processed_count"] == 1

    requested = client.post(
        "/api/v1/stock/return-requests",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "serial_numbers": [serials[1]], "reason": "Recall"},
    )
    assert requested.status_code == 201
    fulfilled = client.post(
        f"/api/v1/stock/return-requests/{requested.json()[0]['id']}/fulfill",
        headers={"Authorization": f"Bearer {branch_token}"},
    )
    assert fulfilled.status_code == 200
    assert fulfilled.json()["status"] == "COMPLETED"

    with SessionLocal() as db:
        sim = db.scalar(select(SimCard).where(SimCard.serial_number == "1000000000000000003"))
        assert sim is not None
        sim.expiry_date = date.today() - timedelta(days=1)
        db.commit()
        expired_count = mark_expired_sim_cards(db)
        assert expired_count == 1
        db.refresh(sim)
        assert sim.status == SimStatus.EXPIRED


def test_ba_sale_recording_with_validation(client):
    """Test BA sale endpoint with validation and conflict handling."""
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    # Intake and distribute stock
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "box_barcode": "BOX-SALE-001",
            "first_serial": "5000000000000000001",
            "quantity": 3,
        },
    )
    assert intake.status_code == 201

    distributed = client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "quantity": 2},
    )
    assert distributed.status_code == 200

    # Assign SIM to BA
    assigned = client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"], "serial_numbers": ["5000000000000000001"]},
    )
    assert assigned.status_code == 200

    # Get BA token
    ba_token = _login(client, "ba2@example.com", "basecret123")

    # Record a sale
    sale_response = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "serial_number": "5000000000000000001",
            "sold_at": datetime.now(timezone.utc).isoformat(),
            "client_event_id": "client-uuid-123",
        },
    )
    assert sale_response.status_code == 201
    assert sale_response.json()["ba_id"] == ba["id"]

    # Try to sell the same SIM again (conflict)
    conflict_response = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "serial_number": "5000000000000000001",
            "sold_at": datetime.now(timezone.utc).isoformat(),
            "client_event_id": "client-uuid-456",
        },
    )
    assert conflict_response.status_code == 409

    # Try to sell SIM not assigned to this BA
    unauthorized_response = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "serial_number": "5000000000000000002",  # This SIM is with branch, not BA
            "sold_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert unauthorized_response.status_code == 409


def test_offline_sync_with_idempotency(client):
    """Test offline sync with client event IDs for idempotency."""
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    # Intake and distribute stock
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "box_barcode": "BOX-SYNC-001",
            "first_serial": "6000000000000000001",
            "quantity": 2,
        },
    )
    assert intake.status_code == 201

    distributed = client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "quantity": 1},
    )
    assert distributed.status_code == 200

    # Assign SIM to BA
    assigned = client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"], "serial_numbers": ["6000000000000000001"]},
    )
    assert assigned.status_code == 200

    # Get BA token
    ba_token = _login(client, "ba2@example.com", "basecret123")

    # Sync with sale event
    sync_response = client.post(
        "/api/v1/stock/sync",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "events": [
                {
                    "type": "sale",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "serial_number": "6000000000000000001",
                        "sold_at": datetime.now(timezone.utc).isoformat(),
                        "client_event_id": "sync-uuid-789",
                    },
                }
            ],
            "last_synced_at": None,
        },
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["processed_count"] == 1

    # Try to sync the same event again (idempotency)
    sync_again_response = client.post(
        "/api/v1/stock/sync",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "events": [
                {
                    "type": "sale",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "serial_number": "6000000000000000001",
                        "sold_at": datetime.now(timezone.utc).isoformat(),
                        "client_event_id": "sync-uuid-789",  # Same UUID
                    },
                }
            ],
            "last_synced_at": sync_response.json()["new_sync_cursor"],
        },
    )
    assert sync_again_response.status_code == 200
    # Should be rejected as duplicate
    assert sync_again_response.json()["failed_count"] >= 1
