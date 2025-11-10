from fastapi import APIRouter, Depends
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
def get_current_user(
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Retorna as informações básicas do usuário autenticado e tenant atual.
    """
    return {
        "user_id": claims.get("sub") or claims.get("user_id"),
        "email": claims.get("email"),
        "tenant_id": tenant_id
    }
