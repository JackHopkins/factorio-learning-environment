from env.src.tools.tool import Tool

class ToggleDebug(Tool):
    """Toggle debug settings in Factorio"""

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, debug_type="rendering", enable=None):
        """
        Toggle or set a debug flag in the game

        Args:
            debug_type: Type of debug to toggle (e.g., "rendering")
            enable: Boolean to enable/disable, or None to toggle

        Returns:
            String: Status message
        """
        enable_str = "true" if enable else "false" if enable is not None else None
        response, _ = self.execute(self.player_index, debug_type, enable_str)
        
        return response.strip('"')