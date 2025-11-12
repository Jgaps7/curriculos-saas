from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class JobCriteria(BaseModel):
    name: str
    weight: float
    description: Optional[str] = None


class JobCreate(BaseModel):
    title: str
    main_activities: str = ""
    prerequisites: str = ""
    differentials: str = ""
    criteria: List[JobCriteria] = Field(default_factory=list)
