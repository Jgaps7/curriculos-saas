import io
import json
import requests
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import os
from supabase import create_client, Client


st.set_page_config(page_title="Currículos SaaS", layout="wide")

# =========================
# 🔐 Configuração Supabase
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vnzmdnwsrmpsxmibxlht.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuem1kbndzcm1wc3htaWJ4bGh0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEzMjY5NTMsImV4cCI6MjA3NjkwMjk1M30.-eBEv4vVPmndt3B2PmIvA_POE2fVr9rqy57P8uOIbAw")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ========================================
# 🔧 Inicialização do Estado (ÚNICA VEZ)
# ========================================
def init_state():
    """Inicializa estado padrão da aplicação."""
    ss = st.session_state
    ss.setdefault("api_url", "https://curriculos-saas.onrender.com")
    ss.setdefault("authenticated", False)
    ss.setdefault("show_register", False)
    ss.setdefault("token", "")
    ss.setdefault("tenant_id", "")
    ss.setdefault("user_email", "")
    ss.setdefault("jobs_cache", [])
    ss.setdefault("resumes_cache", [])
    ss.setdefault("analysis_cache", [])

init_state()


# ========================================
# 🔑 Funções de Autenticação
# ========================================
def login_user(email: str, password: str):
    """Faz login no Supabase e retorna JWT + User ID."""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            return {
                "success": True,
                "token": response.session.access_token,
                "user_id": response.user.id,
                "email": response.user.email
            }
        else:
            return {"success": False, "error": "Login falhou"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_user_tenant(user_id: str, token: str):
    """Busca o tenant_id do usuário na tabela memberships."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_ANON_KEY
        }
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/memberships?user_id=eq.{user_id}&select=tenant_id",
            headers=headers,
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            if data and len(data) > 0:
                return data[0]["tenant_id"]
        
        return None
        
    except Exception as e:
        st.error(f"Erro ao buscar tenant: {e}")
        return None


def register_user(
    email: str,
    password: str,
    full_name: str,
    company_name: str,
    phone: str = "",
    company_size: str = "",
    industry: str = "",
    country: str = ""
):
    """
    Registra novo usuário e cria tenant.
    
    Fluxo:
    1. Cria usuário no Supabase Auth
    2. Chama backend /auth/register para criar tenant
    """
    try:
        # 1️⃣ Cria usuário no Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "company_name": company_name,
                    "phone": phone
                }
            }
        })
        
        if not auth_response.user:
            return {"success": False, "error": "Falha ao criar usuário no Supabase"}
        
        user_id = auth_response.user.id
        token = auth_response.session.access_token if auth_response.session else None
        
        # 2️⃣ Cria tenant via backend
        if token:
            try:
                backend_response = requests.post(
                    f"{st.session_state.api_url}/auth/register",
                    json={
                        "user_id": user_id,
                        "email": email,
                        "full_name": full_name,
                        "company_name": company_name,
                        "phone": phone or None,
                        "company_size": company_size or None,
                        "industry": industry or None,
                        "country": country or None
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                
                if not backend_response.ok:
                    return {
                        "success": False,
                        "error": f"Erro ao criar tenant: {backend_response.text}"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Erro ao conectar com backend: {str(e)}"
                }
        
        return {
            "success": True,
            "message": "Conta criada com sucesso! Verifique seu email para confirmar.",
            "data": {
                "user_id": user_id,
                "email": email
            }
        }
        
    except Exception as e:
        return {"success": False, "error": f"Erro no registro: {str(e)}"}


def logout():
    """Limpa sessão e desloga usuário."""
    for key in ["token", "tenant_id", "user_email", "authenticated", 
                "jobs_cache", "resumes_cache", "analysis_cache"]:  # ✅ Adicionado resumes_cache
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


# ========================================
# 🎨 Interface de Registro
# ========================================
def show_register_page():
    """Tela de registro de novos usuários."""
    st.title("📝 Criar Conta - Currículos SaaS")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Registre-se gratuitamente")
        
        with st.form("register_form"):
            # ✅ OBRIGATÓRIOS
            st.markdown("#### 👤 Dados Pessoais")
            full_name = st.text_input("Nome Completo *", placeholder="João Silva")
            email = st.text_input("Email *", placeholder="joao@empresa.com")
            
            col_pass1, col_pass2 = st.columns(2)
            with col_pass1:
                password = st.text_input("Senha *", type="password", help="Mínimo 6 caracteres")
            with col_pass2:
                password_confirm = st.text_input("Confirmar Senha *", type="password")
            
            st.markdown("---")
            
            # ✅ EMPRESA
            st.markdown("#### 🏢 Dados da Empresa")
            company_name = st.text_input("Nome da Empresa *", placeholder="Tech Corp LTDA")
            
            # ⚪ OPCIONAIS
            phone = st.text_input("Telefone", placeholder="+55 11 99999-9999")
            
            company_size = st.selectbox(
                "Tamanho da Empresa",
                ["", "1-10 funcionários", "11-50 funcionários", "51-200 funcionários", "200+ funcionários"]
            )
            
            industry = st.selectbox(
                "Setor/Indústria",
                ["", "Tecnologia", "Varejo", "Serviços", "Indústria", "Saúde", "Educação", "Outro"]
            )
            
            country = st.selectbox(
                "País",
                ["", "Brasil", "Portugal", "Estados Unidos", "Outro"]
            )
            
            st.markdown("---")
            
            # Termos
            terms = st.checkbox("Aceito os termos de uso e política de privacidade *")
            
            submit = st.form_submit_button("🚀 Criar Conta", use_container_width=True)
        
        # ✅ Processamento
        if submit:
            # Validações
            if not all([full_name, email, password, password_confirm, company_name]):
                st.error("❌ Preencha todos os campos obrigatórios (*)")
                return
            
            if password != password_confirm:
                st.error("❌ As senhas não coincidem")
                return
            
            if len(password) < 6:
                st.error("❌ Senha deve ter no mínimo 6 caracteres")
                return
            
            if not terms:
                st.error("❌ Você precisa aceitar os termos de uso")
                return
            
            # Registra
            with st.spinner("🔄 Criando sua conta..."):
                result = register_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    company_name=company_name,
                    phone=phone,
                    company_size=company_size,
                    industry=industry,
                    country=country
                )
                
                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.info("📧 Enviamos um email de confirmação. Verifique sua caixa de entrada.")
                    
                    time.sleep(3)
                    st.session_state.show_register = False
                    st.rerun()
                else:
                    st.error(f"❌ {result['error']}")
        
        st.markdown("---")
        
        if st.button("⬅️ Já tenho conta, fazer login"):
            st.session_state.show_register = False
            st.rerun()


# ========================================
# 🔐 Interface de Login
# ========================================
def show_login_page():
    """Mostra tela de login ou registro."""
    
    # Verifica se deve mostrar registro
    if st.session_state.get("show_register", False):
        show_register_page()
        return
    
    st.title("🔐 Login - Currículos SaaS")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Entre com suas credenciais")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="seu@email.com")
            password = st.text_input("🔒 Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("❌ Preencha email e senha")
                return
            
            with st.spinner("🔄 Autenticando..."):
                # 1. Faz login
                result = login_user(email, password)
                
                if not result["success"]:
                    st.error(f"❌ Erro no login: {result['error']}")
                    return
                
                token = result["token"]
                user_id = result["user_id"]
                
                # 2. Busca tenant_id
                tenant_id = get_user_tenant(user_id, token)
                
                if not tenant_id:
                    st.error("❌ Usuário não vinculado a nenhum tenant. Entre em contato com o administrador.")
                    return
                
                # 3. Salva no session_state
                st.session_state.token = token
                st.session_state.tenant_id = tenant_id
                st.session_state.user_email = result["email"]
                st.session_state.authenticated = True
                
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
        
        st.markdown("---")
        
        # ✅ Botão para registro
        if st.button("📝 Criar nova conta", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()


# ========================================
# 🔒 GATE: Se não autenticado, mostra login (ÚNICO)
# ========================================
if not st.session_state.authenticated:
    show_login_page()
    st.stop()


# ========================================
# ✅ Usuário Autenticado - Mostra App
# ========================================

# Barra lateral com logout
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Mostra info do usuário
    st.success(f"✅ Logado como: {st.session_state.user_email}")
    
    if st.button("🚪 Sair", use_container_width=True):
        logout()
    
    st.markdown("---")
    
    # API URL editável (para debug)
    st.session_state.api_url = st.text_input(
        "API URL", 
        value=st.session_state.api_url,
        help="URL da API backend"
    )
    
    st.markdown("---")
    
    # Botão de atualizar cache
    if st.button("🔄 Atualizar dados"):
        st.session_state.jobs_cache = []
        st.session_state.resumes_cache = []
        st.session_state.analysis_cache = []
        st.rerun()


# ========================================
# 📡 Funções de API
# ========================================
def headers():
    """
    Retorna headers para requisições à API.
    Token e tenant_id são garantidos pelo gate de autenticação.
    """
    return {
        "Authorization": f"Bearer {st.session_state.token}",
        "X-Tenant-Id": st.session_state.tenant_id
    }


def api_get(path, params=None):
    """Faz requisição GET à API."""
    base = st.session_state.api_url.rstrip("/")
    url = f"{base}{path}"
    
    try:
        r = requests.get(url, headers=headers(), params=params, timeout=60)
        
        if not r.ok:
            # Tenta extrair mensagem de erro
            try:
                error_msg = r.json().get("detail", r.text)
            except:
                error_msg = r.text[:200]
            
            raise RuntimeError(f"GET {path} → {r.status_code}: {error_msg}")
        
        return r.json()
        
    except requests.exceptions.Timeout:
        raise RuntimeError(f"⏱️ Timeout ao acessar {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"❌ Erro de conexão: API pode estar offline")


def api_post(path, json_payload=None, files=None, data=None):
    """Faz requisição POST à API."""
    base = st.session_state.api_url.rstrip("/")
    url = f"{base}{path}"
    
    try:
        r = requests.post(
            url,
            headers=headers(),
            json=json_payload,
            files=files,
            data=data,
            timeout=120
        )
        
        if not r.ok:
            try:
                error_msg = r.json().get("detail", r.text)
            except:
                error_msg = r.text[:200]
            
            raise RuntimeError(f"POST {path} → {r.status_code}: {error_msg}")
        
        return r.json()
        
    except requests.exceptions.Timeout:
        raise RuntimeError(f"⏱️ Timeout ao enviar para {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"❌ Erro de conexão: API pode estar offline")

# =========================
# Funções de dados
# =========================
def load_jobs():
    """Carrega vagas do backend (com cache)."""
    if not st.session_state.jobs_cache:
        data = api_get("/jobs")
        st.session_state.jobs_cache = data.get("jobs", data)
    return st.session_state.jobs_cache


def load_resumes():
    """
    Carrega currículos (ainda não implementado completamente).
    Por enquanto, usa dados de análises.
    """
    if not st.session_state.resumes_cache:
        try:
            data = api_get("/analysis")
            df = pd.DataFrame(data.get("items", data)) if isinstance(data, dict) else pd.DataFrame(data)
            if not df.empty:
                st.session_state.analysis_cache = df.to_dict("records")
        except Exception:
            pass
    return st.session_state.resumes_cache


def load_analysis():
    """Carrega análises de currículos (com cache)."""
    if not st.session_state.analysis_cache:
        data = api_get("/analysis")
        st.session_state.analysis_cache = data.get("items", data) if isinstance(data, dict) else data
    return st.session_state.analysis_cache

# ========================================
# 🎨 Interface Principal do App
# ========================================
st.title("🧠 Currículos SaaS – Painel")

# Abas principais
tabs = st.tabs(["📊 Dashboard", "💼 Vagas", "📄 Currículos", "🔎 Análises", "🛠️ Configurações"])


# ========================================
# 📊 ABA 1: DASHBOARD
# ========================================
with tabs[0]:
    st.subheader("Visão Geral")
    
    # ✅ Carrega dados com tratamento de erro
    try:
        jobs = load_jobs()
    except Exception as e:
        st.error(f"❌ Erro ao carregar vagas: {e}")
        jobs = []

    try:
        analysis = load_analysis()
    except Exception as e:
        st.error(f"❌ Erro ao carregar análises: {e}")
        analysis = []

    # KPIs principais
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vagas Ativas", len(jobs))
    
    # Métricas de análises
    df = pd.DataFrame(analysis)
    
    if not df.empty:
        # ✅ Verifica se colunas existem antes de usar
        if "resume_id" in df.columns:
            col2.metric("Currículos Analisados", df["resume_id"].nunique())
        else:
            col2.metric("Currículos Analisados", 0)
        
        if "score" in df.columns and not df["score"].dropna().empty:
            avg_score = round(df["score"].dropna().mean(), 2)
            col3.metric("Média de Score", avg_score)
        else:
            col3.metric("Média de Score", 0)
        
        # Vaga com mais currículos
        if "job_id" in df.columns and "resume_id" in df.columns:
            by_job = (
                df.groupby("job_id")["resume_id"]
                .nunique()
                .reset_index()
                .rename(columns={"resume_id": "curriculos"})
            )
            
            if not by_job.empty:
                max_curriculos = by_job.sort_values("curriculos", ascending=False).head(1)["curriculos"].iloc[0]
                col4.metric("Vaga com Mais Currículos", max_curriculos)
            else:
                col4.metric("Vaga com Mais Currículos", 0)
        else:
            col4.metric("Vaga com Mais Currículos", 0)

        st.markdown("---")

        # ✅ Gráficos (somente se houver dados)
        if "score" in df.columns and not df["score"].dropna().empty:
            st.markdown("### 📈 Curva de Scores")
            fig = px.histogram(
                df,
                x="score",
                nbins=20,
                title="Distribuição de Scores dos Currículos",
                labels={"score": "Score (0-10)", "count": "Quantidade"}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        if "job_id" in df.columns and "resume_id" in df.columns:
            st.markdown("### 📊 Currículos por Vaga")
            cnt = (
                df.groupby("job_id")["resume_id"]
                .nunique()
                .reset_index()
                .rename(columns={"resume_id": "qtd"})
            )
            
            fig2 = px.bar(
                cnt,
                x="job_id",
                y="qtd",
                title="Número de Currículos por Vaga",
                labels={"job_id": "ID da Vaga", "qtd": "Quantidade de Currículos"}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    else:
        st.info("📭 Ainda não há análises para mostrar no Dashboard.")
        st.markdown("""
        **Primeiros Passos:**
        1. Cadastre uma vaga na aba **💼 Vagas**
        2. Envie currículos na aba **📄 Currículos**
        3. Aguarde o processamento (2-5 minutos)
        4. Visualize os resultados aqui!
        """)

with tabs[1]:
    st.subheader("Gerenciar Vagas")

    st.markdown("#### 📝 Cadastrar Nova Vaga")
    
    with st.form("form_job"):
        # Campos básicos
        name = st.text_input("Nome da Vaga *", placeholder="Ex: Desenvolvedor Python Sênior")
        main_activities = st.text_area(
            "Principais Atividades *",
            placeholder="Descreva as principais responsabilidades da vaga...",
            height=100
        )
        prerequisites = st.text_area(
            "Pré-requisitos *",
            placeholder="Requisitos obrigatórios para a vaga...",
            height=100
        )
        differentials = st.text_area(
            "Diferenciais",
            placeholder="Habilidades e experiências que são um plus...",
            height=100
        )

        st.markdown("---")
        st.markdown("##### 🎯 Critérios de Avaliação (peso deve somar 100%)")
        
        num = st.number_input(
            "Quantidade de critérios",
            min_value=1,
            max_value=10,
            value=5,
            key="num_criterios",
            help="Defina de 1 a 10 critérios para avaliar os currículos"
        )
        
        crits_preview = []
        for i in range(int(num)):
            st.markdown(f"**Critério {i+1}**")
            c1, c2 = st.columns([3, 1])
            
            nm = c1.text_input(
                f"Nome",
                key=f"crit_nm_{i}",
                placeholder=f"Ex: Experiência técnica"
            )
            pw = c2.number_input(
                f"Peso (%)",
                min_value=0,
                max_value=100,
                value=0,
                key=f"crit_pw_{i}"
            )
            ds = st.text_area(
                f"Descrição",
                key=f"crit_ds_{i}",
                placeholder="Descreva o que será avaliado neste critério...",
                height=60
            )
            
            if nm:
                crits_preview.append({"name": nm, "weight": pw, "description": ds})
        
        # Soma dos pesos (pré-visualização)
        total_preview = sum(int(c["weight"]) for c in crits_preview)
        
        if total_preview == 100:
            st.success(f"✅ Soma dos pesos: {total_preview}% (correto!)")
        elif total_preview > 100:
            st.error(f"❌ Soma dos pesos: {total_preview}% (excede 100%)")
        else:
            st.warning(f"⚠️ Soma dos pesos: {total_preview}% (falta {100 - total_preview}%)")
        
        submitted = st.form_submit_button("💾 Salvar Vaga", use_container_width=True)
    
    # ========================================
    # ✅ PROCESSAMENTO (DENTRO DO IF SUBMITTED)
    # ========================================
    if submitted:
        # 1️⃣ Reconstrói critérios do session_state
        crits = []
        num_criterios = int(st.session_state.get("num_criterios", 0))

        for i in range(num_criterios):
            nm = st.session_state.get(f"crit_nm_{i}", "").strip()
            pw = st.session_state.get(f"crit_pw_{i}", 0)
            ds = st.session_state.get(f"crit_ds_{i}", "")

            if nm:
                crits.append({
                    "name": nm,
                    "weight": int(pw),  # ✅ "weight" (não "peso")
                    "description": ds
                })

        # 2️⃣ Calcula soma dos pesos
        total = sum(c["weight"] for c in crits)  # ✅ CORRIGIDO: "weight"

        # 3️⃣ Validações
        if not name:
            st.error("❌ O nome da vaga é obrigatório.")
        elif not main_activities:
            st.error("❌ Descreva as principais atividades da vaga.")
        elif not prerequisites:
            st.error("❌ Defina os pré-requisitos da vaga.")
        elif total != 100:
            st.error(f"❌ A soma dos pesos precisa ser 100%. Soma atual: {total}%.")
        elif not crits:
            st.error("❌ Defina ao menos um critério com nome.")
        else:
            # 4️⃣ Envia para API
            try:
                payload = {
                    "title": name,
                    "main_activities": main_activities,
                    "prerequisites": prerequisites,
                    "differentials": differentials,
                    "criteria": crits
                }
                
                with st.spinner("🔄 Criando vaga..."):
                    resp = api_post("/jobs", json_payload=payload)
                
                st.success("✅ Vaga criada com sucesso!")
                
                # Mostra resposta (opcional)
                with st.expander("📄 Detalhes da vaga criada"):
                    st.json(resp)
                
                # Invalida cache
                st.session_state.jobs_cache = []
                
            except Exception as e:
                st.error(f"❌ Falha ao criar vaga: {e}")

    st.markdown("---")
    
    # ========================================
    # 📋 LISTAGEM DE VAGAS
    # ========================================
    st.markdown("#### 📋 Minhas Vagas")
    
    try:
        jobs = load_jobs()
        
        if jobs:
            df_jobs = pd.DataFrame(jobs)
            
            # Seleciona colunas importantes
            cols_to_show = []
            if "title" in df_jobs.columns:
                cols_to_show.append("title")
            if "created_at" in df_jobs.columns:
                cols_to_show.append("created_at")
            if "id" in df_jobs.columns:
                cols_to_show.append("id")
            
            if cols_to_show:
                st.dataframe(
                    df_jobs[cols_to_show],
                    use_container_width=True,
                    height=350
                )
            else:
                st.dataframe(df_jobs, use_container_width=True, height=350)
            
            st.caption(f"Total: {len(jobs)} vaga(s)")
        else:
            st.info("📭 Nenhuma vaga cadastrada ainda. Crie a primeira acima!")
            
    except Exception as e:
        st.error(f"❌ Erro ao listar vagas: {e}")


# ========================================
# 📄 ABA 3: CURRÍCULOS
# ========================================
with tabs[2]:
    st.subheader("📤 Upload de Currículos (PDF)")
    
    # Carrega vagas disponíveis
    try:
        jobs = load_jobs()
    except Exception as e:
        st.error(f"❌ Erro ao carregar vagas: {e}")
        jobs = []

    # Cria mapa de vagas
    job_map = {}
    for j in jobs:
        title = j.get("title") or j.get("name")
        jid = j.get("id")
        if title and jid:
            job_map[title] = jid
    
    # ========================================
    # 📝 FORMULÁRIO DE UPLOAD
    # ========================================
    if job_map:
        # ✅ Tem vagas disponíveis
        job_name = st.selectbox(
            "Selecione a vaga *",
            list(job_map.keys()),
            help="Escolha para qual vaga você está enviando o currículo"
        )
        
        pdf = st.file_uploader(
            "Arquivo do Currículo (PDF) *",
            type=["pdf"],
            help="Envie apenas arquivos PDF"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            enviar = st.button("📤 Enviar Currículo", use_container_width=True, type="primary")
        
        # ========================================
        # ✅ PROCESSAMENTO DO UPLOAD
        # ========================================
        if enviar:
            # Validações
            if not pdf:
                st.error("❌ Selecione um arquivo PDF antes de enviar.")
            elif not pdf.name.lower().endswith(".pdf"):
                st.error("❌ O arquivo deve ser um PDF.")
            else:
                try:
                    job_id = job_map[job_name]
                    
                    with st.spinner("🔄 Enviando currículo..."):
                        files = {"pdf": (pdf.name, pdf, "application/pdf")}
                        data = {"job_id": job_id}
                        resp = api_post("/resumes/upload", files=files, data=data)
                    
                    st.success("✅ Currículo enviado e enfileirado com sucesso!")
                    st.info("⏳ O processamento pode levar de 2 a 5 minutos. Acompanhe na aba **Análises**.")
                    
                    # Mostra resposta
                    with st.expander("📄 Detalhes do envio"):
                        st.json(resp)
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Falha de conexão. A API pode estar dormindo (Render free tier). Tente novamente em 30 segundos.")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Timeout. O arquivo pode ser muito grande ou a API está lenta.")
                except Exception as e:
                    st.error(f"❌ Erro no upload: {e}")
    else:
        # ❌ Não tem vagas cadastradas
        st.warning("⚠️ Nenhuma vaga cadastrada ainda.")
        st.info("💡 Para enviar currículos, primeiro cadastre uma vaga na aba **💼 Vagas**.")

    st.markdown("---")
    
    # ========================================
    # 📊 STATUS DE PROCESSAMENTO
    # ========================================
    st.markdown("#### 📊 Status de Processamento")
    
    st.caption("""
    Os currículos são processados em fila. O tempo de análise varia de acordo com:
    - Tamanho do arquivo PDF
    - Complexidade da vaga
    - Quantidade de currículos na fila
    
    💡 **Dica:** Use a aba **🔎 Análises** para ver os resultados consolidados.
    """)

# ========================================
# 🔎 ABA 4: ANÁLISES
# ========================================
with tabs[3]:
    st.subheader("🔎 Resultados das Análises")
    
    try:
        analysis = load_analysis()
        df = pd.DataFrame(analysis)
        
        if df.empty:
            st.info("📭 Ainda não há análises disponíveis.")
            st.markdown("""
            **Como funciona:**
            1. Envie currículos na aba **📄 Currículos**
            2. Aguarde 2-5 minutos para o processamento
            3. Os resultados aparecerão aqui automaticamente
            
            💡 **Dica:** Clique em **"🔄 Atualizar dados"** na barra lateral para verificar novos resultados.
            """)
        else:
            # ========================================
            # 📊 KPIs Rápidos
            # ========================================
            col1, col2, col3, col4 = st.columns(4)
            
            total_analysis = len(df)
            col1.metric("Total de Análises", total_analysis)
            
            if "score" in df.columns:
                avg_score = round(df["score"].dropna().mean(), 2)
                col2.metric("Score Médio", f"{avg_score}/10")
                
                max_score = round(df["score"].dropna().max(), 2)
                col3.metric("Melhor Score", f"{max_score}/10")
                
                approved = len(df[df["score"] >= 7.0])
                col4.metric("Score ≥ 7.0", f"{approved} ({int(approved/total_analysis*100)}%)")
            
            st.markdown("---")
            
            # ========================================
            # 🔍 FILTROS
            # ========================================
            st.markdown("#### 🔍 Filtros")
            
            col1, col2, col3, col4 = st.columns(4)
            
            # Filtro por vaga
            with col1:
                if "job_id" in df.columns:
                    unique_jobs = ["Todas"] + sorted(df["job_id"].dropna().unique().tolist())
                    job_filter = st.selectbox("Vaga", unique_jobs)
                else:
                    job_filter = "Todas"
            
            # Filtro por nome
            with col2:
                name_filter = st.text_input(
                    "Nome do Candidato",
                    placeholder="Digite para buscar..."
                )
            
            # Filtro por score mínimo
            with col3:
                score_min = st.number_input(
                    "Score Mínimo",
                    min_value=0.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.5
                )
            
            # Filtro por score máximo
            with col4:
                score_max = st.number_input(
                    "Score Máximo",
                    min_value=0.0,
                    max_value=10.0,
                    value=10.0,
                    step=0.5
                )
            
            # ========================================
            # ✅ APLICAR FILTROS
            # ========================================
            df_filtered = df.copy()
            
            if job_filter != "Todas" and "job_id" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["job_id"] == job_filter]
            
            if name_filter and "candidate_name" in df_filtered.columns:
                df_filtered = df_filtered[
                    df_filtered["candidate_name"]
                    .astype(str)
                    .str.contains(name_filter, case=False, na=False)
                ]
            
            if "score" in df_filtered.columns:
                df_filtered = df_filtered[
                    (df_filtered["score"].fillna(0) >= score_min) &
                    (df_filtered["score"].fillna(10) <= score_max)
                ]
            
            # Mostra quantidade filtrada
            if len(df_filtered) < len(df):
                st.info(f"🔍 Mostrando {len(df_filtered)} de {len(df)} análises")
            
            st.markdown("---")
            
            # ========================================
            # 📊 TABELA DE RESULTADOS
            # ========================================
            st.markdown("#### 📊 Tabela de Resultados")
            
            if not df_filtered.empty:
                # Seleciona e renomeia colunas importantes
                display_cols = []
                col_rename = {}
                
                if "candidate_name" in df_filtered.columns:
                    display_cols.append("candidate_name")
                    col_rename["candidate_name"] = "Candidato"
                
                if "job_id" in df_filtered.columns:
                    display_cols.append("job_id")
                    col_rename["job_id"] = "Vaga"
                
                if "score" in df_filtered.columns:
                    display_cols.append("score")
                    col_rename["score"] = "Score"
                
                if "created_at" in df_filtered.columns:
                    display_cols.append("created_at")
                    col_rename["created_at"] = "Data"
                
                if display_cols:
                    df_display = df_filtered[display_cols].rename(columns=col_rename)
                else:
                    df_display = df_filtered
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    height=400
                )
                
                # ========================================
                # 📈 GRÁFICOS
                # ========================================
                st.markdown("---")
                st.markdown("#### 📈 Visualizações")
                
                col_chart1, col_chart2 = st.columns(2)
                
                # Gráfico 1: Distribuição de Scores
                with col_chart1:
                    if "score" in df_filtered.columns and not df_filtered["score"].dropna().empty:
                        st.markdown("##### Distribuição de Scores")
                        fig = px.histogram(
                            df_filtered,
                            x="score",
                            nbins=20,
                            labels={"score": "Score (0-10)", "count": "Quantidade"},
                            color_discrete_sequence=["#1f77b4"]
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                # Gráfico 2: Top Candidatos
                with col_chart2:
                    if "score" in df_filtered.columns and "candidate_name" in df_filtered.columns:
                        st.markdown("##### Top 10 Candidatos")
                        top_candidates = (
                            df_filtered.nlargest(10, "score")[["candidate_name", "score"]]
                            .reset_index(drop=True)
                        )
                        fig2 = px.bar(
                            top_candidates,
                            x="score",
                            y="candidate_name",
                            orientation="h",
                            labels={"score": "Score", "candidate_name": "Candidato"},
                            color="score",
                            color_continuous_scale="blues"
                        )
                        fig2.update_layout(showlegend=False)
                        st.plotly_chart(fig2, use_container_width=True)
                
                st.markdown("---")
                
                # ========================================
                # ⬇️ DOWNLOAD
                # ========================================
                st.markdown("#### ⬇️ Exportar Dados")
                
                col_download1, col_download2 = st.columns(2)
                
                with col_download1:
                    # Download CSV
                    buf_csv = io.StringIO()
                    df_filtered.to_csv(buf_csv, index=False)
                    st.download_button(
                        "📄 Baixar CSV",
                        data=buf_csv.getvalue(),
                        file_name=f"analises_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_download2:
                    # Download JSON
                    buf_json = io.StringIO()
                    df_filtered.to_json(buf_json, orient="records", indent=2)
                    st.download_button(
                        "📋 Baixar JSON",
                        data=buf_json.getvalue(),
                        file_name=f"analises_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ Nenhum resultado encontrado com os filtros aplicados.")
                
    except Exception as e:
        st.error(f"❌ Erro ao carregar análises: {e}")
        st.caption("💡 Tente clicar em '🔄 Atualizar dados' na barra lateral")


# ========================================
# 🛠️ ABA 5: CONFIGURAÇÕES
# ========================================
with tabs[4]:
    st.subheader("🛠️ Configurações e Ajuda")
    
    # ========================================
    # 📊 Informações do Sistema
    # ========================================
    st.markdown("### 📊 Informações do Sistema")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"""
        **🔐 Usuário Logado:**  
        `{st.session_state.user_email}`
        
        **🏢 Tenant ID:**  
        `{st.session_state.tenant_id[:16]}...`
        
        **🌐 API Backend:**  
        `{st.session_state.api_url}`
        """)
    
    with col_info2:
        # Verifica status da API
        try:
            response = requests.get(
                f"{st.session_state.api_url}/",
                timeout=5
            )
            if response.ok:
                st.success("✅ **API Status:** Online")
            else:
                st.warning(f"⚠️ **API Status:** {response.status_code}")
        except:
            st.error("❌ **API Status:** Offline")
        
        # Cache
        st.markdown(f"""
        **📦 Cache:**
        - Vagas: {len(st.session_state.jobs_cache)}
        - Análises: {len(st.session_state.analysis_cache)}
        """)
    
    st.markdown("---")
    
    # ========================================
    # 🔐 Segurança
    # ========================================
    st.markdown("### 🔐 Segurança")
    st.markdown("""
    - ✅ Seu token JWT expira em **1 hora**
    - ✅ Todos os dados são isolados por tenant
    - ✅ Faça logout ao terminar de usar o sistema
    - ⚠️ Não compartilhe suas credenciais com terceiros
    """)
    
    st.markdown("---")
    
    # ========================================
    # 📚 Guia Rápido
    # ========================================
    st.markdown("### 📚 Guia Rápido")
    
    with st.expander("💼 Como criar uma vaga?"):
        st.markdown("""
        1. Vá para a aba **💼 Vagas**
        2. Preencha os campos obrigatórios
        3. Defina os critérios de avaliação (peso total = 100%)
        4. Clique em **Salvar Vaga**
        """)
    
    with st.expander("📄 Como enviar currículos?"):
        st.markdown("""
        1. Vá para a aba **📄 Currículos**
        2. Selecione a vaga desejada
        3. Faça upload do PDF
        4. Clique em **Enviar Currículo**
        5. Aguarde 2-5 minutos para o processamento
        """)
    
    with st.expander("🔎 Como ver os resultados?"):
        st.markdown("""
        1. Vá para a aba **🔎 Análises**
        2. Use os filtros para refinar a busca
        3. Visualize os gráficos e estatísticas
        4. Baixe os dados em CSV ou JSON
        """)
    
    st.markdown("---")
    
    # ========================================
    # 🆘 Suporte
    # ========================================
    st.markdown("### 🆘 Suporte")
    st.markdown("""
    **Problemas comuns:**
    
    - **API não responde?** 
      - Aguarde 30-60 segundos (Render free tier pode dormir)
      - Verifique sua conexão com a internet
    
    - **Dados não atualizam?**
      - Clique em **🔄 Atualizar dados** na barra lateral
      - Faça logout e login novamente
    
    - **Erro ao processar currículo?**
      - Verifique se o arquivo é um PDF válido
      - Tamanho máximo: 10 MB
      - Apenas PDFs com texto (não escaneados)
    
    **Documentação:**
    - API: `{}/docs`
    - Status: `{}/`
    """.format(st.session_state.api_url, st.session_state.api_url))
    
    st.markdown("---")
    
    # ========================================
    # 🔧 Ferramentas de Desenvolvedor
    # ========================================
    with st.expander("🔧 Ferramentas de Desenvolvedor"):
        st.markdown("##### Limpar Cache Manualmente")
        col_clear1, col_clear2, col_clear3 = st.columns(3)
        
        with col_clear1:
            if st.button("🗑️ Limpar Vagas", use_container_width=True):
                st.session_state.jobs_cache = []
                st.success("Cache de vagas limpo!")
        
        with col_clear2:
            if st.button("🗑️ Limpar Análises", use_container_width=True):
                st.session_state.analysis_cache = []
                st.success("Cache de análises limpo!")
        
        with col_clear3:
            if st.button("🗑️ Limpar Tudo", use_container_width=True):
                st.session_state.jobs_cache = []
                st.session_state.resumes_cache = []
                st.session_state.analysis_cache = []
                st.success("Todo cache limpo!")
        
        st.markdown("##### Testar Conexão com API")
        if st.button("🔍 Testar Healthcheck"):
            try:
                response = requests.get(f"{st.session_state.api_url}/", timeout=10)
                st.success(f"✅ API respondeu: {response.json()}")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
