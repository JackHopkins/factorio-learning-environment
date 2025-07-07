from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class GridLayerRenderer(LayerRenderer):
    """Renderer for the grid layer"""

    @property
    def layer_name(self) -> str:
        return "grid"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw the background grid"""
        if not self.config.style["grid_enabled"]:
            return

        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]
        margin = self.config.style["margin"]
        cell_size = self.config.style["cell_size"]

        # Calculate image dimensions based on map area
        width_tiles = max_x - min_x
        height_tiles = max_y - min_y
        img_width = int(width_tiles * cell_size + 2 * margin)
        img_height = int(height_tiles * cell_size + 2 * margin)

        # Draw vertical grid lines
        for x in range(int(min_x), int(max_x) + 1):
            grid_x = margin + (x - min_x) * cell_size
            draw.line(
                [(grid_x, margin), (grid_x, img_height - margin)],
                fill=self.config.style["grid_color"],
            )

        # Draw horizontal grid lines
        for y in range(int(min_y), int(max_y) + 1):
            grid_y = margin + (y - min_y) * cell_size
            draw.line(
                [(margin, grid_y), (img_width - margin, grid_y)],
                fill=self.config.style["grid_color"],
            )
