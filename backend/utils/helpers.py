# backend/utils/helpers.py

import re
from typing import Dict, List


def parse_resume_markdown(markdown_text: str) -> Dict[str, List[str] | str]:
    """
    Faz o parsing de um resumo Markdown gerado pela IA e extrai:
      - Nome Completo
      - Habilidades
      - Educação
      - Idiomas
    Retorna um dicionário limpo.
    """
    result = {"name": "", "skills": [], "education": [], "languages": []}

    # Nome completo
    match_name = re.search(r"## Nome Completo\s*(.+)", markdown_text)
    if match_name:
        result["name"] = match_name.group(1).strip()

    # Habilidades
    match_skills = re.search(r"## Habilidades\s*([\s\S]*?)(?:##|$)", markdown_text)
    if match_skills:
        skills_text = match_skills.group(1).strip()
        result["skills"] = [s.strip("-• ") for s in skills_text.split("\n") if s.strip()]

    # Educação
    match_edu = re.search(r"## Educação\s*([\s\S]*?)(?:##|$)", markdown_text)
    if match_edu:
        edu_text = match_edu.group(1).strip()
        result["education"] = [e.strip("-• ") for e in edu_text.split("\n") if e.strip()]

    # Idiomas
    match_lang = re.search(r"## Idiomas\s*([\s\S]*?)(?:##|$)", markdown_text)
    if match_lang:
        lang_text = match_lang.group(1).strip()
        result["languages"] = [l.strip("-• ") for l in lang_text.split("\n") if l.strip()]

    return result
