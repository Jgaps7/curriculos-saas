import time
import logging
from typing import Optional
from fastapi import HTTPException, Request
from jose import jwt, jwk  # Certifique-se de ter jose (pip install python-jose)
import requests
from backend.config import settings

logger = logging.getLogger(__name__)

# Carregue as vars com checks (adicione em settings.py se não tiver)
if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL ou SUPABASE_ANON_KEY não configurados!")

# Nova var: o real JWT Secret para HS256 fallback (pegue do Supabase dashboard > Auth > JWT Settings)
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET  

_jwks_cache = {"data": None, "expires_at": 0}

# ======================================================
# 🎫 VALIDAÇÃO DE TOKEN (HS256 ÚNICO)
# ======================================================
def get_current_user_claims(request: Request) -> dict:
    """
    Valida tokens JWT emitidos pelo Supabase em projetos HS256.
    Não usa JWKS, não tenta RS256/ES256.
    100% compatível com seu projeto detectado no log.
    """
    # Extrai o token
    auth_header = request.headers.get("Authorization", "") or ""
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, detail="Empty Bearer token")

    # Lê o header sem validar assinatura
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        logger.error(f"❌ Cabeçalho JWT inválido: {e}")
        raise HTTPException(401, detail="Invalid token header")

    alg = header.get("alg")
    if not alg:
        raise HTTPException(401, detail="Token missing 'alg' header")

    # ==========================================================
    # 🔥 Seu Supabase usa APENAS HS256 → portanto só aceitamos HS*
    # ==========================================================
    if not alg.startswith("HS"):
        logger.error(f"❌ Algoritmo não suportado: {alg}")
        raise HTTPException(401, detail=f"Unsupported JWT alg: {alg}")

    # ==========================================================
    # 🔥 Tenta validar como HS256 ou HS512 (compatibilidade total)
    # ==========================================================
    try:
        claims = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256", "HS512"],  # Permite variações seguras
            options={"verify_aud": False}   # Supabase não usa aud por padrão
        )
        logger.info(f"✅ Token validado com sucesso usando {alg}")
        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ Token expirado")
        raise HTTPException(401, detail="Token expired")

    except Exception as e:
        logger.error(f"❌ Falha ao validar token HS*: {e}")
        raise HTTPException(401, detail=f"Invalid token: {str(e)}")