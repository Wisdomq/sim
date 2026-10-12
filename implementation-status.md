# Implementation Status — Phases 7 & 8

Multi-tenant SIM stock & sales tracking platform (Safaricom dealers).
Backend: FastAPI + PostgreSQL + Celery.

| Phase | Title | Status |
|-------|-------|--------|
| 6 | End-to-end flow | Complete (existing) |
| 7 | Login inactivity flagging | **Complete** |
| 8 | Safaricom reconciliation | **Complete** |
| 9 | Reporting & Export | **Complete** |
| 11 | Flutter mobile app (BA / Branch / HQ) | **Complete** |
| 12 | HQ Web Portal | **Complete** |
| 13 | Cross-cutting polish (seed, E2E, deploy/CI, ops) | **Complete** |

---

## Phase 7 — Login Inactivity Flagging

Reference: design §6.10, FR-LOGIN-02/03/04, tasks.md B-07-01/02/03.

**Behavior implemented**

- A scheduled daily job checks each **Branch** and **BA** account's most recent
  `LoginEvent`. If more than **3 days** have passed with no login, the system:
  1. Creates an `AccountFlag` (`INACTIVE_3_DAYS`), one per inactivity episode
     (accounts with an open flag are skipped → idempotent).
  2. Sets the account `status` to `FLAGGED_INACTIVE`.
  3. Creates an in-app `Notification` for every active HQ user (design §6.10:
     "in-app notification, surfaced on the HQ dashboard").
  4. Writes an `ACCOUNT_FLAGGED_INACTIVE` audit log entry.
- Accounts that **never logged in** are only flagged once they have existed
  longer than the inactivity window (newly created accounts are not flagged).
- **Auto-clear on login**: when a `FLAGGED_INACTIVE` Branch/BA logs in again,
  any open flags are resolved and `status` returns to `ACTIVE`.

### Files added / changed

| File | Change |
|------|--------|
| `backend/src/simcards_backend/models/enums.py` | Added `NotificationType` |
| `backend/src/simcards_backend/models/entities.py` | Added `Notification` model |
| `backend/src/simcards_backend/models/__init__.py` | Exports `Notification`, `NotificationType` |
| `backend/src/simcards_backend/services/inactivity.py` | New: `flag_inactive_accounts()`, `default_cutoff()`, `InactivityFlagOutcome` |
| `backend/src/simcards_backend/tasks/inactivity.py` | New: `flag_inactive_accounts_scheduled` Celery task |
| `backend/src/simcards_backend/celery_app.py` | Registered task + beat schedule `flag-inactive-accounts-daily` (24h) |
| `backend/src/simcards_backend/tasks/__init__.py` | Exports `tasks.inactivity` |
| `backend/src/simcards_backend/api/routes/auth.py` | Login auto-clear: `FLAGGED_INACTIVE → ACTIVE` + resolve open flags |
| `backend/src/simcards_backend/api/routes/flags.py` | New flags + notifications router |
| `backend/src/simcards_backend/api/router.py` | Registered `flags.router` |
| `backend/src/simcards_backend/schemas/flags.py` | New `AccountFlagResponse` |
| `backend/src/simcards_backend/schemas/notifications.py` | New `NotificationResponse` |
| `backend/alembic/versions/20260915_0002_add_notifications.py` | New migration: `notifications` table + RLS policy |
| `tests/test_inactivity_flags.py` | New tests |

### API endpoints (prefix `/api/v1`)

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| `GET` | `/flags` | HQ | List flags; `?resolved=true/false` filter; enriches `last_login_at` |
| `POST` | `/flags/{id}/acknowledge` | HQ | Record acknowledging HQ user |
| `POST` | `/flags/{id}/resolve` | HQ | Manually resolve a flag |
| `GET` | `/flags/notifications` | HQ | In-app notification feed; `?unread_only=true` |
| `POST` | `/flags/notifications/{id}/read` | HQ | Mark notification read |

---

## Phase 9 — Reporting & Export

Reference: design §6.11, FR-RPT-01/02/03, tasks.md B-09-01/02/03/04.

**Behavior implemented**

- Daily/weekly/monthly report endpoints for Branch (own + BAs) and HQ (all branches)
- Reports include: stock counts by state, sales counts, commission owed, performance % (FR-RPT-01/03)
- PDF export generation (reportlab) with formatted reports (FR-RPT-02, FR-HQ-09, FR-BR-06)
- Excel (xlsx) export generation (openpyxl) with raw tabular data (FR-RPT-02)
- Reconciliation headline inclusion in period reports once an import exists (FR-RPT-03, §6.11)
- Role-scoped access: BA self only; Branch own + its BAs; HQ everything + org rollup (FR-PERF-05/06/07)

### Files added / changed

|| File | Change |
||------|--------|
|| `backend/src/simcards_backend/schemas/reports.py` | New report request/response schemas |
|| `backend/src/simcards_backend/services/reports.py` | New: `generate_report()`, `get_report_context()`, stock/sales/performance aggregation functions |
|| `backend/src/simcards_backend/tasks/report_generation.py` | New: `generate_pdf_report()`, `generate_excel_report()` |
|| `backend/src/simcards_backend/api/routes/reports.py` | New reports router with export endpoints |
|| `backend/src/simcards_backend/api/router.py` | Registered `reports.router` |
|| `backend/src/simcards_backend/api/dependencies.py` | Added `require_hq_or_branch` dependency |
|| `tests/test_reports.py` | New comprehensive tests for reporting functionality |

### API endpoints (prefix `/api/v1`)

|| Method | Path | Access | Purpose |
||--------|------|--------|---------|
|| `POST` | `/reports` | HQ/Branch | Generate report data for specified period |
|| `POST` | `/reports/export` | HQ/Branch | Request PDF/XLSX export → `202` with file reference |
|| `GET` | `/reports/download/{file_path}` | HQ/Branch | Download generated report file |
|| `GET` | `/reports/list` | HQ/Branch | List available report files |

### Key Features

- **Role-based scoping**: Branch users see only their branch data; HQ can see all or filter by branch
- **Period flexibility**: Supports DAILY, WEEKLY, and MONTHLY report types
- **Export formats**: Both PDF (formatted) and Excel (tabular) generation
- **Reconciliation integration**: Automatically includes Safaricom reconciliation headlines when imports exist
- **Comprehensive data**: Stock counts by status, sales counts, commission owed, performance percentages, BA-level breakdowns
- **File management**: Dealer-isolated report storage with secure download access

---

## Phase 8 — Safaricom Reconciliation

Reference: design §6.6, FR-HQ-06, FR-REC-01…05, tasks.md B-08-02/03/04/05/06.

**Behavior implemented**

- HQ uploads a Safaricom **line-connection xlsx report** (multipart + report
  date). File is stored on the local filesystem under
  `uploads/safaricom/{dealer_id}/` and a `SafaricomImport` row is created with
  status `PROCESSING`.
- A single background worker (`run_reconciliation`) then:
  1. Parses the xlsx (`parse_safaricom_report_file`), column names resolved
     defensively by header text. Columns **I (Agent MSISDN)** and **J (BA)** are
     never read (FR-REC-04 / B-08-06).
  2. Matches every serial against the dealer's app sales (via `SaleEvent`) and
     writes `ReconciliationResult` + `ReconciliationLineDetail`, then marks the
     import `COMPLETED` (or `FAILED` on error, with rollback).
- Matching rules (design §6.6):

| Condition | Outcome |
|-----------|---------|
| Sold in app **and** present in file with a top-up | `MATCHED` |
| Sold in app but absent from file, or present without top-up | `SOLD_NOT_ACTIVATED` |
| In file (activated) but not sold in app | `ACTIVATED_NOT_RECORDED_SOLD` |

- Aggregates (design §6.6, "across matched rows"): `total_cumulative_commission`
  and `total_fraud_flagged` are summed over **MATCHED** rows only.
  `total_confirmed_activated_by_safaricom` = MATCHED count;
  `total_topped_up` = unique file serials with a top-up.
- Re-running an import is **idempotent** (prior result + details are replaced).
- `SAFARICOM_RECONCILIATION` audit log entry written per run.

### Files added / changed

| File | Change |
|------|--------|
| `backend/src/simcards_backend/services/reconciliation.py` | New: `ParsedSafaricomRow`, `reconcile_safaricom_import()` |
| `backend/src/simcards_backend/tasks/xlsx_parser.py` | Rewritten: `parse_safaricom_report_file()` |
| `backend/src/simcards_backend/tasks/reconciliation.py` | Rewritten: `run_reconciliation` Celery task |
| `backend/src/simcards_backend/schemas/reconciliation.py` | New import/result/line-detail schemas |
| `backend/src/simcards_backend/api/routes/reconciliation.py` | New router |
| `backend/src/simcards_backend/api/router.py` | Registered `reconciliation.router` |
| `tests/test_reconciliation.py` | New tests |

### API endpoints (prefix `/api/v1`)

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| `POST` | `/reconciliation/imports` | HQ | Upload xlsx report → `202` with `import_id` + `task_id` |
| `GET` | `/reconciliation/imports` | HQ | List imports for the dealer |
| `GET` | `/reconciliation/imports/{id}` | HQ | Headline numbers only (FR-REC-03) |
| `GET` | `/reconciliation/imports/{id}/detail` | HQ | Per-SIM drill-down; `?match_status=` filter; `limit`/`offset` |

---

## Phase 11 — Flutter Mobile App (`mobile/simcards_app`)

Reference: design §6.9/§7, FR-BA/BR/HQ/PERF, tasks.md F-11-01…12.

**Status**: F-11-01…12 implemented, wired, and verified: `flutter analyze` clean; `flutter test` green (6 tests); debug APK builds and launches on a Pixel 7 API 34 emulator (`adb install -r` over the previous build preserved app data — the Drift v1→v2 migration ran with no errors; no crashes, activity fully drawn). Visual E2E + real-device NFR-07 performance pass still recommended before release.

### What shipped

- **Auth (F-11-03)**: email+password login with refresh-token exchange, role-scoped redirect (BA/Branch/HQ), JWT claims parsing (unit-tested).
- **Local DB (F-11-02)**: Drift (SQLite) mirrors own SIM assignments, BAs, branches; sale-events outbox + pending sync items; **schema v2** with MigrationStrategy (adds `LocalBranches`, `LocalBrandAmbassadors.updatedAt`). Testable via `AppDatabase.forTesting` (in-memory native executor).
- **BA (F-11-04/05)**: one-screen scan-and-sell (`mobile_scanner`), offline queue + manual serial entry, conflict error UI; own performance % + commission with today/week/month tabs.
- **Sync engine (F-11-06)**: outbox pushed FIFO; conflicts are dropped from the outbox (never re-pushed) and flagged locally; remote changes pulled since `sync_cursor` (sim/BA/branch updates); auto-sync on login, connectivity regain, and 5-min timer; retry cap with `retry_count`.
- **Branch (F-11-07/08)**: BA list + detail (create w/ photo+ID path `create_ba_screen`), assign/reassign serials, return to branch/HQ with fulfillment, sold vs unsold per BA; daily/weekly/monthly report screen with per-BA breakdowns and PDF/Excel export + saved-report list.
- **HQ (F-11-09/10/11)**: stock intake (box-scan + pick-list PDF upload → async task), distribute, return-request workflow, commission rules + branch target config; reconciliation upload/summary/drill-down with match-status filters; consolidated reports with org→branch→BA rollup + export; inactivity flags feed (acknowledge/resolve) + notifications feed.

### Key screens (new/changed)

| Screen | Path |
|--------|------|
| Login | `features/auth/login_screen.dart` |
| BA home / scan-and-sell / performance | `features/ba/{ba_home_screen,scan/scan_screen,performance/performance_screen}.dart` |
| Branch home / BA mgmt / stock / returns / reports | `features/branch/{branch_home_screen,bas/*,stock/*,reports/branch_reports_screen}.dart` |
| HQ home / stock / returns / commission / recon / reports / flags | `features/hq/{hq_home_screen,stock/*,commission/*,reconciliation/*,reports/*,flags/*}.dart` |
| Sync engine / DB | `lib/core/sync/sync_service.dart`, `lib/core/db/database.dart` (+ regenerated `database.g.dart`) |
| Router | `lib/core/routing/router.dart` (routes: `/ba`, `/branch/*`, `/hq/*`) |

### Test commands

```bash
cd /Users/wisdommboya/Desktop/SIMCARDS/mobile/simcards_app
flutter analyze   # No issues found
flutter test      # 6 tests pass (auth JWT parse, login smoke, DB schema/conflict/outbox)
```

---

## Phase 12 — HQ Web Portal (`web/`)

Reference: design §7 (CRUD + monitoring), revised scope (user-confirmed): **web = HQ only**;
Branch/BA remain mobile-only. tasks.md W-12-00…08.

**Status**: W-12-00…08 complete. Backend tests: `118 passed, 5 skipped` (includes 4 new
photo-upload tests). Web: `npm run build` (tsc + vite) clean, `npm run lint` (oxlint) clean.
Browser-equivalent smoke done against the live dev server (`localhost:3000`, proxy → `:8000`):
HQ login + `/auth/me`, report generation (all-zero-but-shaped when no sales), box-scan intake
→ 5 SIMs, reconciliation upload → COMPLETED (1890 rows) → summary + detail + activated-by-month,
commission rule create, branch + BA create (both 201). Emulator re-smoke: app installs, launches,
no crashes (role-switch screens confirmed in Phase 11).

### What shipped

- **Backend addition (W-12-00)**: `POST /api/v1/uploads/photo` (multipart, any authenticated
  user; stores under `uploads/photos/{dealer_id}/`, returns `{"photo_url","file_reference"}`)
  + `GET /api/v1/uploads/photo/{filename}` (dealer-scoped `FileResponse`). Note: the accounts
  router has no `/accounts` prefix, so the endpoint lives at `/api/v1/uploads/photo`.
  Schema in `schemas/accounts.py`, service in `services/accounts.py`, route in
  `api/routes/accounts.py`, tests in `tests/test_photo_upload.py`.
- **Web app (W-12-01…05, 07)**: Vite 8 + React 19 + TypeScript SPA in `web/`.
  - `src/lib/api.ts` — axios client with bearer token + single-flight refresh interceptor;
    tokens: access in localStorage, refresh rotates in localStorage.
  - `src/lib/auth.tsx` — `AuthProvider` (`/auth/login`, `/auth/me` restore); `RequireHQ`
    route guard renders a **Denied** screen for `BRANCH`/`BA` roles (FR-AUTH-01/02/03).
  - `src/pages/Login.tsx`, `src/components/{AppLayout,RequireHQ}.tsx`, Mantine v9 AppShell.
  - Dashboard (W-12-02): DAILY/WEEKLY/MONTHLY via `POST /reports`; KPI cards (stock/sales/
    commission/performance), stock-by-status table, branch rollup → expandable per-BA
    `ba_summaries`, reconciliation headline cards.
  - Stock (W-12-03): pick-list PDF upload with `onUploadProgress` bar, box-scan intake,
    distribute-to-branch, return-request create + tracking.
  - Reconciliation (W-12-04): xlsx + report-date upload with progress + background poll,
    imports list, summary headline cards, per-line drill-down (match-status filter),
    activated-by-month view.
  - Management (W-12-05): branches + BAs with staged photo upload → create/list/remove,
    commission rules + branch targets, inactivity flags (acknowledge) + notifications feed.
  - Exports (W-12-07): `POST /reports/export` + poll `/reports/list`; `downloadReportFile`
    fetches via authenticated axios blob and triggers a browser download.
  - Vite dev server on port 3000 (`/:` proxy → `http://localhost:8000`, matches CORS allowlist).

### Test commands

```bash
# Backend (photo-upload tests included)
cd /Users/wisdommboya/Desktop/SIMCARDS
source backend/.venv/bin/activate && PYTHONPATH=backend/src pytest -q   # 118 passed, 5 skipped

# Web
cd /Users/wisdommboya/Desktop/SIMCARDS/web
npm run build   # tsc -b && vite build — clean
npm run lint    # oxlint — clean
npm run dev     # http://localhost:3000 (HQ login: hq@example.com / supersecret)
```

---

## Phase 13 — Cross-Cutting Polish

Reference: tasks.md Phase 13 (X-13-01…04).

**Status**: X-13-01…04 complete. Backend suite `118 passed, 5 skipped`; web
`npm run build` + `npm run lint` clean; live E2E `scripts/e2e_live.py` 35/35
against the running API + real Celery worker; `flutter test` 6/6.

### What shipped

- **X-13-01 demo seed** — `scripts/seed_demo.py` (`--reset` rebuilds the `QA13`
  tenant; run with `PYTHONPATH=backend/src backend/.venv/bin/python \
  scripts/seed_demo.py --reset`). Seeds dealer + 2 branches + 6 BAs + stock
  (box-scan + pick-list), 142 sales, targets, a COMPLETED recon import (40
  rows), an inactivity flag, and daily/weekly/monthly performance snapshots.
  **Backend bug fixed while verifying the seed**: `update_performance_snapshot`
  counted **all-time** sold SIMs for BRANCH/DEALER instead of period-scoped
  sales (branch daily showed 513%). Now counts `SaleEvent` within the period
  (`services/commission.py`), matching BA logic and AC-7.
- **X-13-02 live E2E** — `scripts/e2e_live.py` exercises AC-1…AC-9 against the
  running backend over HTTP (real worker for pick-list/recon tasks), plus the
  Dashboard report payload, then deletes its throwaway tenant. 35/35 PASS.
  Mobile: existing widget/unit tests green; a real-device or emulator
  click-through of the web + mobile UI remains the only manual step.
- **X-13-03 deployment/CI** — `infra/k3s/` (16-object Kustomize set: namespace,
  config, secrets, Postgres StatefulSet, Redis, API ×2, worker, beat, web
  nginx, ingress, RWX uploads PVC) + `infra/README.md`; `web/Dockerfile` +
  `nginx.conf` (production web host proxying `/api`); backend `Dockerfile`
  now also ships `alembic/`; `.github/workflows/ci.yml` (backend pytest gate,
  web lint+build gate, flutter test/analyze, GHCR image build+push; ruff
  non-blocking because of ~77 pre-existing lint items); `docs/play-store-prep.md`.
- **X-13-04 ops runbooks** — `docs/ops/{README,backup-restore,migrations,
  monitoring}.md`: scheduled `pg_dump` + uploads backup, PITR notes, restore
  and rollback procedures, Alembic upgrade/downgrade + autogenerate rules,
  health probes, Celery/logging telemetry guidance, alerting thresholds.

### Test commands

```bash
# Backend suite
cd /Users/wisdommboya/Desktop/SIMCARDS
source backend/.venv/bin/activate && PYTHONPATH=backend/src pytest -q   # 118 passed, 5 skipped

# Live E2E (needs uvicorn + celery worker on :8000)
PYTHONPATH=backend/src python scripts/e2e_live.py                          # 35/35 PASS

# Web
cd web && npm run build && npm run lint

# Mobile
cd mobile/simcards_app && flutter test                                      # 6/6
```

---

## Tests

New test files (follow existing API + service-level conventions):

- `tests/test_inactivity_flags.py`
  - Flag + notification creation for an inactive branch user (service + API).
  - Notification feed, read/unread, acknowledge/resolve flow.
  - Auto-clear on login (`FLAGGED_INACTIVE → ACTIVE`, open flags resolved).
  - Idempotency of repeated runs; never-logged-in-but-old accounts flagged;
    new accounts not flagged; BA cannot access the HQ feed.
- `tests/test_reconciliation.py`
  - Parser against a realistic 20-column layout (including `-` placeholders,
    `YYYYMMDD` dates, fraud flags).
  - Matching rules + aggregate totals (incl. "aggregates over MATCHED rows only")
    and idempotent re-run.
  - Upload → `202`, import status verified via Celery eager mode (synchronous
    task dispatch), list/summary/detail endpoints, filter + 404 + non-xlsx
    rejection (422).

Run with:

```bash
cd /Users/wisdommboya/Desktop/SIMCARDS
source backend/.venv/bin/activate
PYTHONPATH=backend/src pytest tests -v
```

---

## Notes & follow-ups

- **Celery beat**: `flag-inactive-accounts-daily` is registered in
  `celery_app.py` and a `celery_beat` service is defined in
  `docker-compose.yml` alongside `celery_worker`.
- **Environment (known, pre-existing)**: the checked-in `backend/venv` has
  broken third-party wheels under the installed Python (`click`, `charset_normalizer`,
  `pydantic_core` fail on import for celery/pdfplumber/pydantic). Not fixed here;
  code was syntax-checked (`py_compile`) and service logic verified against a
  fresh throwaway environment + the real Safaricom xlsx (1890 rows, all unique
  serials — parse produced 1890 rows with correct top-up/commission/fraud values).
- **No code changes kept from verification work** (temp venv + scripts lived
  outside the repo).
- **Phase 4 PDF parser false positive** (Move Order Number captured as a bogus
  serial) intentionally **not** fixed — out of scope.
- File storage uses the local filesystem (`settings.UPLOAD_DIR`, default
  `uploads/`). S3 object storage is a possible future swap-in.