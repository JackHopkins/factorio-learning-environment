from typing import Dict, List, Any

from pydantic import BaseModel, Field

from models.message import Message


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
        self.messages.append(Message(role="assistant", content=program, metadata=kwargs))
        self.messages.append(Message(role="user", content=response, metadata=kwargs))


