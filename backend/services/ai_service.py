import re
import json
import logging
import os
from openai import OpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, model_id: str = None):
        self.model_id = model_id or settings.OPENAI_MODEL
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info(f"✅ OpenAI Client inicializado (model={self.model_id})")

    def _chat(self, messages: list, temperature: float = 0.3, max_tokens: int = 500) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ Erro na chamada OpenAI: {e}")
            raise

    def resume_cv(self, cv: str) -> str:
        prompt = f"""
Resuma o currículo abaixo em Markdown com as seções:
## Nome Completo
## Experiência
## Habilidades
## Educação
## Idiomas

Currículo:
{cv}
"""
        return self._chat([
            {"role":"system","content":"Você resume currículos de forma objetiva."},
            {"role":"user","content":prompt}
        ])

    def generate_opinion(self, cv: str, job: dict) -> str:
        job_text = (
            f"{job.get('main_activities', '')}\n"
            f"{job.get('prerequisites', '')}\n"
            f"{job.get('differentials', '')}"
        )
        prompt = f"""
Analise criticamente o currículo versus a vaga.

Vaga:
{job_text}

Currículo:
{cv}

Entregue com títulos:
## Pontos de Alinhamento
## Pontos de Desalinhamento
## Pontos de Atenção
## Recomendação Final
"""
        return self._chat([
            {"role":"system","content":"Você é um recrutador sênior e escreve análises objetivas."},
            {"role":"user","content":prompt}
        ])

    def generate_score(self, cv: str, job: dict) -> float:
        criterios = job.get("criteria", [])
        criterios_txt = "\n".join(
            f"- {c.get('criterio','Sem nome')} ({int(c.get('peso',0))}%): {c.get('descricao','')}"
            for c in criterios
        )
        job_text = (
            f"{job.get('main_activities', '')}\n"
            f"{job.get('prerequisites', '')}\n"
            f"{job.get('differentials', '')}"
        )

        prompt = f"""
Avalie o currículo conforme os critérios e pesos da vaga abaixo.

Critérios:
{criterios_txt}

Descrição da vaga:
{job_text}

Currículo:
{cv}

Instruções:
- Atribua notas parciais de 0 a 10 por critério
- Aplique os pesos e calcule a nota final (0 a 10)
- Retorne APENAS um JSON no formato: {{"score": 7.5, "justificativa": "resumo"}}
- OU no formato texto: Pontuação Final: X.X
"""
        content = self._chat([
            {"role": "system", "content": "Você calcula pontuações de forma rigorosa e padronizada."},
            {"role": "user", "content": prompt}
        ], max_tokens=300)
        try:
            # 1️⃣ Tenta JSON primeiro
            data = json.loads(content)
            score = float(data.get("score", 0))
            logger.info(f"✅ Score extraído via JSON: {score}")
            return max(0.0, min(10.0, score))
    
        except (json.JSONDecodeError, ValueError):
            
            match = re.search(r"(?i)Pontuação Final[:\s]*([\d.,]+)", content)
            if match:
                score = float(match.group(1).replace(",", "."))
                logger.info(f"✅ Score extraído via regex: {score}")
                return max(0.0, min(10.0, score))
            
            
            match = re.search(r"[\d.,]+", content)
            if match:
                score = float(match.group(0).replace(",", "."))
                logger.warning(f"⚠️ Score extraído via fallback genérico: {score}")
                return max(0.0, min(10.0, score))
            
            
            logger.error(f"❌ Falha ao extrair score. Resposta da IA: {content[:200]}")
            return 0.0
