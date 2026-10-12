# SIM Stock & Sales Tracking Platform — Design Document

Version 1.0 (Phase 1 scope) — Android app (Play Store) first, responsive web app second.

---

## 1. Overview

A multi-tenant platform that lets a Safaricom SIM card **dealer** manage the full life of a SIM card from the moment it is picked up from Safaricom's logistics point, through distribution to **Branches** (vans, physical shops, or an individual managing a team of Brand Ambassadors), down to the **Brand Ambassador (BA)** who sells it to an end customer — and then reconciles that internal record against Safaricom's own daily line-connection report.

Three account tiers, one inheritance chain:

```
Dealer (HQ)
   └── Branch (van / shop / individual)
          └── Brand Ambassador (BA)
```

Every SIM card, transfer, sale, and return is always traceable back to its owning Dealer.

---

## 2. Goals & Non-Goals (Phase 1)

**In scope**
- Multi-tenant support for many dealers, each with their own isolated data.
- HQ: stock intake (PDF pick-list parsing or box/pack barcode scan), distribution to branches, return handling, commission-rate configuration, Safaricom xlsx upload & reconciliation, consolidated reporting.
- Branch: BA account creation, SIM reassignment between its own BAs, consolidated sold/unsold view per BA and per branch, handling HQ return requests.
- BA: camera-based barcode scan to mark a SIM as sold. Nothing else.
- Daily/weekly/monthly reports (dashboard + PDF/Excel export) for Branch and HQ.
- Offline-first mobile app with background sync.

**Out of scope (Phase 1)**
- Customer KYC capture at point of sale.
- Payment/commission disbursement (e.g., M-Pesa payout integration) — the app only calculates and displays commission owed.
- Extra KPIs beyond sold/unsold counts, activation/top-up confirmation, cumulative commission, and fraud counts.
- Branch-type-specific behavior (van vs. shop vs. individual are labels only; identical functionality).

---

## 3. High-Level Architecture

```
┌────────────────────┐        ┌──────────────────────┐
│  Android App        │        │  Web App (responsive)│
│  (BA / Branch / HQ)  │        │  (Branch / HQ, BA optional)│
│  Offline-first store │        │  Thin client, online-only  │
└─────────┬────────────┘        └───────────┬───────────┘
          │  REST/JSON + sync queue          │
          └───────────────┬──────────────────┘
                           ▼
                 ┌───────────────────┐
                 │   API Gateway /    │
                 │   Backend service  │
                 │ (multi-tenant)     │
                 └─────────┬──────────┘
                           │
        ┌──────────────────┼───────────────────┐
        ▼                  ▼                    ▼
 ┌─────────────┐   ┌───────────────┐    ┌───────────────────┐
 │ PostgreSQL   │   │ Object storage │    │ Background workers │
 │ (primary DB, │   │ (uploaded PDFs,│    │ (PDF/xlsx parsing,  │
 │ per-tenant   │   │ xlsx files,    │    │ reconciliation,     │
 │ row scoping) │   │ generated      │    │ report generation)  │
 │              │   │ reports)       │    │                     │
 └─────────────┘   └───────────────┘    └───────────────────┘
```

- **Multi-tenancy model:** single database, single schema, every table scoped by `dealer_id` (row-level isolation), enforced both in the ORM layer and via PostgreSQL Row-Level Security policies as a defense-in-depth measure. Simpler to operate than per-tenant databases, and dealer counts/growth don't justify the extra ops overhead at this stage.
- **Sync model:** mobile app is offline-first with a local embedded database; a sync engine pushes/pulls deltas whenever connectivity is available (see §8).

---

## 4. Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Mobile app | **Flutter** | Single codebase ships Android first (Play Store) and can also compile to a web target later, reducing duplicate UI work between "Android first, web second." Strong offline/local-DB story, mature camera-barcode plugins (`mobile_scanner` / ML Kit), good performance on low-end Android devices common with field BAs. |
| Local/offline storage (mobile) | **SQLite via Drift** | Typed, reactive local database; plays well with a queue-based sync engine; battle-tested for offline-first apps. |
| Web app | **React (Vite) + TypeScript**, or **Flutter Web** | React recommended for the *dealer/branch back-office* web app since it's a richer dashboard/reporting UI than the field app — better ecosystem for tables, charts, and PDF/Excel export UX. Reuses the same backend API as mobile. (Flutter Web is a fallback if you want one codebase for everything and are willing to trade off some web-native polish.) |
| Backend API | **Python + FastAPI** | Matches your existing production experience (async, REST, good for background-job orchestration); strong libraries for PDF (`pdfplumber`/`PyMuPDF`) and Excel (`openpyxl`/`pandas`) parsing, which this app needs heavily for stock intake and Safaricom reconciliation. |
| Database | **PostgreSQL** | Relational integrity for the strict one-to-many Dealer→Branch→BA→SIM chain; row-level security for tenant isolation; solid support for reporting queries. |
| Background jobs | **Celery + Redis** (or FastAPI `BackgroundTasks`/`arq` for lighter needs) | PDF/xlsx parsing, reconciliation runs, and report generation are all better as async jobs than blocking the request. |
| Object storage | **S3-compatible bucket** (AWS S3, or Oracle Cloud Object Storage given your OCI background) | Store uploaded pick-list PDFs, Safaricom xlsx files, and generated PDF/Excel reports. |
| Auth | **JWT-based auth (access + refresh tokens)**, email + password, tenant-aware claims (`dealer_id`, `role`, `branch_id`/`ba_id` where relevant) | Matches your stated login method; stateless tokens work well for an offline-first mobile client that needs to operate without a live session. |
| Barcode scanning | **ML Kit Barcode Scanning** (via Flutter `mobile_scanner`) | On-device, offline-capable, no network dependency to read a barcode — important since scanning must work in low-connectivity areas. |
| Deployment | **Docker + Kubernetes (K3s)** | Matches your current production stack; straightforward to containerize FastAPI + Celery workers + Postgres. |
| Reporting exports | **Backend-generated**: `reportlab`/`weasyprint` for PDF, `openpyxl` for xlsx | Keeps export formatting consistent across mobile and web, generated server-side and downloaded/shared from either client. |

---

## 5. Data Model

### 5.1 Core entities

**Dealer** (tenant root)
- id, name, safaricom_dealer_shortcode, created_at

**User**
- id, dealer_id, role (`HQ` | `BRANCH` | `BA`), email, password_hash, branch_id (nullable, set for BRANCH/BA users), ba_profile_id (nullable), status (active/disabled), created_at

**Branch**
- id, dealer_id, name, type (`VAN` | `SHOP` | `INDIVIDUAL` — label only, no behavioral difference), id_number, photo_url (current photo, captured at creation — for audit/security), created_at, created_by (HQ user)

**BrandAmbassador (BA)**
- id, dealer_id, branch_id (exactly one, not nullable), user_id, name, phone_msisdn (used to match Safaricom's `BA` column later if ever needed), id_number, photo_url (current photo, captured at creation — for audit/security), status (incl. `FLAGGED_INACTIVE`), created_by (branch user), created_at

**Target**
- id, dealer_id, branch_id, period_type (`DAILY`|`WEEKLY`|`MONTHLY`), quantity (SIMs to sell), effective_from, effective_to, set_by (HQ user), created_at — HQ sets this at the Branch level; the system derives each BA's daily target from it (see §6.9).

**PerformanceSnapshot**
- id, dealer_id, subject_type (`BA`|`BRANCH`|`DEALER`), subject_id, period_type, period_start, period_end, target_quantity, actual_sold_quantity, percentage_achieved, computed_at — one row per subject per period, refreshed as sales come in.

**LoginEvent**
- id, dealer_id, user_id, role, logged_in_at, device_info (optional)

**AccountFlag**
- id, dealer_id, user_id, role, flag_type (`INACTIVE_3_DAYS`), flagged_at, resolved_at (nullable), acknowledged_by (HQ user, nullable)

**StockBatch** (a box/pack of 100 SIMs, or a PDF pick-list line-item lot)
- id, dealer_id, source (`PDF_IMPORT` | `BOX_SCAN`), source_reference (pick-list order no. / lot code e.g. `787561_GD0014656`, or box barcode), quantity, imported_by (HQ user), imported_at

**SimCard**
- id, dealer_id, serial_number (unique per dealer, indexed — this is the scanned barcode value), stock_batch_id, status (`IN_HQ_STOCK` | `WITH_BRANCH` | `WITH_BA` | `SOLD` | `RETURNED_TO_BRANCH` | `RETURNED_TO_HQ` | `EXPIRED`), current_branch_id (nullable), current_ba_id (nullable), expiry_date, created_at, updated_at

**StockTransfer** (any movement: HQ→Branch, Branch→BA, BA→BA within a branch, Branch→HQ return)
- id, dealer_id, sim_card_id, from_owner_type (`HQ`|`BRANCH`|`BA`), from_owner_id, to_owner_type, to_owner_id, transfer_type (`DISTRIBUTION`|`REASSIGNMENT`|`RETURN`), initiated_by (user_id), created_at

**SaleEvent**
- id, dealer_id, sim_card_id, ba_id, branch_id, sold_at, scanned_via (`CAMERA`), synced_at (for offline-first: local scan timestamp vs. server-received timestamp)

**ReturnEvent**
- id, dealer_id, sim_card_id, requested_by (HQ user, for HQ-requested returns), branch_id, return_date, reason (nullable), status (`REQUESTED`|`COMPLETED`)

**CommissionRule**
- id, dealer_id, name, amount_per_sim, effective_from, effective_to (nullable), created_by (HQ user) — HQ can change the rate over time; each SaleEvent should record which rule applied at time of sale for historical accuracy.

**SafaricomImport**
- id, dealer_id, uploaded_by (HQ user), file_reference (object storage path), report_date, uploaded_at, row_count, status (`PROCESSING`|`COMPLETED`|`FAILED`)

**ReconciliationResult** (one row per SafaricomImport, holding the headline numbers)
- id, dealer_id, safaricom_import_id, total_sold_in_app, total_confirmed_activated_by_safaricom, total_topped_up, total_cumulative_commission, total_fraud_flagged, unmatched_sold_not_in_safaricom_count, unmatched_in_safaricom_not_sold_in_app_count, generated_at

**ReconciliationLineDetail** (drill-down detail, only loaded on demand)
- id, reconciliation_result_id, sim_card_id (nullable if Safaricom row has no matching internal record), top_up_date, top_up_amount, cumulative_commission, fraud_flagged, fraud_reason, match_status (`MATCHED`|`SOLD_NOT_ACTIVATED`|`ACTIVATED_NOT_RECORDED_SOLD`)

**AuditLog**
- id, dealer_id, actor_user_id, action, entity_type, entity_id, metadata (json), created_at

### 5.2 Relationship summary

- Dealer 1—* Branch
- Branch 1—* BrandAmbassador
- Dealer 1—* StockBatch 1—* SimCard
- SimCard 1—* StockTransfer, 1—0..1 SaleEvent, 0..* ReturnEvent
- Dealer 1—* CommissionRule
- Dealer 1—* SafaricomImport 1—1 ReconciliationResult 1—* ReconciliationLineDetail
- Dealer 1—* Target (each tied to one Branch); Target 1—* PerformanceSnapshot (BA-level snapshots derived from it, plus the Branch's and Dealer's own roll-up snapshots)
- User (Branch/BA) 1—* LoginEvent; User 0..1 active AccountFlag at a time

Every row-level table carries `dealer_id` for tenant scoping, even where it's technically derivable through a join — this keeps row-level security policies simple and every query auditable/tenant-safe by default.

---

## 6. Core Workflows

### 6.1 Stock intake (HQ)
1. HQ uploads a Safaricom pick-list PDF **or** scans a box/pack barcode.
   - PDF path: background worker extracts each `<<Lot>>` block and its serials, creates one `StockBatch` per lot, and a `SimCard` row per serial, status `IN_HQ_STOCK`.
   - Box-scan path: HQ scans the barcode printed on the box; if the box barcode encodes/maps to a known lot of 100 serials (either pre-registered via the same PDF import, or via a box→serial-range mapping), the same 100 `SimCard` rows are created/activated in stock.
2. Duplicate serial protection: `serial_number` is unique per dealer; re-scanning an already-known serial is a no-op with a warning, not a duplicate insert.

### 6.2 Distribution (HQ → Branch)
1. HQ selects a quantity or specific serials from `IN_HQ_STOCK` and assigns to a Branch.
2. Each affected `SimCard.status` → `WITH_BRANCH`, `current_branch_id` set; a `StockTransfer` (`DISTRIBUTION`) row is written.

### 6.3 Branch → BA assignment / reassignment
1. Branch assigns SIMs from its `WITH_BRANCH` pool to a specific BA → status `WITH_BA`, `current_ba_id` set, `StockTransfer` (`REASSIGNMENT`) logged.
2. Branch can move a SIM from one BA to another BA **within the same branch** the same way (a fresh `REASSIGNMENT` transfer row).

### 6.4 Sale (BA)
1. BA scans a SIM's serial via the phone camera.
2. App checks the SIM is currently `WITH_BA` and owned by that BA (client-side check against local offline store; re-validated server-side on sync).
3. `SaleEvent` created locally, `SimCard.status` → `SOLD`. Queued for sync if offline.
4. On sync, server re-validates ownership/state to prevent conflicting concurrent sales (see §8.3).

### 6.5 Returns
- **Branch-initiated, day-to-day**: a BA's unsold SIM can be marked `RETURNED_TO_BRANCH` by the Branch (e.g., BA leaving, SIM near expiry) — logged as a `ReturnEvent` + `StockTransfer`.
- **HQ-requested return**: HQ creates a `ReturnEvent` (`REQUESTED`) against a Branch (e.g., to pull back near-expiry stock); Branch fulfills it, moving the relevant SIMs `WITH_BRANCH`/`WITH_BA` → `RETURNED_TO_HQ`, marking the `ReturnEvent` `COMPLETED`.
- Expired, unsold SIMs are flagged (`EXPIRED`) by a scheduled job comparing `expiry_date` to today, surfaced to both Branch and HQ dashboards.

### 6.6 Safaricom reconciliation
1. HQ uploads the daily Safaricom line-connection xlsx.
2. Background worker parses the file and, per SIM serial:
   - Confirms whether the app's `SOLD` SIMs appear with a `Top Up Date`/`Top Up Amount` (i.e., activated) in Safaricom's data.
   - Aggregates `Cumulative Commission` and `Fraud Flagged` counts across matched rows.
3. `ReconciliationResult` is produced with **headline numbers first**:
   - Total confirmed sold & topped-up (quantity)
   - Total cumulative commission (Safaricom-reported)
   - Total fraud-flagged count
   - Count of "sold in app but not yet appearing in Safaricom's file" and "appearing in Safaricom's file but not recorded as sold in app" (mismatch counts, drill-down available)
4. Detail-level rows (dates, amounts, specific serials, fraud reasons) are available on drill-down only, not on the summary view. BA identity is intentionally **not** part of this matching (per requirements — matching is at the SIM/quantity level only).

### 6.7 Commission
- HQ defines/updates `CommissionRule.amount_per_sim` at any time; each `SaleEvent` snapshots which rule/amount applied at time of sale, so historical reports remain accurate even after rate changes.
- Reports show commission owed = `count(SaleEvent) × applicable amount_per_sim`, per BA / per Branch / per Dealer, for the selected period. No payout/disbursement action — display and export only.

### 6.8 Targets & performance tracking
1. HQ sets a `Target` (quantity + period type — daily, weekly, or monthly) against a specific Branch it has assigned stock to. HQ can change a Branch's target at any time; a new `Target` row with a fresh `effective_from` supersedes the old one going forward (history preserved).
2. The system auto-derives each BA's daily target under that branch: **Branch daily target ÷ current number of active BAs in that branch = per-BA daily target**, split evenly. Weekly/monthly BA targets are computed the same way from the branch's weekly/monthly target (or derived as daily × 7 / daily × ~30 if HQ only sets a daily figure — HQ may set any subset of the three periods, and the system fills in the rest using that ratio).
3. If the number of active BAs in a branch changes mid-period (a BA added or removed), the per-BA split recalculates going forward from that point; already-elapsed days are not retroactively altered.
4. `PerformanceSnapshot` rows are recomputed as sales come in (or on a scheduled cadence, e.g. hourly) at three levels:
   - **BA level**: their own actual sold vs. their derived target → their own percentage.
   - **Branch level**: sum of actual sold across all its BAs vs. the branch's own target → branch percentage.
   - **Dealer/organization level**: sum across all branches vs. sum of all branch targets → overall percentage.
5. Visibility follows the role hierarchy: a BA sees only their own performance; a Branch sees its own performance plus every one of its BAs; HQ sees every branch, every BA, and the whole-organization roll-up.

### 6.9 Commission — leading numbers per level
- **BA dashboard**: leading numbers are their own commission earned today, this week, and this month (plus their performance percentage from §6.9).
- **Branch dashboard**: leading numbers are the branch's total commission (sum across its BAs) plus each individual BA's performance and commission, so a branch can see who is over/under-performing at a glance.
- **HQ dashboard**: leading numbers roll up commission and performance at branch level and organization-wide, with drill-down into any branch's BAs.

### 6.10 Login tracking & inactivity flagging
1. Every successful login (Branch or BA) writes a `LoginEvent`.
2. A scheduled daily job checks each Branch's and BA's most recent `LoginEvent`. If more than 3 days have passed with no login, the system creates an `AccountFlag` (`INACTIVE_3_DAYS`) and sets the account status to `FLAGGED_INACTIVE`.
3. HQ is notified (in-app notification, surfaced on the HQ dashboard) whenever a new flag is raised, identifying the branch/BA and their last-login date.
4. A flag does not automatically lock the account (assumption — see §10); HQ can acknowledge/resolve it, and it clears automatically once the user logs in again.

### 6.11 Reporting
- Daily / weekly / monthly views available to Branch (their own branch + BAs) and HQ (all branches):
  - SIM stock levels by state (in stock / with branch / with BA / sold / returned / expired)
  - Sales count, commission owed, and performance-vs-target percentage, by BA, by branch, and (for HQ) organization-wide
  - Reconciliation headline numbers (once a Safaricom import exists for the period)
- Export as PDF (formatted report) and Excel (raw tabular data) from both dashboards, generated server-side and downloaded via the app/web client.

---

## 7. Offline-First Sync Design (Mobile)

- **Local store:** every entity the mobile role needs (its own SIM assignments, BAs, recent sale events) is mirrored into a local SQLite database via Drift.
- **Write path:** all mutations (a BA's scan/sale, a Branch's reassignment/return) are first written locally with a client-generated UUID and an `pending_sync` flag, then queued.
- **Sync engine:** a background sync worker pushes the pending-sync queue whenever connectivity is available, in creation order, and pulls down any server-side changes relevant to that user's scope (their branch's/BA's SIMs) since the last sync checkpoint (a per-device `last_synced_at` cursor).
- **Conflict handling:** the server is the source of truth for `SimCard.status`. If a sync push tries to sell/reassign a SIM the server already shows as `SOLD` or moved elsewhere, the server rejects that specific event, and the app surfaces a clear "this SIM was already processed elsewhere" message rather than silently overwriting anything — this matters most for the BA sale flow, since two people should never be able to "sell" the same physical SIM.
- **Idempotency:** every locally-created event carries a client UUID so retried sync pushes (e.g., after a dropped connection) don't create duplicates server-side.

---

## 8. Security & Permissions

| Capability | HQ | Branch | BA |
|---|---|---|---|
| Add stock (PDF/box scan) | ✅ | ❌ | ❌ |
| Distribute stock to Branch | ✅ | ❌ | ❌ |
| Create BA account | ✅ | ✅ | ❌ |
| Remove BA account | ✅ | ❌ | ❌ |
| Reassign SIM between BAs (own branch) | ❌ | ✅ | ❌ |
| Scan/sell a SIM | ❌ | ❌ | ✅ |
| Request return from Branch | ✅ | ❌ | ❌ |
| Fulfill a return | ❌ | ✅ | ❌ |
| Set commission rate | ✅ | ❌ | ❌ |
| Set Branch targets (daily/weekly/monthly) | ✅ | ❌ | ❌ |
| View own performance % (self only) | ❌ | ✅ (branch + own BAs) | ✅ (self only) |
| View organization-wide performance roll-up | ✅ | ❌ | ❌ |
| View own/branch commission earned (daily/weekly/monthly) | ✅ (all) | ✅ (branch total + per-BA) | ✅ (self only) |
| View login-inactivity flags & notifications | ✅ | ❌ | ❌ |
| Upload Safaricom xlsx / view reconciliation | ✅ | ❌ | ❌ |
| View own branch/BA reports | ✅ (all) | ✅ (own) | ❌ |
| Export PDF/Excel reports | ✅ | ✅ | ❌ |

- All API access is JWT-scoped by `dealer_id` + `role`; a Branch or BA token can never read/write another dealer's or another branch's data, enforced both at the query layer and via Postgres row-level security as a second guard.
- Password auth (email + password) with standard hashing (bcrypt/argon2), rate-limited login attempts, and refresh-token rotation.
- Full `AuditLog` on all stock movements, account creation/removal, and commission-rate changes — important given this touches inventory with real cash value.

---

## 9. Phase Roadmap

**Phase 1 (this design):** everything described above.

**Later phases (explicitly out of scope now, listed for awareness only):**
- Customer KYC capture at sale.
- Commission payout/disbursement integration.
- Extended KPIs (fraud-rate trends, BA leaderboard, activation-rate analytics).
- Branch-type-specific workflows, if they ever diverge from today's identical behavior.

---

## 10. Assumptions Made

- Each SIM box/pack barcode either encodes or can be mapped to its 100 constituent serials (needs confirmation of the exact box-barcode format/encoding from Safaricom/dealer packaging before implementation — flagged as a build-time investigation item, not a design blocker).
- "Daily" Safaricom file uploads are a manual HQ action (no direct API integration with Safaricom assumed for Phase 1).
- Web app in Phase 1 targets Branch and HQ primarily; a BA could still use a mobile browser in a pinch, but the BA experience is designed API-first for the Android app.
- Per-BA targets are derived by an even split of the branch target across active BAs (simplest, most predictable rule); a weighted/manual per-BA override is not assumed for Phase 1 but would be a natural extension if HQ later wants uneven splits.
- A 3-day-inactive `AccountFlag` is informational only (notifies HQ) and does not automatically suspend login access in Phase 1 — HQ can decide manually whether to disable the account.
- ID number and current photo are captured once at account-creation time (Branch by HQ, BA by Branch) and stored as part of that account's record; no periodic re-verification is assumed for Phase 1.
