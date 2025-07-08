from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.entities import Direction, EntityStatus
from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class EntitiesLayerRenderer(LayerRenderer):
    """Renderer for player-built entities"""

    def __init__(self, config, categorizer, color_manager, shape_renderer):
        super().__init__(config)
        self.categorizer = categorizer
        self.color_manager = color_manager
        self.shape_renderer = shape_renderer

    @property
    def layer_name(self) -> str:
        return "entities"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw all entities on the map with their shapes, directions, and status indicators"""
        entities = kwargs.get("entities", [])
        if not entities:
            return

        for entity in entities:
            # Get entity position and dimensions
            pos = entity.position

            width = (
                entity.tile_dimensions.tile_width
                if hasattr(entity, "tile_dimensions")
                else 1
            )
            height = (
                entity.tile_dimensions.tile_height
                if hasattr(entity, "tile_dimensions")
                else 1
            )

            if entity.direction.value in (Direction.LEFT.value, Direction.RIGHT.value):
                width1 = width
                width = height
                height = width1

            # Calculate rectangle coordinates
            x1, y1 = game_to_img_func(pos.x - width / 2, pos.y - height / 2)
            x2, y2 = game_to_img_func(pos.x + width / 2, pos.y + height / 2)

            # Get entity color and category
            entity_color = self.color_manager.get_entity_color(entity)
            category = self.categorizer.get_entity_category(entity)
            shape_type = self.config.get_category_shape(category)

            # Draw entity shape
            self.shape_renderer.draw_shape(
                draw,
                x1,
                y1,
                x2,
                y2,
                shape_type,
                entity_color,
                direction=entity.direction if hasattr(entity, "direction") else None,
            )

            # Add status indicator in corner if enabled
            if (
                self.config.style["status_indicator_enabled"]
                and entity.status != EntityStatus.NORMAL
            ):
                self.shape_renderer.draw_status_indicator(
                    draw, x1, y1, x2, y2, entity.status
                )

            # Add direction indicator if enabled
            if self.config.style["direction_indicator_enabled"] and hasattr(
                entity, "direction"
            ):
                self.shape_renderer.draw_direction_indicator(
                    draw, x1, y1, x2, y2, entity.direction
                )
