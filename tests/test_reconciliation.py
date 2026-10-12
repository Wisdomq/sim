"""Phase 8 tests: Safaricom xlsx parsing + reconciliation matching."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import status as http_status
from sqlalchemy import select

from simcards_backend.core.config import settings
from simcards_backend.core.database import SessionLocal
from simcards_backend.core.security import hash_password, now_utc
from simcards_backend.models import (
    AccountStatus,
    BrandAmbassador,
    Branch,
    BranchType,
    Dealer,
    ReconciliationLineDetail,
    ReconciliationMatchStatus,
    ReconciliationResult,
    Role,
    SafaricomImport,
    SafaricomImportStatus,
    SaleEvent,
    ScannedVia,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    User,
)
from simcards_backend.services.reconciliation import (
    ParsedSafaricomRow,
    list_activated_serials_for_month,
    reconcile_safaricom_import,
)
from simcards_backend.tasks.xlsx_parser import parse_safaricom_report_file

REAL_HEADER = [
    "TM Date",
    "ID Date",
    "ID Month",
    "Dealer Shortcode",
    "Dealer Name",
    "Sim Serial Number",
    "Top Up Date",
    "Top Up Amount",
    "Agent MSISDN",
    "BA",
    "Region",
    "Territory",
    "Cluster",
    "Cumulative Usage",
    "Cumulative Commission",
    "Fraud Flagged",
    "Fraud Suspension Date",
    "Fraud Reason",
    "Role",
    "Quality",
]

# (serial, top_up_date, top_up_amount, cumulative_commission, fraud, fraud_reason)
FILE_ROWS = [
    ("80000000000000000001", "-", "-", "-", "N", "-"),
    ("80000000000000000002", "20260831", "51.0", "300.0", "N", "-"),
    ("80000000000000000003", "20260831", "50.0", "300.0", "Y", "Duplicate activity"),
    ("80000000000000000004", "-", "-", "20.5", "N", "-"),
]


def _full_row(serial: str, top_up_date: str, amount: str, commission: str, fraud: str, reason: str):
    row: list[str] = ["2026-08-01"] * 5
    row.append(serial)
    row.append(top_up_date)
    row.append(amount)
    row.append("254700000000")  # Agent MSISDN - never read (FR-REC-04)
    row.append("Some BA")       # BA - never read
    row.extend(["Region", "Territory", "Cluster"])
    row.append("100.0")  # Cumulative Usage
    row.append(commission)
    row.append(fraud)
    row.append("-")
    row.append(reason)
    row.append("role")
    row.append("quality")
    return row


def _build_xlsx(tmp_path, rows):
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "D-T114 TEST"
    sheet.append(REAL_HEADER)
    for row in rows:
        sheet.append(_full_row(*row))
    path = tmp_path / "safaricom_report.xlsx"
    workbook.save(path)
    return path


def _parsed_rows():
    return [
        ParsedSafaricomRow(
            serial_number=serial,
            top_up_date=None if top_up_date == "-" else datetime.strptime(top_up_date, "%Y%m%d").date(),
            top_up_amount=None if amount == "-" else Decimal(amount),
            cumulative_commission=None if commission == "-" else Decimal(commission),
            fraud_flagged=fraud == "Y",
            fraud_reason=None if reason == "-" else reason,
        )
        for serial, top_up_date, amount, commission, fraud, reason in FILE_ROWS
    ]


def _seed_dealer(db):
    dealer = Dealer(name="Recon Dealer", safaricom_dealer_shortcode="D800")
    db.add(dealer)
    db.flush()
    hq = User(
        dealer_id=dealer.id,
        role=Role.HQ,
        email="recon-hq@example.com",
        password_hash=hash_password("supersecret"),
        status=AccountStatus.ACTIVE,
    )
    db.add(hq)
    db.flush()
    branch = Branch(
        dealer_id=dealer.id,
        name="Recon Shop",
        type=BranchType.SHOP,
        id_number="BR-801",
        photo_url="https://example.com/branch.jpg",
        created_by_id=hq.id,
    )
    db.add(branch)
    db.flush()
    ba_user = User(
        dealer_id=dealer.id,
        role=Role.BA,
        email="recon-ba@example.com",
        password_hash=hash_password("basecret"),
        branch_id=branch.id,
        status=AccountStatus.ACTIVE,
    )
    db.add(ba_user)
    db.flush()
    ba = BrandAmbassador(
        dealer_id=dealer.id,
        branch_id=branch.id,
        user_id=ba_user.id,
        name="Recon BA",
        id_number="BA-801",
        photo_url="https://example.com/ba.jpg",
        status=AccountStatus.ACTIVE,
        created_by_id=hq.id,
    )
    db.add(ba)
    db.flush()
    ba_user.ba_profile_id = ba.id
    batch = StockBatch(
        dealer_id=dealer.id,
        source=StockBatchSource.PDF_IMPORT,
        source_reference="RECON-BATCH",
        quantity=10,
        imported_by_id=hq.id,
    )
    db.add(batch)
    db.flush()
    return dealer, hq, branch, ba, batch


def _add_sim(db, *, dealer, batch, branch, ba, serial, sold):
    sim = SimCard(
        dealer_id=dealer.id,
        serial_number=serial,
        stock_batch_id=batch.id,
        status=SimStatus.SOLD if sold else SimStatus.WITH_BA,
        current_branch_id=branch.id,
        current_ba_id=ba.id,
    )
    db.add(sim)
    db.flush()
    if sold:
        db.add(
            SaleEvent(
                dealer_id=dealer.id,
                sim_card_id=sim.id,
                ba_id=ba.id,
                branch_id=branch.id,
                sold_at=now_utc(),
                scanned_via=ScannedVia.CAMERA,
            )
        )
    return sim


def test_parse_safaricom_report_file_realistic_layout(tmp_path):
    path = _build_xlsx(tmp_path, FILE_ROWS)
    rows = parse_safaricom_report_file(str(path))

    assert len(rows) == 4
    by_serial = {row.serial_number: row for row in rows}
    assert by_serial["80000000000000000001"].top_up_amount is None
    assert by_serial["80000000000000000002"].top_up_date == date(2026, 8, 31)
    assert by_serial["80000000000000000002"].top_up_amount == Decimal("51.0")
    assert by_serial["80000000000000000002"].cumulative_commission == Decimal("300.0")
    assert by_serial["80000000000000000003"].fraud_flagged is True
    assert by_serial["80000000000000000003"].fraud_reason == "Duplicate activity"
    assert by_serial["80000000000000000004"].top_up_amount is None
    assert by_serial["80000000000000000004"].cumulative_commission == Decimal("20.5")


def test_reconcile_safaricom_import_matching_rules():
    with SessionLocal() as db:
        dealer, hq, branch, ba, batch = _seed_dealer(db)
        _add_sim(db, dealer=dealer, batch=batch, branch=branch, ba=ba, serial="80000000000000000001", sold=True)
        _add_sim(db, dealer=dealer, batch=batch, branch=branch, ba=ba, serial="80000000000000000002", sold=True)
        _add_sim(db, dealer=dealer, batch=batch, branch=branch, ba=ba, serial="80000000000000000005", sold=True)
        db.flush()

        imp = SafaricomImport(
            dealer_id=dealer.id,
            uploaded_by_id=hq.id,
            file_reference="synthetic",
            report_date=date(2026, 8, 31),
            status=SafaricomImportStatus.PROCESSING,
        )
        db.add(imp)
        db.commit()

        result = reconcile_safaricom_import(db, safaricom_import=imp, rows=_parsed_rows())
        db.commit()

        assert result.total_sold_in_app == 3
        assert result.total_confirmed_activated_by_safaricom == 1
        assert result.total_topped_up == 2
        assert result.total_cumulative_commission == Decimal("300")
        assert result.total_fraud_flagged == 0
        assert result.unmatched_sold_not_in_safaricom_count == 2
        assert result.unmatched_in_safaricom_not_sold_in_app_count == 2

        lines = db.scalars(
            select(ReconciliationLineDetail).where(
                ReconciliationLineDetail.reconciliation_result_id == result.id
            )
        ).all()
        assert len(lines) == 5
        statuses = {line.serial_number: line.match_status for line in lines}
        assert statuses["80000000000000000002"] == ReconciliationMatchStatus.MATCHED
        assert statuses["80000000000000000001"] == ReconciliationMatchStatus.SOLD_NOT_ACTIVATED
        assert statuses["80000000000000000005"] == ReconciliationMatchStatus.SOLD_NOT_ACTIVATED
        assert statuses["80000000000000000003"] == ReconciliationMatchStatus.ACTIVATED_NOT_RECORDED_SOLD
        assert statuses["80000000000000000004"] == ReconciliationMatchStatus.ACTIVATED_NOT_RECORDED_SOLD

        matched = next(line for line in lines if line.match_status == ReconciliationMatchStatus.MATCHED)
        assert matched.cumulative_commission == Decimal("300")
        assert matched.fraud_flagged is False

        # Re-running the same import is idempotent (no duplicate lines/results).
        result2 = reconcile_safaricom_import(db, safaricom_import=imp, rows=_parsed_rows())
        db.commit()
        results = db.scalars(
            select(ReconciliationResult).where(
                ReconciliationResult.safaricom_import_id == imp.id
            )
        ).all()
        assert len(results) == 1
        lines2 = db.scalars(
            select(ReconciliationLineDetail).where(
                ReconciliationLineDetail.reconciliation_result_id == result2.id
            )
        ).all()
        assert len(lines2) == 5


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_reconciliation_upload_and_query_endpoints(client, tmp_path):
    import io

    from simcards_backend.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    settings.UPLOAD_DIR = str(tmp_path)

    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Recon API Dealer",
            "safaricom_dealer_shortcode": "D801",
            "hq_email": "recon-hq@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "recon-hq@example.com", "supersecret")
    headers = {"Authorization": f"Bearer {hq_token}"}

    path = _build_xlsx(tmp_path, FILE_ROWS)
    with open(path, "rb") as handle:
        response = client.post(
            "/api/v1/reconciliation/imports",
            headers=headers,
            data={"report_date": "2026-08-31"},
            files={"file": ("report.xlsx", handle, "application/octet-stream")},
        )
    assert response.status_code == http_status.HTTP_202_ACCEPTED, response.text
    import_id = response.json()["import_id"]
    assert response.json()["task_id"]

    with SessionLocal() as db:
        imp = db.scalar(select(SafaricomImport).where(SafaricomImport.id == import_id))
        assert imp is not None
        assert imp.report_date == date(2026, 8, 31)
        assert imp.row_count == 4

        # Eager mode already ran the reconciliation task synchronously.
        assert imp.status == SafaricomImportStatus.COMPLETED

    imports = client.get("/api/v1/reconciliation/imports", headers=headers)
    assert imports.status_code == 200
    assert len(imports.json()) == 1
    assert imports.json()[0]["status"] == "COMPLETED"

    summary = client.get(f"/api/v1/reconciliation/imports/{import_id}", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_sold_in_app"] == 0
    assert body["total_confirmed_activated_by_safaricom"] == 0
    assert body["total_topped_up"] == 2
    assert Decimal(body["total_cumulative_commission"]) == Decimal("0")

    detail = client.get(f"/api/v1/reconciliation/imports/{import_id}/detail", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert len(detail_body) == 4
    assert all(
        row["match_status"] == ReconciliationMatchStatus.ACTIVATED_NOT_RECORDED_SOLD
        for row in detail_body
    )

    filtered = client.get(
        f"/api/v1/reconciliation/imports/{import_id}/detail?match_status=MATCHED",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json() == []

    not_found = client.get(
        "/api/v1/reconciliation/imports/999999/detail",
        headers=headers,
    )
    assert not_found.status_code == 404

    # A non-xlsx upload is rejected.
    bad = client.post(
        "/api/v1/reconciliation/imports",
        headers=headers,
        data={"report_date": "2026-08-31"},
        files={"file": ("report.csv", io.BytesIO(b"a,b,c"), "text/csv")},
    )
    assert bad.status_code == 422


def test_list_activated_serials_by_month_separates_months():
    """Serials activated in one month must not leak into another month's view."""
    with SessionLocal() as db:
        dealer, hq, branch, ba, batch = _seed_dealer(db)
        _add_sim(
            db, dealer=dealer, batch=batch, branch=branch, ba=ba,
            serial="80000000000000000011", sold=True,
        )
        _add_sim(
            db, dealer=dealer, batch=batch, branch=branch, ba=ba,
            serial="80000000000000000012", sold=True,
        )
        db.flush()

        aug_import = SafaricomImport(
            dealer_id=dealer.id,
            uploaded_by_id=hq.id,
            file_reference="aug-synthetic",
            report_date=date(2026, 8, 31),
            status=SafaricomImportStatus.PROCESSING,
        )
        db.add(aug_import)
        db.flush()
        reconcile_safaricom_import(
            db,
            safaricom_import=aug_import,
            rows=[
                ParsedSafaricomRow(
                    "80000000000000000011", date(2026, 8, 12), Decimal("50.0"),
                    Decimal("200"), False, None,
                ),
                ParsedSafaricomRow(
                    "80000000000000000013", date(2026, 8, 20), Decimal("50.0"),
                    Decimal("200"), False, None,
                ),
            ],
        )

        sep_import = SafaricomImport(
            dealer_id=dealer.id,
            uploaded_by_id=hq.id,
            file_reference="sep-synthetic",
            report_date=date(2026, 9, 30),
            status=SafaricomImportStatus.PROCESSING,
        )
        db.add(sep_import)
        db.flush()
        reconcile_safaricom_import(
            db,
            safaricom_import=sep_import,
            rows=[
                ParsedSafaricomRow(
                    "80000000000000000012", date(2026, 9, 5), Decimal("50.0"),
                    Decimal("300"), False, None,
                ),
                # Same serial freshly activated in Sep also appears in the Aug file.
                ParsedSafaricomRow(
                    "80000000000000000013", date(2026, 9, 15), Decimal("50.0"),
                    Decimal("300"), True, "Late activation",
                ),
            ],
        )
        db.commit()

        aug_rows = list_activated_serials_for_month(
            db, dealer_id=dealer.id, month_start=date(2026, 8, 1), month_end=date(2026, 9, 1)
        )
        aug_serials = sorted(row.serial_number for row in aug_rows)
        assert aug_serials == ["80000000000000000011", "80000000000000000013"]
        assert all(row.top_up_date <= date(2026, 8, 31) for row in aug_rows)

        sep_rows = list_activated_serials_for_month(
            db, dealer_id=dealer.id, month_start=date(2026, 9, 1), month_end=date(2026, 10, 1)
        )
        sep_serials = sorted(row.serial_number for row in sep_rows)
        assert sep_serials == ["80000000000000000012", "80000000000000000013"]
        sep_by_serial = {row.serial_number: row for row in sep_rows}
        assert sep_by_serial["80000000000000000013"].fraud_flagged is True
        assert sep_by_serial["80000000000000000013"].top_up_date == date(2026, 9, 15)

        # No activated serial outside the requested month.
        assert "80000000000000000011" not in sep_serials
        assert "80000000000000000012" not in aug_serials


def test_activated_serials_by_month_endpoint(client, tmp_path):
    import io

    from simcards_backend.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    settings.UPLOAD_DIR = str(tmp_path)

    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Monthly Recon Dealer",
            "safaricom_dealer_shortcode": "D802",
            "hq_email": "monthly-recon-hq@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "monthly-recon-hq@example.com", "supersecret")
    headers = {"Authorization": f"Bearer {hq_token}"}

    aug_rows = [
        ("80000000000000000021", "20260812", "50.0", "200.0", "N", "-"),
        ("80000000000000000023", "20260820", "50.0", "200.0", "N", "-"),
    ]
    sep_rows = [
        ("80000000000000000022", "20260905", "50.0", "300.0", "N", "-"),
        # Same serial re-activated (new top-up) in Sep; must appear in Sep only via Sep row.
        ("80000000000000000023", "20260915", "50.0", "300.0", "Y", "Duplicate activity"),
    ]

    for rows, report_date, name in [
        (aug_rows, "2026-08-31", "aug"),
        (sep_rows, "2026-09-30", "sep"),
    ]:
        dir_path = tmp_path / name
        dir_path.mkdir(exist_ok=True)
        path = _build_xlsx(dir_path, rows)
        with open(path, "rb") as handle:
            response = client.post(
                "/api/v1/reconciliation/imports",
                headers=headers,
                data={"report_date": report_date},
                files={"file": (f"{name}.xlsx", handle, "application/octet-stream")},
            )
        assert response.status_code == http_status.HTTP_202_ACCEPTED, response.text

    aug_resp = client.get(
        "/api/v1/reconciliation/activated?month=2026-08",
        headers=headers,
    )
    assert aug_resp.status_code == 200
    aug_serials = sorted(row["serial_number"] for row in aug_resp.json())
    assert aug_serials == ["80000000000000000021", "80000000000000000023"]
    assert all(row["top_up_date"] == "2026-08-12" or row["top_up_date"] == "2026-08-20" for row in aug_resp.json())

    sep_resp = client.get(
        "/api/v1/reconciliation/activated?month=2026-09",
        headers=headers,
    )
    assert sep_resp.status_code == 200
    sep_body = sep_resp.json()
    sep_serials = sorted(row["serial_number"] for row in sep_body)
    assert sep_serials == ["80000000000000000022", "80000000000000000023"]
    sep_by_serial = {row["serial_number"]: row for row in sep_body}
    assert sep_by_serial["80000000000000000023"]["top_up_date"] == "2026-09-15"
    assert sep_by_serial["80000000000000000023"]["fraud_flagged"] is True
    assert "80000000000000000021" not in sep_serials

    # Previous-month activations never in current-month view.
    assert "80000000000000000022" not in aug_serials

    # Invalid month format rejected.
    bad = client.get(
        "/api/v1/reconciliation/activated?month=08-2026",
        headers=headers,
    )
    assert bad.status_code == 422