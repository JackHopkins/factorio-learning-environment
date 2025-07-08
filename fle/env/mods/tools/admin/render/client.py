from typing import Optional, Dict
import math

from fle.env import BoundingBox, Position, BeltGroup, PipeGroup, ElectricityGroup, Layer
from fle.env.tools.admin.render.rendered_image import RenderedImage
from fle.env.tools.admin.render.renderer import Renderer
from fle.env.tools.agent.get_entities.client import GetEntities
from fle.env.tools import Tool

MAX_TILES = (
    20  # Don't parameterise this, as the agent could break if it chooses a huge grid.
)


class Render(Tool):
    """Render tool for visualizing Factorio entities"""

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.renderer = Renderer()
        self.get_entities = GetEntities(connection, game_state)

    def __call__(
        self,
        position: Optional[Position] = None,
        bounding_box: Optional[BoundingBox] = None,
        style: Optional[Dict] = None,
        layers: Optional[Layer] = Layer.ALL,
        zoom: float = 1.0,
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
            zoom: Zoom factor for rendering (default: 1.0) - values > 1 zoom in (fewer tiles visible),
                  values < 1 zoom out (more tiles visible)

        Returns:
            RenderedImage: An image object that can be displayed or saved
        """
        radius: int = MAX_TILES
        max_tiles: int = MAX_TILES

        # Apply minimum and maximum bounds to prevent issues with very small or very large zoom values
        MIN_TILES = 2  # Prevent zooming in too much (minimum tiles to show)
        MAX_ZOOM_TILES = 100  # Prevent zooming out too much (maximum tiles to show)

        # Cap the maximum resolution/dimensions of the final image
        MAX_IMAGE_RESOLUTION = 4000  # Maximum pixels in either dimension
        MAX_TOTAL_TILES = (
            8000  # Maximum total tiles (width * height) to prevent memory issues
        )

        # Apply style if provided
        custom_style = {}
        if style:
            custom_style.update(style)

        # Create new renderer with the custom style if any
        if custom_style:
            self.renderer = Renderer(custom_style)

        # Apply zoom by adjusting max_tiles (number of tiles displayed)
        if zoom != 1.0:
            # Adjust the number of tiles displayed based on zoom
            # Zoom in (> 1.0) = fewer tiles displayed (divide by zoom)
            # Zoom out (< 1.0) = more tiles displayed (divide by zoom)
            max_tiles = int(MAX_TILES / zoom)
            radius = max_tiles  # Update radius as well to keep consistent

            # Apply bounds to ensure reasonable limits
            max_tiles = max(MIN_TILES, min(max_tiles, MAX_ZOOM_TILES))
            radius = max_tiles  # Match radius to max_tiles

        # Cap max_tiles to ensure the total image size doesn't exceed maximum resolution
        # Calculate estimated pixels per tile including margins
        estimated_pixels_per_tile = self.renderer.config.style["cell_size"]

        # Calculate maximum tiles in each dimension based on MAX_IMAGE_RESOLUTION
        max_tiles_per_dimension = MAX_IMAGE_RESOLUTION // estimated_pixels_per_tile

        # Ensure max_tiles doesn't exceed the resolution limit
        max_tiles = min(max_tiles, max_tiles_per_dimension)
        radius = min(radius, max_tiles_per_dimension)

        # Ensure total tiles (width * height) doesn't exceed MAX_TOTAL_TILES
        # A square of max_tiles*2 x max_tiles*2 would have 4*max_tiles^2 total tiles
        # We want this to be <= MAX_TOTAL_TILES
        max_tiles_from_total = int(math.sqrt(MAX_TOTAL_TILES / 4))
        max_tiles = min(max_tiles, max_tiles_from_total)
        radius = min(radius, max_tiles_from_total)

        if position is None and bounding_box is None:
            # Get player position from game state
            position = Position(0, 0)  # Default fallback
            player_data = self.game_state.get("player", {})
            if "position" in player_data:
                position = Position(
                    player_data["position"]["x"], player_data["position"]["y"]
                )

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
                    right_top=Position(right, top),
                )

            # Get entities within bounding box
            response, _ = self.execute(
                self.player_index,
                "bounding_box",
                bounding_box.left_top.x,
                bounding_box.left_top.y,
                bounding_box.right_bottom.x,
                bounding_box.right_bottom.y,
            )
        else:
            # Ensure radius is within the max_tiles limit
            radius = min(radius, max_tiles)

            # Get water, resources, trees and rocks within radius of position
            response, _ = self.execute(
                self.player_index, "radius", position.x, position.y, radius
            )

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
        water_tiles = list(response.get("water_tiles", {}).values())
        resource_entities = list(response.get("resources", {}).values())
        trees = list(response.get("trees", {}).values())
        rocks = list(response.get("rocks", {}).values())
        electricity_networks = list(
            response.get("electricity_networks", {}).values()
        )  # Extract electricity networks

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
            layers=layers,
        )

        return RenderedImage(img)

    def _process_nested_dict(self, nested_dict):
        """Helper method to process nested dictionaries"""
        if isinstance(nested_dict, dict):
            if all(isinstance(key, int) for key in nested_dict.keys()):
                return [
                    self._process_nested_dict(value) for value in nested_dict.values()
                ]
            else:
                return {
                    key: self._process_nested_dict(value)
                    for key, value in nested_dict.items()
                }
        return nested_dict
