from .ai_service import OpenAIClient
from .pdf_service import read_pdf, read_pdf_bytes
from sqlalchemy.orm import Session
from database.models import Resume, Analysis
import uuid
import traceback

ai = OpenAIClient()


def process_resume(
    db: Session,
    *,
    tenant_id: str,
    job: dict,
    file_url: str,
    raw_bytes: bytes | None = None,
    local_path: str | None = None
):
    """
    Pipeline síncrono de análise de currículo.
    1️⃣ Extrai texto do PDF
    2️⃣ Gera resumo, opinião e score com IA
    3️⃣ Persiste no banco (Resume + Analysis)
    """
    resume_id = str(uuid.uuid4())
    print(f"[process_resume] Iniciando processamento para job={job.get('id')} tenant={tenant_id}")

    try:
        # ==============================
        # 1) Extração do texto
        # ==============================
        if raw_bytes:
            raw_text = read_pdf_bytes(raw_bytes)
        elif local_path:
            raw_text = read_pdf(local_path)
        else:
            raise ValueError("Nem raw_bytes nem local_path foram fornecidos.")

        # ==============================
        # 2) Análise com IA
        # ==============================
        summary = ai.resume_cv(raw_text)
        opinion = ai.generate_opinion(raw_text, job)
        score = ai.generate_score(raw_text, job)

        # ==============================
        # 3) Criar registro do Resume
        # ==============================
        resume = Resume(
            id=resume_id,
            tenant_id=tenant_id,
            job_id=job["id"],
            file_url=file_url or (local_path or ""),
            raw_text=raw_text,
            summary=summary,
            opinion=opinion,
            score=score,
            status="done",
        )
        db.add(resume)

        # ==============================
        # 4) Criar registro do Analysis
        # ==============================
        analysis = Analysis(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            job_id=job["id"],
            resume_id=resume_id,
            candidate_name="(extraído pela IA futuramente)",
            skills=[],
            education=[],
            languages=[],
            score=score,
        )
        db.add(analysis)

        db.commit()
        db.refresh(resume)

        print(f"[process_resume] ✅ Currículo {resume_id} processado com sucesso (tenant={tenant_id})")
        return resume

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        print(f"[process_resume][ERROR] Falha ao processar resume={resume_id}: {e}")

        # Salvar registro com status failed
        failed_resume = Resume(
            id=resume_id,
            tenant_id=tenant_id,
            job_id=job.get("id", ""),
            file_url=file_url or "",
            raw_text="",
            summary="",
            opinion=str(e),
            score=None,
            status="failed",
        )
        db.add(failed_resume)
        db.commit()
        return failed_resume
