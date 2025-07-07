import datetime
import enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from fle.commons.models.achievements import ProductionFlows


class TaskResponse(BaseModel):
    meta: Dict[str, Any] = {}
    success: bool


class Response(BaseModel):
    score: float
    achievements: Dict[Any, Any]
    flows: ProductionFlows
    task: TaskResponse
    step: int
    ticks: int
    code: str
    created_at: datetime.datetime
    response: str
    error: bool = False
    program_id: Optional[int] = None


class CompletionReason(enum.Enum):
    TIMEOUT = "timeout"
    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"


class CompletionResult(BaseModel):
    step: int
    reason: CompletionReason
    metadata: Dict[str, Any] = {}
