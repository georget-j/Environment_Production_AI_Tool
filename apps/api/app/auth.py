"""Supabase JWT verification.

Newer Supabase projects sign user tokens with ES256 and publish keys at
/auth/v1/.well-known/jwks.json. We verify against the JWKS by default.

For local tests we also accept HS256 — set SUPABASE_JWT_SECRET and the
verifier will fall back to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)

_JWKS_ALGS = ("ES256", "RS256")
_HS_ALGS = ("HS256",)


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str | None


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    settings = get_settings()
    if not settings.supabase_url:
        return None
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(url, cache_keys=True, lifespan=3600)


def _decode(token: str) -> dict:
    settings = get_settings()

    # Inspect the header to decide algorithm path.
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token header: {exc}") from exc

    alg = header.get("alg")

    if alg in _JWKS_ALGS:
        client = _jwks_client()
        if client is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_URL must be set to verify JWKS-signed tokens",
            )
        try:
            signing_key = client.get_signing_key_from_jwt(token).key
            return jwt.decode(token, signing_key, algorithms=list(_JWKS_ALGS), audience="authenticated")
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    if alg in _HS_ALGS:
        if not settings.supabase_jwt_secret:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_JWT_SECRET required to verify HS256 tokens",
            )
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=list(_HS_ALGS),
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Unsupported alg: {alg}")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = _decode(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token has no sub")
    return AuthUser(id=UUID(sub), email=payload.get("email"))
