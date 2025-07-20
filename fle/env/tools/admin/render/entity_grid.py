"""Entity grid view for relative position lookups."""

from typing import Dict, Optional


class EntityGridView:
    """View into the entity grid for relative lookups."""

    def __init__(self, grid: Dict, center_x: float, center_y: float, available_trees: Optional[Dict] = None):
        """Initialize grid view with center position.
        
        Args:
            grid: Entity position grid
            center_x: X coordinate of center position
            center_y: Y coordinate of center position  
            available_trees: Optional dict of available tree sprites
        """
        self.grid = grid
        self.center_x = center_x
        self.center_y = center_y
        self.available_trees = available_trees or {}

    def get_relative(self, relative_x: float, relative_y: float) -> Optional[Dict]:
        """Get entity at relative position from center.
        
        Args:
            relative_x: X offset from center
            relative_y: Y offset from center
            
        Returns:
            Entity dict if found, None otherwise
        """
        x = self.center_x + relative_x
        y = self.center_y + relative_y

        if x not in self.grid:
            return None
        return self.grid[x].get(y)

    def set_center(self, center_x: float, center_y: float) -> None:
        """Update center position.
        
        Args:
            center_x: New X coordinate for center
            center_y: New Y coordinate for center
        """
        self.center_x = center_x
        self.center_y = center_y