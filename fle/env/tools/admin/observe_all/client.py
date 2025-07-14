from typing import Dict, List, Any, Optional

from fle.env.tools import Tool


class ObserveAll(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, include_status: bool = False, radius=100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns information about all entities, tiles, and resources within 500 tiles of the player.
        
        Args:
            include_status: Whether to include status information for entities (optional)
            
        Returns:
            Dictionary containing:
            - entities: List of all entities with:
                - name: Entity name/type
                - position: Position object with x,y coordinates  
                - direction: Direction the entity is facing (if applicable)
                - status: Entity status (if include_status is True and available)
            - water_tiles: List of water tiles with:
                - x: X coordinate
                - y: Y coordinate
                - name: Tile type (water, deepwater, etc.)
            - resources: List of resource patches with:
                - name: Resource type (iron-ore, copper-ore, etc.)
                - position: Position object with x,y coordinates
                - amount: Resource amount in the patch
        """
        result, _ = self.execute(self.player_index, include_status, radius)
        
        return {
            "entities": self.parse_lua_dict(result.get("entities", [])),
            "water_tiles": self.parse_lua_dict(result.get("water_tiles", [])),
            "resources": self.parse_lua_dict(result.get("resources", []))
        }