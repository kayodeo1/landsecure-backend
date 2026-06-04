"""Test configuration — isolated SQLite DB + seeded TestClient."""
from __future__ import annotations

import os
import tempfile

# Point the app at a throwaway SQLite DB *before* importing it.
_TMP = tempfile.mkdtemp(prefix="landsecure_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # entering the context runs the lifespan → init_db + seed demo data
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/api/auth/login", json={
        "email": settings.seed_admin_email, "password": settings.seed_admin_password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def buyer_token(client):
    r = client.post("/api/auth/login", json={
        "email": settings.seed_buyer_email, "password": settings.seed_buyer_password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
