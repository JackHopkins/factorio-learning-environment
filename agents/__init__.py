import ast
import enum
from typing import Dict, Any
from pydantic import BaseModel
from models.achievements import ProductionFlows
import datetime

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


class CompletionReason(enum.Enum):
    TIMEOUT = "timeout",
    SUCCESS = "success",
    RUNTIME_ERROR = "runtime_error"

class CompletionResult:
    step: int
    reason: CompletionReason
    metadata: Dict[str, Any] = {}
