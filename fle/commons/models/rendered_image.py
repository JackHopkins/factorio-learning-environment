import base64
import io
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image


@dataclass
class Viewport:
    """Viewport information for grounding rendered images to world coordinates.

    Attributes:
        world_min_x: Minimum X coordinate in world/game space
        world_min_y: Minimum Y coordinate in world/game space
        world_max_x: Maximum X coordinate in world/game space
        world_max_y: Maximum Y coordinate in world/game space
        center_x: Center X coordinate in world/game space (player position if centered)
        center_y: Center Y coordinate in world/game space (player position if centered)
        width_tiles: Width of the viewport in game tiles
        height_tiles: Height of the viewport in game tiles
        image_width: Width of the rendered image in pixels
        image_height: Height of the rendered image in pixels
        scaling: Pixels per game tile (zoom level)
    """

    world_min_x: float
    world_min_y: float
    world_max_x: float
    world_max_y: float
    center_x: float
    center_y: float
    width_tiles: float
    height_tiles: float
    image_width: int
    image_height: int
    scaling: float

    def world_to_pixel(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to pixel coordinates in the image.

        Args:
            world_x: X coordinate in world/game space
            world_y: Y coordinate in world/game space

        Returns:
            Tuple of (pixel_x, pixel_y) coordinates
        """
        relative_x = world_x - self.world_min_x
        relative_y = world_y - self.world_min_y
        pixel_x = int(relative_x * self.scaling)
        pixel_y = int(relative_y * self.scaling)
        return (pixel_x, pixel_y)

    def pixel_to_world(self, pixel_x: int, pixel_y: int) -> Tuple[float, float]:
        """Convert pixel coordinates to world coordinates.

        Args:
            pixel_x: X coordinate in pixels
            pixel_y: Y coordinate in pixels

        Returns:
            Tuple of (world_x, world_y) coordinates
        """
        world_x = self.world_min_x + (pixel_x / self.scaling)
        world_y = self.world_min_y + (pixel_y / self.scaling)
        return (world_x, world_y)

    def is_in_viewport(self, world_x: float, world_y: float) -> bool:
        """Check if a world coordinate is within the viewport.

        Args:
            world_x: X coordinate in world/game space
            world_y: Y coordinate in world/game space

        Returns:
            True if the coordinate is within the viewport bounds
        """
        return (
            self.world_min_x <= world_x <= self.world_max_x
            and self.world_min_y <= world_y <= self.world_max_y
        )


class RenderedImage:
    """Wrapper for rendered images with display capabilities"""

    def __init__(self, image: Image.Image, viewport: Optional[Viewport] = None):
        self.image = image
        self.viewport = viewport

    def show(self, *args, **kwargs):
        """Display the image (works in IDEs)"""
        self.image.show(*args, **kwargs)

    def save(self, path: str):
        """Save the image to a file"""
        self.image.save(path)

    def to_base64(self):
        """Convert image to base64 string for embedding in HTML/Markdown"""
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def _repr_png_(self):
        """Support for Jupyter notebook display"""
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        return buffer.getvalue()
