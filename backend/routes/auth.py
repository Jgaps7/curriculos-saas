import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Tenant, Membership
from backend.schemas.user import UserRegister
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ========================================
# 🔧 Dependency de sessão DB
# ========================================
def get_db():
    """Cria e fecha sessão do banco automaticamente."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========================================
# 📝 POST /auth/register - Criar Tenant
# ========================================
@router.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Cria tenant e membership após registro no Supabase Auth.
    
    Este endpoint é chamado pelo FRONTEND depois que o usuário
    já foi criado no Supabase Auth.
    
    Args:
        data: Dados do registro (user_id, company_name, etc)
        db: Sessão do banco de dados
        
    Returns:
        dict: {"success": True, "tenant_id": "...", "message": "..."}
        
    Raises:
        HTTPException: 500 se falhar ao criar tenant/membership
    """
    try:
        logger.info(f"📝 Iniciando registro: user_id={data.user_id}, company={data.company_name}")
        
        # ========================================
        # 1️⃣ Verificar se usuário já tem tenant
        # ========================================
        existing = db.query(Membership).filter(
            Membership.user_id == data.user_id
        ).first()
        
        if existing:
            logger.warning(f"⚠️ Usuário {data.user_id} já possui tenant")
            return {
                "success": True,
                "tenant_id": existing.tenant_id,
                "message": "Usuário já possui tenant cadastrado"
            }
        
        # ========================================
        # 2️⃣ Criar Tenant (empresa/workspace)
        # ========================================
        tenant_id = str(uuid.uuid4())
        
        tenant = Tenant(
            id=tenant_id,
            name=data.company_name
        )
        db.add(tenant)
        
        logger.info(f"✅ Tenant criado: {tenant_id}")
        
        # ========================================
        # 3️⃣ Criar Membership (owner)
        # ========================================
        membership = Membership(
            tenant_id=tenant_id,
            user_id=data.user_id,
            role="owner"  # Primeiro usuário é sempre owner
        )
        db.add(membership)
        
        logger.info(f"✅ Membership criado: user={data.user_id}, role=owner")
        
        # ========================================
        # 4️⃣ Commit no banco
        # ========================================
        db.commit()
        
        logger.info(f"🎉 Registro completo: tenant_id={tenant_id}")
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "message": "Tenant criado com sucesso!"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao criar tenant: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar tenant: {str(e)}"
        )


# ========================================
# 🔍 GET /auth/user-info - Info do Usuário
# ========================================
@router.get("/user-info/{user_id}")
def get_user_info(user_id: str, db: Session = Depends(get_db)):
    """
    Retorna informações do usuário e seus tenants.
    
    Args:
        user_id: ID do usuário no Supabase Auth
        
    Returns:
        dict: {"user_id": "...", "tenants": [...]}
    """
    try:
        memberships = db.query(Membership).filter(
            Membership.user_id == user_id
        ).all()
        
        if not memberships:
            raise HTTPException(
                status_code=404,
                detail="Usuário não possui tenants"
            )
        
        tenants = []
        for m in memberships:
            tenant = db.query(Tenant).filter(Tenant.id == m.tenant_id).first()
            if tenant:
                tenants.append({
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "role": m.role
                })
        
        return {
            "user_id": user_id,
            "tenants": tenants
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar info do usuário: {e}")
        raise HTTPException(500, f"Erro interno: {e}")