import ast
import enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from env.src.models.achievements import ProductionFlows
import datetime
from env.src.models.conversation import Conversation
import time

class TimingMetrics(BaseModel):
    """Stores timing metrics for a single operation"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    children: List['TimingMetrics'] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    @property
    def total_duration(self) -> float:
        """Get total duration including children"""
        if not self.children:
            return self.duration
        return sum(child.total_duration for child in self.children)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format"""
        return {
            'operation': self.operation_name,
            'duration': self.duration,
            'total_duration': self.total_duration,
            'children': [child.to_dict() for child in self.children],
            'metadata': self.metadata
        }

class Python(str):
    """A custom type that only accepts syntactically valid Python code."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, values=None, config=None, field=None) -> str:
        if not isinstance(value, str):
            raise TypeError('string required')

        try:
            # Try to parse the string as Python code
            ast.parse(value)
        except SyntaxError as e:
            raise ValueError(f'Invalid Python syntax: {str(e)}')
        except Exception as e:
            raise ValueError(f'Error parsing Python code: {str(e)}')

        return value


class PolicyMeta(BaseModel):
    output_tokens: int
    input_tokens: int
    total_tokens: int
    text_response: str

class Policy(BaseModel):
    code: Python
    input_conversation: Conversation = None
    meta: PolicyMeta

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
    TIMEOUT = "timeout",
    SUCCESS = "success",
    RUNTIME_ERROR = "runtime_error"

class CompletionResult(BaseModel):
    step: int
    reason: CompletionReason
    metadata: Dict[str, Any] = {}
