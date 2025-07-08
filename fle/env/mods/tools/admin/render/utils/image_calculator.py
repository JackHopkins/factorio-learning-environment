from typing import List, Optional, Dict, Callable

from fle.env.entities import Entity, Position, BoundingBox, Direction
from fle.env.tools.admin.render.utils.render_config import RenderConfig


class ImageCalculator:
    """Handles calculations related to the image size and coordinate transforms"""

    def __init__(self, config: RenderConfig):
        self.config = config
        self.boundaries = {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}

    def calculate_boundaries(
        self,
        entities: List[Entity],
        center_pos: Optional[Position] = None,
        bounding_box: Optional[BoundingBox] = None,
        max_tiles: int = 50,
    ) -> Dict:
        """
        Calculate the rendering boundaries based on entities, center position, or bounding box

        Args:
            entities: List of entities to consider for boundary calculation
            center_pos: Optional center position (e.g. player position)
            bounding_box: Optional bounding box to constrain the render area
            max_tiles: Maximum number of tiles to render on each side of the position (default: 50)

        Returns:
            Dict containing min_x, max_x, min_y, max_y
        """
        # If center_pos is provided, we'll ensure the grid is exactly centered on it
        if center_pos:
            # Create a perfectly centered grid around the position
            min_x = center_pos.x - max_tiles
            max_x = center_pos.x + max_tiles
            min_y = center_pos.y - max_tiles
            max_y = center_pos.y + max_tiles

            # If a bounding box was provided, we'll intersect it with our centered grid
            if bounding_box:
                min_x = max(min_x, bounding_box.left_top.x)
                max_x = min(max_x, bounding_box.right_bottom.x)
                min_y = max(min_y, bounding_box.left_top.y)
                max_y = min(max_y, bounding_box.right_bottom.y)
        elif bounding_box:
            # No center_pos but we have a bounding_box
            min_x, max_x = bounding_box.left_top.x, bounding_box.right_bottom.x
            min_y, max_y = bounding_box.left_top.y, bounding_box.right_bottom.y
        else:
            # No center_pos and no bounding_box
            if not entities:
                # Default area around origin
                min_x, max_x = -10, 10
                min_y, max_y = -10, 10
            else:
                # Calculate boundaries from entities
                positions = []
                for entity in entities:
                    pos = entity.position
                    width = (
                        entity.tile_dimensions.tile_width
                        if hasattr(entity, "tile_dimensions")
                        else 1
                    )
                    height = (
                        entity.tile_dimensions.tile_height
                        if hasattr(entity, "tile_dimensions")
                        else 1
                    )

                    if entity.direction.value in (
                        Direction.LEFT.value,
                        Direction.RIGHT.value,
                    ):
                        width1 = width
                        width = height
                        height = width1

                    # Add corners of entity to positions
                    positions.append((pos.x - width / 2, pos.y - height / 2))
                    positions.append((pos.x + width / 2, pos.y + height / 2))

                min_x = min(p[0] for p in positions) - 2
                max_x = max(p[0] for p in positions) + 2
                min_y = min(p[1] for p in positions) - 2
                max_y = max(p[1] for p in positions) + 2

                # Without a center position, ensure we don't exceed max_tiles from origin
                min_x = max(min_x, -max_tiles)
                max_x = min(max_x, max_tiles)
                min_y = max(min_y, -max_tiles)
                max_y = min(max_y, max_tiles)

        # Make the boundaries nice integers
        min_x = int(min_x)
        max_x = int(max_x) + 1
        min_y = int(min_y)
        max_y = int(max_y) + 1

        self.boundaries = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
        }

        return self.boundaries

    def calculate_image_dimensions(
        self, legend_dimensions: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate the final image dimensions based on map size and legend

        Args:
            legend_dimensions: Optional dictionary with legend width, height, and position

        Returns:
            Dictionary with image dimensions and map area dimensions
        """
        width_tiles = self.boundaries["max_x"] - self.boundaries["min_x"]
        height_tiles = self.boundaries["max_y"] - self.boundaries["min_y"]

        cell_size = self.config.style["cell_size"]
        margin = self.config.style["margin"]

        map_width = int(width_tiles * cell_size + 2 * margin)
        map_height = int(height_tiles * cell_size + 2 * margin)

        # Start with map dimensions
        img_width = map_width
        img_height = map_height

        # Add space for legend if needed
        if legend_dimensions:
            legend_width = legend_dimensions["width"]
            legend_height = legend_dimensions["height"]
            legend_position = legend_dimensions["position"]

            if legend_position.startswith("right"):
                img_width += legend_width
            elif legend_position.startswith("bottom"):
                img_height += legend_height

        return {
            "img_width": img_width,
            "img_height": img_height,
            "map_width": map_width,
            "map_height": map_height,
        }

    def get_game_to_image_coordinate_function(self) -> Callable:
        """
        Returns a function that converts game coordinates to image coordinates

        Returns:
            Function that takes game x,y and returns image x,y
        """
        min_x = self.boundaries["min_x"]
        min_y = self.boundaries["min_y"]
        margin = self.config.style["margin"]
        cell_size = self.config.style["cell_size"]

        def game_to_img(x, y):
            return (margin + (x - min_x) * cell_size, margin + (y - min_y) * cell_size)

        return game_to_img
