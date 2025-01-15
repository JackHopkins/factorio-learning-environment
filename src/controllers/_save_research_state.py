from controllers.__action import Action
from factorio_instance import PLAYER
from models.research_state import ResearchState
from models.technology_state import TechnologyState


class SaveResearchState(Action):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self) -> ResearchState:
        """
        Save the current research state of the force

        Returns:
            ResearchState: Complete research state including all technologies
        """
        state, _ = self.execute(PLAYER)

        # Convert the raw state into our dataclass structure
        technologies = {
            name: TechnologyState(
                name=tech["name"],
                researched=tech["researched"],
                enabled=tech["enabled"],
                level=tech["level"],
                research_unit_count=tech["research_unit_count"],
                research_unit_energy=tech["research_unit_energy"],
                prerequisites=tech["prerequisites"],
                ingredients=tech["ingredients"]
            )
            for name, tech in state["technologies"].items()
        }

        return ResearchState(
            technologies=technologies,
            current_research=state["current_research"] if "current_research" in state else None,
            research_progress=state["research_progress"],
            research_queue=state["research_queue"]
        )
