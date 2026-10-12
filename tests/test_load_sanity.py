"""B-10-06: load/performance sanity (NFR-08) regression guard.

NFR-08 is checked by scripts/benchmark_report.py at Small/Medium/Large volumes
(see docs/nfr08-findings.md). This file is a *correctness* guard for the load
data paths at a small seeded volume — it asserts that the rollups stay
numerically correct at scale, without brittle wall-clock timing asserts.

Covered paths:
* ``generate_report``                       (POST /api/v1/reports query load)
* ``get_commission_earned``                 (commission rollup)
* ``get_branch_summary``                    (branch summary rollup)
* ``reconcile_safaricom_import``            (reconciliation matching at volume)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from simcards_backend.models import (
    AccountStatus,
    Branch,
    BranchType,
    BrandAmbassador,
    CommissionRule,
    Dealer,
    PeriodType,
    ReconciliationLineDetail,
    ReconciliationMatchStatus,
    Role,
    SafaricomImport,
    SaleEvent,
    ScannedVia,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    Target,
    User,
)
from simcards_backend.services.commission import get_branch_summary
from simcards_backend.services.reconciliation import (
    ParsedSafaricomRow,
    reconcile_safaricom_import,
)
from simcards_backend.services.reports import generate_report, get_report_context
from simcards_backend.services.sales import get_commission_earned
from sqlalchemy import insert, select

PERIOD_START = date(2026, 7, 1)
PERIOD_END = date(2026, 7, 31)
N_BRANCHES = 2
BAS_PER_BRANCH = 2
N_BAS = N_BRANCHES * BAS_PER_BRANCH
SIMS_PER_BRANCH = 100
N_SIMS = N_BRANCHES * SIMS_PER_BRANCH
SALES_PER_BRANCH = 50
N_SALES = N_BRANCHES * SALES_PER_BRANCH
COMMISSION_AMOUNT = Decimal("50.00")


def _serial(i: int) -> str:
    return str(30_000_000_000_000_000_000 + i)


def _seed(db_session) -> User:
    db_session.execute(
        insert(Dealer), {"id": 1, "name": "Load Dealer", "safaricom_dealer_shortcode": "LOAD001"}
    )
    db_session.execute(
        insert(User),
        {
            "id": 1,
            "dealer_id": 1,
            "role": Role.HQ.value,
            "email": "load-hq@example.com",
            "password_hash": "not-checked",
            "status": AccountStatus.ACTIVE.value,
        },
    )
    db_session.execute(
        insert(Branch),
        [
            {
                "id": b + 1,
                "dealer_id": 1,
                "name": f"Load Branch {b + 1}",
                "type": BranchType.SHOP.value,
                "id_number": f"LOAD-BR-{b + 1}",
                "photo_url": "https://example.com/load.jpg",
                "created_by": 1,
            }
            for b in range(N_BRANCHES)
        ],
    )
    db_session.execute(
        insert(BrandAmbassador),
        [
            {
                "id": i + 1,
                "dealer_id": 1,
                "branch_id": (i // BAS_PER_BRANCH) + 1,
                "user_id": i + 2,
                "name": f"Load BA {i + 1}",
                "phone_msisdn": f"2547{i + 1:08d}",
                "id_number": f"LOAD-BA-{i + 1}",
                "photo_url": "https://example.com/load-ba.jpg",
                "status": AccountStatus.ACTIVE.value,
            }
            for i in range(N_BAS)
        ],
    )
    db_session.execute(
        insert(User),
        [
            {
                "id": i + 2,
                "dealer_id": 1,
                "role": Role.BA.value,
                "email": f"load-ba-{i + 1}@example.com",
                "password_hash": "not-checked",
                "branch_id": (i // BAS_PER_BRANCH) + 1,
                "ba_profile_id": i + 1,
                "status": AccountStatus.ACTIVE.value,
            }
            for i in range(N_BAS)
        ],
    )
    db_session.execute(
        insert(CommissionRule),
        {
            "id": 1,
            "dealer_id": 1,
            "name": "Load Rate",
            "amount_per_sim": COMMISSION_AMOUNT,
            "effective_from": datetime(2026, 1, 1),
            "effective_to": None,
            "created_by": 1,
        },
    )
    db_session.execute(
        insert(Target),
        [
            {
                "id": b + 1,
                "dealer_id": 1,
                "branch_id": b + 1,
                "period_type": PeriodType.MONTHLY.value,
                "quantity": 60,
                "effective_from": datetime(2026, 7, 1),
                "effective_to": None,
                "set_by": 1,
            }
            for b in range(N_BRANCHES)
        ],
    )
    db_session.execute(
        insert(StockBatch),
        [
            {
                "id": b + 1,
                "dealer_id": 1,
                "source": StockBatchSource.BOX_SCAN.value,
                "source_reference": f"LOAD-BOX-{b + 1}",
                "quantity": SIMS_PER_BRANCH,
                "imported_by": 1,
            }
            for b in range(N_BRANCHES)
        ],
    )
    db_session.execute(
        insert(SimCard),
        [
            {
                "id": i + 1,
                "dealer_id": 1,
                "serial_number": _serial(i),
                "stock_batch_id": (i // SIMS_PER_BRANCH) + 1,
                "status": (
                    SimStatus.SOLD.value
                    if (i % SIMS_PER_BRANCH) < SALES_PER_BRANCH
                    else SimStatus.WITH_BRANCH.value
                ),
                "current_branch_id": (i // SIMS_PER_BRANCH) + 1,
                "current_ba_id": None,
            }
            for i in range(N_SIMS)
        ],
    )
    db_session.execute(
        insert(SaleEvent),
        [
            {
                "id": i + 1,
                "dealer_id": 1,
                "sim_card_id": ((i // SALES_PER_BRANCH) * SIMS_PER_BRANCH)
                + (i % SALES_PER_BRANCH)
                + 1,
                "ba_id": ((i // SALES_PER_BRANCH) * BAS_PER_BRANCH) + (i % BAS_PER_BRANCH) + 1,
                "branch_id": (i // SALES_PER_BRANCH) + 1,
                "sold_at": datetime.combine(
                    PERIOD_START + timedelta(days=i % 31), datetime.min.time()
                )
                + timedelta(minutes=(i * 7) % 1440),
                "scanned_via": ScannedVia.CAMERA.value,
                "commission_rule_id": 1,
                "commission_amount": COMMISSION_AMOUNT,
            }
            for i in range(N_SALES)
        ],
    )
    db_session.commit()
    return db_session.get(User, 1)


def test_report_totals_match_seeded_sales(db_session):
    hq_user = _seed(db_session)
    context = get_report_context(hq_user, branch_filter=None)

    report = generate_report(
        db_session,
        context=context,
        period_type="MONTHLY",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    assert report["total_sales_count"] == N_SALES
    assert report["total_commission_owed"] == COMMISSION_AMOUNT * N_SALES
    assert len(report["branch_reports"]) == N_BRANCHES
    for branch_report in report["branch_reports"]:
        assert branch_report.total_sales_count == SALES_PER_BRANCH
        assert branch_report.total_commission_owed == COMMISSION_AMOUNT * SALES_PER_BRANCH
        assert branch_report.stock_counts.sold == SALES_PER_BRANCH


def test_commission_earned_rollup_matches_report(db_session):
    hq_user = _seed(db_session)

    total = get_commission_earned(db_session, dealer_id=hq_user.dealer_id)

    assert total == COMMISSION_AMOUNT * N_SALES


def test_branch_summary_rollup_shape(db_session):
    hq_user = _seed(db_session)

    summary = get_branch_summary(db_session, actor=hq_user)

    assert len(summary["branches"]) == N_BRANCHES
    for branch_summary in summary["branches"]:
        assert branch_summary["total_sims"] == SIMS_PER_BRANCH
        assert branch_summary["sold_count"] == SALES_PER_BRANCH
        assert branch_summary["with_branch_count"] == SIMS_PER_BRANCH - SALES_PER_BRANCH


def test_reconciliation_counts_at_volume(db_session):
    _seed(db_session)
    extra_rows = 5
    imp = SafaricomImport(
        dealer_id=1,
        uploaded_by_id=1,
        file_reference="load-synthetic",
        report_date=PERIOD_END,
    )
    db_session.add(imp)
    db_session.flush()

    rows = [
        ParsedSafaricomRow(
            serial_number=_serial((i // SALES_PER_BRANCH) * SIMS_PER_BRANCH + (i % SALES_PER_BRANCH)),
            top_up_date=PERIOD_START + timedelta(days=i % 31),
            top_up_amount=Decimal("50.00"),
            cumulative_commission=Decimal("200.00"),
            fraud_flagged=False,
            fraud_reason=None,
        )
        for i in range(N_SALES)
    ]
    for j in range(extra_rows):
        rows.append(
            ParsedSafaricomRow(
                serial_number=str(90_000_000_000_000_000_000 + N_SALES + j),
                top_up_date=PERIOD_START + timedelta(days=j),
                top_up_amount=Decimal("50.00"),
                cumulative_commission=Decimal("200.00"),
                fraud_flagged=False,
                fraud_reason=None,
            )
        )

    result = reconcile_safaricom_import(db_session, safaricom_import=imp, rows=rows)
    db_session.flush()

    assert result.total_confirmed_activated_by_safaricom == N_SALES
    assert result.total_fraud_flagged == 0

    detail_rows = db_session.scalars(
        select(ReconciliationLineDetail).where(
            ReconciliationLineDetail.reconciliation_result_id == result.id
        )
    ).all()
    assert len(detail_rows) == N_SALES + extra_rows
    matched_rows = [
        row for row in detail_rows if row.match_status == ReconciliationMatchStatus.MATCHED
    ]
    assert len(matched_rows) == N_SALES
    assert all(row.top_up_date is not None for row in matched_rows)
