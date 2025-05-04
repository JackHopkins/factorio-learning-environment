from typing import Optional, List
from entities import Ingredient
from game_types import Technology, Prototype
from tools.tool import Tool


class GetResearchProgress(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, technology: Optional[Technology] = None) -> List[Ingredient]:
        """
        Get the progress of research for a specific technology or the current research.
        :param technology: The technology to check progress for
            - If provided: Returns remaining requirements for that technology
            - If None: Returns requirements for current research (must have active research!)
        :return a List[Ingredient] where each Ingredient contains:
            - name: Name of the science pack
            - count: Number of packs still needed
            - type: Type of the ingredient (usually "item" for science packs)

        """
        if technology is not None:
            if hasattr(technology, 'value'):
                name = technology.value
            else:
                name = technology
        else:
            name = None

        success, elapsed = self.execute(self.player_index, name)

        if success != {} and isinstance(success, str):
            if success is None:
                raise Exception("No research in progress" if name is None else f"Cannot get progress for {name}")
            else:
                result = ":".join(success.split(':')[2:]).replace('"', '').strip()
                if result:
                    raise Exception(result)
                else:
                    raise Exception(success)

        return [
                Ingredient(
                    name=ingredient["name"],
                    count=ingredient["count"],
                    type=ingredient.get("type")
                )
                for ingredient in success
            ]