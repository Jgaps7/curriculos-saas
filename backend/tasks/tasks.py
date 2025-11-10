import os
import uuid
import traceback
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session
from contextlib import contextmanager
from database.connection import SessionLocal
from database.models import Resume, Job, Analysis
from services.pdf_service import read_pdf_bytes
from services.ai_service import OpenAIClient

ai = OpenAIClient()


# ======================================================
# 🔧 Contexto seguro para abrir/fechar sessão DB
# ======================================================
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] {e}")
        traceback.print_exc()
    finally:
        db.close()


# ======================================================
# 📄 Task 1 — Extrair texto do PDF
# ======================================================
def parse_pdf_task(resume_id: str, tenant_id: str, pdf_bytes: bytes):
    """
    Extrai texto do PDF e atualiza o currículo.
    """
    with get_db() as db:
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.tenant_id == tenant_id)
            .first()
        )
        if not resume:
            print(f"[parse_pdf_task] Resume {resume_id} não encontrado para tenant {tenant_id}.")
            return

        try:
            text = read_pdf_bytes(pdf_bytes)
            resume.raw_text = text
            resume.status = "parsed"
            print(f"[parse_pdf_task] Texto extraído para {resume_id}.")
        except Exception as e:
            resume.status = "failed"
            print(f"[parse_pdf_task][ERROR] {e}")
            traceback.print_exc()


# ======================================================
# 🤖 Task 2 — Analisar currículo com IA
# ======================================================
def analyse_resume_task(resume_id: str, tenant_id: str):
    """
    Executa IA (resumo, opinião, score) e grava no banco.
    """
    with get_db() as db:
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.tenant_id == tenant_id)
            .first()
        )
        if not resume:
            print(f"[analyse_resume_task] Resume {resume_id} não encontrado.")
            return

        job = (
            db.query(Job)
            .filter(Job.id == resume.job_id, Job.tenant_id == tenant_id)
            .first()
        )
        if not job:
            print(f"[analyse_resume_task] Job {resume.job_id} não encontrado para tenant {tenant_id}.")
            return

        try:
            text = resume.raw_text or ""
            summary = ai.resume_cv(text)
            opinion = ai.generate_opinion(text, job.__dict__)
            score = ai.generate_score(text, job.__dict__)

            resume.summary = summary
            resume.opinion = opinion
            resume.score = score
            resume.status = "done"

            # Criar registro detalhado de análise
            analysis = Analysis(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                job_id=job.id,
                resume_id=resume.id,
                candidate_name="(extraído pela IA futuramente)",
                skills=[],
                education=[],
                languages=[],
                score=score,
            )
            db.add(analysis)
            print(f"[analyse_resume_task] Análise concluída para {resume_id}.")
        except Exception as e:
            resume.status = "failed"
            print(f"[analyse_resume_task][ERROR] {e}")
            traceback.print_exc()


# ======================================================
# 🚀 Função principal — Enfileirar processamento
# ======================================================
def enqueue_analysis(job_id: str, tenant_id: str, pdf_bytes: bytes) -> str:
    """
    Cria registro no DB e enfileira as tarefas de PDF e IA.
    """
    with get_db() as db:
        resume_id = str(uuid.uuid4())
        resume = Resume(
            id=resume_id,
            tenant_id=tenant_id,
            job_id=job_id,
            status="queued",
        )
        db.add(resume)
        print(f"[enqueue_analysis] Novo resume criado: {resume_id} (tenant={tenant_id})")

    redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
    q = Queue("default", connection=redis_conn)

    # Enfileira as duas etapas com tenant_id
    q.enqueue(parse_pdf_task, resume_id, tenant_id, pdf_bytes)
    q.enqueue(analyse_resume_task, resume_id, tenant_id)

    print(f"[enqueue_analysis] Tarefas enfileiradas para {resume_id}.")
    return resume_id
