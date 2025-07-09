from abc import ABC, abstractmethod
from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.tools.admin.render.utils.render_config import RenderConfig


class LayerRenderer(ABC):
    """
    Abstract base class for all layer renderers.
    Each layer type should implement a concrete subclass of this.
    """

    def __init__(self, config: RenderConfig):
        """
        Initialize the layer renderer with configuration.

        Args:
            config: The render configuration
        """
        self.config = config

    @abstractmethod
    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """
        Render this layer to the provided image.

        Args:
            draw: The ImageDraw object to draw on
            game_to_img_func: Function to convert game coordinates to image coordinates
            boundaries: Dictionary with min_x, max_x, min_y, max_y values
            **kwargs: Additional arguments needed for rendering this layer
        """
        pass

    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Return the name of this layer"""
        pass
