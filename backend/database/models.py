from sqlalchemy import Column, String, Text, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.connection import Base


# ======================================================
# 🧱 Tabela Tenant (cliente / workspace)
# ======================================================
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="tenant", cascade="all, delete-orphan")


# ======================================================
# 👥 Tabela Membership (usuário vinculado ao tenant)
# ======================================================
class Membership(Base):
    __tablename__ = "memberships"

    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, primary_key=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relação reversa
    tenant = relationship("Tenant", back_populates="memberships")


# ======================================================
# 💼 Tabela Job (vagas)
# ======================================================
class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)              # 🔹 ADICIONADO
    main_activities = Column(Text, nullable=True)
    prerequisites = Column(Text, nullable=True)
    differentials = Column(Text, nullable=True)
    criteria = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relações
    tenant = relationship("Tenant", back_populates="jobs")
    resumes = relationship("Resume", back_populates="job", cascade="all, delete-orphan")


# ======================================================
# 📄 Tabela Resume (currículos)
# ======================================================
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_name = Column(String, nullable=True)          # 🔹 ADICIONADO
    file_url = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    opinion = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    status = Column(String, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relações
    tenant = relationship("Tenant")
    job = relationship("Job", back_populates="resumes")
    analysis = relationship("Analysis", back_populates="resume", cascade="all, delete-orphan")



# ======================================================
# 📊 Tabela Analysis (resultado detalhado da IA)
# ======================================================
class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    candidate_name = Column(String)
    skills = Column(JSON, default=list)
    education = Column(JSON, default=list)
    languages = Column(JSON, default=list)
    score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relações
    resume = relationship("Resume", back_populates="analysis")
