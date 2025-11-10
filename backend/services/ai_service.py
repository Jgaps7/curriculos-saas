import os
from openai import OpenAI

class OpenAIClient:
    def __init__(self, model_id: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")):
        self.model_id = model_id
        self.client = OpenAI()

    def _chat(self, messages, temperature=0.3, max_tokens=500):
        resp = self.client.chat.completions.create(
            model=self.model_id, messages=messages,
            temperature=temperature, max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()

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
        job_text = f"{job.get('main_activities','')}\n{job.get('prerequisites','')}\n{job.get('differentials','')}"
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
        job_text = f"{job.get('main_activities','')}\n{job.get('prerequisites','')}\n{job.get('differentials','')}"

        prompt = f"""
Avalie o currículo conforme os critérios e pesos da vaga abaixo.

Critérios:
{criterios_txt}

Descrição da vaga:
{job_text}

Currículo:
{cv}

Instruções:
- Atribua notas parciais de 0 a 10 por critério, aplique os pesos e calcule a nota final (0 a 10).
- Retorne APENAS no formato: Pontuação Final: X.X
"""
        content = self._chat([
            {"role":"system","content":"Você calcula pontuações de forma rigorosa e padronizada."},
            {"role":"user","content":prompt}
        ], max_tokens=120)

        # extração robusta (0..10)
        import re
        m = re.search(r"(?i)Pontuação Final[:\s]*([\d.,]+)", content)
        if not m:
            return 0.0
        try:
            score = float(m.group(1).replace(",", "."))
            return max(0.0, min(10.0, score))
        except:
            return 0.0
