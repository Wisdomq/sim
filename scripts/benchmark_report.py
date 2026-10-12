"""NFR-08 load/performance sanity benchmark (B-10-06).

Measures report/data-path latency at representative per-dealer volumes against
an isolated SQLite database, printing a markdown results table.

Volume presets (branches / BAs / SIMs / sales):

* small:  3 / 30 / 3,000 / 1,500
* medium: 10 / 100 / 30,000 / 15,000   (default)
* large:  25 / 250 / 100,000 / 60,000  (opt-in; slower)

Measured paths:
* ``generate_report`` (the query load behind ``POST /api/v1/reports``)
* ``get_commission_earned`` (``GET /api/v1/commission/earned`` rollup)
* ``get_branch_summary`` (``GET /api/v1/commission/branch-summary``)
* ``reconcile_safaricom_import`` (reconciliation matching)
* ``generate_pdf_report`` / ``generate_excel_report`` (export generation)

Run from the repo root:

    rm -f /tmp/simcards_bench.db*
    source backend/.venv/bin/activate
    PYTHONPATH="$PWD/backend/src" python scripts/benchmark_report.py [--scale small|medium|large]

NFR-08 acceptance interpretation (documented in docs/nfr08-findings.md): an HQ
consolidated monthly report plus one export should complete within ~5s at
Medium volume and ~20s at Large. This script is informational; the regression
guard lives in tests/test_load_sanity.py (no brittle wall-clock asserts).
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:////tmp/simcards_bench.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "benchmark-secret"

import simcards_backend.models  # noqa: E402, F401
from simcards_backend.core.database import Base, SessionLocal, engine  # noqa: E402
from simcards_backend.core.security import hash_password  # noqa: E402
from simcards_backend.models import (  # noqa: E402
    AccountStatus,
    Branch,
    BranchType,
    BrandAmbassador,
    CommissionRule,
    Dealer,
    PeriodType,
    Role,
    SafaricomImport,
    SafaricomImportStatus,
    SaleEvent,
    ScannedVia,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    Target,
    User,
)
from simcards_backend.services.commission import get_branch_summary  # noqa: E402
from simcards_backend.services.reconciliation import (  # noqa: E402
    ParsedSafaricomRow,
    reconcile_safaricom_import,
)
from simcards_backend.services.reports import generate_report, get_report_context  # noqa: E402
from simcards_backend.services.sales import get_commission_earned  # noqa: E402
from simcards_backend.tasks.report_generation import (  # noqa: E402
    generate_excel_report,
    generate_pdf_report,
)
from sqlalchemy import insert  # noqa: E402

PERIOD_START = date(2026, 7, 1)
PERIOD_END = date(2026, 7, 31)
DAYS_IN_PERIOD = 31

VOLUMES = {
    "small": {"branches": 3, "bas": 30, "sims": 3_000, "sales": 1_500},
    "medium": {"branches": 10, "bas": 100, "sims": 30_000, "sales": 15_000},
    "large": {"branches": 25, "bas": 250, "sims": 100_000, "sales": 60_000},
}

BENCH_DB = "/tmp/simcards_bench.db"


def _reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed(scale: str) -> dict:
    """Seed the benchmark dataset, returning id/role bookkeeping for queries."""
    cfg = VOLUMES[scale]
    n_branches = cfg["branches"]
    n_bas = cfg["bas"]
    n_sims = cfg["sims"]
    n_sales = cfg["sales"]
    bas_per_branch = n_bas // n_branches
    sims_per_branch = n_sims // n_branches

    with SessionLocal() as db:
        db.execute(insert(Dealer), {"id": 1, "name": "Bench Dealer", "safaricom_dealer_shortcode": "BENCH"})
        db.execute(
            insert(User),
            {
                "id": 1,
                "dealer_id": 1,
                "role": Role.HQ.value,
                "email": "bench-hq@example.com",
                "password_hash": hash_password("benchpass"),
                "status": AccountStatus.ACTIVE.value,
            },
        )
        db.execute(
            insert(Branch),
            [
                {
                    "id": b + 1,
                    "dealer_id": 1,
                    "name": f"Branch {b + 1}",
                    "type": BranchType.SHOP.value,
                    "id_number": f"BNCH-BR-{b + 1}",
                    "photo_url": "https://example.com/bench.jpg",
                    "created_by": 1,
                }
                for b in range(n_branches)
            ],
        )
        db.execute(
            insert(BrandAmbassador),
            [
                {
                    "id": i + 1,
                    "dealer_id": 1,
                    "branch_id": (i // bas_per_branch) + 1,
                    "user_id": i + 2,
                    "name": f"BA {i + 1}",
                    "phone_msisdn": f"2547{i + 1:08d}",
                    "id_number": f"BNCH-BA-{i + 1}",
                    "photo_url": "https://example.com/bench-ba.jpg",
                    "status": AccountStatus.ACTIVE.value,
                }
                for i in range(n_bas)
            ],
        )
        db.execute(
            insert(User),
            [
                {
                    "id": i + 2,
                    "dealer_id": 1,
                    "role": Role.BA.value,
                    "email": f"bench-ba-{i + 1}@example.com",
                    "password_hash": hash_password("benchpass"),
                    "branch_id": (i // bas_per_branch) + 1,
                    "ba_profile_id": i + 1,
                    "status": AccountStatus.ACTIVE.value,
                }
                for i in range(n_bas)
            ],
        )
        db.execute(
            insert(CommissionRule),
            {
                "id": 1,
                "dealer_id": 1,
                "name": "Bench Rate",
                "amount_per_sim": Decimal("50.00"),
                "effective_from": datetime(2026, 1, 1),
                "effective_to": None,
                "created_by": 1,
            },
        )
        db.execute(
            insert(Target),
            [
                {
                    "id": i + 1,
                    "dealer_id": 1,
                    "branch_id": i + 1,
                    "period_type": PeriodType.MONTHLY.value,
                    "quantity": 500,
                    "effective_from": datetime(2026, 7, 1),
                    "effective_to": None,
                    "set_by": 1,
                }
                for i in range(n_branches)
            ],
        )
        db.execute(
            insert(StockBatch),
            [
                {
                    "id": b + 1,
                    "dealer_id": 1,
                    "source": StockBatchSource.BOX_SCAN.value,
                    "source_reference": f"BENCH-BOX-{b + 1}",
                    "quantity": sims_per_branch,
                    "imported_by": 1,
                }
                for b in range(n_branches)
            ],
        )
        db.execute(
            insert(SimCard),
            [
                {
                    "id": i + 1,
                    "dealer_id": 1,
                    "serial_number": str(30_000_000_000_000_000_000 + i),
                    "stock_batch_id": (i // sims_per_branch) + 1,
                    "status": (
                        SimStatus.SOLD.value if i < n_sales else SimStatus.WITH_BRANCH.value
                    ),
                    "current_branch_id": (i // sims_per_branch) + 1,
                    "current_ba_id": None,
                }
                for i in range(n_sims)
            ],
        )
        db.execute(
            insert(SaleEvent),
            [
                {
                    "id": i + 1,
                    "dealer_id": 1,
                    "sim_card_id": i + 1,
                    "ba_id": ((i // sims_per_branch) * bas_per_branch) + (i % bas_per_branch) + 1,
                    "branch_id": (i // sims_per_branch) + 1,
                    "sold_at": datetime.combine(
                        PERIOD_START + timedelta(days=i % DAYS_IN_PERIOD), datetime.min.time()
                    )
                    + timedelta(minutes=(i * 7) % 1440),
                    "scanned_via": ScannedVia.CAMERA.value,
                    "commission_rule_id": 1,
                    "commission_amount": Decimal("50.00"),
                }
                for i in range(n_sales)
            ],
        )
        db.commit()

    return {
        "n_branches": n_branches,
        "n_bas": n_bas,
        "n_sims": n_sims,
        "n_sales": n_sales,
        "report_context_kwargs": None,
    }


def _time(label: str, fn) -> float:
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    print(f"    {label:<32} {elapsed:8.3f}s")
    return elapsed


def bench(scale: str, include_exports: bool = True) -> dict:
    print(f"\n== Seeding scale={scale} ==")
    _seed(scale)

    results: dict = {}
    cfg = VOLUMES[scale]

    with SessionLocal() as db:
        hq_user = db.get(User, 1)
        context = get_report_context(hq_user, branch_filter=None)
        report_data = {}

        print("  timings:")
        results["generate_report"] = _time(
            "generate_report(MONTHLY)",
            lambda: report_data.update(
                generate_report(
                    db,
                    context=context,
                    period_type="MONTHLY",
                    period_start=PERIOD_START,
                    period_end=PERIOD_END,
                )
            ),
        )
        results["get_commission_earned"] = _time(
            "get_commission_earned(all)",
            lambda: get_commission_earned(db, dealer_id=1),
        )
        results["get_branch_summary"] = _time(
            "get_branch_summary(all)",
            lambda: get_branch_summary(db, actor=hq_user),
        )

        def _reconcile() -> None:
            rows: list[ParsedSafaricomRow] = []
            for i in range(cfg["sales"]):
                rows.append(
                    ParsedSafaricomRow(
                        serial_number=str(30_000_000_000_000_000_000 + i),
                        top_up_date=PERIOD_START + timedelta(days=i % DAYS_IN_PERIOD),
                        top_up_amount=Decimal("50.00"),
                        cumulative_commission=Decimal("200.00"),
                        fraud_flagged=(i % 97 == 0),
                        fraud_reason="Suspicious" if i % 97 == 0 else None,
                    )
                )
            for i in range(cfg["sales"], cfg["sales"] + 2_000):
                rows.append(
                    ParsedSafaricomRow(
                        serial_number=str(90_000_000_000_000_000_000 + i),
                        top_up_date=PERIOD_START + timedelta(days=i % DAYS_IN_PERIOD),
                        top_up_amount=Decimal("50.00"),
                        cumulative_commission=Decimal("200.00"),
                        fraud_flagged=False,
                        fraud_reason=None,
                    )
                )
            imp = SafaricomImport(
                dealer_id=1,
                uploaded_by_id=1,
                file_reference="bench-synthetic",
                report_date=PERIOD_END,
                status=SafaricomImportStatus.COMPLETED,
            )
            db.add(imp)
            db.flush()
            reconcile_safaricom_import(db, safaricom_import=imp, rows=rows)

        results["reconcile_safaricom_import"] = _time(
            "reconcile_safaricom_import",
            _reconcile,
        )

        if include_exports:
            pdf_path = "/tmp/simcards_bench_report.pdf"
            xlsx_path = "/tmp/simcards_bench_report.xlsx"
            for path in (pdf_path, xlsx_path):
                if os.path.exists(path):
                    os.remove(path)
            results["generate_pdf_report"] = _time(
                "generate_pdf_report",
                lambda: generate_pdf_report(report_data, pdf_path),
            )
            results["generate_excel_report"] = _time(
                "generate_excel_report",
                lambda: generate_excel_report(report_data, xlsx_path),
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale",
        choices=list(VOLUMES),
        default="medium",
        help="volume preset (default: medium)",
    )
    parser.add_argument(
        "--no-exports",
        action="store_true",
        help="skip PDF/xlsx export generation timings",
    )
    args = parser.parse_args()

    _reset_schema()
    results = bench(args.scale, include_exports=not args.no_exports)

    print("\n== Results (s) ==")
    print("| metric | seconds |")
    print("|---|---|")
    for metric, seconds in results.items():
        print(f"| {metric} | {seconds:.3f} |")
    print(f"\nscale={args.scale} volumes={VOLUMES[args.scale]}")


if __name__ == "__main__":
    main()
