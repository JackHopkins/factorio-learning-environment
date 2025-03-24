from typing import Optional, Dict

from entities import BoundingBox, Position, BeltGroup, PipeGroup, \
    ElectricityGroup, Layer
from instance import PLAYER
from tools.admin.render.rendered_image import RenderedImage
from tools.admin.render.renderer import Renderer
from tools.agent.get_entities.client import GetEntities
from tools.tool import Tool

MAX_TILES = 20 # Don't parameterise this, as the agent could break if it chooses a huge grid.

class Render(Tool):
    """Render tool for visualizing Factorio entities"""

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.renderer = Renderer()
        self.get_entities = GetEntities(connection, game_state)

    def __call__(self, position: Optional[Position] = None,
                 bounding_box: Optional[BoundingBox] = None,
                 style: Optional[Dict] = None,
                 layers: Optional[Layer] = Layer.ALL
                 ) -> RenderedImage:
        """
        Render entities around a position or within a bounding box.

        Args:
            position: Center position for rendering (defaults to player position if None)
            radius: Radius around position to render (default: 10)
            bounding_box: Specific area to render (overrides position and radius)
            style: Optional custom style configuration
            max_tiles: Maximum number of tiles to render on each side of the position (default: 50)
            layers: Layer flags to specify which elements to render

        Returns:
            RenderedImage: An image object that can be displayed or saved
        """
        radius: int = MAX_TILES
        max_tiles: int = MAX_TILES

        if style:
            self.renderer = Renderer(style)

        if position is None and bounding_box is None:
            # Get player position from game state
            position = Position(0, 0)  # Default fallback
            player_data = self.game_state.get("player", {})
            if "position" in player_data:
                position = Position(player_data["position"]["x"], player_data["position"]["y"])

        # Ensure radius doesn't exceed max_tiles
        radius = min(radius, max_tiles)

        # Set up area to query
        if bounding_box:
            # Clip bounding box to max_tiles if needed
            if position:
                # Ensure the box doesn't exceed max_tiles from center_pos
                left = max(bounding_box.left_top.x, position.x - max_tiles)
                right = min(bounding_box.right_bottom.x, position.x + max_tiles)
                top = max(bounding_box.left_top.y, position.y - max_tiles)
                bottom = min(bounding_box.right_bottom.y, position.y + max_tiles)

                # Create a new clipped bounding box
                bounding_box = BoundingBox(
                    left_top=Position(left, top),
                    right_bottom=Position(right, bottom),
                    left_bottom=Position(left, bottom),
                    right_top=Position(right, top)
                )

            # Get entities within bounding box
            response, _ = self.execute(PLAYER, "bounding_box",
                                       bounding_box.left_top.x, bounding_box.left_top.y,
                                       bounding_box.right_bottom.x, bounding_box.right_bottom.y)
        else:
            # Ensure radius is within the max_tiles limit
            radius = min(radius, max_tiles)

            # Get water, resources, trees and rocks within radius of position
            response, _ = self.execute(PLAYER, "radius", position.x, position.y, radius)

        # Get entities within radius of position
        entities = self.get_entities(position=position, radius=radius)

        base_entities = []

        for entity in entities:
            if isinstance(entity, BeltGroup):
                base_entities.extend(entity.belts)
            elif isinstance(entity, PipeGroup):
                base_entities.extend(entity.pipes)
            elif isinstance(entity, ElectricityGroup):
                base_entities.extend(entity.poles)
            else:
                base_entities.append(entity)

        # Extract data from the response
        water_tiles = list(response.get('water_tiles', {}).values())
        resource_entities = list(response.get('resources', {}).values())
        trees = list(response.get('trees', {}).values())
        rocks = list(response.get('rocks', {}).values())
        electricity_networks = list(response.get('electricity_networks', {}).values())  # Extract electricity networks

        # Render the entities with all additional elements
        img = self.renderer.render_entities(
            base_entities,
            center_pos=position,
            bounding_box=bounding_box,
            water_tiles=water_tiles,
            resource_entities=resource_entities,
            trees=trees,
            rocks=rocks,
            electricity_networks=electricity_networks,  # Pass electricity networks to renderer
            max_tiles=max_tiles,
            layers=layers
        )

        return RenderedImage(img)

    def _process_nested_dict(self, nested_dict):
        """Helper method to process nested dictionaries"""
        if isinstance(nested_dict, dict):
            if all(isinstance(key, int) for key in nested_dict.keys()):
                return [self._process_nested_dict(value) for value in nested_dict.values()]
            else:
                return {key: self._process_nested_dict(value) for key, value in nested_dict.items()}
        return nested_dict