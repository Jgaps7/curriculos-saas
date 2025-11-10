# backend/routes/jobs.py

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Job
from utils.auth import get_current_user_claims
from utils.tenant import get_tenant_id
import uuid

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ==================================================
# 🧩 Dependência padrão de sessão DB
# ==================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================================================
# 🔹 LISTAR VAGAS (seguro por tenant)
# ==================================================
@router.get("/")
def list_jobs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Lista todas as vagas do tenant do usuário autenticado.
    """
    jobs = db.query(Job).filter(Job.tenant_id == tenant_id).order_by(Job.created_at.desc()).all()

    if not jobs:
        return {"message": "Nenhuma vaga encontrada."}

    return {"tenant_id": tenant_id, "jobs": jobs}


# ==================================================
# 🔹 CRIAR VAGA (seguro por tenant)
# ==================================================
@router.post("/")
def create_job(
    job: dict,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Cria uma nova vaga associada ao tenant autenticado.
    """
    if "name" not in job:
        raise HTTPException(400, "O campo 'name' é obrigatório.")

    job_obj = Job(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,  # 🔒 vincula ao tenant do usuário
        name=job["name"],
        main_activities=job.get("main_activities", ""),
        prerequisites=job.get("prerequisites", ""),
        differentials=job.get("differentials", ""),
        criteria=job.get("criteria", []),
    )

    db.add(job_obj)
    db.commit()
    db.refresh(job_obj)
    return job_obj
