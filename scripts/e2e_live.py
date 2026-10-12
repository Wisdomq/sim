"""X-13-02: live end-to-end check of AC-1..AC-9 against the running backend.

Drives the real API (and the real Celery worker for async pick-list/recon
tasks) over HTTP with a throwaway tenant, then removes that tenant.

Usage:
    source backend/.venv/bin/activate
    PYTHONPATH=backend/src python scripts/e2e_live.py [http://localhost:8000/api/v1]

Prereqs: uvicorn API on :8000, celery worker running, local Postgres reachable.
Exits non-zero if any acceptance item fails.
"""

from __future__ import annotations

import io
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx
import openpyxl

from sqlalchemy import select

from simcards_backend.core.database import SessionLocal
from simcards_backend.core.security import now_utc
from simcards_backend.models import Dealer, LoginEvent, SimStatus, User
from simcards_backend.services.inactivity import flag_inactive_accounts

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
STAMP = datetime.now().strftime("%Y%m%d%H%M%S%f")[2:]  # 18 numeric digits
SHORTCODE = f"E2E{STAMP}"
PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    sym = "PASS" if ok else "FAIL"
    line = f"  [{sym}] {name}"
    if detail and not ok:
        line += f"  <- {detail}"
    print(line)


def _serial_block(letter: str) -> str:
    """19-digit serial block prefix unique per run + AC block."""

    return f"{letter}{STAMP[2:16]}"


def make_serial(block: str, seq: int) -> str:
    b = _serial_block(block)
    return f"{b}{seq:04d}"


# ── HTTP helpers ──────────────────────────────────────────────────────────

client = httpx.Client(base_url=BASE, timeout=30.0)


def login(email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def hreq(method: str, path: str, token: str | None = None, **kw):
    kw["headers"] = {"Authorization": f"Bearer {token}"} if token else kw.get("headers", {})
    return client.request(method, path, **kw)


def poll(path: str, token: str, want_fields: dict, timeout: float = 90.0) -> dict:
    """Poll GET path until JSON has all non-None (key, value) pairs, else raise.

    404 "not completed yet" responses are treated as "keep waiting" (the recon
    summary endpoint returns 404 while the Celery task is still running).
    """

    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(path, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 404 and r.headers.get("content-type", "").startswith("application/json"):
            last = r.json()
            time.sleep(2.0)
            continue
        r.raise_for_status()
        last = r.json()
        if all(last.get(k) == v for k, v in want_fields.items()):
            return last
        time.sleep(2.0)
    raise RuntimeError(f"timeout waiting {path}: {last!r}")


# ── DB helpers (setup + teardown for this throwaway tenant) ───────────────

def delete_e2e_tenants() -> None:
    try:
        with SessionLocal() as db:
            dealers = db.scalars(
                select(Dealer).where(Dealer.safaricom_dealer_shortcode.like("E2E%"))
            ).all()
            for d in dealers:
                db.delete(d)
            db.commit()
            print(f"  cleanup: removed {len(dealers)} E2E tenant(s)")
    except Exception as exc:  # pragma: no cover - best-effort
        print(f"  cleanup warning: {exc}")


def main() -> int:
    ts = datetime.now
    stamp_email = f"hq{STAMP}@e2e.local"

    # -- provision tenant ---------------------------------------------------
    r = hreq(
        "POST",
        "/onboarding/dealers",
        json={
            "dealer_name": f"E2E Dealer {STAMP}",
            "safaricom_dealer_shortcode": SHORTCODE,
            "hq_email": stamp_email,
            "hq_password": "supersecret",
        },
    )
    check("provision dealer (onboarding)", r.status_code == 201, f"status={r.status_code}")
    if r.status_code != 201:
        print("  aborting: cannot provision tenant")
        return 1
    hq_token = login(stamp_email, "supersecret")

    branch_resp = hreq(
        "POST",
        "/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "E2E Branch A",
            "type": "SHOP",
            "id_number": f"E2E-BR-{STAMP[:6]}",
            "photo_url": "https://example.com/e2e-branch.jpg",
            "email": f"br{STAMP}@e2e.local",
            "password": "branchsecret",
        },
    )
    branch = branch_resp.json()
    check("create branch", branch_resp.status_code == 201 and "id" in branch, f"{branch_resp.text[:120]}")
    branch_token = login(f"br{STAMP}@e2e.local", "branchsecret")

    ba_resp = hreq(
        "POST",
        "/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "E2E BA One",
            "email": f"ba{STAMP}@e2e.local",
            "password": "basecret123",
            "phone_msisdn": "254700000777",
            "id_number": f"E2E-BA-{STAMP[:6]}",
            "photo_url": "https://example.com/e2e-ba.jpg",
        },
    )
    ba = ba_resp.json()
    check("create BA", ba_resp.status_code == 201 and "id" in ba, f"{ba_resp.text[:120]}")
    ba_token = login(f"ba{STAMP}@e2e.local", "basecret123")

    # -- AC-9 validations run early so invalid rows never touch the DB -----
    r = hreq(
        "POST",
        "/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": "No Photo", "type": "VAN", "id_number": f"E2E9-{STAMP[:6]}",
              "photo_url": "", "email": f"np{STAMP}@e2e.local", "password": "branchsecret"},
    )
    check("AC-9 reject branch w/o photo", r.status_code == 422, str(r.status_code))
    r = hreq(
        "POST",
        "/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"name": "No ID", "type": "SHOP", "id_number": "",
              "photo_url": "https://example.com/br.jpg",
              "email": f"ni{STAMP}@e2e.local", "password": "branchsecret"},
    )
    check("AC-9 reject branch w/o id_number", r.status_code == 422, str(r.status_code))
    r = hreq(
        "POST",
        "/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": "BA No Photo", "email": f"bnp{STAMP}@e2e.local",
              "password": "basecret123", "phone_msisdn": "254700000981",
              "id_number": f"E2E9-BA-{STAMP[:6]}", "photo_url": ""},
    )
    check("AC-9 reject BA w/o photo", r.status_code == 422, str(r.status_code))
    r = hreq(
        "POST",
        "/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"name": "BA No ID", "email": f"bni{STAMP}@e2e.local",
              "password": "basecret123", "phone_msisdn": "254700000982",
              "id_number": "", "photo_url": "https://example.com/ba.jpg"},
    )
    check("AC-9 reject BA w/o id_number", r.status_code == 422, str(r.status_code))

    # -- AC-1 PDF pick-list import (async via Celery) ----------------------
    ac1 = [make_serial("1", i) for i in range(1, 4)]
    pdf_buf = io.BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    c = pdf_canvas.Canvas(pdf_buf, pagesize=A4)
    c.drawString(50, 750, f"<<Lot>> LOT_E2E_001"
                 )
    for i, s in enumerate(ac1):
        c.drawString(50, 730 - i * 20, s)
    c.save()
    pdf_buf.seek(0)
    r = hreq(
        "POST",
        "/stock/intake/pick-list-pdf",
        headers={"Authorization": f"Bearer {hq_token}"},
        files={"file": ("pick_list.pdf", pdf_buf.getvalue(), "application/pdf")},
    )
    check("AC-1 pick-list import accepted (202)",
          r.status_code == 202 and "task_id" in r.json(), f"{r.text[:160]}")
    try:
        deadline = time.time() + 90
        found: set[str] = set()
        while time.time() < deadline:
            sims = client.get("/stock/sim-cards?status=IN_HQ_STOCK",
                              headers={"Authorization": f"Bearer {hq_token}"}).json()
            found = {s["serial_number"] for s in sims}
            if set(ac1) <= found:
                break
            time.sleep(2.0)
        check("AC-1 serials created IN_HQ_STOCK", set(ac1) <= found, f"missing={set(ac1) - found}")
    except Exception as exc:
        check("AC-1 serials created IN_HQ_STOCK", False, str(exc))

    # -- AC-2 + AC-3 scan/sale, attribution, duplicate rejected ------------
    s23 = make_serial("2", 1)
    r = hreq(
        "POST",
        "/stock/intake/box-scan",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={"box_barcode": f"E2E-BOX-{STAMP[:6]}", "serials": [s23], "quantity": 1},
    )
    check("AC-2 box scan intake", r.status_code == 201, str(r.status_code))
    r = hreq("POST", "/stock/distribute",
             headers={"Authorization": f"Bearer {hq_token}"},
             json={"branch_id": branch["id"], "serial_numbers": [s23]})
    check("AC-2 distribute to branch", r.status_code == 200, str(r.status_code))
    r = hreq("POST", "/stock/assign-to-ba",
             headers={"Authorization": f"Bearer {branch_token}"},
             json={"ba_id": ba["id"], "serial_numbers": [s23]})
    check("AC-2 assign to BA", r.status_code == 200, str(r.status_code))
    r = hreq("POST", "/stock/sales",
             headers={"Authorization": f"Bearer {ba_token}"},
             json={"serial_number": s23, "sold_at": ts().isoformat(), "client_event_id": f"ac2-{STAMP}"})
    body = r.json()
    ok = r.status_code == 201 and body.get("ba_id") == ba["id"] and body.get("branch_id") == branch["id"]
    check("AC-2 sale 201 + BA/branch attribution", ok, f"{r.text[:160]}")
    r = hreq("POST", "/stock/sales",
             headers={"Authorization": f"Bearer {ba_token}"},
             json={"serial_number": s23, "sold_at": ts().isoformat(), "client_event_id": f"ac3-{STAMP}"})
    check("AC-3 double-scan rejected (409)", r.status_code == 409, str(r.status_code))

    # -- AC-4 recon xlsx upload (async) + summary first --------------------
    header = ["TM Date", "ID Date", "ID Month", "Dealer Shortcode", "Dealer Name",
              "Sim Serial Number", "Top Up Date", "Top Up Amount", "Agent MSISDN",
              "BA", "Region", "Territory", "Cluster", "Cumulative Usage",
              "Cumulative Commission", "Fraud Flagged", "Fraud Suspension Date",
              "Fraud Reason", "Role", "Quality"]

    def _row(serial, amount, commission, fraud, reason):
        return ["2026-08-01"] * 5 + [serial, "20260831", amount, "254700000777",
                "BA", "Region", "Territory", "Cluster", "100.0",
                commission, fraud, "-", reason, "role", "quality"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    ws.append(_row(s23, "50.0", "120.0", "N", "-"))
    ws.append(_row("7770000000000000001", "-", "0.0", "Y", "Suspicious"))
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    xlsx_buf.seek(0)
    r = hreq("POST", "/reconciliation/imports",
             headers={"Authorization": f"Bearer {hq_token}"},
             data={"report_date": datetime.now().date().isoformat()},
             files={"file": ("recon.xlsx", xlsx_buf.getvalue(), "application/octet-stream")})
    check("AC-4 recon upload accepted (202)",
          r.status_code == 202 and "import_id" in r.json(), f"{r.text[:160]}")
    import_id = r.json()["import_id"]
    try:
        def _status():
            resp = client.get("/reconciliation/imports", headers={"Authorization": f"Bearer {hq_token}"})
            resp.raise_for_status()
            rows = resp.json()
            if not isinstance(rows, list):
                rows = rows.get("imports", [])
            return next((x["status"] for x in rows if x["id"] == import_id), None)

        deadline = time.time() + 90
        while _status() != "COMPLETED" and time.time() < deadline:
            time.sleep(2.0)
        ok = _status() == "COMPLETED"
        check("AC-4 recon COMPLETED", ok, f"status={_status()}")
        summary = client.get(f"/reconciliation/imports/{import_id}",
                             headers={"Authorization": f"Bearer {hq_token}"}).json()
        keys = {"total_confirmed_activated_by_safaricom", "total_cumulative_commission",
                "total_fraud_flagged", "total_sold_in_app"}
        check("AC-4 summary headline keys", keys <= set(summary), f"{summary}")
        detail = client.get(f"/reconciliation/imports/{import_id}/detail",
                            headers={"Authorization": f"Bearer {hq_token}"})
        check("AC-4 detail rows", detail.status_code == 200 and len(detail.json()) >= 2,
              str(detail.status_code))
    except Exception as exc:
        check("AC-4 recon COMPLETED", False, str(exc))

    # -- AC-5 branch cannot remove BA, HQ can ------------------------------
    r = hreq("DELETE", f"/brand-ambassadors/{ba['id']}",
             headers={"Authorization": f"Bearer {branch_token}"})
    check("AC-5 branch delete BA forbidden (403)", r.status_code == 403, str(r.status_code))
    r = hreq("DELETE", f"/brand-ambassadors/{ba['id']}",
             headers={"Authorization": f"Bearer {hq_token}"})
    check("AC-5 HQ delete BA allowed (204)", r.status_code == 204, str(r.status_code))

    # -- AC-6 target derivation 50/5=10 then 50/6=8 ------------------------
    ac6_branch = hreq("POST", "/branches",
                      headers={"Authorization": f"Bearer {hq_token}"},
                      json={"name": "E2E Target Branch", "type": "SHOP",
                            "id_number": f"E2E6-BR-{STAMP[:6]}",
                            "photo_url": "https://example.com/br.jpg",
                            "email": f"br6{STAMP}@e2e.local", "password": "branchsecret"}).json()
    ac6_token = login(f"br6{STAMP}@e2e.local", "branchsecret")
    for i in range(1, 6):
        hreq("POST", "/brand-ambassadors",
             headers={"Authorization": f"Bearer {ac6_token}"},
             json={"name": f"E2E BA{i}", "email": f"6ba{i}{STAMP}@e2e.local",
                   "password": "basecret123", "phone_msisdn": f"25470000090{i}",
                   "id_number": f"E2E6-BA-{STAMP[:6]}-{i}",
                   "photo_url": "https://example.com/ba.jpg"})
    r = hreq("POST", "/commission/targets",
             headers={"Authorization": f"Bearer {hq_token}"},
             json={"branch_id": ac6_branch["id"], "period_type": "DAILY",
                   "quantity": 50, "effective_from": ts().isoformat()})
    check("AC-6 daily target 50 set", r.status_code == 201, str(r.status_code))
    r = hreq("GET", f"/commission/ba-daily-target?branch_id={ac6_branch['id']}",
             headers={"Authorization": f"Bearer {hq_token}"})
    check("AC-6 BA target 50/5 = 10",
          r.status_code == 200 and r.json()["daily_target_per_ba"] == 10, f"{r.text[:120]}")
    hreq("POST", "/brand-ambassadors",
         headers={"Authorization": f"Bearer {ac6_token}"},
         json={"name": "E2E BA6", "email": f"6ba6{STAMP}@e2e.local",
               "password": "basecret123", "phone_msisdn": "254700000906",
               "id_number": f"E2E6-BA-{STAMP[:6]}-6",
               "photo_url": "https://example.com/ba.jpg"})
    r = hreq("GET", f"/commission/ba-daily-target?branch_id={ac6_branch['id']}",
             headers={"Authorization": f"Bearer {hq_token}"})
    check("AC-6 BA target 50/6 = 8 after 6th BA",
          r.status_code == 200 and r.json()["daily_target_per_ba"] == 8, f"{r.text[:120]}")

    # -- AC-7 7/10 sold -> 70% at BA and branch ----------------------------
    ac7_branch = hreq("POST", "/branches",
                      headers={"Authorization": f"Bearer {hq_token}"},
                      json={"name": "E2E Perf Branch", "type": "SHOP",
                            "id_number": f"E2E7-BR-{STAMP[:6]}",
                            "photo_url": "https://example.com/br.jpg",
                            "email": f"br7{STAMP}@e2e.local", "password": "branchsecret"}).json()
    ac7_token = login(f"br7{STAMP}@e2e.local", "branchsecret")
    ac7_ba = hreq("POST", "/brand-ambassadors",
                  headers={"Authorization": f"Bearer {ac7_token}"},
                  json={"name": "E2E Perf BA", "email": f"7ba{STAMP}@e2e.local",
                        "password": "basecret123", "phone_msisdn": "254700000907",
                        "id_number": f"E2E7-BA-{STAMP[:6]}",
                        "photo_url": "https://example.com/ba.jpg"}).json()
    ac7_serials = [make_serial("5", i) for i in range(1, 11)]
    r = hreq("POST", "/stock/intake/box-scan",
             headers={"Authorization": f"Bearer {hq_token}"},
             json={"box_barcode": f"E2E7-BOX-{STAMP[:6]}", "serials": ac7_serials, "quantity": 10})
    check("AC-7 box scan 10", r.status_code == 201, str(r.status_code))
    r = hreq("POST", "/stock/distribute",
             headers={"Authorization": f"Bearer {hq_token}"},
             json={"branch_id": ac7_branch["id"], "serial_numbers": ac7_serials})
    check("AC-7 distribute 10", r.status_code == 200, str(r.status_code))
    r = hreq("POST", "/stock/assign-to-ba",
             headers={"Authorization": f"Bearer {ac7_token}"},
             json={"ba_id": ac7_ba["id"], "serial_numbers": ac7_serials})
    check("AC-7 assign 10 to BA", r.status_code == 200, str(r.status_code))
    r = hreq("POST", "/commission/targets",
             headers={"Authorization": f"Bearer {hq_token}"},
             json={"branch_id": ac7_branch["id"], "period_type": "DAILY",
                   "quantity": 10, "effective_from": ts().isoformat()})
    check("AC-7 daily target 10", r.status_code == 201, str(r.status_code))
    token7 = login(f"7ba{STAMP}@e2e.local", "basecret123")
    for i in range(1, 8):
        r = hreq("POST", "/stock/sales",
                 headers={"Authorization": f"Bearer {token7}"},
                 json={"serial_number": ac7_serials[i - 1], "sold_at": ts().isoformat(),
                       "client_event_id": f"ac7-{STAMP}-{i}"})
        if r.status_code != 201:
            check("AC-7 sell all 7", False, f"item {i}: {r.text[:120]}")
            break
    today = datetime.now().date().isoformat()
    r = hreq("GET", "/commission/performance",
             headers={"Authorization": f"Bearer {hq_token}"},
             params={"subject_type": "BA", "subject_id": ac7_ba["id"], "period_type": "DAILY",
                     "period_start": today, "period_end": today})
    ba_pct = float(r.json()["percentage_achieved"])
    check("AC-7 BA perf = 70%", abs(ba_pct - 70.0) < 1e-6, f"got {ba_pct}")
    r = hreq("GET", "/commission/performance",
             headers={"Authorization": f"Bearer {hq_token}"},
             params={"subject_type": "BRANCH", "subject_id": ac7_branch["id"],
                     "period_type": "DAILY", "period_start": today, "period_end": today})
    br_pct = float(r.json()["percentage_achieved"])
    check("AC-7 branch perf = 70%", abs(br_pct - 70.0) < 1e-6, f"got {br_pct}")

    # -- AC-8 3-day inactivity flag + notification + autoclear on login -----
    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == f"br{STAMP}@e2e.local"))
        login_event = db.scalars(
            select(LoginEvent).where(LoginEvent.user_id == branch_user.id)
        ).one()
        login_event.logged_in_at = now_utc() - timedelta(days=4)
        db.commit()  # persist the backdate so the GROUP BY last-login query sees it
        outcome = flag_inactive_accounts(db, dealer_id=branch_user.dealer_id,
                                         cutoff_dt=now_utc() - timedelta(days=3),
                                         as_of_dt=now_utc())
        db.commit()
        check("AC-8 flag_inactive_accounts flags 1", outcome.freshly_flagged_count == 1,
              f"got {outcome.freshly_flagged_count}")
    flags = hreq("GET", "/flags?resolved=false", headers={"Authorization": f"Bearer {hq_token}"})
    fl = flags.json()
    check("AC-8 /flags has 1 open flag",
          flags.status_code == 200 and len(fl) == 1 and fl[0]["role"] == "BRANCH",
          f"{fl}"[:160])
    notifs = hreq("GET", "/flags/notifications", headers={"Authorization": f"Bearer {hq_token}"})
    nf = notifs.json()
    check("AC-8 notification created",
          notifs.status_code == 200 and len(nf) == 1 and nf[0]["type"] == "ACCOUNT_FLAGGED_INACTIVE",
          f"{nf}"[:160])
    login(f"br{STAMP}@e2e.local", "branchsecret")  # autoclear on login
    with SessionLocal() as db:
        branch_user = db.scalar(
            select(User).where(User.email == f"br{STAMP}@e2e.local")
        )
        check("AC-8 status active + flag cleared",
              branch_user.status.value == "ACTIVE",
              f"status={branch_user.status}")
    flags2 = hreq("GET", "/flags?resolved=false", headers={"Authorization": f"Bearer {hq_token}"})
    check("AC-8 no open flags remain", flags2.status_code == 200 and len(flags2.json()) == 0,
          f"{flags2.json()}"[:160])

    # -- final live smoke: report the web Dashboard consumes ----------------
    d = datetime.now().date()
    r = hreq("POST", "/reports", headers={"Authorization": f"Bearer {hq_token}"},
             json={"period_type": "MONTHLY", "period_start": d.replace(day=1).isoformat(),
                   "period_end": d.isoformat()})
    check("live report smoke (Dashboard payload)",
          r.status_code == 200 and "branch_reports" in r.json(), f"{r.text[:160]}")

    # summary ---------------------------------------------------------------
    print()
    print(f"E2E complete: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\nFailures:")
        for f in FAIL:
            print(f"  - {f}")
        delete_e2e_tenants()
        return 1
    delete_e2e_tenants()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        client.close()