from typing import Dict, Callable, List
from PIL import ImageDraw

from fle.env.entities import Entity, UndergroundBelt, Pipe
from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class ConnectionsLayerRenderer(LayerRenderer):
    """Renderer for underground connections (belts and pipes)"""

    def __init__(self, config, color_manager, connection_renderer):
        super().__init__(config)
        self.color_manager = color_manager
        self.connection_renderer = connection_renderer

    @property
    def layer_name(self) -> str:
        return "connections"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw connections between underground belts and pipes"""
        entities = kwargs.get("entities", [])
        if not entities:
            return

        self._draw_underground_belt_connections(draw, entities, game_to_img_func)
        self._draw_underground_pipe_connections(draw, entities, game_to_img_func)

    def _draw_underground_belt_connections(
        self,
        draw: ImageDraw.ImageDraw,
        entities: List[Entity],
        game_to_img_func: Callable,
    ) -> None:
        """Draw connections between underground belts"""
        # Find all underground belts
        underground_belts = [e for e in entities if isinstance(e, UndergroundBelt)]

        # Track already processed connections to avoid duplicates
        processed_connections = set()

        # Draw connections for all input underground belts
        for belt in underground_belts:
            # Skip if not an input belt
            if not belt.is_input:
                continue

            # Skip if already processed this connection
            connection_key = f"{belt.id}_{belt.connected_to}"
            reverse_key = f"{belt.connected_to}_{belt.id}"
            if (
                connection_key in processed_connections
                or reverse_key in processed_connections
            ):
                continue

            # Draw the connection
            entity_color = self.color_manager.get_entity_color(belt)
            self.connection_renderer.draw_underground_belt_connection(
                draw, belt, game_to_img_func, entity_color
            )

            # Mark this connection as processed
            processed_connections.add(connection_key)

    def _draw_underground_pipe_connections(
        self,
        draw: ImageDraw.ImageDraw,
        entities: List[Entity],
        game_to_img_func: Callable,
    ) -> None:
        """Draw connections between underground pipes"""
        # Find all pipes
        pipes = [e for e in entities if isinstance(e, Pipe)]

        # Create list of underground pipes (input and output)
        underground_pipes = []
        for pipe in pipes:
            if pipe.name == "pipe-to-ground":
                underground_pipes.append(pipe)

        # Create a lookup dictionary by position
        pipe_by_position = {}
        for pipe in underground_pipes:
            pos_key = f"{pipe.position.x}_{pipe.position.y}"
            pipe_by_position[pos_key] = pipe

        # Track already processed connections to avoid duplicates
        processed_connections = set()

        # Find and draw connections between input and output underground pipes
        for pipe in underground_pipes:
            # Skip if no connection information
            if not hasattr(pipe, "connected_to_position"):
                continue

            # Get connection position
            connection_pos = pipe.connected_to_position
            if not connection_pos:
                continue

            # Create connection keys
            pos_key = f"{pipe.position.x}_{pipe.position.y}"
            connection_key = f"{connection_pos.x}_{connection_pos.y}"
            pipe_connection_key = f"{pos_key}_{connection_key}"

            # Skip if already processed
            if pipe_connection_key in processed_connections:
                continue

            # Find the connected pipe
            connected_pipe = pipe_by_position.get(connection_key)
            if not connected_pipe:
                continue

            # Draw the connection
            entity_color = self.color_manager.get_entity_color(pipe)
            self.connection_renderer.draw_underground_pipe_connection(
                draw, pipe, connected_pipe, game_to_img_func, entity_color
            )

            # Mark as processed
            processed_connections.add(pipe_connection_key)
            processed_connections.add(
                f"{connection_key}_{pos_key}"
            )  # Reverse connection
