"""
config.py
----------------------------------
Responsável por carregar e validar todas as variáveis de ambiente do projeto SaaS.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field, ValidationError

# Carrega o arquivo .env da raiz do projeto
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

class Settings(BaseSettings):
    """
    Configurações principais do sistema.
    """

    # ========== SUPABASE ==========
    SUPABASE_URL: str = Field(..., description="URL do projeto Supabase")
    SUPABASE_ANON_KEY: str = Field(..., description="Chave pública do Supabase (anon)")
    SUPABASE_DB_URL: str = Field(..., description="Connection string para o PostgreSQL do Supabase")

    # ========== OPENAI ==========
    OPENAI_API_KEY: str = Field(..., description="Chave de API da OpenAI")

    # ========== APP ==========
    APP_ENV: str = Field(default="development", description="Ambiente de execução (development/production)")
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log da aplicação")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Instância global das configurações
try:
    settings = Settings()
except ValidationError as e:
    missing = [err["loc"][0] for err in e.errors()]
    print("❌ ERRO: Variáveis obrigatórias ausentes no arquivo .env:")
    for var in missing:
        print(f"   - {var}")
    print("\n⚠️ Corrija o arquivo .env e reinicie o servidor.\n")
    raise SystemExit(1)

# Exemplo de uso rápido (debug)
if __name__ == "__main__":
    print("✅ Configurações carregadas com sucesso:")
    print(f"- Ambiente: {settings.APP_ENV}")
    print(f"- Supabase URL: {settings.SUPABASE_URL}")
    print(f"- Banco: {settings.SUPABASE_DB_URL.split('@')[-1]}")
