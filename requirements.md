# SIM Stock & Sales Tracking Platform — Requirements Document

Version 1.0 (Phase 1 scope) — companion to `design.md`.

---

## 1. Purpose

Define the functional and non-functional requirements for a multi-tenant Android (Play Store, first) and responsive web (second) application that lets Safaricom SIM card dealers track stock from HQ intake through Branch distribution to Brand Ambassador (BA) sale, and reconcile sales against Safaricom's own daily line-connection report.

---

## 2. Actors

| Actor | Definition |
|---|---|
| **Dealer / HQ** | The dealer's head office account; owns the tenant's entire data set. |
| **Branch** | Any point of sale under a dealer: a van, a physical shop, or an individual managing a team of BAs. Functionally identical regardless of type. |
| **Brand Ambassador (BA)** | Field seller; belongs to exactly one Branch; restricted to selling SIMs. |

---

## 3. Functional Requirements

### 3.1 Tenancy
- **FR-TEN-01**: The system shall support multiple independent dealers, each with fully isolated data (branches, BAs, stock, sales, reports).
- **FR-TEN-02**: A dealer's data shall never be visible or writable by another dealer's users.

### 3.2 HQ capabilities
- **FR-HQ-01**: HQ shall add new stock by uploading a Safaricom pick-list PDF; the system shall parse SIM serial numbers from the document automatically.
- **FR-HQ-02**: HQ shall add new stock by scanning the barcode on a SIM card box/pack (100 SIMs per pack) using the phone camera.
- **FR-HQ-03**: HQ shall distribute stock (in specified quantities or specific serials) from HQ inventory to a chosen Branch.
- **FR-HQ-04**: HQ shall request a return of stock from a Branch (e.g., near-expiry SIMs); the Branch shall be notified and able to fulfill the request.
- **FR-HQ-05**: HQ shall define and update the commission amount paid per SIM sold; historical sales shall retain the rate that applied at the time of sale.
- **FR-HQ-06**: HQ shall upload Safaricom's daily line-connection xlsx report and trigger reconciliation against internal sales data.
- **FR-HQ-07**: HQ shall view reconciliation results led by headline numbers (confirmed sold & topped-up quantity, cumulative commission, fraud-flagged count) with the ability to drill into date/amount/serial-level detail.
- **FR-HQ-08**: HQ shall view consolidated daily, weekly, and monthly reports across all branches and BAs.
- **FR-HQ-09**: HQ shall export any report as PDF and as Excel (xlsx).
- **FR-HQ-10**: HQ shall create and remove Branch accounts, capturing the Branch's ID number and a current photo at creation for audit and security purposes.
- **FR-HQ-11**: HQ shall be the only role able to remove a BA account.
- **FR-HQ-13**: HQ shall set custom performance targets (quantity, for a daily, weekly, and/or monthly period) against any Branch it has assigned stock to, and shall be able to update those targets at any time.
- **FR-HQ-14**: HQ shall view performance percentages (actual sold vs. target) at BA level, Branch level, and whole-organization level.
- **FR-HQ-15**: HQ shall view login-inactivity flags and be notified when any Branch or BA account has not logged in for 3 consecutive days.
- **FR-HQ-12**: HQ shall view (but not perform BA-level actions on) any branch's or BA's SIM stock and sales detail.

### 3.3 Branch capabilities
- **FR-BR-01**: A Branch shall create BA accounts under itself, capturing the BA's ID number and a current photo at creation for audit and security purposes.
- **FR-BR-09**: A Branch shall view the performance percentage (actual sold vs. target) of every individual BA under it, and its own branch-level performance percentage.
- **FR-BR-10**: A Branch shall view its own total commission earned and the commission earned by each individual BA under it.
- **FR-BR-02**: A Branch shall reassign a SIM card from one of its BAs to another of its own BAs.
- **FR-BR-03**: A Branch shall view consolidated sold/unsold SIM counts per BA and for the branch as a whole.
- **FR-BR-04**: A Branch shall mark unsold SIMs as returned (from a BA back to the branch, or from the branch back to HQ upon HQ's request).
- **FR-BR-05**: A Branch shall view its own daily, weekly, and monthly reports (own branch + its BAs only).
- **FR-BR-06**: A Branch shall export its own reports as PDF and Excel.
- **FR-BR-07**: A Branch shall **not** be able to remove a BA account (HQ-only, per FR-HQ-11).
- **FR-BR-08**: A Branch shall **not** access another branch's data.

### 3.4 Brand Ambassador (BA) capabilities
- **FR-BA-01**: A BA shall scan a SIM card's barcode (serial number) using the phone camera to register it as sold.
- **FR-BA-02**: A BA shall only be able to sell SIMs currently assigned to them; the app shall reject/flag scans of SIMs not in their possession.
- **FR-BA-03**: A BA account shall have no access to stock intake, distribution, reassignment, reporting, reconciliation, or commission functions.
- **FR-BA-04**: Scanning shall function fully offline, queuing the sale for sync once connectivity returns.
- **FR-BA-05**: A BA shall view their own performance percentage (actual sold vs. their derived daily/weekly/monthly target) and their own commission earned today, this week, and this month. A BA shall not see any other BA's or the branch's aggregate figures.

### 3.5 Stock lifecycle
- **FR-STK-01**: The system shall track each individual SIM card's serial number and current status through the states: in HQ stock, with branch, with BA, sold, returned (to branch or HQ), and expired.
- **FR-STK-02**: The system shall prevent a duplicate SIM serial from being registered twice within the same dealer.
- **FR-STK-03**: The system shall record every stock movement (HQ→Branch, Branch→BA, BA→BA, →Return) with who initiated it and when.
- **FR-STK-04**: The system shall flag SIMs that have passed their expiry date without being sold, visible to both the owning Branch and HQ.
- **FR-STK-05**: Every stock and sale record shall be traceable back to its originating Dealer, following the one-to-many chain (Dealer → Branch → BA → SIM).

### 3.6 Reconciliation
- **FR-REC-01**: The system shall match SIM serials sold in-app against Safaricom's uploaded daily report.
- **FR-REC-02**: The reconciliation summary shall present, as leading figures: total quantity confirmed sold-and-topped-up, total cumulative commission (per Safaricom's data), and total fraud-flagged count.
- **FR-REC-03**: Detailed information (specific dates, top-up amounts, fraud reasons, individual serials) shall be available only on drill-down from the summary, not shown by default.
- **FR-REC-04**: BA identity shall not be part of the sold/unsold-vs-Safaricom matching logic.
- **FR-REC-05**: The system shall surface counts of mismatches in both directions: sold in-app but not yet confirmed by Safaricom, and confirmed by Safaricom but not recorded as sold in-app.
- **FR-REC-06**: The system shall let HQ view the serials activated in a given calendar month across all uploaded Safaricom reports, separated by activation month (per the serial's Top Up Date), so that previous-month activations are not mixed into a different month's verification.

### 3.7 Commission
- **FR-COM-01**: HQ shall set a commission amount per SIM sold; this amount may change over time and may differ across periods.
- **FR-COM-02**: The system shall calculate commission owed per BA, per Branch, and per Dealer for any selected reporting period, using the rate in effect at the time of each sale.
- **FR-COM-03**: The system shall not process or integrate any payment disbursement — commission figures are for display/reporting only.

### 3.8 Targets & performance tracking
- **FR-PERF-01**: HQ shall set a custom target (quantity of SIMs, over a daily, weekly, and/or monthly period) for any Branch it has assigned stock to.
- **FR-PERF-02**: The system shall automatically derive each BA's daily (and corresponding weekly/monthly) target from their branch's target, split evenly across the branch's currently active BAs.
- **FR-PERF-03**: If the number of active BAs in a branch changes, the system shall recalculate the per-BA split going forward without altering already-elapsed periods.
- **FR-PERF-04**: The system shall calculate and display a performance percentage (actual sold ÷ target × 100) at BA level, Branch level, and Dealer/organization level, for daily, weekly, and monthly periods.
- **FR-PERF-05**: A BA shall see only their own performance percentage.
- **FR-PERF-06**: A Branch shall see its own performance percentage and the performance percentage of every BA under it.
- **FR-PERF-07**: HQ shall see the performance percentage of every Branch, every BA, and the organization as a whole.

### 3.9 Login tracking
- **FR-LOGIN-01**: The system shall record every successful login by a Branch or BA user.
- **FR-LOGIN-02**: The system shall flag any Branch or BA account that has not logged in for 3 consecutive days.
- **FR-LOGIN-03**: HQ shall be notified whenever a new inactivity flag is raised, identifying the affected account and its last login date.
- **FR-LOGIN-04**: An inactivity flag shall clear automatically once the flagged account logs in again.

### 3.10 Reporting
- **FR-RPT-01**: The system shall provide daily, weekly, and monthly report views for Branch and HQ roles.
- **FR-RPT-02**: Reports shall be exportable as PDF and as Excel (xlsx) from both the mobile app and web app.
- **FR-RPT-03**: Reports shall include, at minimum: stock counts by state, sales counts, commission owed, and performance-vs-target percentage — scoped appropriately per role (Branch sees its own data; HQ sees all).

### 3.11 Authentication & authorization
- **FR-AUTH-01**: Users shall authenticate via email and password.
- **FR-AUTH-02**: The system shall enforce role-based access control matching the permission matrix in §5.
- **FR-AUTH-03**: HQ shall have full administrative control over its dealer's entire account hierarchy.

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Offline-first (mobile)**: the Android app shall allow BAs and Branches to view relevant data and perform their core actions (scan-to-sell, reassignment) without an active internet connection, syncing automatically once connectivity resumes. |
| NFR-02 | **Data isolation**: no dealer's data shall ever be queryable or visible to a different dealer's users, enforced at the database layer (not application logic alone). |
| NFR-03 | **Scalability**: the data model and infrastructure shall support a growing, currently-undefined number of dealers, branches, and BAs without architectural rework (i.e., avoid per-tenant database instances). |
| NFR-04 | **Auditability**: all stock movements, account creation/removal, and commission-rate changes shall be logged with actor, timestamp, and action for traceability. |
| NFR-05 | **Conflict safety**: the system shall prevent the same physical SIM from being recorded as sold, reassigned, or returned by two different actions concurrently (server is source of truth on sync). |
| NFR-06 | **Performance**: barcode scan-to-confirmation shall feel instantaneous to the BA even when offline (local validation), with server-side re-validation on sync. |
| NFR-07 | **Usability**: the BA app experience shall be reduced to essentially one screen/action (scan → confirm sold) given its restricted scope. |
| NFR-08 | **Report generation time**: standard daily/weekly/monthly report exports (PDF/Excel) shall generate and be available for download within a reasonable time for typical per-dealer data volumes. |
| NFR-09 | **Platform priority**: Android (Google Play Store) is the primary target for Phase 1; the responsive web app follows, sharing the same backend API. |
| NFR-10 | **Security**: passwords stored using industry-standard hashing; API access via short-lived, tenant- and role-scoped tokens. |

---

## 5. Permission Matrix

| Action | HQ | Branch | BA |
|---|:---:|:---:|:---:|
| Add stock (PDF import / box scan) | ✅ | ❌ | ❌ |
| Distribute stock to a Branch | ✅ | ❌ | ❌ |
| Request return from Branch | ✅ | ❌ | ❌ |
| Fulfill a return | ❌ | ✅ | ❌ |
| Set/update commission rate | ✅ | ❌ | ❌ |
| Set/update Branch targets | ✅ | ❌ | ❌ |
| View own performance % | ❌ | ✅ (own + BAs) | ✅ (self only) |
| View organization-wide performance roll-up | ✅ | ❌ | ❌ |
| View commission earned (own/branch/BA scope) | ✅ (all) | ✅ (branch total + per-BA) | ✅ (self only) |
| Receive login-inactivity flags/notifications | ✅ | ❌ | ❌ |
| Upload Safaricom report & view reconciliation | ✅ | ❌ | ❌ |
| Create Branch account (+ ID number & photo) | ✅ | ❌ | ❌ |
| Remove Branch account | ✅ | ❌ | ❌ |
| Create BA account (+ ID number & photo) | ✅ | ✅ | ❌ |
| Remove BA account | ✅ | ❌ | ❌ |
| Reassign SIM between BAs (own branch) | ❌ | ✅ | ❌ |
| Scan/sell a SIM | ❌ | ❌ | ✅ |
| View branch/BA consolidated sold-unsold data | ✅ (all) | ✅ (own) | ❌ |
| View daily/weekly/monthly reports | ✅ (all) | ✅ (own) | ❌ |
| Export PDF/Excel reports | ✅ | ✅ | ❌ |

---

## 6. Out of Scope (Phase 1)

- Customer KYC capture at point of sale.
- Payment/commission disbursement integration (e.g., M-Pesa payout).
- Additional KPIs beyond sold/unsold counts, activation confirmation, cumulative commission, and fraud counts.
- Differentiated behavior by Branch type (van/shop/individual are labels only in Phase 1).
- Direct API integration with Safaricom (report upload is a manual HQ action).

---

## 7. Example Acceptance Criteria

- **AC-1**: Given a HQ user uploads a valid Safaricom pick-list PDF, when the import completes, then every serial number listed under each `<<Lot>>` block appears as an individual SIM record with status "In HQ Stock."
- **AC-2**: Given a BA has a SIM assigned to them, when they scan its barcode, then the SIM's status updates to "Sold" and is attributed to that BA and their branch — even if the device is offline at the time of scanning, syncing once connectivity returns.
- **AC-3**: Given two BAs attempt to scan and sell the same physical SIM before either syncs, when both come online, then only the first-accepted sale is recorded as "Sold," and the second sync attempt is rejected with a clear conflict message.
- **AC-4**: Given HQ uploads a new Safaricom daily report, when reconciliation runs, then the summary view shows total confirmed sold-and-topped-up quantity, total cumulative commission, and total fraud-flagged count before any per-SIM detail is shown.
- **AC-5**: Given a Branch attempts to remove a BA account, when they submit the request, then the system rejects it, since only HQ may remove BA accounts.
- **AC-6**: Given HQ sets a daily target of 50 SIMs for a Branch with 5 active BAs, when the system derives BA-level targets, then each BA's daily target is 10, and if a 6th BA is added mid-period, then each BA's target recalculates to reflect the new headcount going forward (not retroactively).
- **AC-7**: Given a BA has sold 7 of their 10-unit daily target, when they view their dashboard, then their performance percentage shows 70%, and this figure rolls up correctly into their branch's and the organization's overall percentage.
- **AC-8**: Given a Branch or BA account has not logged in for 3 consecutive days, when the daily inactivity check runs, then the account is flagged and HQ receives a notification identifying the account and its last login date.
- **AC-9**: Given HQ attempts to create a Branch account (or a Branch attempts to create a BA account) without an ID number or current photo, when they submit the form, then the system rejects the submission until both are provided.
