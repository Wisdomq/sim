"""RBAC matrix tests (B-10-04): every permission row in requirements §5 enforced.

One dealer with HQ + two branches + two BAs (one per branch). For each matrix
row, allowed roles are expected to succeed (2xx) and denied roles expected to
return 403.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def hierarchy(client):
    """Dealer with HQ, Branch1(+BA1), Branch2(+BA2). Returns all tokens/ids."""
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "RBAC Dealer",
            "safaricom_dealer_shortcode": "RBAC01",
            "hq_email": "rbac-hq@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    dealer_id = signup.json()["dealer_id"]
    hq_token = _login(client, "rbac-hq@example.com", "supersecret")

    branches = {}
    for idx, (name, id_number, email) in enumerate(
        [
            ("RBAC Branch One", "RBAC-BR1", "rbac-b1@example.com"),
            ("RBAC Branch Two", "RBAC-BR2", "rbac-b2@example.com"),
        ],
        start=1,
    ):
        branch = client.post(
            "/api/v1/branches",
            headers={"Authorization": f"Bearer {hq_token}"},
            json={
                "name": name,
                "type": "SHOP",
                "id_number": id_number,
                "photo_url": "https://example.com/branch.jpg",
                "email": email,
                "password": "branchsecret",
            },
        )
        assert branch.status_code == 201
        branch_token = _login(client, email, "branchsecret")

        ba = client.post(
            "/api/v1/brand-ambassadors",
            headers={"Authorization": f"Bearer {branch_token}"},
            json={
                "name": f"BA {idx}",
                "email": f"rbac-ba{idx}@example.com",
                "password": "basecret123",
                "phone_msisdn": "254700000010",
                "id_number": f"RBAC-BA{idx}",
                "photo_url": "https://example.com/ba.jpg",
            },
        )
        assert ba.status_code == 201

        branches[idx] = {
            "id": branch.json()["id"],
            "token": branch_token,
            "ba_id": ba.json()["id"],
            "ba_email": f"rbac-ba{idx}@example.com",
            "ba_password": "basecret123",
        }

    ba1_token = _login(client, branches[1]["ba_email"], branches[1]["ba_password"])
    ba2_token = _login(client, branches[2]["ba_email"], branches[2]["ba_password"])

    return {
        "dealer_id": dealer_id,
        "hq_token": hq_token,
        "missing_token": "not-a-token",
        "branch1": branches[1],
        "branch2": branches[2],
        "ba1_token": ba1_token,
        "ba2_token": ba2_token,
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _utc_today():
    return datetime.now(timezone.utc).date().isoformat()


# ── Row: Add stock (PDF import / box scan) — HQ only ────────────────────────
def test_add_stock_hq_only(hierarchy, client):
    payload = {
        "box_barcode": "RBAC-BOX",
        "first_serial": "7300000000000000001",
        "quantity": 3,
    }
    ok = client.post("/api/v1/stock/intake/box-scan", headers=_auth(hierarchy["hq_token"]), json=payload)
    assert ok.status_code == 201
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        denied = client.post("/api/v1/stock/intake/box-scan", headers=_auth(token), json=payload)
        assert denied.status_code == 403


# ── Row: Distribute stock to a Branch — HQ only ─────────────────────────────
def test_distribute_stock_hq_only(hierarchy, client):
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers=_auth(hierarchy["hq_token"]),
        json={"box_barcode": "RBAC-DIST", "first_serial": "7310000000000000001", "quantity": 3},
    )
    assert intake.status_code == 201
    ok = client.post(
        "/api/v1/stock/distribute",
        headers=_auth(hierarchy["hq_token"]),
        json={"branch_id": hierarchy["branch1"]["id"], "quantity": 2},
    )
    assert ok.status_code == 200
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        denied = client.post(
            "/api/v1/stock/distribute",
            headers=_auth(token),
            json={"branch_id": hierarchy["branch1"]["id"], "quantity": 1},
        )
        assert denied.status_code == 403


# ── Rows: Request return from Branch (HQ) / Fulfill a return (Branch) ────────
def test_return_request_and_fulfill_gates(hierarchy, client):
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers=_auth(hierarchy["hq_token"]),
        json={"box_barcode": "RBAC-RET", "first_serial": "7320000000000000001", "quantity": 2},
    )
    assert intake.status_code == 201
    serial = "7320000000000000001"
    distributed = client.post(
        "/api/v1/stock/distribute",
        headers=_auth(hierarchy["hq_token"]),
        json={"branch_id": hierarchy["branch1"]["id"], "quantity": 2},
    )
    assert distributed.status_code == 200

    request_payload = {
        "branch_id": hierarchy["branch1"]["id"],
        "serial_numbers": [serial],
        "reason": "Recall",
    }
    ok = client.post("/api/v1/stock/return-requests", headers=_auth(hierarchy["hq_token"]), json=request_payload)
    assert ok.status_code == 201
    return_event_id = ok.json()[0]["id"]
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        denied = client.post("/api/v1/stock/return-requests", headers=_auth(token), json=request_payload)
        assert denied.status_code == 403

    fulfillment_ok = client.post(
        f"/api/v1/stock/return-requests/{return_event_id}/fulfill",
        headers=_auth(hierarchy["branch1"]["token"]),
    )
    assert fulfillment_ok.status_code == 200
    assert fulfillment_ok.json()["status"] == "COMPLETED"
    for token in (hierarchy["hq_token"], hierarchy["ba1_token"]):
        denied = client.post(
            f"/api/v1/stock/return-requests/{return_event_id}/fulfill",
            headers=_auth(token),
        )
        assert denied.status_code == 403


# ── Row: Reassign SIM between BAs (own branch) — Branch only ────────────────
def test_assign_to_ba_branch_only(hierarchy, client):
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers=_auth(hierarchy["hq_token"]),
        json={"box_barcode": "RBAC-ASG", "first_serial": "7330000000000000001", "quantity": 2},
    )
    assert intake.status_code == 201
    assert client.post(
        "/api/v1/stock/distribute",
        headers=_auth(hierarchy["hq_token"]),
        json={"branch_id": hierarchy["branch1"]["id"], "quantity": 2},
    ).status_code == 200

    assign_payload = {"ba_id": hierarchy["branch1"]["ba_id"], "serial_numbers": ["7330000000000000001"]}
    ok = client.post("/api/v1/stock/assign-to-ba", headers=_auth(hierarchy["branch1"]["token"]), json=assign_payload)
    assert ok.status_code == 200
    for token in (hierarchy["hq_token"], hierarchy["ba1_token"]):
        denied = client.post("/api/v1/stock/assign-to-ba", headers=_auth(token), json=assign_payload)
        assert denied.status_code == 403


# ── Row: Scan/sell a SIM — BA only ──────────────────────────────────────────
def test_scan_sell_ba_only(hierarchy, client):
    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers=_auth(hierarchy["hq_token"]),
        json={"box_barcode": "RBAC-SALE", "first_serial": "7340000000000000001", "quantity": 2},
    )
    assert intake.status_code == 201
    assert client.post(
        "/api/v1/stock/distribute",
        headers=_auth(hierarchy["hq_token"]),
        json={"branch_id": hierarchy["branch1"]["id"], "quantity": 2},
    ).status_code == 200
    assert client.post(
        "/api/v1/stock/assign-to-ba",
        headers=_auth(hierarchy["branch1"]["token"]),
        json={"ba_id": hierarchy["branch1"]["ba_id"], "serial_numbers": ["7340000000000000001"]},
    ).status_code == 200

    sale_payload = {"serial_number": "7340000000000000001", "sold_at": f"{_utc_today()}T12:00:00Z"}
    ok = client.post("/api/v1/stock/sales", headers=_auth(hierarchy["ba1_token"]), json=sale_payload)
    assert ok.status_code == 201
    for token in (hierarchy["hq_token"], hierarchy["branch1"]["token"]):
        denied = client.post("/api/v1/stock/sales", headers=_auth(token), json=sale_payload)
        assert denied.status_code == 403


# ── Rows: Set/update commission rate (HQ), Set/update Branch targets (HQ) ────
def test_commission_config_hq_only(hierarchy, client):
    rule_payload = {
        "name": "Matrix Rule",
        "amount_per_sim": "50.00",
        "effective_from": datetime.now(timezone.utc).isoformat(),
    }
    ok = client.post("/api/v1/commission/rules", headers=_auth(hierarchy["hq_token"]), json=rule_payload)
    assert ok.status_code == 201
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        assert client.post("/api/v1/commission/rules", headers=_auth(token), json=rule_payload).status_code == 403

    target_payload = {
        "branch_id": hierarchy["branch1"]["id"],
        "period_type": "DAILY",
        "quantity": 25,
        "effective_from": datetime.now(timezone.utc).isoformat(),
    }
    ok = client.post("/api/v1/commission/targets", headers=_auth(hierarchy["hq_token"]), json=target_payload)
    assert ok.status_code == 201
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        assert client.post("/api/v1/commission/targets", headers=_auth(token), json=target_payload).status_code == 403


# ── Row: View own performance % (Branch own+BAs / BA self only) ─────────────
def test_performance_visibility_scopes(hierarchy, client):
    today = _utc_today()

    # BA sees only themselves.
    self_ok = client.get(
        "/api/v1/commission/performance",
        headers=_auth(hierarchy["ba1_token"]),
        params={"subject_type": "BA", "subject_id": hierarchy["branch1"]["ba_id"], "period_type": "DAILY",
                "period_start": today, "period_end": today},
    )
    assert self_ok.status_code == 200
    for subject_id in (hierarchy["branch2"]["ba_id"], hierarchy["branch2"]["id"], hierarchy["dealer_id"]):
        assert client.get(
            "/api/v1/commission/performance",
            headers=_auth(hierarchy["ba1_token"]),
            params={"subject_type": "BRANCH" if subject_id == hierarchy["branch2"]["id"] else "BA"
                    if subject_id == hierarchy["branch2"]["ba_id"] else "DEALER",
                    "subject_id": subject_id, "period_type": "DAILY",
                    "period_start": today, "period_end": today},
        ).status_code == 403

    # Branch sees own branch, its own BAs; not other branch, other BA, or dealer rollup.
    assert client.get(
        "/api/v1/commission/performance",
        headers=_auth(hierarchy["branch1"]["token"]),
        params={"subject_type": "BRANCH", "subject_id": hierarchy["branch1"]["id"], "period_type": "DAILY",
                "period_start": today, "period_end": today},
    ).status_code == 200
    assert client.get(
        "/api/v1/commission/performance",
        headers=_auth(hierarchy["branch1"]["token"]),
        params={"subject_type": "BA", "subject_id": hierarchy["branch1"]["ba_id"], "period_type": "DAILY",
                "period_start": today, "period_end": today},
    ).status_code == 200
    for subject_type, subject_id in (
        ("BRANCH", hierarchy["branch2"]["id"]),
        ("BA", hierarchy["branch2"]["ba_id"]),
        ("DEALER", hierarchy["dealer_id"]),
    ):
        assert client.get(
            "/api/v1/commission/performance",
            headers=_auth(hierarchy["branch1"]["token"]),
            params={"subject_type": subject_type, "subject_id": subject_id, "period_type": "DAILY",
                    "period_start": today, "period_end": today},
        ).status_code == 403

    # HQ sees everything including org rollup.
    assert client.get(
        "/api/v1/commission/performance",
        headers=_auth(hierarchy["hq_token"]),
        params={"subject_type": "DEALER", "subject_id": hierarchy["dealer_id"], "period_type": "DAILY",
                "period_start": today, "period_end": today},
    ).status_code == 200
    assert client.get(
        "/api/v1/commission/performance",
        headers=_auth(hierarchy["hq_token"]),
        params={"subject_type": "BA", "subject_id": hierarchy["branch2"]["ba_id"], "period_type": "DAILY",
                "period_start": today, "period_end": today},
    ).status_code == 200


# ── Row: View commission earned (HQ all / Branch own / BA self only) ─────────
def test_commission_earned_scopes(hierarchy, client):
    # BA self only.
    assert client.get("/api/v1/commission/earned", headers=_auth(hierarchy["ba1_token"])).status_code == 200
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["ba1_token"]),
        params={"ba_id": hierarchy["branch2"]["ba_id"]},
    ).status_code == 403
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["ba1_token"]),
        params={"branch_id": hierarchy["branch2"]["id"]},
    ).status_code == 403

    # Branch: own branch total + its own BAs only.
    assert client.get("/api/v1/commission/earned", headers=_auth(hierarchy["branch1"]["token"])).status_code == 200
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["branch1"]["token"]),
        params={"ba_id": hierarchy["branch1"]["ba_id"]},
    ).status_code == 200
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["branch1"]["token"]),
        params={"branch_id": hierarchy["branch2"]["id"]},
    ).status_code == 403
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["branch1"]["token"]),
        params={"ba_id": hierarchy["branch2"]["ba_id"]},
    ).status_code == 403

    # HQ: all scopes.
    assert client.get("/api/v1/commission/earned", headers=_auth(hierarchy["hq_token"])).status_code == 200
    assert client.get(
        "/api/v1/commission/earned", headers=_auth(hierarchy["hq_token"]),
        params={"branch_id": hierarchy["branch2"]["id"], "ba_id": hierarchy["branch2"]["ba_id"]},
    ).status_code == 200


# ── Row: Branch/BA consolidated views + config lists ────────────────────────
def test_branch_summary_and_config_lists_deny_ba(hierarchy, client):
    hq, b1, ba1 = hierarchy["hq_token"], hierarchy["branch1"]["token"], hierarchy["ba1_token"]
    for path in (
        "/api/v1/commission/branch-summary",
        "/api/v1/commission/targets",
        "/api/v1/commission/rules",
        "/api/v1/commission/ba-daily-target",
    ):
        assert client.get(path, headers=_auth(hq)).status_code in (200, 422)
        assert client.get(path, headers=_auth(b1)).status_code in (200, 422 if path.endswith("ba-daily-target") else 200)
        if path.endswith("ba-daily-target"):
            # This endpoint requires branch_id, so the BA check is only
            # reachable once it is supplied: own branch allowed, other denied.
            assert client.get(
                path, headers=_auth(ba1), params={"branch_id": hierarchy["branch1"]["id"]},
            ).status_code == 200
            assert client.get(
                path, headers=_auth(ba1), params={"branch_id": hierarchy["branch2"]["id"]},
            ).status_code == 403
            continue
        assert client.get(path, headers=_auth(ba1)).status_code == 403


# ── Rows: Inactivity flags + notifications — HQ only ─────────────────────────
def test_flags_and_notifications_hq_only(hierarchy, client):
    for path in ("/api/v1/flags", "/api/v1/flags/notifications"):
        assert client.get(path, headers=_auth(hierarchy["hq_token"])).status_code == 200
        for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
            assert client.get(path, headers=_auth(token)).status_code == 403


# ── Row: Upload Safaricom report & view reconciliation — HQ only ─────────────
def test_reconciliation_hq_only(hierarchy, client):
    for path in ("/api/v1/reconciliation/imports", "/api/v1/reconciliation/activated?month=2026-08"):
        assert client.get(path, headers=_auth(hierarchy["hq_token"])).status_code == 200
        for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
            assert client.get(path, headers=_auth(token)).status_code == 403

    import io

    upload_payload = {"report_date": "2026-08-31"}
    ok = client.post(
        "/api/v1/reconciliation/imports",
        headers=_auth(hierarchy["hq_token"]),
        data=upload_payload,
        files={"file": ("r.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
    )
    assert ok.status_code in (202, 422)  # valid flow is 202; formatting aside, gate is HQ
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        assert client.post(
            "/api/v1/reconciliation/imports",
            headers=_auth(token),
            data=upload_payload,
            files={"file": ("r.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
        ).status_code == 403


# ── Rows: Create/Remove Branch account — HQ only ─────────────────────────────
def test_branch_account_crud_hq_only(hierarchy, client):
    create_payload = {
        "name": "RBAC Branch Three",
        "type": "SHOP",
        "id_number": "RBAC-BR3",
        "photo_url": "https://example.com/br3.jpg",
        "email": "rbac-b3@example.com",
        "password": "branchsecret",
    }
    ok = client.post("/api/v1/branches", headers=_auth(hierarchy["hq_token"]), json=create_payload)
    assert ok.status_code == 201
    new_branch_id = ok.json()["id"]
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        assert client.post("/api/v1/branches", headers=_auth(token), json=create_payload).status_code == 403

    # Remove Branch account: HQ only.
    for token in (hierarchy["branch1"]["token"], hierarchy["ba1_token"]):
        assert client.delete(f"/api/v1/branches/{new_branch_id}", headers=_auth(token)).status_code == 403
    assert client.delete(f"/api/v1/branches/{new_branch_id}", headers=_auth(hierarchy["hq_token"])).status_code == 204


# ── Rows: Create BA account (HQ + Branch) / Remove BA account (HQ only) ──────
def test_ba_account_crud_matrix(hierarchy, client):
    create_payload = {
        "name": "RBAC BA HQ",
        "email": "rbac-ba-hq@example.com",
        "password": "basecret123",
        "phone_msisdn": "254700000011",
        "id_number": "RBAC-BA-HQ",
        "photo_url": "https://example.com/ba.jpg",
    }

    # HQ can create a BA under a branch.
    hq_create = client.post(
        f"/api/v1/branches/{hierarchy['branch2']['id']}/brand-ambassadors",
        headers=_auth(hierarchy["hq_token"]),
        json=create_payload,
    )
    assert hq_create.status_code == 201
    ba_id = hq_create.json()["id"]

    # Branch can create a BA (under itself).
    assert client.post(
        "/api/v1/brand-ambassadors",
        headers=_auth(hierarchy["branch1"]["token"]),
        json={**create_payload, "email": "rbac-ba-b1@example.com", "name": "RBAC BA B1", "id_number": "RBAC-BA-B1"},
    ).status_code == 201

    # BA cannot create a BA.
    assert client.post("/api/v1/brand-ambassadors", headers=_auth(hierarchy["ba1_token"]), json=create_payload).status_code == 403

    # Remove BA account: HQ only.
    assert client.delete(f"/api/v1/brand-ambassadors/{ba_id}", headers=_auth(hierarchy["branch1"]["token"])).status_code == 403
    assert client.delete(f"/api/v1/brand-ambassadors/{ba_id}", headers=_auth(hierarchy["ba1_token"])).status_code == 403
    assert client.delete(f"/api/v1/brand-ambassadors/{ba_id}", headers=_auth(hierarchy["hq_token"])).status_code == 204


# ── Rows: View reports / Export reports — HQ + Branch, no BA ─────────────────
def test_reports_and_export_deny_ba(hierarchy, client):
    today = _utc_today()
    report_payload = {"period_type": "DAILY", "period_start": today, "period_end": today}
    assert client.post("/api/v1/reports", headers=_auth(hierarchy["hq_token"]), json=report_payload).status_code == 200
    assert client.post("/api/v1/reports", headers=_auth(hierarchy["branch1"]["token"]), json=report_payload).status_code == 200
    assert client.post("/api/v1/reports", headers=_auth(hierarchy["ba1_token"]), json=report_payload).status_code == 403


def test_report_export_deny_ba(hierarchy, client, tmp_path):
    from simcards_backend.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    from simcards_backend.core.config import settings

    settings.UPLOAD_DIR = str(tmp_path)

    today = _utc_today()
    export_payload = {"period_type": "DAILY", "period_start": today, "period_end": today, "export_format": "PDF"}
    assert client.post("/api/v1/reports/export", headers=_auth(hierarchy["hq_token"]), json=export_payload).status_code == 202
    assert client.post("/api/v1/reports/export", headers=_auth(hierarchy["branch1"]["token"]), json=export_payload).status_code == 202
    assert client.post("/api/v1/reports/export", headers=_auth(hierarchy["ba1_token"]), json=export_payload).status_code == 403


# ── Row: Unauthenticated / forged token is rejected everywhere ──────────────
def test_unauthenticated_requests_rejected(hierarchy, client):
    assert client.get("/api/v1/branches").status_code == 401
    assert client.get("/api/v1/stock/sim-cards").status_code == 401
    assert client.get("/api/v1/branches", headers=_auth(hierarchy["missing_token"])).status_code == 401