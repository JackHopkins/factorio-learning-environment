import ast
import enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from env.src.models.achievements import ProductionFlows
import datetime
from env.src.models.conversation import Conversation


class Python(str):
    """A custom type that only accepts syntactically valid Python code."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, values=None, config=None, field=None) -> str:
        if not isinstance(value, str):
            raise TypeError("string required")

        try:
            # Try to parse the string as Python code
            ast.parse(value)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing Python code: {str(e)}")

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
    TIMEOUT = ("timeout",)
    SUCCESS = ("success",)
    RUNTIME_ERROR = "runtime_error"


class CompletionResult(BaseModel):
    step: int
    reason: CompletionReason
    metadata: Dict[str, Any] = {}
