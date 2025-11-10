from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Membership
from backend.utils.auth import get_current_user_claims


def get_db():
    """Cria e fecha sessão SQLAlchemy automaticamente."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_id(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims)
) -> str:
    """
    Retorna o tenant_id validado com base no token Supabase e header X-Tenant-Id.
    Garante que o usuário é membro ativo do workspace.
    """
    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header is required")

    user_id = claims.get("sub") or claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token (missing subject)")

    # 🔍 Validação de membership via ORM
    member = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
        .first()
    )

    if not member:
        raise HTTPException(status_code=403, detail="User not authorized for this tenant")

    return tenant_id
