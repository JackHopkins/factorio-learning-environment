"""Direction utilities for VQA tasks."""

import enum
from typing import Union, Optional


class Direction(enum.Enum):
    """Direction enum matching Factorio's internal direction system."""
    
    UP = NORTH = 0
    RIGHT = EAST = 2
    DOWN = SOUTH = 4
    LEFT = WEST = 6

    @classmethod
    def opposite(cls, direction: 'Direction') -> 'Direction':
        """Get the opposite direction."""
        return cls((direction.value + 4) % 8)

    @classmethod
    def next_clockwise(cls, direction: 'Direction') -> 'Direction':
        """Get the next direction clockwise."""
        return cls((direction.value + 2) % 8)

    @classmethod
    def next_counterclockwise(cls, direction: 'Direction') -> 'Direction':
        """Get the next direction counterclockwise."""
        return cls((direction.value - 2) % 8)

    @classmethod
    def to_factorio_direction(cls, direction: 'Direction') -> int:
        """Convert to Factorio's numeric direction (0-3)."""
        return direction.value // 2

    @classmethod
    def from_factorio_direction(cls, direction: int) -> 'Direction':
        """Convert from Factorio's numeric direction (0-3) to enum."""
        return cls(direction * 2)
    
    @classmethod
    def from_value(cls, value: Union[int, str]) -> Optional['Direction']:
        """Convert a value (int or string) to Direction enum."""
        if isinstance(value, int):
            # Handle both full values (0,2,4,6) and Factorio values (0,1,2,3)
            if value in [0, 2, 4, 6]:
                return cls(value)
            elif value in [0, 1, 2, 3]:
                return cls.from_factorio_direction(value)
        elif isinstance(value, str):
            # Handle string names
            value_upper = value.upper()
            for direction in cls:
                if direction.name == value_upper:
                    return direction
        return None
    
    def to_compass_string(self) -> str:
        """Get lowercase compass direction string."""
        if self == Direction.NORTH:
            return "north"
        elif self == Direction.EAST:
            return "east"
        elif self == Direction.SOUTH:
            return "south"
        elif self == Direction.WEST:
            return "west"
    
    def to_relative_string(self) -> str:
        """Get relative direction string."""
        if self == Direction.UP:
            return "up"
        elif self == Direction.RIGHT:
            return "right"
        elif self == Direction.DOWN:
            return "down"
        elif self == Direction.LEFT:
            return "left"


def convert_numeric_direction(direction_value: Union[int, float, str]) -> str:
    """
    Convert numeric direction to compass string.
    
    Args:
        direction_value: Numeric direction (0,2,4,6) or string
        
    Returns:
        Compass direction string (north/east/south/west)
    """
    if isinstance(direction_value, (int, float)):
        direction = Direction.from_value(int(direction_value))
        if direction:
            return direction.to_compass_string()
    return str(direction_value)


def format_direction_in_text(text: str) -> str:
    """
    Replace numeric directions in text with compass directions.
    
    Args:
        text: Text containing direction references
        
    Returns:
        Text with compass directions
    """
    import re
    
    # Pattern to match direction references
    patterns = [
        (r'\bdirection\s*=?\s*(\d)', 'direction_equals'),
        (r'\bfacing\s+(\d)', 'facing'),
        (r'\bdirection\s+(\d)', 'direction'),
    ]
    
    result = text
    for pattern, pattern_type in patterns:
        matches = list(re.finditer(pattern, result, re.IGNORECASE))
        
        # Process matches in reverse to preserve positions
        for match in reversed(matches):
            dir_value = int(match.group(1))
            direction = Direction.from_value(dir_value)
            
            if direction:
                compass = direction.to_compass_string()
                if pattern_type == 'direction_equals':
                    replacement = f'facing {compass}'
                elif pattern_type == 'facing':
                    replacement = f'facing {compass}'
                else:
                    replacement = f'facing {compass}'
                
                result = result[:match.start()] + replacement + result[match.end():]
    
    return result