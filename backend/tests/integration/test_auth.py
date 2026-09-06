"""Regression tests for the "Invalid or expired token" incident: a stale
token from before a JWT_SECRET rotation, or one that has genuinely expired,
must be rejected with a clean 401 (never silently accepted), while a freshly
issued token for the same user must keep working — proving decode is keyed
off the live configured secret, not some cached/mismatched one."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.api.v1.deps import get_db
from app.core.config import get_settings
from app.core.security import TokenError, create_access_token, decode_access_token
from app.main import app


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_freshly_issued_token_decodes_successfully():
    token = create_access_token(subject="usr_test", role="CFO")
    payload = decode_access_token(token)
    assert payload["sub"] == "usr_test"
    assert payload["role"] == "CFO"


def test_expired_token_raises_typed_expired_error():
    settings = get_settings()
    expired_payload = {
        "sub": "usr_test",
        "role": "CFO",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(TokenError) as exc_info:
        decode_access_token(expired_token)
    assert exc_info.value.reason == "expired"


def test_token_signed_with_wrong_secret_is_rejected():
    """Simulates the exact incident: a token minted under a different
    JWT_SECRET (e.g. an older process launch that resolved a different
    .env) must never be accepted by the current process."""
    wrong_secret_payload = {
        "sub": "usr_test",
        "role": "CFO",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token_from_other_secret = jwt.encode(wrong_secret_payload, "a-completely-different-secret", algorithm="HS256")

    with pytest.raises(TokenError) as exc_info:
        decode_access_token(token_from_other_secret)
    assert exc_info.value.reason == "invalid_signature_or_malformed"


def test_protected_route_rejects_missing_authorization_header(client):
    response = client.post("/api/v1/scenarios", json={"scenario_type": "FUNDING_CHANGE", "params": {"pct": 10}})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_protected_route_rejects_stale_token(client):
    settings = get_settings()
    stale_token = jwt.encode(
        {"sub": "usr_test", "role": "CFO", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = client.post(
        "/api/v1/scenarios",
        json={"scenario_type": "FUNDING_CHANGE", "params": {"pct": 10}},
        headers={"Authorization": f"Bearer {stale_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_protected_route_accepts_freshly_issued_token(client):
    fresh_token = create_access_token(subject="usr_test", role="CFO")
    response = client.post(
        "/api/v1/scenarios",
        json={"scenario_type": "FUNDING_CHANGE", "params": {"pct": 10}},
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    assert response.status_code == 200


def test_malformed_authorization_scheme_is_rejected(client):
    response = client.post(
        "/api/v1/scenarios",
        json={"scenario_type": "FUNDING_CHANGE", "params": {"pct": 10}},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401
