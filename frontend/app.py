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
    if not st.session_state.token:
        raise RuntimeError("Token JWT não configurado. Preencha o campo 'Supabase JWT' na barra lateral.")
    if not st.session_state.tenant_id:
        raise RuntimeError("Tenant ID não configurado. Preencha o campo 'Tenant ID' na barra lateral.")

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
    st.session_state.api_url = st.text_input("API URL", value=st.session_state.api_url, help="URL base da API FastAPI (ex: https://curriculos-saas.onrender.com)",)
    st.session_state.token = st.text_input("Supabase JWT", type="password", value=st.session_state.token, help="Cole aqui o JWT gerado para o usuário/tenant.")
    st.session_state.tenant_id = st.text_input("Tenant ID", value=st.session_state.tenant_id, help="UUID do tenant cadastrado na tabela tenants.")
    st.markdown("---")
    if st.button("🔄 Atualizar dados"):
        st.session_state.jobs_cache = []
        st.session_state.resumes_cache = []
        st.session_state.analysis_cache = []
        st.rerun()

        # Aviso global se estiver sem JWT/Tenant
if not st.session_state.token or not st.session_state.tenant_id:
    st.warning("⚠️ Preencha **Supabase JWT** e **Tenant ID** na barra lateral antes de usar o painel.")

st.title("🧠 Currículos SaaS – Painel")

# =========================
# Funções de dados
# =========================
def load_jobs():
    if not st.session_state.jobs_cache:
        data = api_get("/jobs")
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
        col3.metric("Média de Score", round(df["score"].dropna().mean(), 2) if "score" in df and not df["score"].dropna().empty else 0)
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
        num = st.number_input("Qtd critérios", min_value=1, max_value=10, value=5, key="num_criterios")
        crits_preview = []
        for i in range(int(num)):
            c1, c2 = st.columns([2, 1])
            nm = c1.text_input(f"Nome do critério {i+1}", key=f"crit_nm_{i}")
            pw = c2.number_input(
                f"Peso {i+1} (%)",
                min_value=0,
                max_value=100,
                value=0,
                key=f"crit_pw_{i}"
            )
            ds = st.text_area(f"Descrição {i+1}", key=f"crit_ds_{i}")
            if nm:
                crits_preview.append({"name": nm, "weight": pw, "description": ds})
        total_preview = sum(int(c["weight"]) for c in crits_preview)
        st.caption(f"Soma (pré-visualização): {total_preview}%")
        submitted = st.form_submit_button("Salvar vaga")
    if submitted:

        crits = []
        num_criterios = int(st.session_state.get("num_criterios", 0))

        for i in range(num_criterios):
                nm = st.session_state.get(f"crit_nm_{i}", "").strip()
                pw = st.session_state.get(f"crit_pw_{i}", 0)
                ds = st.session_state.get(f"crit_ds_{i}", "")

                if nm:
                    crits.append({
                        "name": nm,
                        "weight": int(pw),
                        "description": ds
                    })

        total = sum(c["peso"] for c in crits)

    if not name:
            st.error("❌ O nome da vaga é obrigatório.")
    elif total != 100:
            st.error(f"❌ A soma dos pesos precisa ser 100%. Soma atual: {total}%.")
    elif not crits:
            st.error("❌ Defina ao menos um critério com nome.")
    else:
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

    job_map = {}
    for j in jobs:
        title = j.get("title") or j.get("name")
        jid   = j.get("id")
        if title and jid:
            job_map[title] = jid
    job_name = st.selectbox("Selecione a vaga", list(job_map.keys())) if job_map else ["Nenhuma vaga disponível"]
    pdf = st.file_uploader("Enviar PDF do currículo", type=["pdf"])
    enviar = st.button("📤 Enviar currículo")
    if enviar:
        # 1. Validações antes do envio
        if not job_map:
            st.error("❌ Nenhuma vaga cadastrada. Cadastre uma vaga primeiro.")
            st.stop()

        if job_name not in job_map:
            st.error("❌ Selecione uma vaga válida.")
            st.stop()

        if pdf is None:
            st.error("❌ Envie um arquivo PDF antes de continuar.")
            st.stop()

        if not pdf.name.lower().endswith(".pdf"):
            st.error("❌ O arquivo enviado não é um PDF.")
            st.stop()

        try:
            job_id = job_map[job_name]
            files = {"pdf": (pdf.name, pdf, "application/pdf")}
            data = {"job_id": job_id}
            resp = api_post("/resumes/upload", files=files, data=data)
            st.success("Currículo enviado e enfileirado com sucesso!")
            st.json(resp)
        except requests.exceptions.ConnectionError:
            st.error("❌ Falha de conexão com a API (Render pode estar dormindo).")
        except Exception as e:
            st.error(f"❌ Falha no upload: {e}")

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
