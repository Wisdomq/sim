"""Test configuration for the backend API."""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/simcards_tests.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import simcards_backend.models  # noqa: F401
from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import Base, engine, SessionLocal
from simcards_backend.main import app

# Run Celery tasks synchronously in tests (matches tests/test_reconciliation.py).
celery_app.conf.task_always_eager = True


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """Provide a database session for unit tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
