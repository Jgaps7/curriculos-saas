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

def _get_jwks() -> Optional[dict]:
    global _jwks_cache
    now = time.time()
    if _jwks_cache["data"] and now < _jwks_cache["expires_at"]:
        logger.info("🔑 Usando JWKS do cache")
        return _jwks_cache["data"]
    
    # URLs corretas baseadas em docs Supabase (priorize a principal)
    jwks_urls = [
        f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",  # Principal
        f"{settings.SUPABASE_URL}/.well-known/jwks.json",           # Alternativa sem /auth/v1/
    ]
    
    for url in jwks_urls:
        try:
            logger.info(f"🔑 Tentando buscar JWKS de: {url}")
            response = requests.get(
                url,
                timeout=10,
                headers={"Accept": "application/json"}  
            )
            response.raise_for_status()  
            data = response.json()
            _jwks_cache = {"data": data, "expires_at": now + 300}  # Cache 5min
            logger.info(f"✅ JWKS obtido com sucesso de {url}")
            return data
        except requests.RequestException as e:
            logger.warning(f"⚠️ Erro ao buscar de {url}: {str(e)}")
            continue
    
    logger.error("❌ Falha total ao obter JWKS. Verifique SUPABASE_URL e rede.")
    return None

def get_current_user_claims(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")

    token = auth_header.split(" ", 1)[1]

    unverified_header = jwt.get_unverified_header(token)
    alg = unverified_header.get("alg")

    # ❗ Seu Supabase NÃO usa JWKS / RS256 → tudo é HS*
    if alg.startswith("HS"):
        try:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256", "HS512"],
                options={"verify_aud": False}
            )
        except Exception as e:
            raise HTTPException(401, detail=f"Invalid token: {str(e)}")

    raise HTTPException(401, detail=f"Unsupported alg: {alg}")