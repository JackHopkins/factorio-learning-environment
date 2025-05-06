from typing import Optional
import time
from pydantic import BaseModel
from tools.tool import Tool
from tools.admin.render_message.client import RenderMessage
from tools.admin.get_messages.client import GetMessages


class AgentMessage(BaseModel):
    """Represents a message sent between agents"""
    sender: int
    recipient: Optional[int] = None
    content: str
    timestamp: float
    is_new: bool = True

    def __repr__(self):
        return f"Message(sender={self.sender}, recipient={self.recipient}, content={self.content}, timestamp={self.timestamp}, is_new={self.is_new})"


class SendMessage(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "send_message"
        self.game_state = game_state
        self.render_message = RenderMessage(connection, game_state)
        self.get_messages = GetMessages(connection, game_state)
        self.load()

    def __call__(self, message: str, recipient: int = -1) -> bool:
        """
        Send a message to other agents. If recipient is specified, message is only sent to that agent.
        :param message: The message to send
        :param recipient: Optional recipient agent index. If -1, message is sent to all other agents.
        :return: True if message was sent successfully
        """
        if recipient != -1:
            recipient += 1  # Convert to 1-based index
        try:
            rendered_message = self.render_message(message)
            print(f'sending message from {self.player_index} to {recipient}: {message}')
            response = self.execute(self.player_index, message, recipient)
            if isinstance(response, str):
                raise Exception(f"Could not send message: {response}")
            messages = self.get_messages(True)
            return True
            
        except Exception as e:
            raise Exception(f"Error sending message: {str(e)}") 
        