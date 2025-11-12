# backend/routes/jobs.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Job
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id
from backend.schemas.job import JobCreate
import uuid, json

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
                    "criteria": j.criteria if isinstance(j.criteria, list) else [],
                    "created_at": j.created_at.isoformat() if getattr(j, "created_at", None) else None,
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
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID inválido ou ausente.")
    try:
        criteria_safe = json.loads(json.dumps(job.criteria)) if job.criteria else []

        job_obj = Job(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=job.title,
            description=job.main_activities or "",                       
            main_activities=job.main_activities or "",   
            prerequisites=job.prerequisites or "",
            differentials=job.differentials or "",
            criteria=criteria_safe,
            # description pode ser opcional dependendo da tabela:
            **({"description": job.main_activities} if hasattr(Job, "description") else {}),
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
                "created_at": job_obj.created_at.isoformat() if getattr(job_obj, "created_at", None) else None,
            },
        }
    except Exception as e:
        db.rollback()
        print(f"[ERROR][create_job]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar vaga: {e}")
    
    finally:
        db.close()
