from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.entities import Position, Layer
from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class MarkersLayerRenderer(LayerRenderer):
    """Renderer for markers (origin, player position)"""

    def __init__(self, config, shape_renderer):
        super().__init__(config)
        self.shape_renderer = shape_renderer

    @property
    def layer_name(self) -> str:
        return "markers"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw map markers (origin, player position)"""
        requested_layers = kwargs.get("layers", Layer.ALL)
        font = kwargs.get("font")

        # Draw player position if requested
        if Layer.PLAYER in requested_layers:
            center_pos = kwargs.get("center_pos")
            if center_pos:
                self._draw_player_marker(draw, center_pos, game_to_img_func)

        # Draw origin marker if requested
        if (
            Layer.ORIGIN in requested_layers
            and self.config.style["origin_marker_enabled"]
        ):
            if (
                0 >= boundaries["min_x"]
                and 0 <= boundaries["max_x"]
                and 0 >= boundaries["min_y"]
                and 0 <= boundaries["max_y"]
            ):
                origin_x, origin_y = game_to_img_func(0, 0)
                self.shape_renderer.draw_origin_marker(draw, origin_x, origin_y, font)

    def _draw_player_marker(
        self,
        draw: ImageDraw.ImageDraw,
        center_pos: Position,
        game_to_img_func: Callable,
    ) -> None:
        """Draw a marker at the center position (usually player position)"""
        center_x, center_y = game_to_img_func(center_pos.x, center_pos.y)
        # Draw a distinctive player marker (crosshair)
        marker_size = 8
        draw.ellipse(
            [
                center_x - marker_size,
                center_y - marker_size,
                center_x + marker_size,
                center_y + marker_size,
            ],
            fill=self.config.style["player_indicator_color"],
        )
        # Add crosshair in center
        draw.line(
            [center_x, center_y - marker_size, center_x, center_y + marker_size],
            fill=(0, 0, 0),
            width=2,
        )
        draw.line(
            [center_x - marker_size, center_y, center_x + marker_size, center_y],
            fill=(0, 0, 0),
            width=2,
        )
