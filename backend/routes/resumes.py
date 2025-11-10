from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Job
from services.pipeline import process_resume  # versão síncrona (para debug)
from tasks.tasks import enqueue_analysis       # nova versão assíncrona
from utils.auth import get_current_user_claims
from utils.tenant import get_tenant_id

router = APIRouter(prefix="/resumes", tags=["Resumes"])


# ======================================================
# 🧩 Função padrão para abrir e fechar sessão do banco
# ======================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# 🔹 ENDPOINT ASSÍNCRONO — Usa fila Redis (Produção)
# ======================================================
@router.post("/upload")
async def upload_resume(
    request: Request,
    job_id: str = Form(...),
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Enfileira o processamento do currículo no Redis.
    O tenant_id é validado automaticamente pelo contexto do usuário.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == tenant_id).first()
    if not job:
        raise HTTPException(404, "Vaga não encontrada ou não pertence ao seu tenant")

    pdf_bytes = await pdf.read()
    resume_id = enqueue_analysis(job_id, tenant_id, pdf_bytes)

    return {"status": "queued", "resume_id": resume_id, "tenant_id": tenant_id}


# ======================================================
# 🔹 ENDPOINT SÍNCRONO — Para debug local (sem Redis)
# ======================================================
@router.post("/analyse/sync")
async def analyse_resume_sync(
    request: Request,
    job_id: str = Form(...),
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Processamento completo (sincrônico) — útil para testes locais.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == tenant_id).first()
    if not job:
        raise HTTPException(404, "Vaga não encontrada ou não pertence ao seu tenant")

    content = await pdf.read()
    res = process_resume(
        db,
        tenant_id=tenant_id,
        job={
            "id": job.id,
            "main_activities": job.main_activities,
            "prerequisites": job.prerequisites,
            "differentials": job.differentials,
            "criteria": job.criteria or [],
        },
        file_url="",  # se ainda não usa Supabase Storage
        raw_bytes=content,
    )

    return {"id": res.id, "score": res.score, "status": res.status, "tenant_id": tenant_id}
