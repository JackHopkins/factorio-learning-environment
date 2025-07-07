from typing import Dict, List, Any

from pydantic import BaseModel, Field

from fle.commons.models.message import Message


class Conversation(BaseModel):
    """Tracks dialogue between LLM and Factorio"""

    messages: List[Message] = Field(default_factory=list)

    @classmethod
    def parse_raw(cls, data: Dict[str, Any]) -> "Conversation":
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg for msg in data["messages"]
        ]
        return cls(messages=messages)

    def set_system_message(self, message: str):
        if self.messages and self.messages[0].role == "system":
            self.messages[0] = Message(role="system", content=message)
        else:
            self.messages.insert(0, Message(role="system", content=message))

    def add_agent_message(self, message: str, **kwargs):
        self.messages.append(
            Message(role="assistant", content=message, metadata=kwargs)
        )

    def add_user_message(self, message: str, **kwargs):
        self.messages.append(Message(role="user", content=message, metadata=kwargs))

    def add_result(self, program: str, response: str, **kwargs):
        """Add program execution result to conversation"""
        self.add_agent_message(program, **kwargs)
        self.add_user_message(response, **kwargs)
