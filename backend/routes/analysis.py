from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Analysis
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id


router = APIRouter(prefix="/analysis", tags=["Analysis"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/")
def list_analysis(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id),
    job_id: str | None = None,
    limit: int = 500,
    offset: int = 0
):
    q = db.query(Analysis).filter(Analysis.tenant_id == tenant_id)
    if job_id:
        q = q.filter(Analysis.job_id == job_id)
    q = q.order_by(Analysis.created_at.desc()).offset(offset).limit(limit)
    items = [
        {
            "id": a.id,
            "resume_id": a.resume_id,
            "job_id": a.job_id,
            "tenant_id": a.tenant_id,
            "candidate_name": a.candidate_name,
            "skills": a.skills or [],
            "education": a.education or [],
            "languages": a.languages or [],
            "score": a.score,
            "created_at": a.created_at,
        }
        for a in q.all()
    ]
    return {"items": items, "count": len(items)}
