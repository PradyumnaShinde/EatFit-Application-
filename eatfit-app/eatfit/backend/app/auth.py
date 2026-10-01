"""Who is calling? Returns the user's id (a UUID string) for every request.

AUTH_MODE=supabase : the app sends 'Authorization: Bearer <Supabase access token>'.
                     We verify the token's signature, expiry, audience and issuer.
AUTH_MODE=dev      : for local development only, send 'X-User-Id: <any uuid>'.
"""
import json
import urllib.request
import uuid
from typing import Optional

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from .config import settings

_jwks_client: Optional[PyJWKClient] = None


def _jwks():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
            cache_keys=True, lifespan=3600)
    return _jwks_client


def verify_supabase_token(token: str) -> str:
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":                       # legacy shared-secret projects
            if not settings.supabase_jwt_secret:
                raise HTTPException(401, "Token type not accepted")
            key, algorithms = settings.supabase_jwt_secret, ["HS256"]
        else:                                    # new asymmetric signing keys (recommended)
            key, algorithms = _jwks().get_signing_key_from_jwt(token).key, ["RS256", "ES256"]

        claims = jwt.decode(
            token, key, algorithms=algorithms, audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1" if settings.supabase_url else None,
        )
        return str(uuid.UUID(claims["sub"]))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid or expired login, please sign in again")


def current_user(authorization: Optional[str] = Header(None),
                 x_user_id: Optional[str] = Header(None)) -> str:
    if settings.auth_mode == "dev":
        try:
            return str(uuid.UUID(x_user_id or ""))
        except ValueError:
            raise HTTPException(401, "Dev mode: send header X-User-Id with a UUID")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing login token")
    return verify_supabase_token(authorization.split(" ", 1)[1])


def delete_login(uid: str):
    """Delete the user's Supabase Auth account (needs SUPABASE_SERVICE_ROLE_KEY).
    Their rows are also removed by the ON DELETE CASCADE foreign keys."""
    if settings.auth_mode != "supabase" or not settings.supabase_service_key:
        return False
    req = urllib.request.Request(
        f"{settings.supabase_url}/auth/v1/admin/users/{uid}", method="DELETE",
        headers={"apikey": settings.supabase_service_key,
                 "Authorization": f"Bearer {settings.supabase_service_key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return 200 <= r.status < 300
