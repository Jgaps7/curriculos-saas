from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
from .routes import analysis

# Carrega variáveis de ambiente (.env)
load_dotenv()

# Configuração básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

# Importa rotas
from .routes import jobs, resumes

# Inicializa app FastAPI
app = FastAPI(
    title="Currículos SaaS API",
    version="1.0",
    description="API multi-tenant para análise de currículos com IA"
)

# Middleware de CORS (necessário para Streamlit e requisições externas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # durante desenvolvimento — em produção, restrinja aos domínios do seu front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(analysis.router)

# Healthcheck
@app.get("/")
def healthcheck():
    return {"status": "ok", "message": "API rodando!"}
