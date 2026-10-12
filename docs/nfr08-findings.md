# NFR-08 — Load / Performance Findings (B-10-06)

Measured 2026-09-19 on macOS (darwin), Python 3.11, SQLite (`scripts/benchmark_report.py`).
The script seeds an isolated benchmark DB and times the real service/export paths
behind the report API; it does **not** include HTTP/middleware/network overhead.

## Interpretation of NFR-08

NFR-08 ("report generation within reasonable time") is interpreted as: an HQ
consolidated monthly report plus one export (PDF or xlsx) should complete within
~5s at Medium volume and ~20s at Large volume for a single dealer. The heaviest
comparable operation (reconciliation matching) is included as a sanity readout.

## Volumes

| scale  | branches | BAs | SIMs  | sales |
|--------|---------:|----:|------:|------:|
| small  |        3 |  30 |  3,000|  1,500|
| medium |       10 | 100 | 30,000| 15,000|
| large  |       25 | 250 |100,000| 60,000|

## Results (seconds)

| metric                      | small  | medium | large  |
|------------------------------|-------:|-------:|-------:|
| `generate_report` (MONTHLY)  | 0.019  | 0.078  | 0.301  |
| `get_commission_earned`      | 0.006  | 0.112  | 0.477  |
| `get_branch_summary`         | 0.001  | 0.015  | 0.099  |
| `reconcile_safaricom_import` | 0.077  | 0.391  | 1.485  |
| `generate_pdf_report`        | 0.006  | 0.012  | 0.025  |
| `generate_excel_report`      | 0.006  | 0.012  | 0.020  |

## Verdict

- All measured paths are far inside budget. Worst single op is reconciliation at
  **1.485s @ Large**; a complete report + export at Large is ~0.35s.
- **No performance gap confirmed** → per the agreed approach, no query rewrites
  (`get_commission_earned` sum, `get_ba_sales_summaries` N+1, `get_branch_summary`)
  were applied — the Python-side sums and per-BA queries stay negligible at the
  seeded ceiling.
- **Proactive safeguard applied:** `(dealer_id, top_up_date)` composite index on
  `reconciliation_line_details` (mirrors the `get_reconciliation_headlines` and
  drill-down filter paths). Model `__table_args__` + Alembic migration
  `20260919_0003_add_recon_detail_index`.

## Regression guard

`tests/test_load_sanity.py` re-runs the same data paths at a small seeded volume
and asserts the rollups stay numerically correct (`generate_report` totals,
commission rollup, branch summary counts, reconciliation line counts). It asserts
correctness only — no brittle wall-clock timing.

Re-run benchmarks with:

    rm -f /tmp/simcards_bench.db "/tmp/simcards_bench.db-*"
    source backend/.venv/bin/activate
    PYTHONPATH="$PWD/backend/src" python scripts/benchmark_report.py --scale medium
    PYTHONPATH="$PWD/backend/src" python scripts/benchmark_report.py --scale large