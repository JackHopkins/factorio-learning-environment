import math
import random
from typing import Dict, Callable, List
from PIL import ImageDraw

from fle.env.entities import Layer
from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class NaturalLayerRenderer(LayerRenderer):
    """Renderer for natural elements (trees and rocks)"""

    @property
    def layer_name(self) -> str:
        return "natural"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw natural elements (trees and rocks) on the map"""
        requested_layers = kwargs.get("layers", Layer.ALL)

        # Draw rocks if requested
        if Layer.ROCKS in requested_layers:
            rocks = kwargs.get("rocks", [])
            if rocks:
                self._draw_rocks(draw, rocks, game_to_img_func, boundaries)

        # Draw trees if requested
        if Layer.TREES in requested_layers:
            trees = kwargs.get("trees", [])
            if trees:
                self._draw_trees(draw, trees, game_to_img_func, boundaries)

    def _draw_trees(
        self,
        draw: ImageDraw.ImageDraw,
        trees: List[Dict],
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
    ) -> None:
        """Draw trees on the map with natural variations"""
        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]
        cell_size = self.config.style["cell_size"]

        # Set a fixed seed for random to ensure consistent rendering of trees
        random.seed(42)

        for tree in trees:
            # Get tree position
            x, y = (
                tree.get("position", {}).get("x", 0),
                tree.get("position", {}).get("y", 0),
            )

            # Skip trees outside the grid boundaries
            if x < min_x or x > max_x or y < min_y or y > max_y:
                continue

            # Get tree name and size if available
            tree_name = tree.get("name", "")
            tree_size = tree.get(
                "size", hash(tree_name) % 5
            )  # Use hash of name if size not provided

            # Convert to image coordinates
            img_x, img_y = game_to_img_func(x, y)

            # Get tree color based on size/variation
            tree_color = self._get_tree_color(tree_size)

            # Draw tree based on type
            if "dead" in tree_name.lower():
                self._draw_dead_tree(draw, img_x, img_y, cell_size, tree_color)
            else:
                self._draw_living_tree(
                    draw, img_x, img_y, cell_size, tree_color, tree_name
                )

        # Reset random seed
        random.seed()

    def _draw_living_tree(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        cell_size: float,
        color: tuple,
        tree_name: str,
    ) -> None:
        """Draw a living tree with foliage"""
        # Use hash of tree name to get consistent random variations for each tree
        seed = hash(tree_name)
        random.seed(seed)

        # Trunk
        trunk_width = cell_size / 6
        trunk_height = cell_size / 3
        trunk_color = (101, 67, 33)  # Brown

        # Slightly randomize trunk position
        offset_x = random.uniform(-cell_size / 10, cell_size / 10)

        draw.rectangle(
            [
                x - trunk_width / 2 + offset_x,
                y - trunk_height / 2 + trunk_height / 2,
                x + trunk_width / 2 + offset_x,
                y + trunk_height / 2 + trunk_height / 2,
            ],
            fill=trunk_color,
            outline=None,
        )

        # Foliage (multi-layered to give depth)
        foliage_radius = cell_size / 3

        # Draw several overlapping circles with slight variations in color and position
        for i in range(3):
            # Vary position slightly for each layer
            fx_offset = random.uniform(-cell_size / 12, cell_size / 12)
            fy_offset = random.uniform(-cell_size / 12, 0)  # More variation at top

            # Vary color slightly for each layer
            r, g, b = color
            r_var = max(0, min(255, r + random.randint(-15, 15)))
            g_var = max(0, min(255, g + random.randint(-15, 15)))
            b_var = max(0, min(255, b + random.randint(-15, 10)))
            foliage_color = (r_var, g_var, b_var)

            # Each layer gets slightly smaller
            layer_radius = foliage_radius * (1.0 - i * 0.2)

            draw.ellipse(
                [
                    x - layer_radius + fx_offset,
                    y - layer_radius - trunk_height / 2 + fy_offset,
                    x + layer_radius + fx_offset,
                    y + layer_radius - trunk_height / 2 + fy_offset,
                ],
                fill=foliage_color,
                outline=None,
            )

    def _draw_dead_tree(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        cell_size: float,
        color: tuple,
    ) -> None:
        """Draw a dead tree (just trunk and branches)"""
        # Trunk
        trunk_width = cell_size / 6
        trunk_height = cell_size / 2
        trunk_color = (120, 100, 80)  # Grayish brown

        draw.rectangle(
            [
                x - trunk_width / 2,
                y - trunk_height / 2,
                x + trunk_width / 2,
                y + trunk_height / 2,
            ],
            fill=trunk_color,
            outline=None,
        )

        # Branches (simple lines)
        branch_color = (100, 90, 70)  # Slightly darker

        # Right branch
        branch_angle = random.uniform(math.pi / 6, math.pi / 3)  # 30-60 degrees
        branch_length = cell_size / 3
        end_x = x + math.cos(branch_angle) * branch_length
        end_y = y - math.sin(branch_angle) * branch_length

        draw.line(
            [(x, y - trunk_height / 4), (end_x, end_y)],
            fill=branch_color,
            width=int(trunk_width / 2),
        )

        # Left branch
        branch_angle = random.uniform(
            2 * math.pi / 3, 5 * math.pi / 6
        )  # 120-150 degrees
        end_x = x + math.cos(branch_angle) * branch_length
        end_y = y - math.sin(branch_angle) * branch_length

        draw.line(
            [(x, y - trunk_height / 4), (end_x, end_y)],
            fill=branch_color,
            width=int(trunk_width / 2),
        )

    def _draw_rocks(
        self,
        draw: ImageDraw.ImageDraw,
        rocks: List[Dict],
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
    ) -> None:
        """Draw rocks on the map with natural variations"""
        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]
        cell_size = self.config.style["cell_size"]

        # Set a fixed seed for random to ensure consistent rendering of rocks
        random.seed(42)

        for rock in rocks:
            # Get rock position
            x, y = (
                rock.get("position", {}).get("x", 0),
                rock.get("position", {}).get("y", 0),
            )

            # Skip rocks outside the grid boundaries
            if x < min_x or x > max_x or y < min_y or y > max_y:
                continue

            # Get rock name
            rock_name = rock.get("name", "")

            # Convert to image coordinates
            img_x, img_y = game_to_img_func(x, y)

            # Get rock color based on name
            rock_color = self._get_rock_color(rock_name)

            # Draw the rock
            self._draw_rock(draw, img_x, img_y, cell_size, rock_color, rock_name)

        # Reset random seed
        random.seed()

    def _draw_rock(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        cell_size: float,
        color: tuple,
        rock_name: str,
    ) -> None:
        """Draw a rock with natural variations"""
        # Use hash of rock name to get consistent random variations for each rock
        seed = hash(rock_name)
        random.seed(seed)

        # Determine rock size based on name
        if "huge" in rock_name.lower():
            size_factor = 0.7
        elif "big" in rock_name.lower():
            size_factor = 0.6
        elif "small" in rock_name.lower():
            size_factor = 0.4
        else:
            size_factor = 0.5

        rock_radius = cell_size * size_factor / 2

        # Create an irregular polygon for the rock
        num_points = random.randint(6, 10)
        points = []

        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            # Vary the radius slightly for each point
            point_radius = rock_radius * random.uniform(0.8, 1.2)
            px = x + math.cos(angle) * point_radius
            py = y + math.sin(angle) * point_radius
            points.append((px, py))

        # Draw the rock
        draw.polygon(
            points,
            fill=color,
            outline=(
                min(color[0] - 30, 255),
                min(color[1] - 30, 255),
                min(color[2] - 30, 255),
            ),
        )

        # Add some texture with small lines or dots
        for _ in range(3):
            tx = x + random.uniform(-rock_radius / 2, rock_radius / 2)
            ty = y + random.uniform(-rock_radius / 2, rock_radius / 2)
            tx2 = tx + random.uniform(-rock_radius / 4, rock_radius / 4)
            ty2 = ty + random.uniform(-rock_radius / 4, rock_radius / 4)

            # Slightly darker color for texture
            texture_color = (
                max(0, color[0] - 20),
                max(0, color[1] - 20),
                max(0, color[2] - 20),
            )

            draw.line([(tx, ty), (tx2, ty2)], fill=texture_color, width=1)

    def _get_tree_color(self, tree_size: int = None) -> tuple:
        """Get a color for a tree, optionally based on its size/variation"""
        tree_color_variations = [
            (20, 100, 20),  # Darker green
            (40, 130, 40),  # Medium green
            (60, 150, 60),  # Lighter green
            (80, 150, 40),  # Yellow-green
            (100, 160, 60),  # Bright green
        ]

        if tree_size is not None and 0 <= tree_size < len(tree_color_variations):
            return tree_color_variations[tree_size]
        return (50, 150, 50)  # Default tree color

    def _get_rock_color(self, rock_name: str = None) -> tuple:
        """Get a color for a rock, optionally based on its name"""
        rock_color_variations = [
            (100, 90, 80),  # Dark grey-brown
            (130, 120, 110),  # Medium grey
            (160, 150, 140),  # Light grey
            (140, 130, 100),  # Brownish grey
        ]

        # Use hash of rock name to get a consistent but varied color
        if rock_name:
            index = hash(rock_name) % len(rock_color_variations)
            return rock_color_variations[index]
        return (120, 110, 100)  # Default rock color
