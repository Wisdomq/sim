# SIM Stock & Sales Tracking Platform — Task Breakdown

Derived from `design.md` + `requirements.md`. **Backend is the priority** — all backend work lands before any frontend work. Frontend begins only after the backend is solid and testable.

Legend: `[ ]` = not started · `[~]` = in progress · `[x]` = done

---

## Phase 0 — Environment & Project Scaffolding (Backend-first)

- [x] `B-00-01` Create project root with `backend/`, `mobile/`, `web/`, `infra/` directories and a top-level `README.md`
- [x] `B-00-02` Python 3.11 venv + `pyproject.toml`; pin FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, JWT libs, Celery, redis, pdfplumber/PyMuPDF, openpyxl/pandas, reportlab
- [x] `B-00-03` `docker-compose.yml` with PostgreSQL 17, Redis, API service, and Celery worker (local dev parity with prod)
- [x] `B-00-04` FastAPI app skeleton: settings (pydantic-settings + `.env`), DB session wiring, health-check endpoint, structured logging, request IDs
- [x] `B-00-05` `.gitignore`, `.env.example`, pre-commit hooks (ruff + mypy)

## Phase 1 — Data Model, Migrations & DB Layer (Backend)

- [x] `B-01-01` SQLAlchemy models for all core entities (dealer-scoped per design §5.1):
      `Dealer`, `User`, `Branch`, `BrandAmbassador`, `Target`, `PerformanceSnapshot`,
      `LoginEvent`, `AccountFlag`, `StockBatch`, `SimCard`, `StockTransfer`,
      `SaleEvent`, `ReturnEvent`, `CommissionRule`, `SafaricomImport`,
      `ReconciliationResult`, `ReconciliationLineDetail`, `AuditLog`
- [x] `B-01-02` Every tenant-scoped table carries `dealer_id`; serial unique **per dealer** (`SimCard.serial_number`)
- [x] `B-01-03` Alembic migration for full schema, including indexes (serial per dealer, branch, BA, period keys)
- [x] `B-01-04` PostgreSQL Row-Level Security policies on all dealer-scoped tables as defense-in-depth (NFR-02)
- [x] `B-01-05` Enum/choice constraints for: roles (`HQ|BRANCH|BA`), SIM states (`IN_HQ_STOCK|WITH_BRANCH|WITH_BA|SOLD|RETURNED_TO_BRANCH|RETURNED_TO_HQ|EXPIRED`), transfer/return/reconcile statuses
- [x] `B-01-06` AuditLog write-path helper: actor + timestamp + action on every stock movement, account create/remove, commission change (NFR-04, FR-HQ-04)

## Phase 2 — Auth, Multi-Tenancy & Access Control (Backend)

- [x] `B-02-01` JWT auth (access + refresh tokens, refresh-token rotation, short-lived access), email+password, bcrypt/argon2, rate-limited login (NFR-10)
- [x] `B-02-02` Token claims: `dealer_id`, `role`, `branch_id`/`ba_id` where relevant
- [x] `B-02-03` `get_current_user` + role/permission dependencies matching the permission matrix (requirements §5) — HQ/Branch/BA scoping on every endpoint
- [x] `B-02-04` Login-event recording (FR-LOGIN-01) on every successful login
- [x] `B-02-05` Tenant isolation guard layer: every query scoped by `dealer_id` from token, never from request body (FR-TEN-01/02)

## Phase 3 — Tenant Setup & Account Management (Backend)

- [x] `B-03-01` Dealer signup/onboarding (creates tenant root + first HQ user)
- [x] `B-03-02` HQ: create Branch account with **ID number + current photo** (required, else reject — FR-HQ-10, AC-9)
- [x] `B-03-03` HQ: remove Branch account; view all branches (FR-HQ-10)
- [x] `B-03-04` HQ: create BA account under a Branch with **ID number + current photo** (FR-HQ-11 creation path; AC-9)
- [x] `B-03-05` QA Check: remove BA account is **HQ-only** — Branch endpoint is rejected (FR-HQ-11, FR-BR-07, AC-5)
- [x] `B-03-06` Branch: create BA account under itself (with photo+ID) (FR-BR-01)

## Phase 4 — Stock Intake & Lifecycle (Backend)

- [x] `B-04-01` HQ: upload Safaricam pick-list PDF → background worker parses each `<<Lot>>` block → creates `StockBatch` per lot + one `SimCard` per serial (`IN_HQ_STOCK`) (FR-HQ-01, FR-STK-01, AC-1)
- [x] `B-04-02` HQ: box/pack barcode scan intake → maps to 100 serials via pre-registered lot or serial-range map → creates stock (FR-HQ-02)
- [x] `B-04-03` Duplicate-serial protection: re-scan of known serial is a no-op + warning, never a duplicate (FR-STK-02)
- [x] `B-04-04` HQ: distribute stock (quantity or specific serials) HQ→Branch: status updates, `StockTransfer` (`DISTRIBUTION`) row + AuditLog (FR-HQ-03, FR-STK-03)
- [x] `B-04-05` Branch: assign/transfer SIMs from branch pool ↔ BA and BA→BA (within same branch): `StockTransfer` (`REASSIGNMENT`) (FR-BR-02, FR-STK-03)
- [x] `B-04-06` Branch: mark BA's unsold SIM returned to branch (`RETURNED_TO_BRANCH`) (FR-BR-04, §6.5)
- [x] `B-04-07` HQ: request stock return → `ReturnEvent` (`REQUESTED`) → Branch fulfills → `RETURNED_TO_HQ`, event `COMPLETED` (FR-HQ-04, FR-BR-04, §6.5)
- [x] `B-04-08` Expiry flagging: scheduled job marks unsold SIMs past `expiry_date` as `EXPIRED`, surfaced to Branch + HQ (FR-STK-04, §6.5)

## Phase 5 — Sales, Offline Sync & Conflict Safety (Backend)

- [x] `B-05-01` BA sale endpoint: validate SIM is `WITH_BA` + owned by this BA; write `SaleEvent` (with `sold_at` local + `synced_at` server), set `SOLD` (FR-BA-01/02, §6.4, AC-2)
- [x] `B-05-02` Offline sync queue API: accept client-generated UUID events with `pending_sync` flag, in creation order (FR-BA-04, NFR-01, §7)
- [x] `B-05-03` Idempotent sync: client UUID prevents duplicate rows on retry (§7)
- [x] `B-05-04` Conflict handling: server = source of truth for `SimCard.status`; concurrent/second scan rejected with clear conflict response (NFR-05, AC-3, §7)
- [x] `B-05-05` Pull-side of sync: deliver server changes relevant to user scope since `last_synced_at` cursor (branch/BA SIMs) (§7)
- [x] `B-05-06` Binding sale to `CommissionRule.amount_per_sim` in effect at time of sale (snapshot) (FR-COM-01/02, §6.7)

## Phase 6 — Commission, Targets & Performance (Backend)

- [x] `B-06-01` HQ: create/update `CommissionRule` (amount per SIM, effective dates, history preserved) (FR-COM-01, FR-HQ-05)
- [x] `B-06-02` Commission calculation per BA/Branch/Dealer for any period, using rate-at-time-of-sale (FR-COM-02, §6.7)
- [x] `B-06-03` HQ: set/update Branch `Target` (DAILY/WEEKLY/MONTHLY, quantity, `effective_from`, supersedes going forward, history kept) (FR-PERF-01, FR-HQ-13, AC-6)
- [x] `B-06-04` BA daily target derivation: branch daily target ÷ current active BAs; weekly/monthly filled from ratio if HQ only set subset (FR-PERF-02, AC-6)
- [x] `B-06-05` Mid-period BA headcount change recalculates per-BA split going forward, never retroactively (FR-PERF-03, AC-6)
- [x] `B-06-06` `PerformanceSnapshot` recompute (BA/Branch/Dealer level, percentage achieved) on schedule or on sale (FR-PERF-04, §6.8)
- [x] `B-06-07` Role-scoped performance exposure: BA self only; Branch own + its BAs; HQ everything + org rollup (FR-PERF-05/06/07, FR-BR-09, FR-HQ-14)
- [x] `B-06-08` Branch summary endpoints: sold/unsold counts per BA and per branch (FR-BR-03, FR-HQ-12)

## Phase 7 — Login Inactivity Flagging (Backend)

- [x] `B-07-01` Daily scheduled job: flag Branch/BA accounts with no login for 3 consecutive days → `AccountFlag` (`INACTIVE_3_DAYS`), status `FLAGGED_INACTIVE` (FR-LOGIN-02, AC-8)
- [x] `B-07-02` HQ notification/in-app feed when a flag is raised (account + last-login date) (FR-LOGIN-03, AC-8)
- [x] `B-07-03` Auto-clear flag on next login; HQ acknowledge/resolve support (FR-LOGIN-04, §6.10)

## Phase 8 — Safaricom Import & Reconciliation (Backend)

- [x] `B-08-01` HQ: upload daily Safaricom line-connection xlsx → object storage + `SafaricomImport` (status `PROCESSING|COMPLETED|FAILED`) (FR-HQ-06, FR-REC-01)
- [x] `B-08-02` Background worker: parse xlsx, match per serial → activated (`Top Up Date`/`Top Up Amount`), aggregate `Cumulative Commission`, `Fraud Flagged` counts (FR-REC-01/02, §6.6)
- [x] `B-08-03` `ReconciliationResult` headline numbers first: confirmed sold & topped-up quantity, cumulative commission, fraud count (FR-REC-02, FR-HQ-07, AC-4)
- [x] `B-08-04` `ReconciliationLineDetail` on drill-down only: dates, amounts, serials, fraud reasons, match status (`MATCHED|SOLD_NOT_ACTIVATED|ACTIVATED_NOT_RECORDED_SOLD`) (FR-REC-03, §6.6)
- [x] `B-08-05` Mismatch counts both directions: sold-in-app-not-in-Safaricom, in-Safaricom-not-sold-in-app (FR-REC-05)
- [x] `B-08-06` Confirm BA identity is **excluded** from matching logic (FR-REC-04)

## Phase 9 — Reporting & Export (Backend)

- [x] `B-09-01` Daily/weekly/monthly report endpoints (Branch = own + BAs; HQ = all) incl. stock counts by state, sales counts, commission owed, performance % (FR-RPT-01/03, FR-HQ-08, FR-BR-05)
- [x] `B-09-02` PDF export generation (reportlab): formatted report (FR-RPT-02, FR-HQ-09, FR-BR-06)
- [x] `B-09-03` Excel (xlsx) export generation (openpyxl): raw tabular data (FR-RPT-02)
- [x] `B-09-04` Reconciliation headline inclusion in period reports once an import exists (FR-RPT-03, §6.11)

## Phase 10 — Backend Hardening, Tests & API Docs (Backend)

- [x] `B-10-01` Acceptance-Criteria tests: AC-1 … AC-9 mapped to integration tests (see requirements §7)
- [x] `B-10-02` Unit tests: PDF `<<Lot>>` parser, xlsx parser, target derivation/split, commission history, reconciliation matching
- [x] `B-10-03` Tenant-isolation test: dealer A's tokens/rows never reach dealer B (FR-TEN-02, NFR-02)
- [x] `B-10-04` RBAC matrix test: every permission row in requirements §5 enforced on endpoints
- [x] `B-10-05` OpenAPI auto-docs `/docs`; consistent error schema; request validation everywhere
- [x] `B-10-06` Load/performance sanity: report generation within reasonable time at typical volumes (NFR-08; see docs/nfr08-findings.md)

---

## BACKEND GATE ✅ — Frontend work starts only when Phase 1–10 are complete & backend is proven (migrations clean, tests green, endpoints stable).

---

## Phase 11 — Flutter Mobile App (BA first, then Branch, then HQ)

- [x] `F-11-01` `flutter create` app; theme/branding; routing; shared API client + token storage (secure storage)
- [x] `F-11-02` Drift local DB: mirrored entities (own SIM assignments, BAs, local events) per design §7 (NFR-01)
- [x] `F-11-03` Login screen (email+password, refresh-token flow)
- [x] `F-11-04` **BA**: one-screen scan-and-sell via `mobile_scanner`/ML Kit; offline queue; conflict error UI (NFR-06/07, FR-BA-01/02/04)
- [x] `F-11-05` **BA**: own performance % + own commission (today/week/month) — self only (FR-BA-05, FR-PERF-05)
- [x] `F-11-06` Background sync engine: push pending queue in order, pull since last sync cursor, idempotent + conflict-aware (FR-BA-04, §7)
- [x] `F-11-07` **Branch**: BA management (create w/ photo+ID), SIM assignment/reassignment, returns to branch/HQ, sold-unsold per BA (FR-BR-01/02/03/04)
- [x] `F-11-08` **Branch**: reports + PDF/Excel export; branch + per-BA performance & commission (FR-BR-05/06/09/10, FR-PERF-06)
- [x] `F-11-09` **HQ**: stock intake (PDF upload picker + box-scan), distribution, returns request, commission + target config (FR-HQ-01/02/03/04/05/13)
- [x] `F-11-10` **HQ**: reconciliation summary (headline numbers) + drill-down detail (FR-HQ-06/07, FR-REC-02/03)
- [x] `F-11-11` **HQ**: consolidated reports + export; org/branch/BA performance rollup; inactivity flags feed (FR-HQ-08/09/14/15)
- [x] `F-11-12` Test on device/emulator: offline scan→sync flow, conflict case, low-end Android performance (NFR-06/07)

> Phase 11 notes: `flutter analyze` clean, `flutter test` 6/6 green (auth JWT parse, login smoke,
> DB schema v2 + conflict-no-repush + FIFO outbox/retry). Debug APK builds and launches on emulator
> (Pixel 7 API 34) with `adb install -r` (migration ran on preserved app data, no crashes).
> Build fix: pinned `flutter_plugin_android_lifecycle 2.0.24` — `file_picker` hardcodes
> android compileSdk 34 while the latest lifecycle AAR requires 36. Visual E2E walkthrough on a real
> low-end device + final performance check (NFR-07) still recommended before Play Store release.

## Phase 12 — HQ-only Web App (React/Vite + TypeScript back-office)

Scope decision (confirmed 2026-09-21): the web app serves **HQ only**. Branch and BA
**have no web access** — the guard layer rejects their tokens. Branch features remain
mobile-only (already shipped in Phase 11 as role-switching screens in the single Flutter
app: BA/Branch/HQ). A small backend photo-upload endpoint is added to support Branch/BA
creation with photo + ID from any client.

### Backend addition
- [x] `W-12-00` **Backend**: `POST /api/v1/uploads/photo` (multipart, any
      authenticated user) → stores under `uploads/photos/{dealer_id}/`, returns
      `{"photo_url", "file_reference"}`; schema + service + route + pytest; also
      adoptable from the mobile `create_ba_screen` later. *(note: accounts router has no
      `/accounts` prefix, so the endpoint lives at `/api/v1/uploads/photo`; verified live:
      upload 201 + fetch 200)*

### Web app (HQ only)
- [x] `W-12-01` Vite + TypeScript scaffold in `web/`; shared API client (same backend) with
      JWT + refresh-token interceptor; Mantine + TanStack Query + axios + react-router;
      `server.port=3000` + proxy `/api` → `localhost:8000` (matches CORS allowlist);
      OAuth-style route guards — **HQ-only login, Branch/BA tokens rejected**
      (FR-AUTH-01/02/03) *(note: Vite v8 + Mantine v9 + react-router v7; access token in
      localStorage + single-flight refresh interceptor; `RequireHQ` route guard renders a
      Denied screen for BRANCH/BA roles; verified login + `/auth/me` through the Vite proxy
      for both HQ and BRANCH tokens)*
- [x] `W-12-02` **HQ dashboard**: consolidated DAILY/WEEKLY/MONTHLY reports, org-wide
      performance % + commission rollup, stock-by-status, branch rollup → per-BA drill-down,
      reconciliation headlines (FR-HQ-08/14, FR-RPT-01/03) *(note: implemented as the
      Dashboard page calling `POST /reports` with a period segmented control; expandable
      branch rows show `ba_summaries`; export dispatch + `/reports/list` matching +
      blob download also live here)*
- [x] `W-12-03` **HQ stock**: pick-list PDF upload with progress bar, box-scan intake,
      distribution to branches, return-request creation + tracking (FR-HQ-01/02/03/04)
      *(note: implemented as Stock page with Intake/Distribute/Returns tabs; pick-list uses
      axios `onUploadProgress` + "parsing queued" state (no task-status endpoint exists);
      box-scan + distribute + returns create/track all verified live through the proxy)*
- [x] `W-12-04` **HQ reconciliation**: xlsx upload + report date with progress, imports list,
      summary headline cards, drill-down detail table (match-status filter + paging),
      activated-by-month view (FR-HQ-06/07, FR-REC-02/03/06) *(note: implemented as the
      Reconciliation page; live-verified with a real Safaricom xlsx: 202 → COMPLETED
      (1890 rows) → summary + per-line detail + activated-by-month)*
- [x] `W-12-05` **HQ management**: commission rules, branch targets, Branch accounts
      (create w/ photo+ID, list, remove — HQ only), BA accounts per branch (create w/ photo+ID,
      list, remove — HQ only), inactivity flags + notifications feed (FR-HQ-05/10/11/13/15,
      FR-LOGIN-02/03) *(note: implemented as the Management page with Accounts / Commission /
      Flags & alerts tabs; branch + BA creation with staged photo upload verified live (201))*
- [x] `W-12-06` **Branch: mobile-only** — verify role-switching screens in the single Flutter
      app (BA/Branch/HQ) on emulator; branch BA mgmt, reassignment, returns, per-BA reports
      ship via mobile (FR-BR-01→06). No branch web screens. *(note: shipped + smoke-verified
      in Phase 11; web access guarded to HQ in the RequireHQ route guard)*
- [x] `W-12-07` Export downloads wired to backend PDF/xlsx endpoints via authenticated
      axios blob (`GET /reports/download/{file_path}`); PDF + Excel export buttons across
      HQ dashboard/reports (FR-RPT-02, FR-HQ-09) *(note: `dispatchExport` POSTs and the
      Dashboard polls `/reports/list`; `downloadReportFile` fetches the file as a blob with
      auth headers and triggers a browser download)*

### Verification
- [x] `W-12-08` `pytest` + new photo-upload test; `npm run build` (tsc) + eslint; browser
      smoke with `hq@example.com`/`supersecret` (login, dashboard, export, recon upload,
      BA create w/ photo); Branch/BA web login rejected; emulator role-switch smoke
      *(note: full suite 118 passed / 5 skipped; web build+lint clean; API-level smoke of
      login, reports, intake, recon, commission, branch/BA creation all through the Vite
      proxy; Branch/BA tokens resolve to BRANCH/BA roles → Denied screen; emulator relaunch
      clean; implementation-status.md Phase 12 written)*
      (branch + HQ homes)

## Phase 13 — Cross-Cutting Polish

- [x] `X-13-01` Seed/demo script: dealer + branches + BAs + stock + sales for manual QA
      *(scripts/seed_demo.py --reset; runs against live Postgres; verifies via API: HQ login,
      flags callout, recon import COMPLETED 40 rows/32 activated, DAILY/WEEKLY/MONTHLY
      percentages sane. Fixed backend bug — BRANCH/DEALER performance snapshots counted
      all-time SOLD instead of period-scoped Sales (backend/src/.../services/commission.py);
      118 passed/5 skipped.)*
- [x] `X-13-02` End-to-end test of AC-1 … AC-9 through web/mobile against live backend
      *(scripts/e2e_live.py: provisions a throwaway tenant over HTTP against the running API +
      real Celery worker, asserts AC-1..AC-9 and the Dashboard report payload, cleans up.
      35/35 PASS, exit 0. Mobile: flutter test 6/6. Web consumed the live API via the Vite
      proxy (login, report, flags, recon) — a real browser click-through is the one remaining
      manual check.)*
- [x] `X-13-03` Deployment manifests (Docker/K3s), CI pipeline (lint → test → build), Play Store release prep notes
      *(infra/k3s/* 16-object manifest set + infra/README.md; backend + web Docker images
      build cleanly (Dockerfile fix: src/ + alembic/ copied before `pip install -e .`;
      web image is nginx-serving dist); .github/workflows/ci.yml (backend pytest gate, web
      lint+build, flutter test/analyze, docker build+push to GHCR; ruff non-blocking due to
      pre-existing debt); docs/play-store-prep.md.)*
- [x] `X-13-04` Operations: backup/restore, SQL migration runbook, monitoring/logging hooks
      *(docs/ops/{README,backup-restore,migrations,monitoring}.md; alembic runbook + upgrade
      command; hourly-cron backups/PITR; alerting thresholds; see infra/k3s + docs/.)*