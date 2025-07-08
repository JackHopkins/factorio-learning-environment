from fle.commons.models.research_state import ResearchState
from fle.commons.models.technology_state import TechnologyState
from fle.env.tools import Tool


class SaveResearchState(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self) -> ResearchState:
        """
        Save the current research state of the force

        Returns:
            ResearchState: Complete research state including all technologies
        """
        state, _ = self.execute(self.player_index)

        if not isinstance(state, dict):
            raise Exception(f"Could not save research state: {state}")

        try:
            # Convert the raw state into our dataclass structure
            technologies = {}
            if "technologies" in state:
                technologies = {
                    name: TechnologyState(
                        name=tech["name"],
                        researched=tech["researched"],
                        enabled=tech["enabled"],
                        level=tech["level"],
                        research_unit_count=tech["research_unit_count"],
                        research_unit_energy=tech["research_unit_energy"],
                        prerequisites=[x for x in tech["prerequisites"].values()],
                        ingredients=[
                            {x["name"]: x["amount"]}
                            for x in tech["ingredients"].values()
                        ],
                    )
                    for name, tech in state["technologies"].items()
                }
            return ResearchState(
                technologies=technologies,
                current_research=state["current_research"]
                if "current_research" in state
                else None,
                research_progress=state["research_progress"],
                research_queue=[x for x in state["research_queue"].values()],
                progress=state["progress"] if "progress" in state else None,
            )

        except Exception as e:
            print(f"Could not save technologies: {e}")
            raise e
