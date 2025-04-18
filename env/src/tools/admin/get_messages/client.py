from typing import List, Dict, Optional, Union
from tools.tool import Tool


class GetMessages(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "get_messages"
        self.game_state = game_state
        self.load()

    def __call__(self, all_players: bool = False) -> List[Dict]:   
        if all_players:
            all_messages = []
            for player_index in range(self.game_state.instance.num_players):
                messages = self.get_single_player_messages(player_index)
                all_messages.extend(messages)
            return all_messages
        else:
            return self.get_single_player_messages(self.player_index - 1)

    
    def get_single_player_messages(self, player_index: int) -> List[Dict]:
        """
        Get all messages sent to this agent.
        :return: List of message dictionaries containing sender, message, timestamp, and recipient
        """
        try:
            response = self.execute(player_index)
            
            if isinstance(response, str):
                raise Exception(f"Could not get messages: {response}")
                
            # The response is a tuple where the first element is the parsed response and second is the raw lua_response
            if isinstance(response, tuple) and len(response) >= 2:
                _, lua_response = response
                # lua_response:  { ["a"] = true,["b"] = 1|Hello Agent 1|3650830|1,}
                # Extract data after ["b"] = if present
                if '["b"] = ' in lua_response:
                    lua_response = lua_response.split('["b"] = ')[1]
                    # Remove trailing comma and closing bracket
                    lua_response = lua_response.rstrip(',}')
                
                # Parse the simple string format: sender|message|timestamp|recipient
                messages = []
                for line in lua_response.split('\n'):
                    if not line.strip():
                        continue
                    try:
                        sender, message, timestamp, recipient = line.split('|')
                        messages.append({
                            'sender': int(sender),
                            'message': message,
                            'timestamp': int(timestamp),
                            'recipient': int(recipient)
                        })
                    except ValueError:
                        # Skip malformed lines
                        continue
                
                print(f'get_messages for player {self.player_index - 1} messages: {messages}')
                return messages
            print(f'get_messages for player {self.player_index - 1} no messages')
            return []
            
        except Exception as e:
            raise Exception(f"Error getting messages: {str(e)}")