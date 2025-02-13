import ast
import enum
from typing import Dict, Any
from pydantic import BaseModel
from models.achievements import ProductionFlows


class Python(str):
    """A custom type that only accepts syntactically valid Python code."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError('string required')

        try:
            # Try to parse the string as Python code
            ast.parse(v)
        except SyntaxError as e:
            raise ValueError(f'Invalid Python syntax: {str(e)}')
        except Exception as e:
            raise ValueError(f'Error parsing Python code: {str(e)}')

        return v


class PolicyMeta(BaseModel):
    output_tokens: int
    input_tokens: int
    total_tokens: int

class Policy(BaseModel):
    code: Python
    meta: PolicyMeta

class TaskResponse:
    meta: Dict[str, Any] = {}

class Response:
    score: float
    achievements: Dict[Any, Any]
    flows: ProductionFlows
    task: TaskResponse
    step: int
    ticks: int


class CompletionReason(enum.Enum):
    TIMEOUT = "timeout",
    SUCCESS = "success",
    RUNTIME_ERROR = "runtime_error"

class CompletionResult:
    step: int
    reason: CompletionReason
    metadata: Dict[str, Any] = {}
