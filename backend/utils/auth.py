import time
import logging
from typing import Optional
from fastapi import HTTPException, Request
from jose import jwt, jwk  # Certifique-se de ter jose (pip install python-jose)
import requests
import os
from backend.config import settings

logger = logging.getLogger(__name__)

# Carregue as vars com checks (adicione em settings.py se não tiver)
if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL ou SUPABASE_ANON_KEY não configurados!")

# Nova var: o real JWT Secret para HS256 fallback (pegue do Supabase dashboard > Auth > JWT Settings)
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET  # Adicione isso no settings.py: os.getenv("SUPABASE_JWT_SECRET")

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
                headers={"Accept": "application/json"}  # Sem apikey! É público.
            )
            response.raise_for_status()  # Levanta se não 200
            data = response.json()
            _jwks_cache = {"data": data, "expires_at": now + 300}  # Cache 5min
            logger.info(f"✅ JWKS obtido com sucesso de {url}")
            return data
        except requests.RequestException as e:
            logger.warning(f"⚠️ Erro ao buscar de {url}: {str(e)}")
            continue
    
    # Sem fallback pra cache antigo aqui; melhor falhar e usar HS256
    logger.error("❌ Falha total ao obter JWKS. Verifique SUPABASE_URL e rede.")
    return None

def get_current_user_claims(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")
    
    token = auth_header.split(" ", 1)[1]

    jwks = _get_jwks()
    
    if jwks:
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise ValueError("JWT sem 'kid' header")
            
            signing_key_dict = next(
                (k for k in jwks.get("keys", []) if k["kid"] == kid),
                None
            )
            if not signing_key_dict:
                raise ValueError("Chave não encontrada no JWKS")
            
            # Converta JWK dict para public key (fix essencial!)
            algorithm = signing_key_dict.get("alg", "RS256")
            if algorithm == "RS256":
                public_key = jwk.construct(signing_key_dict).to_pem().decode('utf-8')  # Converte para PEM
            else:
                raise ValueError(f"Algoritmo não suportado: {algorithm}")
            
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[algorithm],
                options={"verify_aud": False}  # Adicione audience se precisar: audience="authenticated"
            )
            logger.info(f"✅ Token validado com {algorithm}")
            return claims
        except Exception as e:
            logger.warning(f"⚠️ Falha na validação RS256: {str(e)}")
    
    try:
        logger.info("🔄 Tentando validação com HS256")
        claims = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        logger.info(f"✅ Token validado com HS256")
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expired")
    except Exception as e:
        logger.error(f"❌ Erro ao validar token: {str(e)}")
        raise HTTPException(401, detail=f"Invalid token: {str(e)}")