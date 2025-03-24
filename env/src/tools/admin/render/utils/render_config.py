from typing import Dict, Optional, Tuple, Any
from entities import EntityStatus

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
        "cell_size": 20,  # pixels per game tile
        "margin": 10,  # pixels around the edge
        "grid_enabled": True,
        "direction_indicator_enabled": True,
        "status_indicator_enabled": True,
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
        }
    }

    # Fixed colors for common entity categories - moved from Renderer
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
    }

    # Shape mappings for different entity categories - moved from Renderer
    CATEGORY_SHAPES = {
        "resource": "circle",  # Resources are circles
        "belt": "triangle",  # Belts are triangles
        "inserter": "diamond",  # Inserters are diamonds
        "power": "rectangle",  # Power entities are pentagons
        "fluid": "triangle",  # Fluid entities are hexagons
        "production": "square",  # Production entities are squares
        "logistics": "octagon",  # Logistics are octagons
        "defense": "cross",  # Defense are crosses
        "mining": "star",  # Mining entities are stars
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
        return self.style["status_colors"].get(status, (255, 0, 255))  # Magenta for unknown status