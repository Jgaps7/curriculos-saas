from pydantic import BaseModel, Field
from typing import List, Dict, Any

class JobCreate(BaseModel):
    name: str
    main_activities: str = ""
    prerequisites: str = ""
    differentials: str = ""
    criteria: List[Dict[str, Any]] = Field(default_factory=list)
