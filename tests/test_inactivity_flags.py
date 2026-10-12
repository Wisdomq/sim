"""Phase 7 tests: login-inactivity flagging + HQ notifications."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from simcards_backend.core.database import SessionLocal
from simcards_backend.core.security import now_utc
from simcards_backend.models import (
    AccountFlag,
    AccountStatus,
    LoginEvent,
    NotificationType,
    User,
)
from simcards_backend.services.inactivity import default_cutoff, flag_inactive_accounts


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _setup_accounts(client):
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Inactivity Dealer",
            "safaricom_dealer_shortcode": "D700",
            "hq_email": "hq@inactivity.example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "hq@inactivity.example.com", "supersecret")
    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Inactive Shop",
            "type": "SHOP",
            "id_number": "BR-701",
            "photo_url": "https://example.com/branch.jpg",
            "email": "branch1@inactivity.example.com",
            "password": "branchsecret",
        },
    )
    assert branch.status_code == 201
    branch_token = _login(client, "branch1@inactivity.example.com", "branchsecret")
    ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "Inactive BA",
            "email": "ba1@inactivity.example.com",
            "password": "basecret123",
            "phone_msisdn": "254700000701",
            "id_number": "BA-701",
            "photo_url": "https://example.com/ba.jpg",
        },
    )
    assert ba.status_code == 201
    return hq_token, branch_token, branch.json(), ba.json()


def test_flag_inactive_and_notification_feed_and_login_autoclear(client):
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    # The branch user has logged in (recently) during setup; rewind the event so
    # the account appears inactive, then run the daily flagging job.
    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == "branch1@inactivity.example.com"))
        login_event = db.scalars(select(LoginEvent).where(LoginEvent.user_id == branch_user.id)).one()
        login_event.logged_in_at = now_utc() - timedelta(days=4)
        db.commit()

        as_of, cutoff = default_cutoff()
        outcome = flag_inactive_accounts(db, dealer_id=branch_user.dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        assert outcome.freshly_flagged_count == 1, outcome
        assert outcome.flagged_user_ids == [branch_user.id], outcome
        db.refresh(branch_user)
        assert branch_user.status == AccountStatus.FLAGGED_INACTIVE

    headers = {"Authorization": f"Bearer {hq_token}"}

    # The BA never logged in but was created recently: should not be flagged yet.
    flags = client.get("/api/v1/flags", headers=headers)
    assert flags.status_code == 200
    body = flags.json()
    assert len(body) == 1
    assert body[0]["role"] == "BRANCH"
    assert body[0]["last_login_at"] is not None
    flag_id = body[0]["id"]

    assert client.get("/api/v1/flags?resolved=true", headers=headers).json() == []

    ack = client.post(f"/api/v1/flags/{flag_id}/acknowledge", headers=headers)
    assert ack.status_code == 200
    assert ack.json()["acknowledged_by_id"] is not None

    resolved = client.post(f"/api/v1/flags/{flag_id}/resolve", headers=headers)
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None
    assert len(client.get("/api/v1/flags?resolved=true", headers=headers).json()) == 1

    # HQ in-app notification feed (design §6.10).
    feed = client.get("/api/v1/flags/notifications", headers=headers)
    assert feed.status_code == 200
    feed_body = feed.json()
    assert len(feed_body) == 1
    assert feed_body[0]["type"] == "ACCOUNT_FLAGGED_INACTIVE"
    assert feed_body[0]["metadata_json"]["role"] == "BRANCH"
    assert feed_body[0]["metadata_json"]["last_login"] is not None
    notif_id = feed_body[0]["id"]

    unread = client.get("/api/v1/flags/notifications?unread_only=true", headers=headers)
    assert len(unread.json()) == 1

    read = client.post(f"/api/v1/flags/notifications/{notif_id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    assert client.get("/api/v1/flags/notifications?unread_only=true", headers=headers).json() == []

    # The account is still FLAGGED_INACTIVE until the user logs in again.
    branch_token = _login(client, "branch1@inactivity.example.com", "branchsecret")
    assert branch_token
    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == "branch1@inactivity.example.com"))
        assert branch_user.status == AccountStatus.ACTIVE
        open_flags = db.scalars(
            select(AccountFlag).where(
                AccountFlag.user_id == branch_user.id,
                AccountFlag.resolved_at.is_(None),
            )
        ).all()
        assert open_flags == []


def test_flagging_idempotent_and_old_never_logged_in_accounts(client):
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    with SessionLocal() as db:
        ba_user = db.scalar(select(User).where(User.email == "ba1@inactivity.example.com"))
        as_of, cutoff = default_cutoff()

        # Newly created account with no login: not flagged yet (created recently).
        outcome = flag_inactive_accounts(db, dealer_id=ba_user.dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        assert outcome.freshly_flagged_count == 0

        # Once the account has existed longer than the window, flag it.
        ba_user.created_at = now_utc() - timedelta(days=10)
        db.commit()
        outcome2 = flag_inactive_accounts(db, dealer_id=ba_user.dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        assert outcome2.freshly_flagged_count == 1

# Re-running the job does not create duplicates for open flags.
        outcome3 = flag_inactive_accounts(db, dealer_id=ba_user.dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()
        assert outcome3.freshly_flagged_count == 0
        open_flags = db.scalars(
            select(AccountFlag).where(
                AccountFlag.user_id == ba_user.id,
                AccountFlag.resolved_at.is_(None),
            )
        ).all()
        assert len(open_flags) == 1

    flags = client.get("/api/v1/flags", headers={"Authorization": f"Bearer {hq_token}"})
    assert flags.status_code == 200
    assert len(flags.json()) == 1
    assert flags.json()[0]["role"] == "BA"


def test_flag_notification_created_for_hq_only(client):
    hq_token, branch_token, branch, ba = _setup_accounts(client)

    with SessionLocal() as db:
        branch_user = db.scalar(select(User).where(User.email == "branch1@inactivity.example.com"))
        login_event = db.scalars(select(LoginEvent).where(LoginEvent.user_id == branch_user.id)).one()
        login_event.logged_in_at = now_utc() - timedelta(days=4)
        db.commit()
        as_of, cutoff = default_cutoff()
        flag_inactive_accounts(db, dealer_id=branch_user.dealer_id, cutoff_dt=cutoff, as_of_dt=as_of)
        db.commit()

        from simcards_backend.models import Notification

        hq_user = db.scalar(select(User).where(User.email == "hq@inactivity.example.com"))
        notifications = db.scalars(
            select(Notification).where(
                Notification.dealer_id == hq_user.dealer_id,
                Notification.type == NotificationType.ACCOUNT_FLAGGED_INACTIVE,
            )
        ).all()
        assert len(notifications) == 1
        assert notifications[0].user_id == hq_user.id
        assert notifications[0].body is not None

    # BA cannot see the HQ notification feed.
    ba_login = client.post(
        "/api/v1/auth/login",
        json={"email": "ba1@inactivity.example.com", "password": "basecret123"},
    )
    assert ba_login.status_code == 200
    forbidden = client.get(
        "/api/v1/flags/notifications",
        headers={"Authorization": f"Bearer {ba_login.json()['access_token']}"},
    )
    assert forbidden.status_code == 403