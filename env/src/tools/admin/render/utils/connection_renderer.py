import math
from typing import Tuple, Callable
from PIL import ImageDraw

from entities import UndergroundBelt
from color_manager import ColorManager


class ConnectionRenderer:
    """Renders connections between related entities, like underground belts"""

    def __init__(self, color_manager: ColorManager):
        self.color_manager = color_manager

    def draw_underground_belt_connection(self, draw: ImageDraw.ImageDraw,
                                         entity: 'UndergroundBelt',
                                         game_to_img_func: Callable,
                                         color: Tuple[int, int, int]) -> None:
        """
        Draw a dotted line between connected Underground Belts

        Args:
            draw: ImageDraw object
            entity: The first UndergroundBelt entity
            game_to_img_func: Function to convert game coordinates to image coordinates
            color: Color to use for the connection line
        """
        # Ensure we have both entities
        if not entity:
            return

        # Get positions for both entities
        pos1 = entity.position
        pos2 = entity.output_position

        # Convert to image coordinates
        x1, y1 = game_to_img_func(pos1.x, pos1.y)
        x2, y2 = game_to_img_func(pos2.x, pos2.y)

        # Calculate distance
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Set properties for dotted line
        segments = max(int(distance / 6), 4)  # Ensure at least 4 segments
        dash_length = distance / segments * 0.6  # Make dashes 60% of segment length

        # Draw dotted line
        self.draw_dotted_line(draw, x1, y1, x2, y2, dash_length, color, width=2)

        # Draw small arrows to indicate direction in the middle of the line
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Calculate direction vector
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length

        # Draw small arrow
        arrow_size = 6
        end_x = mid_x + dx * arrow_size
        end_y = mid_y + dy * arrow_size

        # Draw arrow head
        draw.polygon([
            (end_x, end_y),
            (end_x - dx * arrow_size - dy * arrow_size / 2, end_y - dy * arrow_size + dx * arrow_size / 2),
            (end_x - dx * arrow_size + dy * arrow_size / 2, end_y - dy * arrow_size - dx * arrow_size / 2)
        ], fill=color)

    def draw_dotted_line(self, draw: ImageDraw.ImageDraw, x1: float, y1: float,
                         x2: float, y2: float, segment_length: float,
                         color: Tuple[int, int, int], width: int = 1) -> None:
        """
        Helper function to draw a dotted line between two points

        Args:
            draw: ImageDraw object
            x1, y1: Start point coordinates
            x2, y2: End point coordinates
            segment_length: Length of each dash
            color: Line color
            width: Line width
        """
        # Calculate line length and direction vector
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)

        # Normalize direction vector
        if length > 0:
            dx /= length
            dy /= length

        # Calculate number of segments
        num_segments = int(length / segment_length)
        if num_segments == 0:
            # If too short, just draw a normal line
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            return

        # Draw dashed line segments
        dash_length = segment_length * 0.6  # Make dashes 60% of segment length
        gap_length = segment_length * 0.4  # Make gaps 40% of segment length

        current_x, current_y = x1, y1

        for i in range(num_segments):
            # Calculate dash end point
            dash_end_x = current_x + dx * dash_length
            dash_end_y = current_y + dy * dash_length

            # Draw dash
            draw.line([(current_x, current_y), (dash_end_x, dash_end_y)],
                      fill=color, width=width)

            # Move to next dash start
            current_x = dash_end_x + dx * gap_length
            current_y = dash_end_y + dy * gap_length

            # Stop if we've reached the end
            if math.sqrt((current_x - x1) ** 2 + (current_y - y1) ** 2) >= length:
                break