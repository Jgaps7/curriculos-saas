import time
import logging
from typing import Optional

from fastapi import HTTPException, Request
from jose import jwt, jwk  # Certifique-se de ter jose (pip install python-jose)
import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# ======================================================
# 🔐 VALIDAÇÃO DE VARIÁVEIS OBRIGATÓRIAS
# ======================================================
if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL ou SUPABASE_ANON_KEY não configurados!")

# Secret real para tokens HS* (pegar em Supabase → Auth → JWT Settings)
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

# Cache simples de JWKS (para tokens assimétricos)
_jwks_cache = {"data": None, "expires_at": 0}


# ======================================================
# 🔑 OBTENÇÃO DO JWKS DO SUPABASE
# ======================================================
def _get_jwks() -> Optional[dict]:
    """
    Busca e cacheia o JWKS do Supabase por 5 minutos.
    Usado para validar tokens RS*/ES*/Ed*/PS*.
    """
    global _jwks_cache
    now = time.time()

    # Usa cache se ainda estiver válido
    if _jwks_cache["data"] and now < _jwks_cache["expires_at"]:
        logger.info("🔑 Usando JWKS do cache")
        return _jwks_cache["data"]

    jwks_urls = [
        f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",  # principal
        f"{settings.SUPABASE_URL}/.well-known/jwks.json",          # alternativa
    ]

    for url in jwks_urls:
        try:
            logger.info(f"🔑 Tentando buscar JWKS de: {url}")
            response = requests.get(
                url,
                timeout=10,
                headers={"Accept": "application/json"},  # público, sem apikey
            )
            response.raise_for_status()
            data = response.json()
            _jwks_cache = {"data": data, "expires_at": now + 300}  # 5 min
            logger.info(f"✅ JWKS obtido com sucesso de {url}")
            return data
        except requests.RequestException as e:
            logger.warning(f"⚠️ Erro ao buscar JWKS em {url}: {str(e)}")
            continue

    logger.error("❌ Falha total ao obter JWKS. Verifique SUPABASE_URL e rede.")
    return None


# ======================================================
# 🎫 FUNÇÃO PRINCIPAL DE VALIDAÇÃO DO TOKEN
# ======================================================
def get_current_user_claims(request: Request) -> dict:
    """
    Extrai o token do header Authorization, identifica o algoritmo (alg)
    e valida o JWT de forma segura, suportando:
      - HS256 / HS512 (Supabase antigo / variações HS)
      - RS256 / RS512 / ES256 / Ed* / PS* (via JWKS)
    """
    auth_header = request.headers.get("Authorization", "") or ""
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, detail="Empty Bearer token")

    # 1️⃣ Lê header sem verificar assinatura (somente para descobrir alg/kid)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        logger.error(f"❌ Header JWT inválido: {e}")
        raise HTTPException(401, detail="Invalid token header")

    alg: Optional[str] = unverified_header.get("alg")
    kid: Optional[str] = unverified_header.get("kid")

    if not alg:
        raise HTTPException(401, detail="Token missing 'alg' header")

    # ==================================================
    # 2️⃣ TOKENS ASSIMÉTRICOS (RS*, ES*, Ed*, PS*)
    # ==================================================
    if alg.startswith(("RS", "ES", "Ed", "PS")):
        jwks = _get_jwks()
        if not jwks:
            logger.error("❌ Não foi possível obter JWKS para validar token")
            raise HTTPException(401, detail="Unable to fetch JWKS")

        if not kid:
            raise HTTPException(401, detail="JWT missing 'kid' header")

        key_dict = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            None,
        )
        if not key_dict:
            logger.error(f"❌ Chave pública não encontrada para kid={kid}")
            raise HTTPException(401, detail="Public key not found for token")

        # Usa o alg da chave, se existir, senão cai pro alg do header
        key_alg = key_dict.get("alg") or alg

        try:
            public_key = jwk.construct(key_dict).to_pem().decode("utf-8")
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[key_alg],
                options={"verify_aud": False},
            )
            logger.info(f"✅ Token validado com algoritmo assimétrico {key_alg}")
            return claims
        except Exception as e:
            logger.error(f"❌ Falha ao validar token assimétrico ({key_alg}): {e}")
            raise HTTPException(401, detail="Invalid token")

    # ==================================================
    # 3️⃣ TOKENS SIMÉTRICOS (HS256 / HS512)
    # ==================================================
    if alg.startswith("HS"):
        # Permitimos HS256 + HS512 pra evitar erro de "alg not allowed"
        allowed_algs = ["HS256", "HS512"]
        if alg not in allowed_algs:
            allowed_algs.insert(0, alg)  # garante que o alg do header entra

        try:
            claims = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=list(dict.fromkeys(allowed_algs)),  # remove duplicados
                options={"verify_aud": False},
            )
            logger.info(f"✅ Token validado com algoritmo simétrico {alg}")
            return claims
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token expirado")
            raise HTTPException(401, detail="Token expired")
        except Exception as e:
            logger.error(f"❌ Falha ao validar token HS*: {e}")
            raise HTTPException(401, detail="Invalid token")

    # ==================================================
    # 4️⃣ ALG DESCONHECIDO
    # ==================================================
    logger.warning(f"Algoritmo JWT não suportado: {alg}")
    raise HTTPException(401, detail=f"Unsupported JWT alg: {alg}")
