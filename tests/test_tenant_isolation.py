"""Tenant-isolation tests (FR-TEN-02, NFR-02, B-10-03).

Verifies that a dealer's data is never visible or writable by another
dealer's users. Two fully-populated dealers (A and B) are created; every
read endpoint is exercised with dealer A's token and we assert that none
of dealer B's rows leak through.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from simcards_backend.models import SubjectType


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _serial(serial_first, offset):
    return str(int(serial_first) + offset).zfill(len(str(serial_first)))


def _seed_dealer(client, *, dealer_name, shortcode, serial_first, hq_email, hq_password, ba_email):
    """Create a dealer with branch, BA, stock, target, rule, and a sale.

    Serial numbers must be globally unique, so each dealer seeds a distinct
    numeric range. Returns a dict of tokens and entity ids for cross-referencing.
    """
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": dealer_name,
            "safaricom_dealer_shortcode": shortcode,
            "hq_email": hq_email,
            "hq_password": hq_password,
        },
    )
    assert signup.status_code == 201
    dealer_id = signup.json()["dealer_id"]
    hq_token = _login(client, hq_email, hq_password)

    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": f"{dealer_name} Branch",
            "type": "SHOP",
            "id_number": f"{shortcode}-BR",
            "photo_url": "https://example.com/branch.jpg",
            "email": f"{shortcode.lower()}@branch.example.com",
            "password": "branchsecret",
        },
    )
    assert branch.status_code == 201
    branch_id = branch.json()["id"]
    branch_token = _login(client, f"{shortcode.lower()}@branch.example.com", "branchsecret")

    ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": f"{dealer_name} BA",
            "email": ba_email,
            "password": "basecret123",
            "phone_msisdn": "254700000017",
            "id_number": f"{shortcode}-BA",
            "photo_url": "https://example.com/ba.jpg",
        },
    )
    assert ba.status_code == 201
    ba_id = ba.json()["id"]
    ba_token = _login(client, ba_email, "basecret123")

    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "box_barcode": f"{shortcode}-BOX",
            "first_serial": serial_first,
            "quantity": 3,
        },
    )
    assert intake.status_code == 201

    distribute = client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch_id, "quantity": 2},
    )
    assert distribute.status_code == 200

    assign = client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba_id, "serial_numbers": [_serial(serial_first, 0)]},
    )
    assert assign.status_code == 200

    target = client.post(
        "/api/v1/commission/targets",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "branch_id": branch_id,
            "period_type": "DAILY",
            "quantity": 10,
            "effective_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert target.status_code == 201

    rule = client.post(
        "/api/v1/commission/rules",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": f"{dealer_name} Commission",
            "amount_per_sim": "50.00",
            "effective_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert rule.status_code == 201

    sale = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "serial_number": _serial(serial_first, 0),
            "sold_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert sale.status_code == 201

    return {
        "dealer_id": dealer_id,
        "hq_token": hq_token,
        "branch_id": branch_id,
        "ba_id": ba_id,
        "ba_email": ba_email,
        "shortcode": shortcode,
        "serial_numbers": {
            "sold": _serial(serial_first, 0),
            "with_ba": _serial(serial_first, 1),
            "in_hq": _serial(serial_first, 2),
        },
    }


def _setup_two_dealers(client):
    dealer_a = _seed_dealer(
        client,
        dealer_name="Isolation Dealer A",
        shortcode="ISOA",
        serial_first="7000000000000000101",
        hq_email="iso-a@example.com",
        hq_password="supersecret",
        ba_email="iso-ba-a@example.com",
    )
    dealer_b = _seed_dealer(
        client,
        dealer_name="Isolation Dealer B",
        shortcode="ISOB",
        serial_first="8000000000000000101",
        hq_email="iso-b@example.com",
        hq_password="supersecret",
        ba_email="iso-ba-b@example.com",
    )
    return dealer_a, dealer_b


def test_onboarding_returns_distinct_dealer_ids(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    assert dealer_a["dealer_id"] != dealer_b["dealer_id"]


def test_branches_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/branches", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    ids = [b["id"] for b in response.json()]
    dealer_ids = {b["dealer_id"] for b in response.json()}
    assert dealer_a["branch_id"] in ids
    assert dealer_b["branch_id"] not in ids
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_brand_ambassadors_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/brand-ambassadors", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    ids = [ba["id"] for ba in response.json()]
    dealer_ids = {ba["dealer_id"] for ba in response.json()}
    assert dealer_a["ba_id"] in ids
    assert dealer_b["ba_id"] not in ids
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_stock_sim_cards_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/stock/sim-cards", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    serials = {sim["serial_number"] for sim in response.json()}
    dealer_ids = {sim["dealer_id"] for sim in response.json()}
    assert dealer_a["serial_numbers"]["sold"] in serials
    assert dealer_b["serial_numbers"]["sold"] not in serials
    assert dealer_b["serial_numbers"]["with_ba"] not in serials
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_sales_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/stock/sales", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    sales = response.json()
    ba_ids = {sale["ba_id"] for sale in sales}
    dealer_ids = {sale["dealer_id"] for sale in sales}
    assert dealer_a["ba_id"] in ba_ids
    assert dealer_b["ba_id"] not in ba_ids
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_commission_targets_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/commission/targets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    targets = response.json()
    branch_ids = {t["branch_id"] for t in targets}
    dealer_ids = {t["dealer_id"] for t in targets}
    assert dealer_a["branch_id"] in branch_ids
    assert dealer_b["branch_id"] not in branch_ids
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_commission_rules_are_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/commission/rules", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    rules = response.json()
    dealer_ids = {r["dealer_id"] for r in rules}
    assert dealer_ids == {dealer_a["dealer_id"]}


def test_commission_earned_is_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get(
        "/api/v1/commission/earned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    # Dealer A has exactly ONE sale at 50.00; Dealer B's sale must not leak in.
    assert float(response.json()["total_commission"]) == 50.0


def test_branch_summary_is_isolated(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get("/api/v1/commission/branch-summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    summaries = body["branches"] if "branches" in body else [body]
    branch_ids = {s["branch_id"] for s in summaries}
    assert dealer_a["branch_id"] in branch_ids
    assert dealer_b["branch_id"] not in branch_ids


def test_dealer_performance_snapshot_ignores_other_dealer_targets(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    today = date.today()
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "subject_type": SubjectType.DEALER.value,
            "subject_id": dealer_a["dealer_id"],
            "period_type": "DAILY",
            "period_start": today.isoformat(),
            "period_end": today.isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dealer_id"] == dealer_a["dealer_id"]
    # Only dealer A's branch target (10) counts; dealer B's target (10) must not.
    assert body["target_quantity"] == 10
    assert body["actual_sold_quantity"] == 1


def test_branch_performance_snapshot_is_scoped_by_dealer(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    today = date.today()
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "subject_type": SubjectType.BRANCH.value,
            "subject_id": dealer_a["branch_id"],
            "period_type": "DAILY",
            "period_start": today.isoformat(),
            "period_end": today.isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dealer_id"] == dealer_a["dealer_id"]
    assert body["target_quantity"] == 10


def test_report_does_not_include_other_dealer_data(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    today = datetime.now(timezone.utc).date()
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "period_type": "DAILY",
            "period_start": today.isoformat(),
            "period_end": today.isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    branch_ids = [b["branch_id"] for b in body["branch_reports"]]
    assert dealer_a["branch_id"] in branch_ids
    assert dealer_b["branch_id"] not in branch_ids
    assert body["total_sales_count"] == 1


def test_cannot_list_other_dealers_branches_via_summary(client):
    dealer_a, dealer_b = _setup_two_dealers(client)
    token = dealer_a["hq_token"]
    response = client.get(
        "/api/v1/commission/branch-summary",
        headers={"Authorization": f"Bearer {token}"},
        params={"branch_id": dealer_b["branch_id"]},
    )
    # A non-existent / foreign branch in A's dealer scope -> empty result.
    assert response.status_code == 200
    assert response.json() == {"branches": []}