from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Optional

from fle.env.entities import Entity, Position, BoundingBox, Layer, EntityStatus
from fle.env.tools.admin.render.layers.connection_layers_renderer import (
    ConnectionsLayerRenderer,
)
from fle.env.tools.admin.render.layers.marker_layers_renderer import (
    MarkersLayerRenderer,
)
from fle.env.tools.admin.render.layers.resource_layer_renderer import (
    ResourcesLayerRenderer,
)
from fle.env.tools.admin.render.utils.electricity_renderer import (
    ElectricityLayerRenderer,
)
from fle.env.tools.admin.render.utils.render_config import RenderConfig
from fle.env.tools.admin.render.utils.entity_categoriser import EntityCategoriser
from fle.env.tools.admin.render.utils.colour_manager import ColourManager
from fle.env.tools.admin.render.utils.shape_renderer import ShapeRenderer
from fle.env.tools.admin.render.utils.legend_renderer import LegendRenderer
from fle.env.tools.admin.render.utils.connection_renderer import ConnectionRenderer
from fle.env.tools.admin.render.utils.image_calculator import ImageCalculator


# Import layer renderers
from fle.env.tools.admin.render.layers.grid_layer_renderer import GridLayerRenderer
from fle.env.tools.admin.render.layers.water_layer_renderer import WaterLayerRenderer
from fle.env.tools.admin.render.layers.natural_layer_renderer import (
    NaturalLayerRenderer,
)
from fle.env.tools.admin.render.layers.entities_layer_renderer import (
    EntitiesLayerRenderer,
)


class Renderer:
    """
    Main renderer class for Factorio entities that composes all rendering components
    """

    def __init__(self, style: Optional[Dict] = None):
        """Initialize renderer with optional custom style"""
        # Core components
        self.config = RenderConfig(style)
        self.categorizer = EntityCategoriser()
        self.color_manager = ColourManager(self.config, self.categorizer)
        self.shape_renderer = ShapeRenderer(self.config)
        self.connection_renderer = ConnectionRenderer(self.color_manager)
        self.legend_renderer = LegendRenderer(
            self.config, self.color_manager, self.categorizer, self.shape_renderer
        )
        self.image_calculator = ImageCalculator(self.config)

        # Initialize layer renderers
        self.layer_renderers = {
            Layer.GRID: GridLayerRenderer(self.config),
            Layer.WATER: WaterLayerRenderer(self.config),
            Layer.RESOURCES: ResourcesLayerRenderer(self.config),
            Layer.NATURAL: NaturalLayerRenderer(self.config),
            Layer.ENTITIES: EntitiesLayerRenderer(
                self.config, self.categorizer, self.color_manager, self.shape_renderer
            ),
            Layer.CONNECTIONS: ConnectionsLayerRenderer(
                self.config, self.color_manager, self.connection_renderer
            ),
            Layer.PLAYER | Layer.ORIGIN: MarkersLayerRenderer(
                self.config, self.shape_renderer
            ),
            Layer.ELECTRICITY: ElectricityLayerRenderer(
                self.config
            ),  # Add the new electricity layer renderer
        }

    def render_entities(
        self,
        entities: List[Entity],
        center_pos: Optional[Position] = None,
        bounding_box: Optional[BoundingBox] = None,
        water_tiles: Optional[List[Dict]] = None,
        resource_entities: Optional[List[Dict]] = None,
        trees: Optional[List[Dict]] = None,
        rocks: Optional[List[Dict]] = None,
        electricity_networks: Optional[List[Dict]] = None,
        max_tiles: int = 20,
        layers: Layer = Layer.ALL,
    ) -> Image.Image:
        """
        Render a list of Factorio entities to an image

        Args:
            entities: List of entities to render
            center_pos: Optional center position (e.g. player position)
            bounding_box: Optional bounding box to constrain the render area
            water_tiles: Optional list of water tiles to render
            resource_entities: Optional list of resource entities to render
            trees: Optional list of trees to render
            rocks: Optional list of rocks to render
            electricity_networks: Optional list of electricity network data to render
            max_tiles: Maximum number of tiles on each side of the center position
            layers: Layer flags to specify which elements to render

        Returns:
            PIL Image containing the rendered map
        """
        # Track resources and natural elements present in the map for the legend
        resources_present = set()
        natural_elements_present = set()

        # Track entity statuses present in the map
        statuses_present = set()

        # Track electricity networks and their colors
        network_colors = {}

        # Add water if water tiles are present and water layer is enabled
        if Layer.WATER in layers and water_tiles and len(water_tiles) > 0:
            resources_present.add("water")

        # Add resources from resource_entities if resources layer is enabled
        if Layer.RESOURCES in layers and resource_entities:
            for resource in resource_entities:
                if "name" in resource:
                    resources_present.add(resource["name"])

        # Track trees and rocks if their respective layers are enabled
        if Layer.TREES in layers and trees and len(trees) > 0:
            natural_elements_present.add("tree")

        if Layer.ROCKS in layers and rocks and len(rocks) > 0:
            natural_elements_present.add("rock")

        # Track electricity networks if that layer is enabled
        if Layer.ELECTRICITY in layers and electricity_networks:
            # Create a renderer to get network colors if needed
            electricity_renderer = self.layer_renderers.get(Layer.ELECTRICITY)
            if electricity_renderer:
                # Collect all network IDs
                network_ids = set()
                for network in electricity_networks:
                    if "network_id" in network:
                        network_ids.add(network["network_id"])

                # Generate colors for each network
                electricity_renderer._assign_network_colors(network_ids, network_colors)

        # Assign colors to entities
        self.color_manager.assign_entity_colors(entities)

        # Calculate boundaries for rendering, making sure max_tiles is passed
        boundaries = self.image_calculator.calculate_boundaries(
            entities, center_pos, bounding_box, max_tiles=max_tiles
        )

        # Filter entities that are outside the boundaries
        filtered_entities = []
        for entity in entities:
            pos = entity.position
            # Check if entity is within boundaries
            if (
                pos.x >= boundaries["min_x"]
                and pos.x <= boundaries["max_x"]
                and pos.y >= boundaries["min_y"]
                and pos.y <= boundaries["max_y"]
            ):
                filtered_entities.append(entity)

                # Track entity status if the status indicator is enabled
                if (
                    self.config.style["status_indicator_enabled"]
                    and entity.status != EntityStatus.NORMAL
                ):
                    statuses_present.add(entity.status)

        # Update the entity list
        entities = filtered_entities

        # Always position the legend to the right of the grid
        self.config.style["legend_position"] = "right_top"

        # Calculate legend dimensions
        legend_dimensions = None
        if self.config.style["legend_enabled"] and (
            self.color_manager.entity_colors
            or resources_present
            or natural_elements_present
            or statuses_present
            or network_colors
        ):
            # Create a temporary image to calculate legend dimensions properly
            # Use constant base cell size for legend calculations to ensure consistent legend sizing regardless of zoom
            BASE_CELL_SIZE = 20  # Base cell size - this ensures legend remains readable at all zoom levels

            tmp_width = int(
                (boundaries["max_x"] - boundaries["min_x"]) * BASE_CELL_SIZE
                + 2 * self.config.style["margin"]
            )
            tmp_height = int(
                (boundaries["max_y"] - boundaries["min_y"]) * BASE_CELL_SIZE
                + 2 * self.config.style["margin"]
            )

            legend_dimensions = self.legend_renderer.calculate_legend_dimensions(
                tmp_width,
                tmp_height,
                resources_present,
                natural_elements_present,
                statuses_present,
                network_colors,
            )

        # Calculate final image dimensions
        dimensions = self.image_calculator.calculate_image_dimensions(legend_dimensions)
        img_width = dimensions["img_width"]
        img_height = dimensions["img_height"]

        # Create image and drawing context
        img = Image.new(
            "RGBA", (img_width, img_height), self.config.style["background_color"]
        )
        draw = ImageDraw.Draw(img)

        # Get coordinate conversion function
        game_to_img = self.image_calculator.get_game_to_image_coordinate_function()

        # Load fonts for text rendering - one for the map and one for the legend
        font = self._load_font()
        legend_font = self._load_legend_font()

        # Define the render order - certain layers should be rendered before others
        render_order = [
            Layer.WATER,  # Water tiles (background)
            Layer.GRID,  # Grid lines
            Layer.RESOURCES,  # Resource patches
            Layer.ROCKS,  # Rocks
            Layer.TREES,  # Trees
            Layer.ELECTRICITY,  # Electricity networks
            Layer.ENTITIES,  # Player-built entities
            Layer.CONNECTIONS,  # Underground connections
            Layer.ORIGIN,  # Origin marker (0,0)
            Layer.PLAYER,  # Player position marker
        ]

        # Common kwargs for all layer renderers
        render_kwargs = {
            "entities": entities,
            "water_tiles": water_tiles,
            "resource_entities": resource_entities,
            "trees": trees,
            "rocks": rocks,
            "electricity_networks": electricity_networks,
            "center_pos": center_pos,
            "font": font,
            "layers": layers,
        }

        # Render each layer in order if it's enabled
        for layer_type in render_order:
            if layer_type in layers:
                # Find the appropriate renderer
                for renderer_key, renderer in self.layer_renderers.items():
                    if layer_type in renderer_key:
                        renderer.render(draw, game_to_img, boundaries, **render_kwargs)
                        break

        # Draw the legend with resources, natural elements, statuses, and electricity networks
        # Use the legend_font for consistent readability regardless of zoom
        self.legend_renderer.draw_combined_legend(
            draw,
            img_width,
            img_height,
            legend_font,
            resources_present,
            natural_elements_present,
            statuses_present,
            network_colors,
        )

        return img

    def _load_font(self) -> ImageFont.ImageFont:
        """Load a font for text rendering with fallbacks"""
        try:
            font = ImageFont.truetype("arial.ttf", size=10)
        except IOError:
            try:
                # Try another common font on different systems
                font = ImageFont.truetype("DejaVuSans.ttf", size=10)
            except IOError:
                # Fallback to default font
                font = ImageFont.load_default()
        return font

    def _load_legend_font(self) -> ImageFont.ImageFont:
        """Load a font specifically for the legend with a consistent size"""
        legend_font_size = self.config.style.get("legend_font_size", 10)
        try:
            font = ImageFont.truetype("arial.ttf", size=legend_font_size)
        except IOError:
            try:
                # Try another common font on different systems
                font = ImageFont.truetype("DejaVuSans.ttf", size=legend_font_size)
            except IOError:
                # Fallback to default font
                font = ImageFont.load_default()
        return font
