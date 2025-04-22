from typing import List, Dict
from tools.tool import Tool


class LoadMessages(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "load_messages"
        self.game_state = game_state
        self.load()

    def __call__(self, messages: List[Dict]) -> bool:
        """
        Load messages into the game state.
        :param messages: List of message dictionaries containing sender, message, timestamp, and recipient
        :return: True if successful, raises exception if not
        """
        try:
            # Convert messages to the format expected by the server
            formatted_messages = []
            for msg in messages:
                if not all(k in msg for k in ['sender', 'message', 'timestamp', 'recipient']):
                    raise ValueError("Message missing required fields: sender, message, timestamp, recipient")
                
                formatted_messages.append(
                    f"{msg['sender']}|{msg['message']}|{msg['timestamp']}|{msg['recipient']}"
                )
            
            # Join messages with newlines
            messages_str = "\n".join(formatted_messages)
            
            # Execute the server command
            response = self.execute(messages_str)
            
            if isinstance(response, str):
                raise Exception(f"Could not load messages: {response}")
                
            return True
            
        except Exception as e:
            raise Exception(f"Error loading messages: {str(e)}")
