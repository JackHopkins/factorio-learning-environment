from typing import List, Dict, Callable
from PIL import ImageDraw
import math

from fle.env.tools.admin.render.utils.render_config import RenderConfig


class TileRenderer:
    """Handles rendering of map tiles (water, land) on the Factorio map"""

    def __init__(self, config: RenderConfig):
        self.config = config

    def draw_water_tiles(
        self,
        draw: ImageDraw.ImageDraw,
        water_tiles: List[Dict],
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
    ) -> None:
        """
        Draw water tiles on the map with a cross-hatched pattern

        Args:
            draw: ImageDraw object
            water_tiles: List of water tile information
            game_to_img_func: Function to convert game coordinates to image coordinates
            boundaries: Dictionary with min_x, max_x, min_y, max_y values defining render area
        """
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

    def draw_resource_entities(
        self,
        draw: ImageDraw.ImageDraw,
        resources: List[Dict],
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
    ) -> None:
        """
        Draw resource entities (ore patches) on the map

        Args:
            draw: ImageDraw object
            resources: List of resource entity information
            game_to_img_func: Function to convert game coordinates to image coordinates
            boundaries: Dictionary with min_x, max_x, min_y, max_y values defining render area
        """
        if not resources:
            return

        # Define colors for different resource types
        resource_colors = {
            "iron-ore": (140, 140, 190),
            "copper-ore": (200, 100, 60),
            "coal": (50, 50, 50),
            "stone": (130, 130, 110),
            "uranium-ore": (50, 190, 50),
            "crude-oil": (20, 20, 20),
        }

        cell_size = self.config.style["cell_size"]

        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]

        for resource in resources:
            # Get resource position and type
            x, y = (
                resource.get("position", {}).get("x", 0),
                resource.get("position", {}).get("y", 0),
            )

            # Skip resources outside the grid boundaries
            if x < min_x or x > max_x or y < min_y or y > max_y:
                continue

            resource_name = resource.get("name", "unknown")
            amount = resource.get("amount", 0)

            # Get color based on resource type
            resource_color = resource_colors.get(resource_name, (150, 150, 150))

            # Convert to image coordinates
            img_x, img_y = game_to_img_func(x, y)

            # Adjust color based on amount (richer resources are more vibrant)
            color_intensity = min(1.0, amount / 5000)  # Normalize amount
            adjusted_color = tuple(
                int(c * (0.6 + 0.4 * color_intensity)) for c in resource_color
            )

            # Draw different shapes based on resource type
            if resource_name == "crude-oil":
                # Oil is a circle
                radius = cell_size / 3
                draw.ellipse(
                    [img_x - radius, img_y - radius, img_x + radius, img_y + radius],
                    fill=adjusted_color,
                    outline=(0, 0, 0),
                )
                # Add oil "bubbles"
                small_radius = radius / 4
                offsets = [
                    (radius / 2, 0),
                    (0, radius / 2),
                    (-radius / 2, 0),
                    (0, -radius / 2),
                ]
                for dx, dy in offsets:
                    draw.ellipse(
                        [
                            img_x + dx - small_radius,
                            img_y + dy - small_radius,
                            img_x + dx + small_radius,
                            img_y + dy + small_radius,
                        ],
                        fill=(
                            min(adjusted_color[0] + 40, 255),
                            min(adjusted_color[1] + 40, 255),
                            min(adjusted_color[2] + 40, 255),
                        ),
                        outline=None,
                    )
            else:
                # Other resources are drawn as small squares or diamonds
                size = cell_size / 3.5

                if resource_name in ["iron-ore", "copper-ore"]:
                    # Square for iron and copper
                    draw.rectangle(
                        [img_x - size, img_y - size, img_x + size, img_y + size],
                        fill=adjusted_color,
                        outline=(0, 0, 0),
                    )

                    # Add small texture dots
                    dot_size = size / 4
                    dot_color = (
                        min(adjusted_color[0] + 30, 255),
                        min(adjusted_color[1] + 30, 255),
                        min(adjusted_color[2] + 30, 255),
                    )

                    dot_positions = [
                        (img_x - size / 2, img_y - size / 2),
                        (img_x + size / 2, img_y - size / 2),
                        (img_x, img_y),
                        (img_x - size / 2, img_y + size / 2),
                        (img_x + size / 2, img_y + size / 2),
                    ]

                    for dot_x, dot_y in dot_positions:
                        draw.ellipse(
                            [
                                dot_x - dot_size,
                                dot_y - dot_size,
                                dot_x + dot_size,
                                dot_y + dot_size,
                            ],
                            fill=dot_color,
                            outline=None,
                        )

                elif resource_name in ["coal", "stone"]:
                    # Diamond for coal and stone
                    draw.polygon(
                        [
                            (img_x, img_y - size),  # Top
                            (img_x + size, img_y),  # Right
                            (img_x, img_y + size),  # Bottom
                            (img_x - size, img_y),
                        ],  # Left
                        fill=adjusted_color,
                        outline=(0, 0, 0),
                    )

                elif resource_name == "uranium-ore":
                    # Radioactive symbol for uranium
                    draw.ellipse(
                        [img_x - size, img_y - size, img_x + size, img_y + size],
                        fill=adjusted_color,
                        outline=(0, 0, 0),
                    )

                    # Draw radiation symbol inside
                    inner_radius = size * 0.5
                    draw.ellipse(
                        [
                            img_x - inner_radius,
                            img_y - inner_radius,
                            img_x + inner_radius,
                            img_y + inner_radius,
                        ],
                        fill=(0, 0, 0),
                        outline=None,
                    )

                    # Radiation "blades"
                    blade_length = size * 0.8
                    for angle in [0, 2.0944, 4.18879]:  # 0, 120, 240 degrees
                        end_x = img_x + blade_length * math.cos(angle)
                        end_y = img_y + blade_length * math.sin(angle)
                        mid_x = img_x + inner_radius * math.cos(angle)
                        mid_y = img_y + inner_radius * math.sin(angle)

                        draw.polygon(
                            [(img_x, img_y), (mid_x, mid_y), (end_x, end_y)],
                            fill=adjusted_color,
                            outline=None,
                        )
                else:
                    # Default shape (hexagon)
                    points = []
                    for i in range(6):
                        angle = i * 2 * 3.14159 / 6
                        px = img_x + size * math.cos(angle)
                        py = img_y + size * math.sin(angle)
                        points.append((px, py))

                    draw.polygon(points, fill=adjusted_color, outline=(0, 0, 0))
