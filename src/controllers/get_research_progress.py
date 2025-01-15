from typing import Optional, List
from controllers.__action import Action
from factorio_entities import Ingredient
from factorio_types import Technology, Prototype
from factorio_instance import PLAYER




class GetResearchProgress(Action):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, technology: Optional[Technology] = None) -> List[Ingredient]:
        """
        Get the progress of research for a specific technology or the current research.

        Args:
            technology: Optional technology to check. If None, checks current research.

        Returns:
            [Ingredient]: Remaining ingredients required

        Raises:
            Exception: If technology doesn't exist or isn't being researched
        """
        if technology is not None:
            if hasattr(technology, 'value'):
                name = technology.value
            else:
                name = technology
        else:
            name = None

        success, elapsed = self.execute(PLAYER, name)

        if success != {} and isinstance(success, str):
            if success is None:
                raise Exception("No research in progress" if name is None else f"Cannot get progress for {name}")
            else:
                result = ":".join(success.split(':')[2:]).replace('"', '').strip()
                raise Exception(result)

        return [
                Ingredient(
                    name=ingredient["name"],
                    count=ingredient["count"],
                    type=ingredient.get("type")
                )
                for ingredient in success
            ]