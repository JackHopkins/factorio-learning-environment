import math
from typing import Tuple, Callable, List

from PIL import ImageDraw
from fle.env import UndergroundBelt, Pipe
from fle.env.tools.admin.render.utils.colour_manager import ColourManager


class ConnectionRenderer:
    """Renders connections between related entities, like underground belts and pipes"""

    def __init__(self, color_manager: ColourManager):
        self.color_manager = color_manager

    def draw_underground_belt_connection(
        self,
        draw: ImageDraw.ImageDraw,
        entity: "UndergroundBelt",
        game_to_img_func: Callable,
        color: Tuple[int, int, int],
    ) -> None:
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
        draw.polygon(
            [
                (end_x, end_y),
                (
                    end_x - dx * arrow_size - dy * arrow_size / 2,
                    end_y - dy * arrow_size + dx * arrow_size / 2,
                ),
                (
                    end_x - dx * arrow_size + dy * arrow_size / 2,
                    end_y - dy * arrow_size - dx * arrow_size / 2,
                ),
            ],
            fill=color,
        )

    def draw_underground_pipe_connection(
        self,
        draw: ImageDraw.ImageDraw,
        input_pipe: "Pipe",
        output_pipe: "Pipe",
        game_to_img_func: Callable,
        color: Tuple[int, int, int],
    ) -> None:
        """
        Draw a dotted line between connected Underground Pipes

        Args:
            draw: ImageDraw object
            input_pipe: The input underground pipe entity
            output_pipe: The output underground pipe entity
            game_to_img_func: Function to convert game coordinates to image coordinates
            color: Color to use for the connection line
        """
        # Ensure we have both entities
        if not input_pipe or not output_pipe:
            return

        # Get positions for both entities
        pos1 = input_pipe.position
        pos2 = output_pipe.position

        # Convert to image coordinates
        x1, y1 = game_to_img_func(pos1.x, pos1.y)
        x2, y2 = game_to_img_func(pos2.x, pos2.y)

        # Calculate distance
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Set properties for dotted line
        segments = max(int(distance / 6), 4)  # Ensure at least 4 segments
        dash_length = distance / segments * 0.6  # Make dashes 60% of segment length

        # Draw dotted line with different pattern for pipes
        self.draw_dotted_line(
            draw, x1, y1, x2, y2, dash_length, color, width=2, pattern=[4, 2]
        )

        # Draw small fluid flow indicator in the middle of the line
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Calculate direction vector
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length

        # Draw small fluid flow indicator (circular with direction)
        flow_size = 4
        draw.ellipse(
            [
                mid_x - flow_size,
                mid_y - flow_size,
                mid_x + flow_size,
                mid_y + flow_size,
            ],
            fill=color,
            outline=(255, 255, 255),
        )

        # Draw flow direction indicator (small arrow)
        end_x = mid_x + dx * flow_size * 2
        end_y = mid_y + dy * flow_size * 2
        arrow_size = 4

        draw.line([(mid_x, mid_y), (end_x, end_y)], fill=(255, 255, 255), width=1)
        draw.polygon(
            [
                (end_x, end_y),
                (
                    end_x - dx * arrow_size - dy * arrow_size / 2,
                    end_y - dy * arrow_size + dx * arrow_size / 2,
                ),
                (
                    end_x - dx * arrow_size + dy * arrow_size / 2,
                    end_y - dy * arrow_size - dx * arrow_size / 2,
                ),
            ],
            fill=(255, 255, 255),
        )

    def draw_dotted_line(
        self,
        draw: ImageDraw.ImageDraw,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        segment_length: float,
        color: Tuple[int, int, int],
        width: int = 1,
        pattern: List[int] = None,
    ) -> None:
        """
        Helper function to draw a dotted line between two points

        Args:
            draw: ImageDraw object
            x1, y1: Start point coordinates
            x2, y2: End point coordinates
            segment_length: Length of each dash
            color: Line color
            width: Line width
            pattern: Optional pattern for dash-gap sequence [dash_length, gap_length]
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

        # Set dash and gap lengths
        if pattern:
            dash_ratio = pattern[0] / (pattern[0] + pattern[1])
            gap_ratio = pattern[1] / (pattern[0] + pattern[1])
        else:
            # Default pattern: dash is 60% of segment, gap is 40%
            dash_ratio = 0.6
            gap_ratio = 0.4

        dash_length = segment_length * dash_ratio
        gap_length = segment_length * gap_ratio

        current_x, current_y = x1, y1

        for i in range(num_segments):
            # Calculate dash end point
            dash_end_x = current_x + dx * dash_length
            dash_end_y = current_y + dy * dash_length

            # Draw dash
            draw.line(
                [(current_x, current_y), (dash_end_x, dash_end_y)],
                fill=color,
                width=width,
            )

            # Move to next dash start
            current_x = dash_end_x + dx * gap_length
            current_y = dash_end_y + dy * gap_length

            # Stop if we've reached the end
            if math.sqrt((current_x - x1) ** 2 + (current_y - y1) ** 2) >= length:
                break
