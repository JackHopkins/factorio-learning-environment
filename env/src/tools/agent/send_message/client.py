from typing import Optional
import time
from pydantic import BaseModel
from tools.tool import Tool
from tools.admin.render_message.client import RenderMessage


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
        self.load()

    def __call__(self, message: str, recipient: int = -1) -> bool:
        """
        Send a message to other agents. If recipient is specified, message is only sent to that agent.
        :param message: The message to send
        :param recipient: Optional recipient agent index. If -1, message is sent to all other agents.
        :return: True if message was sent successfully
        """
        try:
            if not message.startswith("Output from agent"):
                rendered_message = self.render_message(message, duration=3000)
                message = "Direct message from agent " + str(self.player_index) + ": " + message
            print(f'sending message from {self.player_index} to {recipient}: {message}')
            response = self.execute(self.player_index, message, recipient)
            if isinstance(response, str):
                raise Exception(f"Could not send message: {response}")
            return True
            
        except Exception as e:
            raise Exception(f"Error sending message: {str(e)}") 
        

# /c local e=global.agent_characters[1];rendering.draw_rectangle{surface=e.surface,left_top={e.position.x-0.5,e.position.y-1.2},right_bottom={e.position.x+0.5,e.position.y-0.8},color={r=0,g=0,b=0,a=0.7},filled=true,time_to_live=300};rendering.draw_text{surface=e.surface,text="Hello, World!",target={e.position.x,e.position.y-1},color={r=1,g=1,b=1,a=1},alignment="center",time_to_live=300}