import math
from typing import Tuple, Optional
from PIL import ImageDraw

from fle.env.entities import Direction, EntityStatus
from fle.env.tools.admin.render.utils.render_config import RenderConfig


class ShapeRenderer:
    """Handles drawing shapes for entities on the Factorio map"""

    def __init__(self, config: RenderConfig):
        self.config = config

    def draw_shape(
        self,
        draw: ImageDraw.ImageDraw,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        shape_type: str,
        color: Tuple[int, int, int],
        direction: Optional[Direction] = None,
    ) -> None:
        """Draw a shape of specified type at the given coordinates, optionally rotated by direction"""
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2  # Center point
        width, height = x2 - x1, y2 - y1
        size = min(width, height)  # Use smaller dimension for consistent shapes

        # First, draw the backing rectangle to show the actual entity space
        backing_color = self.get_backing_rectangle_color(color)
        draw.rectangle([x1, y1, x2, y2], fill=backing_color, outline=(0, 0, 0))

        # Calculate rotation angle based on direction if provided and orient_shapes is enabled
        angle_rad = 0
        if direction is not None and self.config.style["orient_shapes"]:
            if direction == Direction.UP or direction == Direction.NORTH:
                angle_rad = 0  # No rotation needed
            elif direction == Direction.RIGHT or direction == Direction.EAST:
                angle_rad = math.pi / 2  # 90 degrees
            elif direction == Direction.DOWN or direction == Direction.SOUTH:
                angle_rad = math.pi  # 180 degrees
            elif direction == Direction.LEFT or direction == Direction.WEST:
                angle_rad = 3 * math.pi / 2  # 270 degrees

        # Function to rotate a point around the center
        def rotate_point(px, py, angle):
            if angle == 0:
                return px, py
            s, c = math.sin(angle), math.cos(angle)
            px, py = px - cx, py - cy  # Translate to origin
            nx, ny = px * c - py * s, px * s + py * c  # Rotate
            return nx + cx, ny + cy  # Translate back

        # Draw the actual shape but slightly smaller to fit within the backing rectangle
        # Apply a small reduction to shape size to make backing rectangle visible
        shrink_factor = 0.85
        # Calculate new coordinates for the shape
        shape_x1 = cx - (width * shrink_factor / 2)
        shape_y1 = cy - (height * shrink_factor / 2)
        shape_x2 = cx + (width * shrink_factor / 2)
        shape_y2 = cy + (height * shrink_factor / 2)
        size = min(
            shape_x2 - shape_x1, shape_y2 - shape_y1
        )  # Recalculate size for shape

        # For simple shapes like square and circle
        if shape_type == "square":
            if angle_rad == 0:
                # No rotation needed for square
                draw.rectangle(
                    [shape_x1, shape_y1, shape_x2, shape_y2],
                    fill=color,
                    outline=(0, 0, 0),
                )
            else:
                # For rotated square, use polygon
                points = [
                    (shape_x1, shape_y1),  # Top-left
                    (shape_x2, shape_y1),  # Top-right
                    (shape_x2, shape_y2),  # Bottom-right
                    (shape_x1, shape_y2),  # Bottom-left
                ]
                # Rotate all points
                rotated_points = [rotate_point(px, py, angle_rad) for px, py in points]
                draw.polygon(rotated_points, fill=color, outline=(0, 0, 0))

        elif shape_type == "circle":
            # Circle is rotation-invariant
            draw.ellipse(
                [shape_x1, shape_y1, shape_x2, shape_y2], fill=color, outline=(0, 0, 0)
            )

        elif shape_type == "triangle":
            # Define triangle points
            points = [
                (cx, shape_y1),  # Top
                (shape_x1, shape_y2),  # Bottom left
                (shape_x2, shape_y2),  # Bottom right
            ]
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        elif shape_type == "diamond":
            # Define diamond points
            points = [
                (cx, shape_y1),  # Top
                (shape_x2, cy),  # Right
                (cx, shape_y2),  # Bottom
                (shape_x1, cy),  # Left
            ]
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        elif shape_type == "pentagon":
            # Define pentagon points
            points = []
            for i in range(5):
                angle = i * (2 * math.pi / 5) - math.pi / 2  # Start from top
                px = cx + size / 2 * math.cos(angle)
                py = cy + size / 2 * math.sin(angle)
                points.append((px, py))
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        elif shape_type == "hexagon":
            # Define hexagon points
            points = []
            for i in range(6):
                angle = i * (2 * math.pi / 6)
                px = cx + size / 2 * math.cos(angle)
                py = cy + size / 2 * math.sin(angle)
                points.append((px, py))
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        elif shape_type == "octagon":
            # Define octagon points
            points = []
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                px = cx + size / 2 * math.cos(angle)
                py = cy + size / 2 * math.sin(angle)
                points.append((px, py))
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        elif shape_type == "cross":
            # Cross shape - using lines for simplicity
            thickness = size / 4
            if angle_rad == 0 or angle_rad == math.pi:  # 0 or 180 degrees
                # Vertical bar
                draw.rectangle(
                    [cx - thickness / 2, shape_y1, cx + thickness / 2, shape_y2],
                    fill=color,
                    outline=(0, 0, 0),
                )
                # Horizontal bar
                draw.rectangle(
                    [shape_x1, cy - thickness / 2, shape_x2, cy + thickness / 2],
                    fill=color,
                    outline=(0, 0, 0),
                )
            else:  # 90 or 270 degrees
                # Use polygon for rotated cross
                v_points = [
                    (cx - thickness / 2, shape_y1),
                    (cx + thickness / 2, shape_y1),
                    (cx + thickness / 2, shape_y2),
                    (cx - thickness / 2, shape_y2),
                ]
                h_points = [
                    (shape_x1, cy - thickness / 2),
                    (shape_x2, cy - thickness / 2),
                    (shape_x2, cy + thickness / 2),
                    (shape_x1, cy + thickness / 2),
                ]
                # Rotate all points
                v_rotated = [rotate_point(px, py, angle_rad) for px, py in v_points]
                h_rotated = [rotate_point(px, py, angle_rad) for px, py in h_points]
                draw.polygon(v_rotated, fill=color, outline=(0, 0, 0))
                draw.polygon(h_rotated, fill=color, outline=(0, 0, 0))

        elif shape_type == "star":
            # Star with 5 points
            outer_radius = size / 2
            inner_radius = outer_radius * 0.4
            points = []
            for i in range(10):
                angle = i * math.pi / 5
                radius = outer_radius if i % 2 == 0 else inner_radius
                px = cx + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                points.append((px, py))
            # Rotate points if needed
            if angle_rad != 0:
                points = [rotate_point(px, py, angle_rad) for px, py in points]
            draw.polygon(points, fill=color, outline=(0, 0, 0))

        else:
            # Default to rectangle for unknown shapes - no need to draw since backing is already a rectangle
            pass

    def get_backing_rectangle_color(
        self, shape_color: Tuple[int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Generate a semi-transparent backing rectangle color based on the shape color"""
        # Use shape_color as base, but make it slightly lighter and semi-transparent
        r, g, b = shape_color
        # Calculate a lighter, slightly desaturated version
        lightness_factor = 0.6
        lighter_r = int(r + (255 - r) * lightness_factor)
        lighter_g = int(g + (255 - g) * lightness_factor)
        lighter_b = int(b + (255 - b) * lightness_factor)
        # Add transparency (alpha channel)
        alpha = 120  # Semi-transparent (0-255)
        return (lighter_r, lighter_g, lighter_b, alpha)

    def draw_direction_indicator(
        self,
        draw: ImageDraw.ImageDraw,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        direction: Direction,
    ) -> None:
        """Draw a direction indicator arrow on the entity"""
        if not self.config.style["direction_indicator_enabled"]:
            return

        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        width, height = x2 - x1, y2 - y1
        indicator_size = min(width, height) * 0.5

        # Calculate direction vector
        dx, dy = 0, 0
        if direction == Direction.UP or direction == Direction.NORTH:
            dy = -1
        elif direction == Direction.RIGHT or direction == Direction.EAST:
            dx = 1
        elif direction == Direction.DOWN or direction == Direction.SOUTH:
            dy = 1
        elif direction == Direction.LEFT or direction == Direction.WEST:
            dx = -1

        # Draw direction arrow if we have a direction
        if dx != 0 or dy != 0:
            end_x = cx + dx * indicator_size
            end_y = cy + dy * indicator_size

            # Draw arrow shaft
            draw.line([(cx, cy), (end_x, end_y)], fill=(255, 255, 255), width=2)

            # Draw arrow head
            arrow_size = indicator_size * 0.5
            if dx != 0:  # Horizontal arrow
                draw.polygon(
                    [
                        (end_x, end_y),
                        (end_x - dx * arrow_size, end_y + arrow_size / 2),
                        (end_x - dx * arrow_size, end_y - arrow_size / 2),
                    ],
                    fill=(255, 255, 255),
                )
            else:  # Vertical arrow
                draw.polygon(
                    [
                        (end_x, end_y),
                        (end_x + arrow_size / 2, end_y - dy * arrow_size),
                        (end_x - arrow_size / 2, end_y - dy * arrow_size),
                    ],
                    fill=(255, 255, 255),
                )

    def draw_status_indicator(
        self,
        draw: ImageDraw.ImageDraw,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        status: EntityStatus,
    ) -> None:
        """Draw a status indicator in the corner if the entity status is not normal"""
        if (
            not self.config.style["status_indicator_enabled"]
            or status == EntityStatus.NORMAL
        ):
            return

        status_color = self.config.get_status_color(status)

        # Draw a small triangle in the top-left corner
        draw.polygon([(x1, y1), (x1 + 8, y1), (x1, y1 + 8)], fill=status_color)

    def draw_origin_marker(
        self, draw: ImageDraw.ImageDraw, x: float, y: float, font
    ) -> None:
        """Draw a marker for the origin (0,0) point"""
        if not self.config.style["origin_marker_enabled"]:
            return

        marker_size = self.config.style["origin_marker_size"]
        marker_color = self.config.style["origin_marker_color"]

        # Draw a distinctive origin marker
        draw.ellipse(
            [x - marker_size, y - marker_size, x + marker_size, y + marker_size],
            outline=marker_color,
            width=2,
        )

        # Add crosshair
        draw.line([x - marker_size, y, x + marker_size, y], fill=marker_color, width=2)
        draw.line([x, y - marker_size, x, y + marker_size], fill=marker_color, width=2)

        # Add text label for origin
        draw.text(
            (x, y - marker_size - 5), "(0,0)", fill=marker_color, anchor="ms", font=font
        )
