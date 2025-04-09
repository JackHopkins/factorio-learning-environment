from typing import List, Optional
from pydantic import BaseModel
from game_types import Technology
from instance import PLAYER
from tools.tool import Tool


class Ingredient(BaseModel):
    name: str
    count: Optional[int] = 1
    type: Optional[str] = None


class SetResearch(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, technology: Technology) -> List[Ingredient]:
        """
        Set the current research technology for the player's force.
        :param technology: A Technology enum value representing the technology to research
        :return: A list of `Ingredient` objects containing the required science packs and their quantities
            - Each `Ingredient` object has:
            - `name`: Name of the required science pack
            - `count`: Number of science packs needed
            - `type`: Type of the ingredient (usually "item" for science packs)
        """
        if hasattr(technology, 'value'):
            name = technology.value
        else:
            name = technology

        success, elapsed = self.execute(PLAYER, name)

        if success != {} and isinstance(success, str):
            if success is None:
                raise Exception(f"Could not set research to {name} - Technology is invalid or unavailable.")
            else:
                result = ":".join(success.split(':')[2:]).replace('"', '').strip()
                if not result:
                    raise Exception(f"Could not set research to {name} - {success}")
                else:
                    raise Exception(result)

        # Parse the returned ingredients list
        if isinstance(success, list):
            return [
                Ingredient(
                    name=ingredient.get('name'),
                    count=ingredient.get('count', 1),
                    type=ingredient.get('type')
                )
                for ingredient in success
            ]

        # Fallback empty list if no ingredients returned
        return []