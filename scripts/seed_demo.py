#!/usr/bin/env python
"""Seed a rich QA demo tenant into the live backend database (Phase 13, X-13-01).

Creates an isolated dealer ("Phase 13 QA", shortcode QA13) with:
  - HQ, 2 branches (Shop + Van), 3 BAs per branch (each with an identity photo)
  - Stock via PDF pick-list import (real parser exercised) + box scans
  - HQ->Branch distribution, Branch->BA assignment using the real services
  - Sales spread across the last 5 days so daily/weekly/monthly reports,
    commission and performance percentages all populate
  - BA->Branch return, HQ->Branch return request fulfilled, expired-SIM box
  - Commission rule + daily/weekly/monthly branch targets
  - A synthetic Safaricom xlsx reconciliation (COMPLETED) with MATCHED /
    SOLD_NOT_ACTIVATED / ACTIVATED_NOT_RECORDED_SOLD + a fraud-flagged line
  - Login events (most users active today) + one stale BA that triggers the
    INACTIVE_3_DAYS flag and an HQ notification

Run from the repository root with the backend venv:
    source backend/.venv/bin/activate
    PYTHONPATH=backend/src python scripts/seed_demo.py [--reset] [--exhaustive]

The database is taken from settings.DATABASE_URL (env DATABASE_URL wins).
"""

from __future__ import annotations

import argparse
import os as _os
import struct
import uuid
import zlib
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# The dev uvicorn server runs with CWD=backend, so its relative uploads/ root is
# <repo>/backend/uploads. Point the seed at the same absolute root so identity
# photos, pick-lists and recon files the script writes are servable via the API.
if "UPLOAD_DIR" not in _os.environ:
    _os.environ["UPLOAD_DIR"] = f"{Path(__file__).resolve().parents[1]}/backend/uploads"

from sqlalchemy import delete, func, select

from simcards_backend.core.config import settings
from simcards_backend.core.database import SessionLocal, set_tenant_context
from simcards_backend.core.security import now_utc
from simcards_backend.models import (
    AccountFlag,
    AccountStatus,
    AuditLog,
    Branch,
    BranchType,
    BrandAmbassador,
    CommissionRule,
    Dealer,
    LoginEvent,
    Notification,
    PeriodType,
    PerformanceSnapshot,
    ReconciliationLineDetail,
    ReconciliationResult,
    RefreshToken,
    Role,
    ReturnEvent,
    SafaricomImport,
    SafaricomImportStatus,
    SaleEvent,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    StockTransfer,
    SubjectType,
    Target,
    User,
)
from simcards_backend.services.accounts import (
    create_branch_account,
    create_brand_ambassador_account,
    onboard_dealer,
    photo_dir_for,
)
from simcards_backend.services.commission import (
    create_commission_rule,
    create_target,
    update_performance_snapshot,
)
from simcards_backend.services.inactivity import default_cutoff, flag_inactive_accounts
from simcards_backend.services.reconciliation import reconcile_safaricom_import
from simcards_backend.services.sales import record_sale
from simcards_backend.services.stock import (
    assign_sims_to_ba,
    create_stock_batch_with_serials,
    distribute_stock_to_branch,
    fulfill_return_request,
    intake_box_scan,
    mark_expired_sim_cards,
    request_stock_return,
    return_sims_to_branch,
)
from simcards_backend.tasks.pdf_parser import extract_pick_list_lots
from simcards_backend.tasks.xlsx_parser import parse_safaricom_report_file

DEALER_NAME = "Phase 13 QA"
DEALER_SHORTCODE = "QA13"
HQ_EMAIL = "hqa13@example.com"
HQ_PASSWORD = "qaHQsecret13"

BASE_SERIAL = "894101010000020001"  # box-scan stock (active)
PDF_SERIAL_BASE = "894101010000030001"  # pick-list stock (active)
EXPIRY_SERIAL_BASE = "894101010000021001"  # expired demo box

# Sales per BA per day, offset 0 = today ... 4 = four days ago.
SALES_PLAN: dict[str, list[int]] = {
    "b1a1": [7, 6, 8, 6, 5],
    "b1a2": [5, 5, 4, 6, 5],
    "b1a3": [4, 4, 5, 3, 4],
    "b2a1": [6, 5, 6, 5, 4],
    "b2a2": [5, 4, 5, 4, 4],
    "b2a3": [4, 3, 4, 3, 3],
}

DISTANCE = {
    "b1": {"ba1": 40, "ba2": 40, "ba3": 30},  # 110 of 120 assigned; 10 stay WITH_BRANCH
    "b2": {"ba1": 35, "ba2": 30, "ba3": 25},  # 90 assigned
}

TARGETS = {
    "b1": {PeriodType.DAILY: 15, PeriodType.WEEKLY: 105, PeriodType.MONTHLY: 450},
    "b2": {PeriodType.DAILY: 12, PeriodType.WEEKLY: 84, PeriodType.MONTHLY: 360},
}


def _make_png(rgb: tuple[int, int, int]) -> bytes:
    """Return a minimal valid 1x1 RGB PNG (no external imaging dependency)."""

    def chunk(typ: bytes, data: bytes) -> bytes:
        payload = struct.pack(">I", len(data)) + typ + data
        return payload + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00" + bytes(rgb))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def _save_photo(dealer_id: int, label: str) -> str:
    """Persist an identity-style photo and return its authorized API URL."""
    import hashlib

    label = "".join(ch for ch in label.lower() if ch.isalnum())
    photo_dir = photo_dir_for(dealer_id)
    photo_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(label.encode()).hexdigest()[:10]
    filename = f"{label}_{digest}{uuid.uuid4().hex[:4]}.png"
    (photo_dir / filename).write_bytes(_make_png((34, 139, 230)))
    return f"/api/v1/uploads/photo/{filename}"


def _sell_past_period(
    db, *, ba_user: User, sims: list[SimCard], counts: list[int], commission_base: datetime
) -> None:
    """Sell ``counts[d]`` SIMs on each of the last len(counts) days for a BA."""
    cursor = 0
    for day_offset, count in enumerate(counts):
        sold_day = now_utc().date() - timedelta(days=day_offset)
        for index in range(count):
            if cursor >= len(sims):
                return
            sim = sims[cursor]
            cursor += 1
            hour = (8 + index % 10) % 24
            sold_at = datetime(
                sold_day.year, sold_day.month, sold_day.day, hour, (index * 7) % 60, tzinfo=timezone.utc
            )
            if sold_at < commission_base:
                sold_at = commission_base
            record_sale(db, actor=ba_user, serial_number=sim.serial_number, sold_at=sold_at)


def _seed_picklist_pdf(db, *, dealer: Dealer, hq_user: User, count: int) -> list[str]:
    """Generate a real Safaricom-style pick-list PDF and ingest it via the parser."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    serials = [str(int(PDF_SERIAL_BASE) + i).zfill(len(PDF_SERIAL_BASE)) for i in range(count)]
    path = Path(settings.UPLOAD_DIR) / "pick-lists" / str(dealer.id)
    path.mkdir(parents=True, exist_ok=True)
    pdf_path = path / f"seed-pick-list-{uuid.uuid4().hex[:8]}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(40, 800, "Safaricom SIM Pick List")
    c.drawString(40, 785, "<< Lot >> QA13-PICK-2026")
    y = 765
    for i in range(0, count, 5):
        chunk = "  ".join(serials[i : i + 5])
        c.drawString(40, y, chunk)
        y -= 14
        if y < 40:
            c.showPage()
            y = 800
    c.save()

    lots = extract_pick_list_lots(str(pdf_path))
    assert lots, "generated PDF yielded no lots"
    for lot in lots:
        create_stock_batch_with_serials(
            db,
            dealer_id=dealer.id,
            source=StockBatchSource.PDF_IMPORT,
            source_reference=lot.source_reference,
            serials=lot.serials,
            imported_by_id=hq_user.id,
        )
    db.commit()
    return serials


def _seed_reconciliation(db, *, dealer: Dealer, hq_user: User, sold_serials: list[str]) -> None:
    """Build a synthetic Safaricom xlsx and reconcile a COMPLETED import."""

    def pct(amount: Decimal) -> str:
        return f"{amount:.2f}"

    commission_per = Decimal("12.50")
    matched = sold_serials[:32]
    unmatched_sold = sold_serials[32:36]  # sold in app, absent from file
    not_recorded = [str(int(PDF_SERIAL_BASE) - 1 - i).zfill(len(PDF_SERIAL_BASE)) for i in range(8)]
    fraud_serial = matched[-1]

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LineConnections"
    ws.append(
        [
            "SIM Serial Number",
            "Top Up Date",
            "Top Up Amount",
            "Cumulative Commission",
            "Fraud Flagged",
            "Fraud Reason",
        ]
    )
    today = now_utc().date()
    for serial in matched:
        top_up_day = today - timedelta(days=sold_serials.index(serial) % 5)
        ws.append(
            [
                serial,
                top_up_day,
                Decimal("20.00"),
                commission_per,
                "Yes" if serial == fraud_serial else "No",
                ("SIM swapped / wrong IMEI" if serial == fraud_serial else None),
            ]
        )
    for serial in not_recorded:
        ws.append([serial, today - timedelta(days=2), Decimal("10.00"), Decimal("0.00"), "No", None])

    upload_dir = Path(settings.UPLOAD_DIR) / "safaricom" / str(dealer.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"seed-recon-{uuid.uuid4().hex[:8]}.xlsx"
    wb.save(file_path)

    safaricom_import = SafaricomImport(
        dealer_id=dealer.id,
        uploaded_by_id=hq_user.id,
        file_reference=str(file_path),
        report_date=today,
        status=SafaricomImportStatus.PROCESSING,
    )
    db.add(safaricom_import)
    db.flush()

    rows = parse_safaricom_report_file(str(file_path))
    reconcile_safaricom_import(db, safaricom_import=safaricom_import, rows=rows, as_of=now_utc())
    safaricom_import.status = SafaricomImportStatus.COMPLETED
    safaricom_import.row_count = len(rows)
    result = db.scalar(
        select(ReconciliationResult).where(ReconciliationResult.safaricom_import_id == safaricom_import.id)
    )
    matched_count = result.total_confirmed_activated_by_safaricom if result else 0
    fraud_count = result.total_fraud_flagged if result else 0
    db.commit()
    db.refresh(safaricom_import)
    print(
        f"  recon: {safaricom_import.id} COMPLETED ({len(rows)} rows; "
        f"MATCHED={matched_count} "
        f"fraud={fraud_count})"
    )


def _reset_dealer(db, *, dealer_id: int) -> None:
    """Delete every row owned by the QA dealer (FK-safe order)."""
    set_tenant_context(db, dealer_id)
    for model in (
        ReconciliationLineDetail,
        ReconciliationResult,
        SafaricomImport,
        ReturnEvent,
        SaleEvent,
        StockTransfer,
        SimCard,
        StockBatch,
        Target,
        PerformanceSnapshot,
        LoginEvent,
        AccountFlag,
        Notification,
        AuditLog,
        BrandAmbassador,
        Branch,
        User,
        CommissionRule,
        RefreshToken,
    ):
        db.execute(delete(model).where(model.dealer_id == dealer_id))
    db.execute(delete(Dealer).where(Dealer.id == dealer_id))
    db.commit()


def _find_qa_dealer(db) -> Dealer | None:
    return db.scalar(select(Dealer).where(Dealer.safaricom_dealer_shortcode == DEALER_SHORTCODE))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Phase 13 QA demo dealer.")
    parser.add_argument("--reset", action="store_true", help="Delete the QA dealer's data first.")
    parser.add_argument("--exhaustive", action="store_true", help="Add extra HQ stock for load QA.")
    args = parser.parse_args()

    with SessionLocal() as db:
        existing = _find_qa_dealer(db)
        if existing is not None:
            if not args.reset:
                raise SystemExit(
                    f"QA dealer already exists (id={existing.id}). Re-run with --reset to rebuild."
                )
            print(f"Resetting dealer {existing.id} …")
            _reset_dealer(db, dealer_id=existing.id)
            existing = None

        dealer, hq_user = onboard_dealer(
            db,
            dealer_name=DEALER_NAME,
            hq_email=HQ_EMAIL,
            hq_password=HQ_PASSWORD,
            safaricom_dealer_shortcode=DEALER_SHORTCODE,
        )
        dealer_id = dealer.id
        db.refresh(hq_user)
        print(f"Dealer '{DEALER_NAME}' (id={dealer_id}) hq_user={hq_user.id}")

        set_tenant_context(db, dealer_id)

        today_date = now_utc().date()
        month_start = today_date.replace(day=1)
        month_end = date(
            today_date.year + (1 if today_date.month == 12 else 0),
            1 if today_date.month == 12 else today_date.month + 1,
            1,
        ) - timedelta(days=1)

        commission_base = now_utc() - timedelta(days=60)
        rule = create_commission_rule(
            db,
            actor=hq_user,
            name="QA default per-SIM commission",
            amount_per_sim=Decimal("12.50"),
            effective_from=commission_base,
        )
        print(f"  commission rule {rule.id} (KSh {rule.amount_per_sim})")

        branches: dict[str, Branch] = {}
        branch_actors: dict[str, User] = {}
        for key, (name, btype) in {
            "b1": ("QA Branch HQ Shop", BranchType.SHOP),
            "b2": ("QA Branch Van Unit", BranchType.VAN),
        }.items():
            branch = create_branch_account(
                db,
                actor=hq_user,
                name=name,
                branch_type=btype,
                id_number=f"QA13-BR-{key.upper()}-001",
                photo_url=_save_photo(dealer_id, f"branch-{key}"),
                email=f"qa13-{key}@example.com",
                password="qaBranch13Secret",
            )
            branch_actors[key] = db.scalar(
                select(User).where(User.branch_id == branch.id, User.dealer_id == dealer_id)
            )
            branches[key] = branch
            print(f"  branch {branch.id} '{name}' (user {branch_actors[key].id})")

        bas: dict[str, BrandAmbassador] = {}
        ba_actors: dict[str, User] = {}
        for branch_key in ("b1", "b2"):
            for index, suffix in enumerate(("a1", "a2", "a3"), start=1):
                key = f"{branch_key}{suffix}"
                name = f"QA {branch_key.upper()} BA {index}"
                ba = create_brand_ambassador_account(
                    db,
                    actor=hq_user,
                    branch_id=branches[branch_key].id,
                    name=name,
                    email=f"qa13-{key}@example.com",
                    password="qaBA13Secret",
                    phone_msisdn=f"07{key}00000",
                    id_number=f"QA13-BA-{key.upper()}-001",
                    photo_url=_save_photo(dealer_id, f"ba-{key}"),
                )
                bas[key] = ba
                ba_actors[key] = db.scalar(select(User).where(User.id == ba.user_id))
                print(f"  ba {ba.id} '{name}'")

        # ── Stock intake ──────────────────────────────────────────────────────
        pdf_serials = _seed_picklist_pdf(db, dealer=dealer, hq_user=hq_user, count=150)
        print(f"  pick-list PDF import: {len(pdf_serials)} serials")
        intake_box_scan(
            db,
            actor=hq_user,
            box_barcode="QA13-BOX-001",
            serials=None,
            first_serial=BASE_SERIAL,
            quantity=100,
            expiry_date=date(2027, 12, 31),
        )
        intake_box_scan(
            db,
            actor=hq_user,
            box_barcode="QA13-BOX-EXPIRED",
            serials=None,
            first_serial=EXPIRY_SERIAL_BASE,
            quantity=100,
            expiry_date=date(2023, 6, 30),
        )
        print("  box scan: 100 active (QA13-BOX-001), 100 past-expiry (QA13-BOX-EXPIRED)")
        if args.exhaustive:
            for extra in range(29):
                intake_box_scan(
                    db,
                    actor=hq_user,
                    box_barcode=f"QA13-BOX-EXT-{extra:02d}",
                    serials=None,
                    first_serial=str(int(BASE_SERIAL) + 1_000_000 + extra * 100).zfill(len(BASE_SERIAL)),
                    quantity=100,
                    expiry_date=date(2027, 12, 31),
                )
            print("  exhaustive: +2900 extra HQ stock SIMs")

        expired_count = mark_expired_sim_cards(db, as_of=now_utc().date())
        print(f"  expired SIMs: {expired_count}")

        # ── Distribution & assignment ─────────────────────────────────────────
        distribute_stock_to_branch(db, actor=hq_user, branch_id=branches["b1"].id, quantity=120, serial_numbers=None)
        distribute_stock_to_branch(db, actor=hq_user, branch_id=branches["b2"].id, quantity=90, serial_numbers=None)
        print("  distributed: b1=120, b2=90; HQ keeps 40 active")

        assigned: dict[str, list[SimCard]] = {}
        for branch_key, plan in DISTANCE.items():
            branch_user = branch_actors[branch_key]
            for suffix, quantity in plan.items():
                ba_key = f"{branch_key}{suffix.replace('ba', 'a', 1)}"
                sims = assign_sims_to_ba(
                    db,
                    actor=branch_user,
                    ba_id=bas[ba_key].id,
                    serial_numbers=[
                        s.serial_number
                        for s in db.scalars(
                            select(SimCard)
                            .where(
                                SimCard.dealer_id == dealer_id,
                                SimCard.status == SimStatus.WITH_BRANCH,
                                SimCard.current_branch_id == branches[branch_key].id,
                            )
                            .order_by(SimCard.id)
                            .limit(quantity)
                        )
                    ],
                )
                assigned[ba_key] = sims
        print("  assigned to BAs:", {k: len(v) for k, v in assigned.items()})

        # ── Sales (current period) ────────────────────────────────────────────
        total_sold = 0
        for key, counts in SALES_PLAN.items():
            _sell_past_period(db, ba_user=ba_actors[key], sims=assigned[key], counts=counts, commission_base=commission_base)
            total_sold += sum(counts)
        print(f"  sales: {total_sold} across last 5 days")

        # ── Returns ───────────────────────────────────────────────────────────
        returned_serials = [assigned["b1a1"][-1].serial_number, assigned["b1a1"][-2].serial_number]
        return_sims_to_branch(db, actor=branch_actors["b1"], serial_numbers=returned_serials, reason="Unsold after promo period")
        print(f"  BA->branch return: {len(returned_serials)} SIMs")

        with_branch_br1 = db.scalars(
            select(SimCard).where(
                SimCard.dealer_id == dealer_id,
                SimCard.status == SimStatus.WITH_BRANCH,
                SimCard.current_branch_id == branches["b1"].id,
            )
            .order_by(SimCard.id)
            .limit(3)
        ).all()
        requested = request_stock_return(
            db, actor=hq_user, branch_id=branches["b1"].id, serial_numbers=[s.serial_number for s in with_branch_br1],
            reason="Near-expiry stock recall",
        )
        fulfilled = [fulfill_return_request(db, actor=branch_actors["b1"], return_event_id=ev.id) for ev in requested]
        print(f"  HQ return request: {len(fulfilled)} SIMs returned to HQ")

        # ── Targets ───────────────────────────────────────────────────────────
        week_start = now_utc().date() - timedelta(days=now_utc().date().weekday())
        period_starts = {
            PeriodType.DAILY: today_date,
            PeriodType.WEEKLY: week_start,
            PeriodType.MONTHLY: month_start,
        }
        for branch_key, plan in TARGETS.items():
            for period_type, quantity in plan.items():
                create_target(
                    db,
                    actor=hq_user,
                    branch_id=branches[branch_key].id,
                    period_type=period_type,
                    quantity=quantity,
                    effective_from=datetime.combine(period_starts[period_type], time.min, tzinfo=timezone.utc),
                )
        print("  targets: b1 daily=15/week=105/month=450; b2 daily=12/week=84/month=360")

        # ── Performance snapshots (so web reports show real percentages) ─────
        week_end = week_start + timedelta(days=6)
        for branch_key in ("b1", "b2"):
            for period_type, start, end in (
                (PeriodType.MONTHLY, month_start, month_end),
                (PeriodType.WEEKLY, week_start, week_end),
                (PeriodType.DAILY, today_date, today_date),
            ):
                update_performance_snapshot(
                    db,
                    dealer_id=dealer_id,
                    subject_type=SubjectType.BRANCH,
                    subject_id=branches[branch_key].id,
                    period_type=period_type,
                    period_start=start,
                    period_end=end,
                )
            for suffix in ("a1", "a2", "a3"):
                ba_key = f"{branch_key}{suffix}"
                update_performance_snapshot(
                    db,
                    dealer_id=dealer_id,
                    subject_type=SubjectType.BA,
                    subject_id=bas[ba_key].id,
                    period_type=PeriodType.DAILY,
                    period_start=today_date,
                    period_end=today_date,
                )

        # BA weekly + monthly snapshots: target = branch target split across its
        # 3 BAs (the service derives only the DAILY BA target automatically).
        for branch_key, plan in TARGETS.items():
            for period_type, start, end, target_key in (
                (PeriodType.WEEKLY, week_start, week_end, PeriodType.WEEKLY),
                (PeriodType.MONTHLY, month_start, month_end, PeriodType.MONTHLY),
            ):
                ba_target = plan[target_key] // 3
                for suffix in ("a1", "a2", "a3"):
                    ba_key = f"{branch_key}{suffix}"
                    actual_sold = db.scalar(
                        select(func.count(SaleEvent.id)).where(
                            SaleEvent.dealer_id == dealer_id,
                            SaleEvent.ba_id == bas[ba_key].id,
                            SaleEvent.sold_at >= datetime.combine(start, time.min, tzinfo=timezone.utc),
                            SaleEvent.sold_at <= datetime.combine(end, time.max, tzinfo=timezone.utc),
                        )
                    ) or 0
                    existing_ba = db.scalar(
                        select(PerformanceSnapshot).where(
                            PerformanceSnapshot.dealer_id == dealer_id,
                            PerformanceSnapshot.subject_type == SubjectType.BA,
                            PerformanceSnapshot.subject_id == bas[ba_key].id,
                            PerformanceSnapshot.period_type == period_type,
                            PerformanceSnapshot.period_start == start,
                            PerformanceSnapshot.period_end == end,
                        )
                    )
                    if existing_ba is None:
                        db.add(
                            PerformanceSnapshot(
                                dealer_id=dealer_id,
                                subject_type=SubjectType.BA,
                                subject_id=bas[ba_key].id,
                                period_type=period_type,
                                period_start=start,
                                period_end=end,
                                target_quantity=ba_target,
                                actual_sold_quantity=actual_sold,
                                percentage_achieved=Decimal(actual_sold) / Decimal(ba_target) * 100,
                            )
                        )
        db.commit()

        for period_type, start, end in (
            (PeriodType.MONTHLY, month_start, month_end),
            (PeriodType.WEEKLY, week_start, week_end),
            (PeriodType.DAILY, today_date, today_date),
        ):
            update_performance_snapshot(
                db,
                dealer_id=dealer_id,
                subject_type=SubjectType.DEALER,
                subject_id=dealer_id,
                period_type=period_type,
                period_start=start,
                period_end=end,
            )
        print("  performance snapshots: daily/weekly/monthly (branches, BAs, dealer)")

        # ── Reconciliation ────────────────────────────────────────────────────
        sold_serials = [
            s.serial_number
            for s in db.scalars(select(SimCard).where(SimCard.dealer_id == dealer_id, SimCard.status == SimStatus.SOLD))
        ]
        _seed_reconciliation(db, dealer=dealer, hq_user=hq_user, sold_serials=sold_serials)

        # ── Login activity + inactivity flag demo ─────────────────────────────
        now = now_utc()
        for user in db.scalars(
            select(User).where(User.dealer_id == dealer_id, User.role.in_([Role.BRANCH, Role.BA]))
        ):
            if user.email == "qa13-b2a3@example.com":
                db.add(
                    LoginEvent(
                        dealer_id=dealer_id,
                        user_id=user.id,
                        role=user.role,
                        logged_in_at=now - timedelta(days=5),
                    )
                )
            else:
                db.add(
                    LoginEvent(
                        dealer_id=dealer_id,
                        user_id=user.id,
                        role=user.role,
                        logged_in_at=now - timedelta(minutes=30),
                    )
                )
        db.commit()

        as_of, cutoff = default_cutoff()
        outcome = flag_inactive_accounts(db, dealer_id=dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        print(f"  inactivity flags: {outcome.freshly_flagged_count} freshly flagged")

        branch_count = db.scalar(
            select(func.count())
            .select_from(SimCard)
            .where(SimCard.dealer_id == dealer_id, SimCard.status == SimStatus.WITH_BRANCH)
        )
        print(f"  final WITH_BRANCH remaining (b1): {branch_count}")
        print("\nCredentials for the QA dealer:")
        print(f"  HQ     {HQ_EMAIL} / {HQ_PASSWORD}")
        for key in ("b1", "b2"):
            print(f"  Branch {key}  qa13-{key}@example.com / qaBranch13Secret")
        for key in sorted(bas):
            print(f"  BA {key.upper()}  qa13-{key}@example.com / qaBA13Secret")


if __name__ == "__main__":
    main()