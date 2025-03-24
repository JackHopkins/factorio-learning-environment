from typing import List, Tuple, Optional, Dict, Callable

from entities import Entity, Position, BoundingBox
from render_config import RenderConfig


class ImageCalculator:
    """Handles calculations related to the image size and coordinate transforms"""

    def __init__(self, config: RenderConfig):
        self.config = config
        self.boundaries = {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}

    def calculate_boundaries(self, entities: List[Entity],
                             center_pos: Optional[Position] = None,
                             bounding_box: Optional[BoundingBox] = None) -> Dict:
        """
        Calculate the rendering boundaries based on entities, center position, or bounding box

        Returns:
            Dict containing min_x, max_x, min_y, max_y
        """
        if bounding_box:
            min_x, max_x = bounding_box.left_top.x, bounding_box.right_bottom.x
            min_y, max_y = bounding_box.left_top.y, bounding_box.right_bottom.y
        else:
            # Calculate boundaries from entities
            if not entities:
                # Default small area around center or origin
                if center_pos:
                    min_x, max_x = center_pos.x - 10, center_pos.x + 10
                    min_y, max_y = center_pos.y - 10, center_pos.y + 10
                else:
                    min_x, max_x = -10, 10
                    min_y, max_y = -10, 10
            else:
                positions = []
                for entity in entities:
                    pos = entity.position
                    width = entity.tile_dimensions.tile_width if hasattr(entity, "tile_dimensions") else 1
                    height = entity.tile_dimensions.tile_height if hasattr(entity, "tile_dimensions") else 1

                    # Add corners of entity to positions
                    positions.append((pos.x - width / 2, pos.y - height / 2))
                    positions.append((pos.x + width / 2, pos.y + height / 2))

                min_x = min(p[0] for p in positions) - 2
                max_x = max(p[0] for p in positions) + 2
                min_y = min(p[1] for p in positions) - 2
                max_y = max(p[1] for p in positions) + 2

                # If center_pos is provided, ensure it's in view
                if center_pos:
                    min_x = min(min_x, center_pos.x - 5)
                    max_x = max(max_x, center_pos.x + 5)
                    min_y = min(min_y, center_pos.y - 5)
                    max_y = max(max_y, center_pos.y + 5)

        self.boundaries = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y
        }

        return self.boundaries

    def calculate_image_dimensions(self, legend_dimensions: Optional[Dict] = None) -> Dict:
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
                img_width += legend_width + self.config.style["legend_padding"]
            elif legend_position.startswith("bottom"):
                img_height += legend_height + self.config.style["legend_padding"]

        return {
            "img_width": img_width,
            "img_height": img_height,
            "map_width": map_width,
            "map_height": map_height
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
            return (margin + (x - min_x) * cell_size,
                    margin + (y - min_y) * cell_size)

        return game_to_img