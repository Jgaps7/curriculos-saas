import os
from dotenv import load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings

# Carrega o arquivo .env da raiz do projeto
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

class Settings(BaseSettings):
    SUPABASE_URL: str = Field(..., description="URL do projeto Supabase")
    
    # Chave pública (para autenticação de usuários)
    SUPABASE_ANON_KEY: str = Field(
        ..., 
        description="Chave pública do Supabase (anon key)"
    )
    
    # ✅ ADICIONE: Chave de serviço (para operações backend)
    SUPABASE_SERVICE_KEY: str = Field(
        ..., 
        description="Chave privada do Supabase (service_role) - NUNCA exponha!"
    )
    
    SUPABASE_DB_URL: str = Field(..., description="Connection string PostgreSQL")

    # ========== OPENAI ==========
    OPENAI_API_KEY: str = Field(
        ..., 
        description="Chave de API da OpenAI (sk-...)"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",  
        description="Modelo OpenAI a ser usado (gpt-4o-mini, gpt-4, etc)"
    )

    # ========== REDIS (Filas Assíncronas) ==========
    REDIS_URL: str = Field(
        default="redis://localhost:6379",  # ✅ ADICIONADO: valor padrão para dev local
        description="URL de conexão do Redis para RQ worker"
    )

    # ========== APP ==========
    APP_ENV: str = Field(
        default="development", 
        description="Ambiente de execução (development/production/staging)"
    )
    LOG_LEVEL: str = Field(
        default="INFO", 
        description="Nível de log da aplicação (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )

    # ========================================
    #  CONFIGURAÇÃO DO PYDANTIC V2
    # ========================================

    model_config = {
    "env_file": ".env",
    "case_sensitive": True,
    "extra": "ignore",
    "env_file_encoding": "utf-8"
}

# Instância global das configurações
def load_settings() -> Settings:
    """
    Carrega e valida as configurações do sistema.
    
    Raises:
        SystemExit: Se houver variáveis obrigatórias ausentes
    
    Returns:
        Settings: Instância validada das configurações
    """
    try:
        return Settings()
    
    except ValidationError as e:
        # ❌ Extrai os nomes das variáveis que estão faltando
        missing_vars = []
        invalid_vars = []
        
        for error in e.errors():
            field_name = error["loc"][0]
            error_type = error["type"]
            
            if error_type == "missing":
                missing_vars.append(field_name)
            else:
                invalid_vars.append(f"{field_name} ({error['msg']})")
        
        # Exibe erro formatado
        print("\n" + "="*60)
        print("❌ ERRO: Configurações Inválidas no .env")
        print("="*60)
        
        if missing_vars:
            print("\n🔴 Variáveis OBRIGATÓRIAS ausentes:")
            for var in missing_vars:
                print(f"   - {var}")
        
        if invalid_vars:
            print("\n🟡 Variáveis com valores INVÁLIDOS:")
            for var in invalid_vars:
                print(f"   - {var}")
        
        print("\n⚠️  Corrija o arquivo .env e reinicie o servidor.")
        print("="*60 + "\n")
        
        # ✅ MELHORIA: Retorna código de erro específico
        raise SystemExit(1)


# ========================================
# 🌐 INSTÂNCIA SINGLETON
# ========================================

settings = load_settings()

print("\n" + "="*60)
print("✅ Configurações carregadas com sucesso!")
print("="*60)
    
    # Informações seguras (sem expor chaves completas)
print(f"\n📋 Ambiente: {settings.APP_ENV}")
print(f"📊 Log Level: {settings.LOG_LEVEL}")
print(f"🤖 Modelo OpenAI: {settings.OPENAI_MODEL}")
    
    # ✅ MELHORIA: Oculta partes sensíveis das credenciais
print(f"\n🔐 Supabase URL: {settings.SUPABASE_URL}")
print(f"🔑 Supabase Anon Key: {settings.SUPABASE_ANON_KEY[:20]}...{settings.SUPABASE_ANON_KEY[-10:]}")
print(f"🔑 OpenAI Key: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-5:]}")
    
    # Extrai host do banco de dados sem expor senha
try:
        db_parts = settings.SUPABASE_DB_URL.split('@')
        if len(db_parts) > 1:
            db_host = db_parts[-1]
            print(f"🗄️  Database: {db_host}")
        else:
            print(f"🗄️  Database: {settings.SUPABASE_DB_URL}")
except Exception:
        print("🗄️  Database: [configurado]")
    
    # ✅ ADICIONADO: Testa conexão Redis (opcional)
try:
        from redis import Redis
        redis_conn = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        redis_conn.ping()
        print(f"📦 Redis: Conectado ({settings.REDIS_URL})")
except Exception as e:
        print(f"📦 Redis: ⚠️  Não conectado ({settings.REDIS_URL}) - {str(e)[:50]}")
    
print("="*60 + "\n")
