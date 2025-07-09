from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class WaterLayerRenderer(LayerRenderer):
    """Renderer for water tiles"""

    @property
    def layer_name(self) -> str:
        return "water"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw water tiles on the map"""
        water_tiles = kwargs.get("water_tiles", [])
        if not water_tiles:
            return

        # Water colors for different types
        water_colors = {
            "water": (0, 70, 140),  # Regular water
            "deepwater": (0, 50, 120),  # Deep water
            "water-shallow": (30, 90, 150),  # Shallow water
            "water-mud": (70, 80, 50),  # Mud water
        }

        cell_size = self.config.style["cell_size"]
        hatching_spacing = max(3, cell_size // 6)  # Space between hatch lines

        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]

        for tile in water_tiles:
            # Get tile position
            x, y = tile.get("x", 0), tile.get("y", 0)
            x += 0.5
            y += 0.5

            # Skip tiles outside the grid boundaries
            if x < min_x or x > max_x or y < min_y or y > max_y:
                continue

            tile_name = tile.get("name", "water")

            # Get color based on water type
            water_color = water_colors.get(tile_name, water_colors["water"])

            # Convert to image coordinates
            img_x, img_y = game_to_img_func(x, y)

            # Draw water tile background
            draw.rectangle(
                [
                    img_x - cell_size / 2,
                    img_y - cell_size / 2,
                    img_x + cell_size / 2,
                    img_y + cell_size / 2,
                ],
                fill=water_color,
                outline=None,
            )

            # Add cross-hatched pattern
            # First set of diagonal lines
            for i in range(-int(cell_size / 2), int(cell_size / 2), hatching_spacing):
                line_start_x = img_x - cell_size / 2
                line_start_y = img_y - cell_size / 2 + i
                line_end_x = img_x - cell_size / 2 + i + cell_size
                line_end_y = img_y - cell_size / 2

                # Only draw if endpoints are within tile bounds
                if (
                    line_end_x >= img_x - cell_size / 2
                    and line_start_y <= img_y + cell_size / 2
                ):
                    draw.line(
                        [
                            (line_start_x, line_start_y),
                            (
                                min(line_end_x, img_x + cell_size / 2),
                                max(line_end_y, img_y - cell_size / 2),
                            ),
                        ],
                        fill=(
                            min(water_color[0] + 30, 255),
                            min(water_color[1] + 30, 255),
                            min(water_color[2] + 40, 255),
                        ),
                        width=1,
                    )

            # Second set of diagonal lines (perpendicular to first set)
            for i in range(-int(cell_size / 2), int(cell_size / 2), hatching_spacing):
                line_start_x = img_x - cell_size / 2
                line_start_y = img_y + cell_size / 2 - i
                line_end_x = img_x - cell_size / 2 + i + cell_size
                line_end_y = img_y + cell_size / 2

                # Only draw if endpoints are within tile bounds
                if (
                    line_end_x >= img_x - cell_size / 2
                    and line_start_y >= img_y - cell_size / 2
                ):
                    draw.line(
                        [
                            (line_start_x, line_start_y),
                            (
                                min(line_end_x, img_x + cell_size / 2),
                                min(line_end_y, img_y + cell_size / 2),
                            ),
                        ],
                        fill=(
                            min(water_color[0] + 15, 255),
                            min(water_color[1] + 15, 255),
                            min(water_color[2] + 25, 255),
                        ),
                        width=1,
                    )
