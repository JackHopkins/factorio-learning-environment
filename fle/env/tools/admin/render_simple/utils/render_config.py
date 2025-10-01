from typing import Dict, Optional, Tuple, Any
from fle.env.entities import EntityStatus


class RenderConfig:
    """Manages configuration settings for Factorio entity rendering"""

    # Default style configuration
    DEFAULT_STYLE = {
        "background_color": (30, 30, 30),
        "grid_color": (60, 60, 60),
        "text_color": (255, 255, 255),
        "legend_bg_color": (40, 40, 40, 180),  # Semi-transparent background
        "legend_border_color": (100, 100, 100),
        "legend_position": "outside",  # Options: top_left, top_right, bottom_left, bottom_right, outside
        "legend_padding": 10,
        "legend_item_height": 15,
        "legend_item_spacing": 5,
        "legend_enabled": True,
        "legend_font_size": 10,  # Font size for legend text
        "legend_shape_size": 15,  # Size of shapes in the legend
        "cell_size": 20,  # pixels per game tile
        "margin": 10,  # pixels around the edge
        "grid_enabled": True,
        "direction_indicator_enabled": True,
        "status_indicator_enabled": True,
        "backing_rectangle_enabled": True,  # NEW: Whether to show backing rectangles for entities
        "backing_rectangle_opacity": 120,  # NEW: Opacity of backing rectangles (0-255)
        "backing_rectangle_lightness": 0.6,  # NEW: How much to lighten the backing rectangle color (0-1)
        "player_indicator_color": (255, 255, 0),
        "origin_marker_enabled": True,  # Show origin (0,0) marker
        "origin_marker_color": (255, 100, 100),  # Color for origin marker
        "origin_marker_size": 10,  # Size of origin marker
        "orient_shapes": True,  # Whether to rotate shapes based on entity direction
        "status_colors": {
            EntityStatus.WORKING: (0, 255, 0),
            EntityStatus.NORMAL: (255, 255, 255),
            EntityStatus.NO_POWER: (255, 100, 0),
            EntityStatus.LOW_POWER: (255, 180, 0),
            EntityStatus.NO_FUEL: (255, 0, 0),
            EntityStatus.EMPTY: (150, 150, 150),
            EntityStatus.NOT_CONNECTED: (255, 80, 80),
            EntityStatus.FULL_OUTPUT: (80, 180, 255),
            EntityStatus.NO_RECIPE: (200, 200, 50),
            EntityStatus.NO_INGREDIENTS: (255, 80, 0),
        },
        # Water and resource-related style settings
        "water_color": (0, 70, 140),  # Base water color
        "deepwater_color": (0, 50, 120),  # Deep water color
        "water_pattern_color": (30, 100, 170),  # Color for water pattern lines
        "resource_colors": {
            "iron-ore": (140, 140, 190),
            "copper-ore": (200, 100, 60),
            "coal": (50, 50, 50),
            "stone": (130, 130, 110),
            "uranium-ore": (50, 190, 50),
            "crude-oil": (20, 20, 20),
        },
        # Tree and rock related settings
        "tree_color": (20, 120, 20),  # Base green color for trees
        "tree_color_variations": [  # Different shades for tree variations
            (20, 100, 20),  # Darker green
            (40, 130, 40),  # Medium green
            (60, 150, 60),  # Lighter green
            (80, 150, 40),  # Yellow-green
            (100, 160, 60),  # Bright green
        ],
        "rock_color": (120, 110, 100),  # Base color for rocks
        "rock_color_variations": [  # Different shades for rock variations
            (100, 90, 80),  # Dark grey-brown
            (130, 120, 110),  # Medium grey
            (160, 150, 140),  # Light grey
            (140, 130, 100),  # Brownish grey
        ],
    }

    # Fixed colors for common entity categories
    CATEGORY_COLORS = {
        "resource": (100, 120, 160),  # Resources have blue-ish tint
        "belt": (255, 210, 0),  # Belts are yellow
        "inserter": (220, 140, 0),  # Inserters are orange
        "power": (180, 30, 180),  # Power-related entities are purple
        "fluid": (30, 100, 200),  # Fluid entities are blue
        "production": (180, 40, 40),  # Production entities are red
        "logistics": (40, 180, 40),  # Logistics entities are green
        "defense": (180, 80, 80),  # Defense entities are reddish
        "mining": (140, 100, 40),  # Mining entities are brown
        "origin": (255, 255, 0),  # Origin/player marker is yellow
        "water": (0, 70, 140),  # Water tiles
        "iron-ore": (140, 140, 190),  # Iron ore resource
        "copper-ore": (200, 100, 60),  # Copper ore resource
        "coal": (50, 50, 50),  # Coal resource
        "stone": (130, 130, 110),  # Stone resource
        "uranium-ore": (50, 190, 50),  # Uranium resource
        "crude-oil": (20, 20, 20),  # Oil resource
        "tree": (50, 150, 50),  # Trees
        "rock": (120, 110, 100),  # Rocks
    }

    # Shape mappings for different entity categories
    CATEGORY_SHAPES = {
        "resource": "circle",  # Resources are circles
        "belt": "triangle",  # Belts are triangles
        "inserter": "diamond",  # Inserters are diamonds
        "power": "rectangle",  # Power entities are pentagons
        "fluid": "triangle",  # Fluid entities are triangles
        "pipe": "circle",
        "production": "square",  # Production entities are squares
        "logistics": "octagon",  # Logistics are octagons
        "defense": "cross",  # Defense are crosses
        "mining": "star",  # Mining entities are stars
        "water": "square",  # Water tiles are squares with cross-hatch
        "iron-ore": "square",  # Iron ore is square
        "copper-ore": "square",  # Copper ore is square
        "coal": "diamond",  # Coal is diamond
        "stone": "diamond",  # Stone is diamond
        "uranium-ore": "circle",  # Uranium is circle with radiation symbol
        "crude-oil": "circle",  # Oil is circle with bubbles
        "tree": "circle",  # Trees are circles with special rendering
        "rock": "pentagon",  # Rocks are pentagons with rougher edges
    }

    def __init__(self, style: Optional[Dict[str, Any]] = None):
        """Initialize configuration with optional custom style"""
        self.style = self.DEFAULT_STYLE.copy()
        if style:
            self._update_nested_dict(self.style, style)

    def _update_nested_dict(self, d: Dict, u: Dict) -> None:
        """Recursively update a nested dictionary"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v

    def get_category_color(self, category: str) -> Tuple[int, int, int]:
        """Get the color for a category, with a default if not found"""
        return self.CATEGORY_COLORS.get(category, (200, 200, 200))

    def get_category_shape(self, category: str) -> str:
        """Get the shape for a category, with a default if not found"""
        return self.CATEGORY_SHAPES.get(category, "square")

    def get_status_color(self, status: EntityStatus) -> Tuple[int, int, int]:
        """Get the color for an entity status"""
        return self.style["status_colors"].get(
            status, (255, 0, 255)
        )  # Magenta for unknown status

    def get_resource_color(self, resource_name: str) -> Tuple[int, int, int]:
        """Get the color for a resource type"""
        return self.style["resource_colors"].get(
            resource_name, (150, 150, 150)
        )  # Gray for unknown resources

    def get_tree_color(self, tree_size: int = None) -> Tuple[int, int, int]:
        """Get a color for a tree, optionally based on its size/variation"""
        if tree_size is not None and 0 <= tree_size < len(
            self.style["tree_color_variations"]
        ):
            return self.style["tree_color_variations"][tree_size]
        return self.style["tree_color"]  # Default tree color

    def get_rock_color(self, rock_name: str = None) -> Tuple[int, int, int]:
        """Get a color for a rock, optionally based on its name"""
        # Use hash of rock name to get a consistent but varied color
        if rock_name:
            index = hash(rock_name) % len(self.style["rock_color_variations"])
            return self.style["rock_color_variations"][index]
        return self.style["rock_color"]  # Default rock color

    def get_backing_rectangle_color(
        self, shape_color: Tuple[int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Get the backing rectangle color based on the shape color"""
        if not self.style["backing_rectangle_enabled"]:
            return (0, 0, 0, 0)  # Fully transparent if disabled

        r, g, b = shape_color
        lightness = self.style["backing_rectangle_lightness"]
        opacity = self.style["backing_rectangle_opacity"]

        # Calculate a lighter, slightly desaturated version
        lighter_r = int(r + (255 - r) * lightness)
        lighter_g = int(g + (255 - g) * lightness)
        lighter_b = int(b + (255 - b) * lightness)

        return (lighter_r, lighter_g, lighter_b, opacity)
