from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CriteriaItem(BaseModel):
    name: str
    weight: float
    description: Optional[str] = None


class ResumeBase(BaseModel):
    job_id: str
    tenant_id: str
    file_url: Optional[str] = ""
    status: Optional[str] = "queued"


class ResumeCreate(ResumeBase):
    raw_text: Optional[str] = ""
    summary: Optional[str] = ""
    opinion: Optional[str] = ""
    score: Optional[float] = None


class ResumeOut(BaseModel):
    id: str
    job_id: str
    tenant_id: str
    score: Optional[float]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class AnalysisOut(BaseModel):
    id: str
    resume_id: str
    job_id: str
    tenant_id: str
    candidate_name: Optional[str] = None
    skills: List[str] = []
    education: List[str] = []
    languages: List[str] = []
    score: Optional[float] = None
    created_at: datetime

    class Config:
        orm_mode = True
