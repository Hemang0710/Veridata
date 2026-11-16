"""Supabase JWT verification: a FastAPI dependency yielding the user id.

HS256 shared-secret verification against SUPABASE_JWT_SECRET (read from env, no
network). Supabase documents this alongside asymmetric signing keys and now
nudges new projects toward the latter.
ponytail: HS256 shared secret; switch to asymmetric signing keys verified via
the JWKS endpoint (RS256/ES256) if/when we rotate to public-key signing.
"""

from __future__ import annotations

import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# auto_error=False: a missing header should be our own 401, not HTTPBearer's 403.
_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Verify the Supabase access token and return its `sub` (the user id).

    Rejects an absent or invalid token with 401. The user id comes only from the
    verified token — never from the request body.
    """
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Auth is not configured")

    try:
        payload = jwt.decode(
            creds.credentials,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub")
    return user_id
