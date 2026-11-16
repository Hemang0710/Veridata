"""Auth gate on /upload and /ask: valid, invalid, and absent tokens.

No network: HS256 tokens are minted locally with the same test secret the
dependency verifies against.
"""

import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

SECRET = "test-jwt-secret-at-least-32-bytes-long"
SAMPLE = Path(__file__).parent / "data" / "sample.csv"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(secret=SECRET, sub="user-123"):
    return jwt.encode(
        {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )


def _upload(client, headers=None):
    with open(SAMPLE, "rb") as f:
        return client.post(
            "/upload",
            files={"file": ("sample.csv", f, "text/csv")},
            headers=headers or {},
        )


def test_valid_token_is_accepted(client):
    resp = _upload(client, {"Authorization": f"Bearer {_token()}"})
    assert resp.status_code == 200


def test_invalid_token_is_rejected(client):
    # Signed with the wrong secret -> signature verification fails.
    bad = _token(secret="a-different-secret-also-32-bytes-long")
    assert _upload(client, {"Authorization": f"Bearer {bad}"}).status_code == 401
    assert (
        client.post(
            "/ask", json={"question": "x"}, headers={"Authorization": f"Bearer {bad}"}
        ).status_code
        == 401
    )


def test_absent_token_is_rejected(client):
    # Both protected endpoints reject a request with no token.
    assert _upload(client).status_code == 401
    assert client.post("/ask", json={"question": "x"}).status_code == 401
