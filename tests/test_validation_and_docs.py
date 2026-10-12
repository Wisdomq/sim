"""B-10-05: OpenAPI auto-docs, consistent error schema, and request validation.

Covers:
- `GET /docs` (Swagger UI) and `GET /openapi.json` render cleanly with the
  `/api/v1` router's paths present.
- Every error response (401/403/404/422/500) keeps FastAPI's ``{"detail": ...}``
  shape.
- Hand-parsed params on `/commission/performance`, `/commission/earned`, and
  `/commission/ba-daily-target` now validate via declared types (422 instead of
  an uncaught 500).
- `POST /commission/targets` rejects an invalid `period_type` with 422.
- `GET /stock/sales` enforces `limit`/`offset` bounds.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _setup_dealer(client: TestClient) -> dict:
    """Seed a dealer with a branch + BA and return auth headers for each role."""
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Validation Dealer",
            "safaricom_dealer_shortcode": "VAL001",
            "hq_email": "val-hq@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "val-hq@example.com", "supersecret")

    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Validation Branch",
            "type": "SHOP",
            "id_number": "VAL-BR-001",
            "photo_url": "https://example.com/val-branch.jpg",
            "email": "val-branch@example.com",
            "password": "branchsecret",
        },
    )
    assert branch.status_code == 201
    branch_token = _login(client, "val-branch@example.com", "branchsecret")

    ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "Validation BA",
            "email": "val-ba@example.com",
            "password": "basecret123",
            "phone_msisdn": "254700000009",
            "id_number": "VAL-BA-001",
            "photo_url": "https://example.com/val-ba.jpg",
        },
    )
    assert ba.status_code == 201
    ba_token = _login(client, "val-ba@example.com", "basecret123")

    return {
        "hq": hq_token,
        "branch": branch_token,
        "ba": ba_token,
        "branch_id": branch.json()["id"],
        "ba_id": ba.json()["id"],
    }


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


# ── OpenAPI auto-docs ────────────────────────────────────────────────────────

def test_openapi_and_docs_reachable(client):
    """Swagger UI and the OpenAPI schema serve the /api/v1 router cleanly."""
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    spec = openapi.json()
    paths = spec["paths"]
    for path in [
        "/api/v1/commission/performance",
        "/api/v1/commission/earned",
        "/api/v1/commission/ba-daily-target",
        "/api/v1/reports",
        "/api/v1/reconciliation/imports",
        "/api/v1/stock/sim-cards",
        "/api/v1/auth/login",
    ]:
        assert path in paths, f"missing {path} in OpenAPI spec"

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "swagger-ui" in docs.text.lower()


# ── Consistent error schema ──────────────────────────────────────────────────

def test_error_responses_have_detail_key(client):
    """401/403/404/422 responses all keep FastAPI's {"detail": ...} shape."""
    accounts = _setup_dealer(client)

    unauthenticated = client.get("/api/v1/branches")
    assert unauthenticated.status_code == 401
    assert "detail" in unauthenticated.json()

    not_found = client.delete(
        "/api/v1/branches/999999",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
    )
    assert not_found.status_code == 404
    assert "detail" in not_found.json()

    forbidden = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {accounts['ba']}"},
        json={"period_type": "DAILY", "period_start": _today(), "period_end": _today()},
    )
    assert forbidden.status_code == 403
    assert "detail" in forbidden.json()

    bad_period = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        json={"period_type": "ANNUALLY", "period_start": _today(), "period_end": _today()},
    )
    assert bad_period.status_code == 422
    assert "detail" in bad_period.json()


# ── /commission/performance typed params ────────────────────────────────────

def test_performance_invalid_subject_type_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={
            "subject_type": "BRANCH_MANAGER",
            "subject_id": accounts["branch_id"],
            "period_type": "DAILY",
            "period_start": _today(),
            "period_end": _today(),
        },
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_performance_invalid_period_type_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={
            "subject_type": "BRANCH",
            "subject_id": accounts["branch_id"],
            "period_type": "YEARLY",
            "period_start": _today(),
            "period_end": _today(),
        },
    )
    assert response.status_code == 422


def test_performance_invalid_period_start_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={
            "subject_type": "BRANCH",
            "subject_id": accounts["branch_id"],
            "period_type": "DAILY",
            "period_start": "not-a-date",
            "period_end": _today(),
        },
    )
    assert response.status_code == 422


def test_performance_invalid_period_end_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/performance",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={
            "subject_type": "BRANCH",
            "subject_id": accounts["branch_id"],
            "period_type": "DAILY",
            "period_start": _today(),
            "period_end": "2026-13-40",
        },
    )
    assert response.status_code == 422


# ── /commission/earned typed date params ────────────────────────────────────

def test_earned_invalid_from_date_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/earned",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={"from_date": "bogus"},
    )
    assert response.status_code == 422


def test_earned_invalid_to_date_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/earned",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={"to_date": "yesterday-ish"},
    )
    assert response.status_code == 422


# ── /commission/ba-daily-target typed as_of param ───────────────────────────

def test_ba_daily_target_invalid_as_of_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/commission/ba-daily-target",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={"branch_id": accounts["branch_id"], "as_of": "not-a-date"},
    )
    assert response.status_code == 422


# ── POST /commission/targets period_type enum ───────────────────────────────

def test_target_create_invalid_period_type_422(client):
    accounts = _setup_dealer(client)
    response = client.post(
        "/api/v1/commission/targets",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        json={
            "branch_id": accounts["branch_id"],
            "period_type": "QUARTERLY",
            "quantity": 50,
            "effective_from": f"{_today()}T00:00:00",
        },
    )
    assert response.status_code == 422
    assert "detail" in response.json()


# ── GET /stock/sales pagination bounds ──────────────────────────────────────

def test_stock_sales_invalid_limit_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={"limit": 0},
    )
    assert response.status_code == 422


def test_stock_sales_invalid_offset_422(client):
    accounts = _setup_dealer(client)
    response = client.get(
        "/api/v1/stock/sales",
        headers={"Authorization": f"Bearer {accounts['hq']}"},
        params={"offset": -1},
    )
    assert response.status_code == 422
