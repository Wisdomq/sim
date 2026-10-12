# SIMCARDS — Session Continuity Summary (Phase 12 done)

## Objective
- **Phase 11 (Flutter app)** closed and verified: `flutter analyze` clean, 6/6 tests, debug APK builds + launches on emulator, Drift v1→v2 migration clean.
- **Phase 12 (HQ web portal + backend photo upload)** now COMPLETE per the user-confirmed revised scope: **web = HQ only** (Branch/BA are mobile-only via the single role-switching Flutter app); Mantine v9 + TanStack Query + axios + react-router (Vite 8 / React 19 / TS 6); backend `POST /uploads/photo` W-12-00.

## Important Details
- **Backend**: runs on `0.0.0.0:8000` (uvicorn, log `/tmp/simcards_api.log`, restarted after W-12-00 with new code); celery worker running (log `/tmp/simcards_celery.log`). Run tests: `cd /Users/wisdommboya/Desktop/SIMCARDS && source backend/.venv/bin/activate && PYTHONPATH=backend/src pytest -q` (add `-o log_cli=1` for debugging; full suite ~140s). Test DB `sqlite:////tmp/simcards_tests.db`, autouse reset in `tests/conftest.py`.
- **Web dev server** currently running: `./node_modules/.bin/vite --host 127.0.0.1 --port 3000` in `web/` (log `/tmp/simcards_web.log`); note `npm run dev` via nohup got killed here — launch with the explicit `--host 127.0.0.1` form. Vite config proxies `/api` → `http://localhost:8000` (backend CORS allowlist includes :3000).
- **Proof accounts** (shared backend DB): HQ `hq@example.com`/`supersecret`; Branch `branch@example.com`/`branchsecret`; BA `ba@example.com`/`basecret123`. Smoke demo data on dealer 1: 5 box-scanned SIMs (`8994...123-127`), branch "Web Test Branch" (id 2) + BA "Web BA", commission rule "Demo per-SIM" (12.50), recon imports #1 FAILED (4-byte stub) + #2 COMPLETED (1890 rows), report exports in `uploads/reports/1/`.
- **Accounts router has NO `/accounts` prefix** → photo endpoints live at `/api/v1/uploads/photo` (+ `/uploads/photo/{filename}`). Other accounts endpoints: `/api/v1/branches`, `/api/v1/brand-ambassadors`.
- **BrandAmbassadorResponse has NO `email` field** (name/phone_msisdn/id_number/photo_url/status/branch_id/user_id). BranchResponse: id, dealer_id, name, type, id_number, photo_url, created_by_id, created_at.
- **Mantine v9 specifics**: CSS via `@mantine/{core,notifications,dates}/styles.css`; `useDisclosure` from `@mantine/hooks` (not core); `notifications.show()` requires a `message`; `MonthPickerInput` uses string values (avoid — used native `<input type="date/month">` instead). Decimal fields serialize as strings (`"12.50"`) — `formatMoney`/`formatPercent` in `web/src/lib/reports.ts` handle that. Report: `POST /reports` `{period_type, period_start, period_end, branch_id?}`; export `POST /reports/export` → 202; files `GET /reports/list`; download `GET /reports/download/{file_path}` with `responseType:'blob'` (path includes `uploads/reports/{dealer_id}/…`).
- **Emulator**: `export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"`; package = `com.simcards.simcards_app` (NOT com.example). Device `emulator-5554` (boot_completed=1); app launches, no crashes. APK: `mobile/simcards_app/build/app/outputs/flutter-apk/app-debug.apk`.
- `web/package.json`: name `simcards-web`; scripts `build` (tsc -b && vite build; rolldown chunk-size warning is harmless), `lint` (oxlint).

## Work State
### Completed (Phase 12)
- W-12-00 photo upload: `PhotoUploadResponse` (schemas/accounts.py); photo service (`photo_dir_for`/`save_uploaded_photo`/`resolve_photo`, UPLOAD_DIR monkey-patchable for tests) (services/accounts.py); POST/GET routes in api/routes/accounts.py; `tests/test_photo_upload.py` (4 tests). Live: upload 201 + fetch 200.
- W-12-01 web scaffold: `web/` (Vite+TS); `src/lib/{api,tokens,auth}.ts(x)`, `src/components/{AppLayout,RequireHQ}.tsx`, `src/pages/{Login,Denied}.tsx`, `src/router.tsx`, `src/types/api.ts`. RequireHQ → Denied screen for BRANCH/BA.
- W-12-02 Dashboard: `src/lib/reports.ts` + `src/pages/Dashboard.tsx` (period segmented control, KPI cards, stock-by-status, branch rollup w/ expandable BA rows, recon headlines, export dispatch + poll + blob download).
- W-12-03 Stock: `src/lib/stock.ts` + `src/pages/Stock.tsx` (Intake/Distribute/Returns tabs; pick-list upload w/ `onUploadProgress` + "parsing queued" (no task-status endpoint exists); box-scan; distribute; return-requests create/track). Live box-scan verified (201, 5 SIMs).
- W-12-04 Reconciliation: `src/lib/recon.ts` + `src/pages/Reconciliation.tsx` (xlsx+report-date upload w/ progress + background poll, imports list, headline cards, detail drill-down w/ match-status filter, activated-by-month). Live: real xlsx → COMPLETED (1890 rows).
- W-12-05 Management: `src/lib/hq.ts` + `src/pages/Management.tsx` (Branches + BAs create/list/remove w/ staged photo upload, Commission rules + targets, Flags + notifications feed). Live: commission rule 201, branch+BA create 201.
- W-12-06 emulator role-switch smoke (relaunch clean; role switching verified in Phase 11). W-12-07 export downloads wired (blob + auth) in Dashboard.
- W-12-08 verification + docs: backend `118 passed, 5 skipped`; web build+lint clean; API-level smoke via Vite proxy for login/me/reports/intake/recon/commission/branches/BA-create; implementation-status.md Phase 12 section added; tasks.md W-12-00..08 all [x].

### Active
- None.

### Blocked
- None.

## Next Move
- All queue items done; no in-progress todos. Remaining options for the user:
  1. **Visual QA**: open http://localhost:3000 (HQ login) in a browser — verify layout, dashboard, recon detail, Management create flows, and export downloads render properly (this session verified via API + build only; the model cannot view screenshots).
  2. **Real-device / NFR-07 performance pass** on the Flutter app (recommended pre-release per Phase 11 notes).
  3. **Cleanup optional**: broker live-DB smoke data (FAILED recon import #1, "Live Photo" dealer id 2, test branch/BA/rule) or reset the demo DB before demos.
  4. Git init + first commit if desired (workspace is not yet a git repo).

## Relevant Files
- Backend: `backend/src/simcards_backend/api/routes/{accounts,stock,reports,reconciliation,commission,flags}.py`, `api/dependencies.py`, `schemas/{accounts,reports,commission,reconciliation,flags,notifications}.py`, `core/config.py` (UPLOAD_DIR, CORS), `models/enums.py`.
- Web: `web/src/lib/{api,tokens,auth,reports,stock,recon,hq}.ts(x)`, `web/src/pages/{Login,Denied,Dashboard,Stock,Reconciliation,Management}.tsx`, `web/src/components/{AppLayout,RequireHQ}.tsx`, `web/src/router.tsx`, `web/vite.config.ts`, `web/package.json`.
- Mobile (done; only W-12-06 touch-ups possible): `mobile/simcards_app/lib/...`.
- Docs: `/Users/wisdommboya/Desktop/SIMCARDS/tasks.md` (Phase 12 W-12-00..08 all checked), `/Users/wisdommboya/Desktop/SIMCARDS/implementation-status.md` (Phase 12 section added).