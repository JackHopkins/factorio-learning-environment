import json
from enum import Enum
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from factorio_entities import Direction as DirectionA
from factorio_instance import Direction

class EntityEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Direction):
            return obj.value
        if isinstance(obj, Enum):
            if hasattr(obj, "value") and isinstance(obj.value, tuple):
                return obj.value[0]
            return obj.value
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items()
                   if not k.startswith('_')}
        return super().default(obj)

def entity_serializer(obj: Any) -> Dict:
    """Custom serializer for entity-related objects"""
    if isinstance(obj, DirectionA) or isinstance(obj, Direction):
        return obj.value
    if isinstance(obj, Enum):
        if hasattr(obj, "value") and isinstance(obj.value, tuple):
            return obj.value[0]
        return obj.value
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items()
               if not k.startswith('_')}
    raise TypeError(f"Object of type {type(obj)} is not serializable")


class Message(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerationParameters(BaseModel):
    model: str
    n: int = 1
    temperature: float = 0.7
    max_tokens: int = 2048
    logit_bias: Optional[Dict[str, float]] = None
    stop_sequences: Optional[List] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    

class Conversation(BaseModel):
    """Tracks dialogue between LLM and Factorio"""
    messages: List[Message] = Field(default_factory=list)

    @classmethod
    def parse_raw(cls, data: Dict[str, Any]) -> 'Conversation':
        messages = [Message(**msg) if isinstance(msg, dict) else msg
                    for msg in data['messages']]
        return cls(messages=messages)

    def add_result(self, program: str, response: str, **kwargs):
        """Add program execution result to conversation"""
        self.messages.append(Message(role="assistant",content=program, metadata=kwargs))
        self.messages.append(Message(role="user", content=f"Execution result: \n{response}"))

            # Updated state:
            # Inventory: {json.dumps(new_state.inventory.__dict__, indent=2)}
            # Entities: {json.dumps(entities, indent=2, cls=EntityEncoder)}"""))