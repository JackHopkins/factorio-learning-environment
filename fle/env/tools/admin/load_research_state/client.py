from fle.commons.models.research_state import ResearchState
from fle.env.tools import Tool


class LoadResearchState(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, state: ResearchState) -> bool:
        """
        Load a saved research state into the force

        Args:
            state: ResearchState to load

        Returns:
            bool: True if successful
        """

        if not state:
            return False

        # Convert our dataclass structure back to raw dict for Lua
        raw_state = {
            "technologies": {
                name: {
                    "name": tech.name,
                    "researched": tech.researched,
                    "enabled": tech.enabled,
                    # "visible": tech.visible,
                    "level": tech.level,
                    "research_unit_count": tech.research_unit_count,
                    "research_unit_energy": tech.research_unit_energy,
                    "prerequisites": tech.prerequisites,
                    "ingredients": tech.ingredients,
                }
                for name, tech in state.technologies.items()
            },
            "current_research": state.current_research,
            "research_progress": state.research_progress,
            "research_queue": state.research_queue,
            "progress": state.progress,
        }

        return self.execute(self.player_index, raw_state)
