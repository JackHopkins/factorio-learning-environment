from typing import Optional
import time
from pydantic import BaseModel
from tools.tool import Tool


class AgentMessage(BaseModel):
    """Represents a message sent between agents"""
    sender: int
    recipient: Optional[int] = None
    content: str
    timestamp: float
    is_new: bool = True


class SendMessage(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "send_message"
        self.game_state = game_state
        self.load()

    def __call__(self, message: str, recipient: int = -1) -> bool:
        """
        Send a message to other agents. If recipient is specified, message is only sent to that agent.
        :param message: The message to send
        :param recipient: Optional recipient agent index. If -1, message is sent to all other agents.
        :return: True if message was sent successfully
        """
        try:
            response = self.execute(self.player_index - 1, message, recipient)
            if isinstance(response, str):
                raise Exception(f"Could not send message: {response}")
            
            return True
            
        except Exception as e:
            raise Exception(f"Error sending message: {str(e)}") 