import time
import logging
from typing import Optional
from fastapi import HTTPException, Request
from jose import jwt
import requests
import os
from backend.config import settings

logger = logging.getLogger(__name__)

SUPABASE_JWKS_URL = f"{os.getenv('SUPABASE_URL')}/auth/v1/keys"

_jwks_cache = {"data": None, "expires_at": 0}
def _get_jwks() -> dict:
    global _jwks_cache
    now = time.time()
    if _jwks_cache["data"] and now < _jwks_cache["expires_at"]:
        return _jwks_cache["data"]
    try:
        response = requests.get(SUPABASE_JWKS_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        _jwks_cache = {"data": data, "expires_at": now + 3600}
        return data
    except Exception as e:
        # Se falhar, tenta usar cache antigo
        if _jwks_cache["data"]:
            logger.warning(f"⚠️ Falha ao atualizar JWKS, usando cache: {e}")
            return _jwks_cache["data"]
        logger.error(f"❌ Erro crítico ao buscar JWKS: {e}")
        raise HTTPException(502, f"Erro ao buscar JWKS do Supabase: {e}")

def get_current_user_claims(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")
    
    token = auth_header.split(" ", 1)[1]

    jwks = _get_jwks()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(401, detail="Invalid token format")
    
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(401, detail="Token missing 'kid' in header")
    
    signing_key = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
    if not signing_key:
        logger.warning(f"⚠️ JWKS key não encontrada: kid={kid}")
        raise HTTPException(401, detail="JWKS signing key not found")

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=[signing_key.get("alg", "RS256")],
            options={"verify_aud": False}
        )
        logger.debug(f"✅ Token validado: user_id={claims.get('sub')}")
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expired")
    except jwt.JWTClaimsError as e:
        logger.warning(f"⚠️ JWT claims inválidas: {e}")
        raise HTTPException(401, detail=f"Invalid token claims: {e}")
    except Exception as e:
        logger.error(f"❌ Erro ao validar token: {e}")
        raise HTTPException(401, detail=f"Token validation failed: {e}")
