"""Acceptance-Criteria tests: AC-1 … AC-9 (requirements §7).

Each test is self-contained against the local test client and follows the
existing helper patterns used across the suite.
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from simcards_backend.core.database import SessionLocal
from simcards_backend.core.security import hash_password, now_utc
from simcards_backend.models import (
    AccountFlag,
    AccountStatus,
    BrandAmbassador,
    Branch,
    BranchType,
    CommissionRule,
    Dealer,
    LoginEvent,
    Role,
    SafaricomImport,
    SafaricomImportStatus,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    Target,
    PeriodType,
    User,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _signup(client, dealer="AC Dealer", code="AC001", email="hq@ac.example.com"):
    r = client.post(
        "/api/v1/onboarding/dealers",
        json={"dealer_name": dealer, "safaricom_dealer_shortcode": code,
              "hq_email": email, "hq_password": "supersecret"},
    )
    assert r.status_code == 201
    return _login(client, email, "supersecret")


def _create_branch(client, hq_token, branch_email="branch@ac.example.com",
                   branch_name="Branch A", branch_id_num="AC-BR-001"):
    r = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": branch_name, "type": "SHOP", "id_number": branch_id_num,
              "photo_url": "https://example.com/branch.jpg",
              "email": branch_email, "password": "branchsecret"},
    )
    assert r.status_code == 201
    return r.json()


def _create_ba(client, branch_token, branch_id, ba_email="ba@ac.example.com",
               ba_name="BA One", ba_id_num="AC-BA-001"):
    r = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": ba_name, "email": ba_email, "password": "basecret123",
              "phone_msisdn": "254700000100", "id_number": ba_id_num,
              "photo_url": "https://example.com/ba.jpg"},
    )
    assert r.status_code == 201
    return r.json()


def _setup_full(client, *, dealer_email="hq@ac.example.com",
                branch_email="branch@ac.example.com", ba_email="ba@ac.example.com"):
    hq_token = _signup(client, email=dealer_email)
    branch = _create_branch(client, hq_token, branch_email=branch_email)
    branch_token = _login(client, branch_email, "branchsecret")
    ba = _create_ba(client, branch_token, branch["id"], ba_email=ba_email)
    return hq_token, branch_token, branch, ba


def _seed_commission_rule(db, dealer_id, hq_user_id, amount="15.00"):
    now = datetime.now(timezone.utc)
    rule = CommissionRule(
        dealer_id=dealer_id, name="AC Commission", amount_per_sim=amount,
        effective_from=now, created_by_id=hq_user_id,
    )
    db.add(rule)
    db.flush()
    return rule


# ── AC-1  PDF pick-list import creates serials as IN_HQ_STOCK ──────────────

def _make_pick_list_pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    c.drawString(50, 750, "<<Lot>> LOT_AC_001")
    c.drawString(50, 730, "1000000000000000001")
    c.drawString(50, 710, "1000000000000000002")
    c.drawString(50, 690, "<<Lot>> LOT_AC_002")
    c.drawString(50, 670, "1000000000000000003")
    c.save()
    return buf.getvalue()


def test_ac1_pdf_pick_list_import_creates_in_hq_stock(client, tmp_path):
    from simcards_backend.celery_app import celery_app
    from simcards_backend.core.config import settings

    celery_app.conf.task_always_eager = True
    settings.UPLOAD_DIR = str(tmp_path)

    hq_token = _signup(client, dealer="AC1 Dealer", code="AC100",
                       email="hq@ac1.example.com")
    headers = {"Authorization": f"Bearer {hq_token}"}

    pdf_bytes = _make_pick_list_pdf()
    resp = client.post(
        "/api/v1/stock/intake/pick-list-pdf",
        headers=headers,
        files={"file": ("pick_list.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]
    assert task_id

    with SessionLocal() as db:
        hq_user = db.scalar(select(User).where(User.email == "hq@ac1.example.com"))
        sims = list(db.scalars(
            select(SimCard).where(SimCard.dealer_id == hq_user.dealer_id)
        ))
        serials = {s.serial_number for s in sims}
        assert serials == {
            "1000000000000000001",
            "1000000000000000002",
            "1000000000000000003",
        }
        assert all(s.status == SimStatus.IN_HQ_STOCK for s in sims)


# ── AC-2  BA scans assigned SIM → SOLD, attributed to BA+branch ───────────

def test_ac2_ba_scan_sold_attribution(client):
    hq_token, branch_token, branch, ba = _setup_full(client)
    ba_token = _login(client, "ba@ac.example.com", "basecret123")

    intake = client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"box_barcode": "AC2-BOX", "first_serial": "2000000000000000001",
              "quantity": 2, "expiry_date": (date.today() + timedelta(days=30)).isoformat()},
    )
    assert intake.status_code == 201

    client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "serial_numbers": ["2000000000000000001"]},
    )
    client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"], "serial_numbers": ["2000000000000000001"]},
    )

    sale_resp = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={"serial_number": "2000000000000000001",
              "sold_at": datetime.now(timezone.utc).isoformat(),
              "client_event_id": "ac2-sale-001"},
    )
    assert sale_resp.status_code == 201
    body = sale_resp.json()
    assert body["ba_id"] == ba["id"]
    assert body["branch_id"] == branch["id"]

    with SessionLocal() as db:
        sim = db.scalar(
            select(SimCard).where(SimCard.serial_number == "2000000000000000001")
        )
        assert sim.status == SimStatus.SOLD


# ── AC-3  Double-scan same SIM → only first accepted, second 409 ──────────

def test_ac3_double_scan_conflict(client):
    hq_token, branch_token, branch, ba = _setup_full(client)
    ba_token = _login(client, "ba@ac.example.com", "basecret123")

    client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"box_barcode": "AC3-BOX", "first_serial": "3000000000000000001",
              "quantity": 1},
    )
    client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "serial_numbers": ["3000000000000000001"]},
    )
    client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"], "serial_numbers": ["3000000000000000001"]},
    )

    first = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={"serial_number": "3000000000000000001",
              "sold_at": datetime.now(timezone.utc).isoformat(),
              "client_event_id": "ac3-sale-001"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={"serial_number": "3000000000000000001",
              "sold_at": datetime.now(timezone.utc).isoformat(),
              "client_event_id": "ac3-sale-002"},
    )
    assert second.status_code == 409


# ── AC-4  Reconciliation summary: headline numbers first ──────────────────

def _seed_sold_sim_for_recon(db, *, dealer, batch, branch, ba, serial):
    sim = SimCard(
        dealer_id=dealer.id, serial_number=serial, stock_batch_id=batch.id,
        status=SimStatus.SOLD, current_branch_id=branch.id, current_ba_id=ba.id,
    )
    db.add(sim)
    db.flush()
    from simcards_backend.models import SaleEvent, ScannedVia
    db.add(SaleEvent(
        dealer_id=dealer.id, sim_card_id=sim.id, ba_id=ba.id, branch_id=branch.id,
        sold_at=now_utc(), scanned_via=ScannedVia.CAMERA,
    ))
    return sim


def test_ac4_reconciliation_summary_first(client, tmp_path):
    from simcards_backend.celery_app import celery_app
    from simcards_backend.core.config import settings

    celery_app.conf.task_always_eager = True
    settings.UPLOAD_DIR = str(tmp_path)

    hq_token = _signup(client, dealer="AC4 Recon Dealer", code="AC400",
                       email="hq@ac4.example.com")
    headers = {"Authorization": f"Bearer {hq_token}"}

    import openpyxl
    header = ["TM Date", "ID Date", "ID Month", "Dealer Shortcode", "Dealer Name",
              "Sim Serial Number", "Top Up Date", "Top Up Amount", "Agent MSISDN",
              "BA", "Region", "Territory", "Cluster", "Cumulative Usage",
              "Cumulative Commission", "Fraud Flagged", "Fraud Suspension Date",
              "Fraud Reason", "Role", "Quality"]

    def _row(serial, top_up_date="-", amount="-", commission="-", fraud="N", reason="-"):
        return ["2026-08-01"] * 5 + [serial, top_up_date, amount, "254700000000",
                "BA", "Region", "Territory", "Cluster", "100.0",
                commission, fraud, "-", reason, "role", "quality"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    ws.append(_row("4000000000000000001", "20260831", "50.0", "120.0", "N"))
    ws.append(_row("4000000000000000002", "-", "-", "0.0", "Y", "Suspicious"))
    xlsx_path = tmp_path / "recon.xlsx"
    wb.save(xlsx_path)

    with open(xlsx_path, "rb") as fh:
        upload = client.post(
            "/api/v1/reconciliation/imports",
            headers=headers,
            data={"report_date": "2026-08-31"},
            files={"file": ("recon.xlsx", fh, "application/octet-stream")},
        )
    assert upload.status_code == 202
    import_id = upload.json()["import_id"]

    summary = client.get(f"/api/v1/reconciliation/imports/{import_id}", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert "total_confirmed_activated_by_safaricom" in body
    assert "total_cumulative_commission" in body
    assert "total_fraud_flagged" in body
    assert "total_sold_in_app" in body

    detail = client.get(
        f"/api/v1/reconciliation/imports/{import_id}/detail", headers=headers
    )
    assert detail.status_code == 200
    assert len(detail.json()) == 2


# ── AC-5  Branch cannot remove BA (HQ-only, FR-HQ-11 / FR-BR-07) ──────────

def test_ac5_branch_cannot_remove_ba(client):
    hq_token, branch_token, branch, ba = _setup_full(client)

    forbidden = client.delete(
        f"/api/v1/brand-ambassadors/{ba['id']}",
        headers={"Authorization": f"Bearer {branch_token}"},
    )
    assert forbidden.status_code == 403

    allowed = client.delete(
        f"/api/v1/brand-ambassadors/{ba['id']}",
        headers={"Authorization": f"Bearer {hq_token}"},
    )
    assert allowed.status_code == 204


# ── AC-6  Target derivation: 50 ÷ 5 = 10; +6th BA recalculates forward ────

def test_ac6_target_derivation_mid_period_ba_added(client, tmp_path):
    from simcards_backend.core.config import settings

    hq_token = _signup(client, dealer="AC6 Target Dealer", code="AC600",
                       email="hq@ac6.example.com")

    branch = _create_branch(client, hq_token, branch_email="br@ac6.example.com",
                            branch_name="Target Branch")
    branch_token = _login(client, "br@ac6.example.com", "branchsecret")

    bas = []
    for i in range(1, 6):
        ba = _create_ba(client, branch_token, branch["id"],
                        ba_email=f"ba{i}@ac6.example.com", ba_name=f"BA{i}",
                        ba_id_num=f"AC6-BA-{i}")
        bas.append(ba)

    now = datetime.now(timezone.utc)
    target = client.post(
        "/api/v1/commission/targets",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "period_type": "DAILY",
              "quantity": 50, "effective_from": now.isoformat()},
    )
    assert target.status_code == 201

    ba_target = client.get(
        f"/api/v1/commission/ba-daily-target?branch_id={branch['id']}",
        headers={"Authorization": f"Bearer {hq_token}"},
    )
    assert ba_target.status_code == 200
    assert ba_target.json()["daily_target_per_ba"] == 10

    sixth_ba = _create_ba(client, branch_token, branch["id"],
                          ba_email="ba6@ac6.example.com", ba_name="BA6",
                          ba_id_num="AC6-BA-6")
    ba_target_after = client.get(
        f"/api/v1/commission/ba-daily-target?branch_id={branch['id']}",
        headers={"Authorization": f"Bearer {hq_token}"},
    )
    assert ba_target_after.status_code == 200
    assert ba_target_after.json()["daily_target_per_ba"] == 8  # 50 // 6

    with SessionLocal() as db:
        old_target = db.scalar(
            select(Target).where(
                Target.branch_id == branch["id"],
                Target.period_type == PeriodType.DAILY,
            )
        )
        assert old_target is not None
        assert old_target.quantity == 50


# ── AC-7  Performance percentage: 7/10 sold → 70%, rolls up correctly ─────

def test_ac7_performance_percentage_rollup(client):
    hq_token, branch_token, branch, ba = _setup_full(client)

    client.post(
        "/api/v1/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"box_barcode": "AC7-BOX", "first_serial": "7000000000000000001",
              "quantity": 10},
    )
    client.post(
        "/api/v1/stock/distribute",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "quantity": 10},
    )
    client.post(
        "/api/v1/stock/assign-to-ba",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"ba_id": ba["id"],
              "serial_numbers": [f"7000000000000000{i:03d}" for i in range(1, 11)]},
    )

    now = datetime.now(timezone.utc)
    client.post(
        "/api/v1/commission/targets",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"branch_id": branch["id"], "period_type": "DAILY",
              "quantity": 10, "effective_from": now.isoformat()},
    )

    ba_token = _login(client, "ba@ac.example.com", "basecret123")
    for i in range(1, 8):
        serial = f"7000000000000000{i:03d}"
        client.post(
            "/api/v1/stock/sales",
            headers={"Authorization": f"Bearer {ba_token}"},
            json={"serial_number": serial,
                  "sold_at": datetime.now().isoformat(),
                  "client_event_id": f"ac7-sale-{i:03d}"},
        )

    today = date.today()
    ba_perf = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {hq_token}"},
        params={"subject_type": "BA", "subject_id": ba["id"],
                "period_type": "DAILY",
                "period_start": today.isoformat(), "period_end": today.isoformat()},
    )
    assert ba_perf.status_code == 200
    pct = float(ba_perf.json()["percentage_achieved"])
    assert pct == 70.0

    branch_perf = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {hq_token}"},
        params={"subject_type": "BRANCH", "subject_id": branch["id"],
                "period_type": "DAILY",
                "period_start": today.isoformat(), "period_end": today.isoformat()},
    )
    assert branch_perf.status_code == 200
    assert float(branch_perf.json()["percentage_achieved"]) == 70.0

    dealer_perf = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {hq_token}"},
        params={"subject_type": "DEALER", "subject_id": branch["id"],
                "period_type": "DAILY",
                "period_start": today.isoformat(), "period_end": today.isoformat()},
    )
    assert dealer_perf.status_code == 200


# ── AC-8  3-day inactivity → flag + HQ notification (autoclear on login) ──

def test_ac8_inactivity_flag_and_hq_notification(client):
    from simcards_backend.services.inactivity import default_cutoff, flag_inactive_accounts

    hq_token, branch_token, branch, ba = _setup_full(client)

    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == "branch@ac.example.com"))
        login_event = db.scalars(
            select(LoginEvent).where(LoginEvent.user_id == branch_user.id)
        ).one()
        login_event.logged_in_at = now_utc() - timedelta(days=4)
        db.commit()

        as_of, cutoff = default_cutoff()
        outcome = flag_inactive_accounts(db, dealer_id=branch_user.dealer_id,
                                        cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        assert outcome.freshly_flagged_count == 1

        db.refresh(branch_user)
        assert branch_user.status == AccountStatus.FLAGGED_INACTIVE

    flags = client.get("/api/v1/flags",
                       headers={"Authorization": f"Bearer {hq_token}"})
    assert flags.status_code == 200
    assert len(flags.json()) == 1
    assert flags.json()[0]["role"] == "BRANCH"
    assert flags.json()[0]["last_login_at"] is not None

    notifs = client.get("/api/v1/flags/notifications",
                        headers={"Authorization": f"Bearer {hq_token}"})
    assert notifs.status_code == 200
    assert len(notifs.json()) == 1
    assert notifs.json()[0]["type"] == "ACCOUNT_FLAGGED_INACTIVE"

    branch_token2 = _login(client, "branch@ac.example.com", "branchsecret")
    assert branch_token2

    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == "branch@ac.example.com"))
        assert branch_user.status == AccountStatus.ACTIVE
        open_flags = db.scalars(
            select(AccountFlag).where(
                AccountFlag.user_id == branch_user.id,
                AccountFlag.resolved_at.is_(None),
            )
        ).all()
        assert open_flags == []


# ── AC-9  Missing ID number or photo → 422 rejection ─────────────────────

def test_ac9_missing_id_or_photo_rejected(client):
    hq_token = _signup(client, dealer="AC9 Validator", code="AC900",
                       email="hq@ac9.example.com")

    no_photo = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": "No Photo", "type": "VAN", "id_number": "AC9-BR-01",
              "photo_url": "", "email": "no-photo@ac9.example.com",
              "password": "branchsecret"},
    )
    assert no_photo.status_code == 422

    no_id = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": "No ID", "type": "SHOP", "id_number": "",
              "photo_url": "https://example.com/br.jpg",
              "email": "no-id@ac9.example.com", "password": "branchsecret"},
    )
    assert no_id.status_code == 422

    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": "Good Branch", "type": "SHOP", "id_number": "AC9-BR-OK",
              "photo_url": "https://example.com/br.jpg",
              "email": "good@ac9.example.com", "password": "branchsecret"},
    )
    assert branch.status_code == 201
    branch_token = _login(client, "good@ac9.example.com", "branchsecret")

    no_ba_photo = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": "BA No Photo", "email": "bnp@ac9.example.com",
              "password": "basecret123", "phone_msisdn": "254700000900",
              "id_number": "AC9-BA-01", "photo_url": ""},
    )
    assert no_ba_photo.status_code == 422

    no_ba_id = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": "BA No ID", "email": "bni@ac9.example.com",
              "password": "basecret123", "phone_msisdn": "254700000901",
              "id_number": "", "photo_url": "https://example.com/ba.jpg"},
    )
    assert no_ba_id.status_code == 422

    good_ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": "Good BA", "email": "gba@ac9.example.com",
              "password": "basecret123", "phone_msisdn": "254700000902",
              "id_number": "AC9-BA-OK", "photo_url": "https://example.com/ba.jpg"},
    )
    assert good_ba.status_code == 201
