import os
import uuid
import traceback
import logging
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session
from contextlib import contextmanager
from backend.database.connection import SessionLocal
from backend.database.models import Resume, Job, Analysis
from backend.services.pdf_service import read_pdf_bytes
from backend.services.ai_service import OpenAIClient
from backend.config import settings

logger = logging.getLogger(__name__)

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
        logger.error(f"❌ [DB ERROR] {e}")
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
            logger.warning(
                f"⚠️ [parse_pdf_task] Resume {resume_id} não encontrado "
                f"para tenant {tenant_id}"
            )
            return

        try:
            text = read_pdf_bytes(pdf_bytes)
            resume.raw_text = text
            resume.status = "parsed"
            logger.info(f"✅ [parse_pdf_task] Texto extraído para {resume_id}")
        except Exception as e:
            resume.status = "failed"
            resume.opinion = f"Erro ao extrair PDF: {str(e)}"
            logger.error(f"❌ [parse_pdf_task] Erro ao processar {resume_id}: {e}")
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
            logger.warning(
                f"⚠️ [analyse_resume_task] Resume {resume_id} não encontrado"
            )
            return

        job = (
            db.query(Job)
            .filter(Job.id == resume.job_id, Job.tenant_id == tenant_id)
            .first()
        )
        if not job:
            logger.warning(
                f"⚠️ [analyse_resume_task] Job {resume.job_id} não encontrado "
                f"para tenant {tenant_id}"
            )
            return

        try:
            text = resume.raw_text or ""
             # Prepara dados da vaga para a IA
            job_data = {
                "main_activities": job.main_activities or "",
                "prerequisites": job.prerequisites or "",
                "differentials": job.differentials or "",
                "criteria": job.criteria or []
            }
            
            # 3️⃣ Chama OpenAI para análise
            logger.info(f"🤖 [analyse_resume_task] Iniciando análise IA para {resume_id}")

            summary = ai.resume_cv(text)
            opinion = ai.generate_opinion(text, job_data)
            score = ai.generate_score(text, job_data)

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
            logger.info(
                f"✅ [analyse_resume_task] Análise concluída para {resume_id} "
                f"(score={score:.2f})"
            )
        except Exception as e:
            resume.status = "failed"
            resume.opinion = f"Erro na análise: {str(e)}"
            logger.error(f"❌ [analyse_resume_task] Erro ao analisar {resume_id}: {e}")
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
        logger.info(
            f"📝 [enqueue_analysis] Resume criado: {resume_id} "
            f"(tenant={tenant_id}, job={job_id})"
        )

    redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
    q = Queue("default", connection=redis_conn)

    # Enfileira as duas etapas com tenant_id
    q.enqueue(parse_pdf_task, resume_id, tenant_id, pdf_bytes)
    q.enqueue(analyse_resume_task, resume_id, tenant_id)

    logger.info(f"✅ [enqueue_analysis] Tarefas enfileiradas para {resume_id}")
    return resume_id
