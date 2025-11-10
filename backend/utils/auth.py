from typing import Optional
from fastapi import HTTPException, Request
from jose import jwt
import requests
import os

SUPABASE_JWKS_URL = f"{os.getenv('SUPABASE_URL')}/auth/v1/keys"

_jwks_cache = None
def _get_jwks():
    global _jwks_cache
    if _jwks_cache: return _jwks_cache
    _jwks_cache = requests.get(SUPABASE_JWKS_URL, timeout=10).json()
    return _jwks_cache

def get_current_user_claims(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = auth.split(" ", 1)[1]

    jwks = _get_jwks()
    unverified = jwt.get_unverified_header(token)
    kid = unverified.get("kid")
    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if not key:
        raise HTTPException(401, "JWKS key not found")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=None,  # aud é opcional no Supabase
            options={"verify_aud": False}
        )
        return claims
    except Exception:
        raise HTTPException(401, "Invalid token")
