from datetime import datetime
from typing import Dict, Any
from typing import Optional
from pydantic import BaseModel, Field
from models.achievements import ProductionFlows


class TaskResponse(BaseModel):
    meta: Dict[str, Any] = {}

class Response(BaseModel):
    code: str
    score: float = 0.0
    achievements: dict = {}
    flows: Optional[ProductionFlows] = None
    created_at: datetime = Field(default_factory=datetime.now)
    response: Optional[str] = None
    task: Optional[TaskResponse] = None # Not used in Open play
    step: int = 0
    ticks: int = 0

    def __repr__(self):
        return self.code