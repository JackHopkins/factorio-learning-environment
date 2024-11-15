from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datasetgen.mcts.task_status import TaskStatus


class EvaluationTask(BaseModel):
    id: Optional[int] = None
    program_id: int
    status: TaskStatus = TaskStatus.PENDING
    instance_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None