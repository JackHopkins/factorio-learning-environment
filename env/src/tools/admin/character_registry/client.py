from instance import PLAYER
from tools.init import Init


class CharacterRegistry(Init):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def create_character(self, x, y):
        """Create a new character at the specified position"""
        response, time_elapsed = self.execute(PLAYER, x=x, y=y)
        return response

    def get_character_index(self, unit_number):
        """Get the registry index for a character by its unit number"""
        response, time_elapsed = self.execute(PLAYER, unit_number=unit_number)
        return response

    def get_all_characters(self):
        """Get list of all registered characters"""
        response, time_elapsed = self.execute(PLAYER)
        return response
