from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Analysis
from backend.utils.auth import get_current_user_claims
from backend.utils.tenant import get_tenant_id
import json

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ======================================================
# 🧩 Dependência padrão do banco
# ======================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# 🔹 LISTAR ANÁLISES (seguro por tenant e job)
# ======================================================
@router.get("/")
def list_analysis(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id),
    job_id: str | None = None,
    limit: int = 500,
    offset: int = 0,
):
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID inválido ou ausente.")
    
    try:
        # Base query
        q = db.query(Analysis).filter(Analysis.tenant_id == tenant_id)

        # Filtro opcional por vaga
        if job_id:
            q = q.filter(Analysis.job_id == job_id)

        # Ordenação e paginação
        q = q.order_by(Analysis.created_at.desc()).offset(offset).limit(limit)

        # Serialização segura
        items = []
        for a in q.all():
            def safe_json(value):
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except Exception:
                        return []
                return value if isinstance(value, list) else []
            
            items.append({
                "id": a.id,
                "resume_id": a.resume_id,
                "job_id": a.job_id,
                "tenant_id": a.tenant_id,
                "candidate_name": a.candidate_name,
                "skills": safe_json(a.skills),
                "education": safe_json(a.education),
                "languages": safe_json(a.languages),
                "score": float(a.score) if a.score is not None else None,
                "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
            })

        return {
            "items": items,
            "count": len(items)
        }

    except Exception as e:
        print(f"[ERROR][analysis]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar análises: {e}")
