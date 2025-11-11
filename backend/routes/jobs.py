from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Job
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id
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
    jobs = db.query(Job).filter(Job.tenant_id == tenant_id).order_by(Job.created_at.desc()).all()

    if not jobs:
        return {"message": "Nenhuma vaga encontrada."}

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

@router.post("/")
def create_job(
    job: dict,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id)
):
    if "title" not in job:
        raise HTTPException(400, "O campo 'title' é obrigatório.")

    job_obj = Job(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=job["title"],
        main_activities=job.get("main_activities", ""),
        prerequisites=job.get("prerequisites", ""),
        differentials=job.get("differentials", ""),
        criteria=job.get("criteria", []),
    )

    db.add(job_obj)
    db.commit()
    db.refresh(job_obj)
    return job_obj
