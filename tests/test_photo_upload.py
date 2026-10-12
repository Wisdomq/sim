"""Photo upload endpoint tests (Phase 12, W-12-00).

Covers the multipart upload, dealer-scoped retrieval, cross-dealer isolation,
and non-image rejection.
"""

from __future__ import annotations

import io

import simcards_backend.services.accounts as account_services


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _signup(client, tmp_path, email="hq@photo.example.com", dealer="Photo Dealer", shortcode="PT001"):
    account_services.settings.UPLOAD_DIR = str(tmp_path)
    r = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": dealer,
            "safaricom_dealer_shortcode": shortcode,
            "hq_email": email,
            "hq_password": "supersecret",
        },
    )
    assert r.status_code == 201
    return _login(client, email, "supersecret")


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_upload_and_fetch_photo(client, tmp_path):
    token = _signup(client, tmp_path)
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/api/v1/uploads/photo",
        headers=headers,
        files={"file": ("photo.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["photo_url"].startswith("/api/v1/uploads/photo/")
    assert "/" in body["file_reference"]

    fetched = client.get(body["photo_url"], headers=headers)
    assert fetched.status_code == 200
    assert fetched.content == _png_bytes()


def test_photo_is_dealer_scoped(client, tmp_path):
    token_a = _signup(client, tmp_path, email="hqa@example.com", dealer="Dealer A")
    token_b = _signup(client, tmp_path, email="hqb@example.com", dealer="Dealer B", shortcode="PT002")

    upload = client.post(
        "/api/v1/uploads/photo",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("photo.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert upload.status_code == 201
    photo_url = upload.json()["photo_url"]

    other = client.get(photo_url, headers={"Authorization": f"Bearer {token_b}"})
    assert other.status_code == 404


def test_upload_requires_auth_and_image(client, tmp_path):
    account_services.settings.UPLOAD_DIR = str(tmp_path)

    anon = client.post(
        "/api/v1/uploads/photo",
        files={"file": ("photo.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert anon.status_code in (401, 403)

    token = _signup(client, tmp_path)
    bad = client.post(
        "/api/v1/uploads/photo",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert bad.status_code == 422
    assert "PNG, JPEG, or WebP" in bad.json()["detail"]


def test_path_traversal_is_rejected(client, tmp_path):
    token = _signup(client, tmp_path)
    got = client.get(
        "/api/v1/uploads/photo/..%2F..%2Fenemies.png",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert got.status_code == 404