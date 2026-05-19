import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_healthz_returns_ok() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_me_requires_bearer_token() -> None:
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_accepts_valid_token(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-test-secret-test-secret-test-secret")
    get_settings.cache_clear()
    secret = get_settings().supabase_jwt_secret
    token = jwt.encode(
        {"sub": "11111111-1111-1111-1111-111111111111", "email": "u@e.com", "aud": "authenticated"},
        secret,
        algorithm="HS256",
    )
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "u@e.com"
    get_settings.cache_clear()
