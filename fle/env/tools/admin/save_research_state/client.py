from fle.commons.models.research_state import ResearchState
from fle.commons.models.technology_state import TechnologyState
from fle.env.tools import Tool


class SaveResearchState(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, compact: bool = False) -> ResearchState | dict:
        """
        Save the current research state of the force

        ``compact=True`` returns a sparse mapping containing only dynamic
        research identity. It is intended for state hashing when the complete
        technology graph would exceed the RCON response limit.

        Returns:
            ResearchState: Complete research state including all technologies
        """
        if compact:
            state, _ = self.execute(self.player_index, compact)
        else:
            state, _ = self.execute(self.player_index)

        if not isinstance(state, dict):
            raise Exception(f"Could not save research state: {state}")

        if compact:
            return state

        # A truncated RCON dump can still decode as ``{}`` (or an error
        # mapping). Treat that as a failed full capture so callers can retry
        # with the compact identity form instead of hashing missing research.
        technologies = state.get("technologies")
        if not isinstance(technologies, dict) or not technologies:
            raise Exception(
                "Could not save research state: incomplete technology table"
            )

        try:
            # Convert the raw state into our dataclass structure
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
                for name, tech in technologies.items()
            }
            return ResearchState(
                technologies=technologies,
                current_research=state["current_research"]
                if "current_research" in state
                else None,
                research_progress=state["research_progress"]
                if "research_progress" in state
                else None,
                research_queue=[x for x in state["research_queue"].values()]
                if "research_queue" in state
                else [],
                progress=state["progress"] if "progress" in state else None,
            )

        except Exception as e:
            print(f"Could not save technologies: {e}")
            raise e
