from __future__ import annotations


def _signup_hq(client):
    response = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Dealer One",
            "safaricom_dealer_shortcode": "D001",
            "hq_email": "hq@example.com",
            "hq_password": "supersecret",
        },
    )
    assert response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "hq@example.com", "password": "supersecret"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_branch(client, hq_token):
    response = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Branch A",
            "type": "SHOP",
            "id_number": "BR-001",
            "photo_url": "https://example.com/branch-a.jpg",
            "email": "branch@example.com",
            "password": "branchsecret",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_onboarding_login_and_account_permissions(client):
    hq_token = _signup_hq(client)

    missing_photo = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "No Photo Branch",
            "type": "VAN",
            "id_number": "BR-002",
            "photo_url": "",
            "email": "missing-photo@example.com",
            "password": "branchsecret",
        },
    )
    assert missing_photo.status_code == 422

    branch = _create_branch(client, hq_token)
    branch_login = client.post(
        "/api/v1/auth/login",
        json={"email": "branch@example.com", "password": "branchsecret"},
    )
    assert branch_login.status_code == 200
    branch_token = branch_login.json()["access_token"]

    ba_response = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "BA One",
            "email": "ba@example.com",
            "password": "basecret123",
            "phone_msisdn": "254700000001",
            "id_number": "BA-001",
            "photo_url": "https://example.com/ba-one.jpg",
        },
    )
    assert ba_response.status_code == 201
    assert ba_response.json()["branch_id"] == branch["id"]

    forbidden_delete = client.delete(
        f"/api/v1/brand-ambassadors/{ba_response.json()['id']}",
        headers={"Authorization": f"Bearer {branch_token}"},
    )
    assert forbidden_delete.status_code == 403

    hq_delete = client.delete(
        f"/api/v1/brand-ambassadors/{ba_response.json()['id']}",
        headers={"Authorization": f"Bearer {hq_token}"},
    )
    assert hq_delete.status_code == 204
