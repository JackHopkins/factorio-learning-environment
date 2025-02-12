from typing import Dict, Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
