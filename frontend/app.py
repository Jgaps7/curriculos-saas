import io
import json
import time
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Currículos SaaS", layout="wide")

# =========================
# Helpers de estado/config
# =========================
def init_state():
    ss = st.session_state
    ss.setdefault("api_url", "https://curriculos-saas.onrender.com")
    ss.setdefault("token", "")
    ss.setdefault("tenant_id", "")
    ss.setdefault("jobs_cache", [])
    ss.setdefault("resumes_cache", [])
    ss.setdefault("analysis_cache", [])
init_state()

def headers():
    if not st.session_state.token or not st.session_state.tenant_id:
        return {}
    return {
        "Authorization": f"Bearer {st.session_state.token}",
        "X-Tenant-Id": st.session_state.tenant_id
    }

def api_get(path, params=None):
    base = st.session_state.api_url.rstrip("/")
    r = requests.get(f"{base}{path}", headers=headers(), params=params, timeout=60)

    if not r.ok:
        raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text}")
    return r.json()

def api_post(path, json_payload=None, files=None, data=None):
    base = st.session_state.api_url.rstrip("/")
    r = requests.post(f"{base}{path}", headers=headers(), json=json_payload, files=files, data=data, timeout=120)
    if not r.ok:
        raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text}")
    return r.json()

# =========================
# Barra lateral (Config)
# =========================
with st.sidebar:
    st.header("⚙️ Configurações")
    st.session_state.api_url = st.text_input("API URL", value=st.session_state.api_url)
    st.session_state.token = st.text_input("Supabase JWT", type="password", value=st.session_state.token)
    st.session_state.tenant_id = st.text_input("Tenant ID", value=st.session_state.tenant_id)
    st.markdown("---")
    if st.button("🔄 Atualizar dados"):
        st.session_state.jobs_cache = []
        st.session_state.resumes_cache = []
        st.session_state.analysis_cache = []
        st.rerun()

st.title("🧠 Currículos SaaS – Painel")

# =========================
# Funções de dados
# =========================
def load_jobs():
    if not st.session_state.jobs_cache:
        data = api_get("/jobs")
        # backend retorna {"tenant_id": ..., "jobs": [...]}
        st.session_state.jobs_cache = data.get("jobs", data)  # fallback se sua rota retornar a lista pura
    return st.session_state.jobs_cache

def load_resumes():
    # caso você crie uma rota GET /resumes, ajuste aqui; por enquanto, tenta via /analysis base
    if not st.session_state.resumes_cache:
        try:
            data = api_get("/analysis")  # nova rota no backend (abaixo)
            # agrupa por resume_id para compor status/score
            df = pd.DataFrame(data.get("items", data)) if isinstance(data, dict) else pd.DataFrame(data)
            if not df.empty:
                # Só para sumarizar (se você tiver rota dedicada de resumes, use-a)
                st.session_state.analysis_cache = df.to_dict("records")
        except Exception:
            pass  # pode ainda não existir a rota
    return st.session_state.resumes_cache

def load_analysis():
    if not st.session_state.analysis_cache:
        data = api_get("/analysis")
        st.session_state.analysis_cache = data.get("items", data) if isinstance(data, dict) else data
    return st.session_state.analysis_cache

# =========================
# Abas
# =========================
tabs = st.tabs(["📊 Dashboard", "💼 Vagas", "📄 Currículos", "🔎 Análises", "🛠️ Configurações"])

# -------------------------
# DASHBOARD
# -------------------------
with tabs[0]:
    st.subheader("Visão Geral")
    try:
        jobs = load_jobs()
    except Exception as e:
        st.warning(f"Carregar vagas: {e}")
        jobs = []

    try:
        analysis = load_analysis()
    except Exception as e:
        st.warning(f"Carregar análises: {e}")
        analysis = []

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vagas", len(jobs))
    # KPIs a partir de analysis (se houver)
    df = pd.DataFrame(analysis)
    if not df.empty:
        col2.metric("Currículos Analisados", df["resume_id"].nunique())
        col3.metric("Média de Score", round(df["score"].dropna().mean(), 2) if "score" in df else 0)
        by_job = df.groupby("job_id")["resume_id"].nunique().reset_index().rename(columns={"resume_id": "curriculos"})
        col4.metric("Vaga com mais currículos", by_job.sort_values("curriculos", ascending=False).head(1)["curriculos"].iloc[0] if not by_job.empty else 0)

        st.markdown("### Curva de Scores")
        fig = px.histogram(df, x="score", nbins=20, title="Distribuição de Scores")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Currículos por Vaga")
        cnt = df.groupby("job_id")["resume_id"].nunique().reset_index().rename(columns={"resume_id":"qtd"})
        fig2 = px.bar(cnt, x="job_id", y="qtd")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Ainda não há análises para mostrar no Dashboard.")

# -------------------------
# VAGAS
# -------------------------
with tabs[1]:
    st.subheader("Gerenciar Vagas")

    st.markdown("#### Cadastrar nova vaga")
    with st.form("form_job"):
        name = st.text_input("Nome da vaga")
        main_activities = st.text_area("Principais atividades")
        prerequisites = st.text_area("Pré-requisitos")
        differentials = st.text_area("Diferenciais")

        st.markdown("##### Critérios (peso deve somar 100%)")
        num = st.number_input("Qtd critérios", 1, 10, 5)
        crits = []
        for i in range(int(num)):
            c1, c2 = st.columns([2, 1])
            nm = c1.text_input(f"Nome do critério {i+1}", key=f"crit_nm_{i}")
            pw = c2.number_input(f"Peso {i+1} (%)", 0, 100, 0, key=f"crit_pw_{i}")
            ds = st.text_area(f"Descrição {i+1}", key=f"crit_ds_{i}")
            if nm:
                crits.append({"criterio": nm, "peso": pw, "descricao": ds})
        total = sum(c.get("peso", 0) for c in crits)
        st.caption(f"Soma dos pesos: {total}%")
        submitted = st.form_submit_button("Salvar vaga", disabled=not name or total != 100)

    if submitted:
        try:
            payload = {
                "title": name,
                "main_activities": main_activities,
                "prerequisites": prerequisites,
                "differentials": differentials,
                "criteria": crits
            }
            resp = api_post("/jobs", json_payload=payload)
            st.success("✅ Vaga criada!")
            st.json(resp)
            st.session_state.jobs_cache = []  # invalida cache
        except Exception as e:
            st.error(f"Falha ao criar vaga: {e}")

    st.markdown("#### Minhas Vagas")
    try:
        jobs = load_jobs()
        df_jobs = pd.DataFrame(jobs)
        if not df_jobs.empty:
            st.dataframe(df_jobs, use_container_width=True, height=350)
        else:
            st.info("Sem vagas cadastradas.")
    except Exception as e:
        st.error(f"Erro ao listar vagas: {e}")

# -------------------------
# CURRÍCULOS
# -------------------------
with tabs[2]:
    st.subheader("Upload de Currículos (PDF)")
    try:
        jobs = load_jobs()
    except Exception as e:
        st.warning(f"Carregar vagas: {e}")
        jobs = []

    job_map = {j.get("name") or j.get("title"): j.get("id") for j in jobs} if jobs else {}
    job_name = st.selectbox("Selecione a vaga", list(job_map.keys())) if job_map else None
    pdf = st.file_uploader("Enviar PDF do currículo", type=["pdf"])
    if st.button("📤 Enviar", disabled=not (pdf and job_name)):
        try:
            job_id = job_map[job_name]
            files = {"pdf": (pdf.name, pdf.getvalue(), "application/pdf")}
            data = {"job_id": job_id}
            resp = api_post("/resumes/upload", files=files, data=data)
            st.success("Enfileirado com sucesso!")
            st.json(resp)
        except Exception as e:
            st.error(f"Falha no upload: {e}")

    st.markdown("---")
    st.markdown("#### Status de Processamento")
    st.caption("Use a aba *Análises* para ver resultados consolidados.")

# -------------------------
# ANÁLISES
# -------------------------
with tabs[3]:
    st.subheader("Resultados das Análises")
    try:
        analysis = load_analysis()
        df = pd.DataFrame(analysis)
        if df.empty:
            st.info("Ainda não há análises.")
        else:
            # Filtros
            c1, c2, c3 = st.columns(3)
            job_filter = c1.text_input("Filtrar por Job ID")
            name_filter = c2.text_input("Filtrar por Nome do candidato")
            score_min = c3.number_input("Score mínimo", 0.0, 10.0, 0.0, 0.1)

            if job_filter:
                df = df[df["job_id"].astype(str).str.contains(job_filter)]
            if name_filter and "candidate_name" in df:
                df = df[df["candidate_name"].astype(str).str.contains(name_filter, case=False, na=False)]
            if "score" in df:
                df = df[df["score"].fillna(0) >= score_min]

            st.dataframe(df, use_container_width=True, height=450)

            # Gráfico por score
            if "score" in df:
                st.markdown("##### Distribuição de Score (filtrada)")
                fig = px.histogram(df, x="score", nbins=20)
                st.plotly_chart(fig, use_container_width=True)

            # Download CSV
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button("⬇️ Baixar CSV", data=buf.getvalue(), file_name="analises.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Erro ao carregar análises: {e}")

# -------------------------
# CONFIGURAÇÕES (já na sidebar)
# -------------------------
with tabs[4]:
    st.subheader("Configurações e Ajuda")
    st.markdown("""
- API pública: https://curriculos-saas.onrender.com

""")
