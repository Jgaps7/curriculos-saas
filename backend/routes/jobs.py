# backend/routes/jobs.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Job
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id
from backend.schemas.job import JobCreate
import uuid

router = APIRouter(prefix="/jobs", tags=["Jobs"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def list_jobs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    try:
        jobs = (
            db.query(Job)
            .filter(Job.tenant_id == tenant_id)
            .order_by(Job.created_at.desc())
            .all()
        )
        return {
            "tenant_id": tenant_id,
            "jobs": [
                {
                    "id": j.id,
                    "title": j.title,
                    "main_activities": j.main_activities,
                    "prerequisites": j.prerequisites,
                    "differentials": j.differentials,
                    "criteria": j.criteria,
                    "created_at": j.created_at,
                }
                for j in jobs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar vagas: {e}")

@router.post("/")
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    try:
        job_obj = Job(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=job.title,                       # <- AQUI: atributo, não dict
            main_activities=job.main_activities,   # <- idem
            prerequisites=job.prerequisites,
            differentials=job.differentials,
            criteria=[
                c if isinstance(c, dict) else c.dict()
                for c in (job.criteria or [])
            ],
        )
        db.add(job_obj)
        db.commit()
        db.refresh(job_obj)

        # retorne JSON serializável (evita 500 por objeto ORM)
        return {
            "message": "Vaga criada com sucesso!",
            "job": {
                "id": job_obj.id,
                "title": job_obj.title,
                "main_activities": job_obj.main_activities,
                "prerequisites": job_obj.prerequisites,
                "differentials": job_obj.differentials,
                "criteria": job_obj.criteria,
                "created_at": job_obj.created_at,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar vaga: {e}")
