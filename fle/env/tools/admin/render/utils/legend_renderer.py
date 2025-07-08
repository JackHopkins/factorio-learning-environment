from typing import Dict, Any, Set, Optional
from PIL import ImageDraw, ImageFont, Image
import math

from fle.env.entities import EntityStatus
from fle.env.tools.admin.render.utils.render_config import RenderConfig
from fle.env.tools.admin.render.utils.colour_manager import ColourManager
from fle.env.tools.admin.render.utils.entity_categoriser import EntityCategoriser
from fle.env.tools.admin.render.utils.shape_renderer import ShapeRenderer


class LegendRenderer:
    """Renders legends for Factorio entities visualization"""

    def __init__(
        self,
        config: RenderConfig,
        color_manager: ColourManager,
        categorizer: EntityCategoriser,
        shape_renderer: ShapeRenderer,
    ):
        """Initialize the legend renderer with required components"""
        self.config = config
        self.color_manager = color_manager
        self.categorizer = categorizer  # Make sure this is stored
        self.shape_renderer = shape_renderer

    # def get_entities_by_category(self) -> Dict[str, List[Tuple[str, int]]]:
    #     """Group entity types by their categories with counts and collect shape information"""
    #     entities_by_category = defaultdict(list)
    #
    #     # Track entity shapes for use in the legend
    #     entity_shapes = {}
    #
    #     # Find the category for each entity type and group them
    #     for entity_name in self.entity_type_counts:
    #         # For resource categories, map them directly to their specific categories
    #         if entity_name in ["iron-ore", "copper-ore", "coal", "stone", "uranium-ore", "crude-oil"]:
    #             category = entity_name
    #         elif entity_name == "water":
    #             category = "water"
    #         else:
    #             # For regular entities, get their actual category
    #             category = self.categorizer.get_entity_category(entity_name)
    #
    #         # Get the shape for this entity type
    #         shape_type = self.config.get_category_shape(category)
    #         entity_shapes[entity_name] = shape_type
    #
    #         entities_by_category[category].append(
    #             (entity_name, self.entity_type_counts[entity_name], shape_type)
    #         )
    #
    #     # Sort entities within each category by count (descending)
    #     for category in entities_by_category:
    #         entities_by_category[category] = sorted(
    #             entities_by_category[category],
    #             key=lambda x: (-x[1], x[0])  # Sort by count (descending), then name
    #         )
    #
    #     return dict(entities_by_category), entity_shapes

    def calculate_legend_dimensions(
        self,
        img_width: int,
        img_height: int,
        resources_present: Optional[Set[str]] = None,
        natural_elements_present: Optional[Set[str]] = None,
        statuses_present: Optional[Set[EntityStatus]] = None,
        electricity_networks: Optional[Dict[int, tuple]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the dimensions of the legend without actually drawing it

        Args:
            img_width: Width of the original map image
            img_height: Height of the original map image
            resources_present: Set of resource types present in the map
            natural_elements_present: Set of natural element types present in the map
            statuses_present: Set of entity statuses present in the map
            electricity_networks: Dictionary mapping network IDs to their colors

        Returns:
            Dict with width, height, and position of the legend
        """
        # Create a temporary image and drawing context to measure text
        tmp_img = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))

        # Get consistent legend settings to ensure readability regardless of zoom
        padding = self.config.style["legend_padding"]
        item_height = self.config.style["legend_item_height"]
        item_spacing = self.config.style["legend_item_spacing"]
        category_spacing = item_spacing * 2  # Extra space between categories

        # Try to load a font for text measurement - use consistent font size for legend
        legend_font_size = self.config.style.get("legend_font_size", 10)
        try:
            font = ImageFont.truetype("arial.ttf", size=legend_font_size)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size=legend_font_size)
            except IOError:
                font = ImageFont.load_default()

        # Settings were already loaded above - no need to redefine
        category_spacing = item_spacing * 2

        # Get all entities and count them
        entity_counts = {}
        entity_categories = {}

        # Get entities by category from color manager and include shapes
        entities_by_category, entity_shapes = (
            self.color_manager.get_entities_by_category()
        )

        # Flatten all entities into a single list
        all_entities = []
        for category, entities in entities_by_category.items():
            for entity_data in entities:
                entity_name = entity_data[0]
                count = entity_data[1]
                if entity_name not in entity_counts:
                    entity_counts[entity_name] = count
                    entity_categories[entity_name] = category
                    all_entities.append((entity_name, count))
                else:
                    entity_counts[entity_name] += count

        # Sort entities by count (descending)
        all_entities.sort(key=lambda x: (-x[1], x[0]))

        # Calculate legend dimensions
        total_items = len(all_entities)
        total_categories = 3  # TERRAIN, RESOURCES, ENTITIES (initially)

        # Determine which resources to include in the legend
        resource_types = []
        if resources_present:
            # Add water if present
            if "water" in resources_present:
                resource_types.append({"name": "Water", "type": "water"})

            # Add other resources if present
            resource_mapping = {
                "iron-ore": "Iron Ore",
                "copper-ore": "Copper Ore",
                "coal": "Coal",
                "stone": "Stone",
                "uranium-ore": "Uranium Ore",
                "crude-oil": "Crude Oil",
            }

            for resource_id, display_name in resource_mapping.items():
                if resource_id in resources_present:
                    resource_types.append({"name": display_name, "type": resource_id})
        else:
            # Default resources to show if no specific resources are indicated
            resource_types = []

        # Determine which natural elements to include
        natural_types = []
        if natural_elements_present:
            if "tree" in natural_elements_present:
                natural_types.append({"name": "Trees", "type": "tree"})
            if "rock" in natural_elements_present:
                natural_types.append({"name": "Rocks", "type": "rock"})
        else:
            natural_types = []

        # Get status indicators to include (only those that are present)
        status_items = []
        if self.config.style["status_indicator_enabled"] and statuses_present:
            status_map = {
                EntityStatus.WORKING: "Working",
                EntityStatus.NO_POWER: "No Power",
                EntityStatus.LOW_POWER: "Low Power",
                EntityStatus.NO_FUEL: "No Fuel",
                EntityStatus.EMPTY: "Empty",
                EntityStatus.NOT_CONNECTED: "Not Connected",
                EntityStatus.FULL_OUTPUT: "Full Output",
                EntityStatus.NO_RECIPE: "No Recipe",
                EntityStatus.NO_INGREDIENTS: "No Ingredients",
            }

            # Only include statuses that are actually present
            for status in statuses_present:
                if status in status_map:
                    status_items.append({"name": status_map[status], "status": status})

        # Add electricity networks if present
        electricity_items = []
        if electricity_networks:
            for network_id, color in electricity_networks.items():
                electricity_items.append(
                    {
                        "name": f"Network {network_id}",
                        "network_id": network_id,
                        "color": color,
                    }
                )

        # Add player marker to the legend
        player_marker = {"name": "Character Position", "is_player": True}
        player_items = [player_marker]

        # If we have status items or electricity items, add another category for each
        if status_items:
            total_categories += 1
        if electricity_items:
            total_categories += 1

        # Add resources, natural elements, status items, and electricity networks to total items
        total_items += (
            len(resource_types)
            + len(natural_types)
            + len(status_items)
            + len(electricity_items)
            + len(player_items)
        )

        # Measure text widths to determine legend width
        max_text_width = 0

        # Check category titles
        category_titles = [
            "TERRAIN",
            "RESOURCES",
            "NATURAL",
            "ENTITIES",
            "STATUS",
            "ELECTRICITY",
        ]
        for title in category_titles:
            title_width = tmp_img.textlength(title, font=font)
            max_text_width = max(max_text_width, title_width)

        # Check entity name widths
        for entity_name, count in all_entities:
            display_name = entity_name.replace("-", " ").title()
            display_text = f"{display_name} ({count})"
            text_width = tmp_img.textlength(display_text, font=font)
            max_text_width = max(max_text_width, text_width)

        # Check resource type widths
        for resource in resource_types:
            text_width = tmp_img.textlength(resource["name"], font=font)
            max_text_width = max(max_text_width, text_width)

        # Check natural element type widths
        for natural in natural_types:
            text_width = tmp_img.textlength(natural["name"], font=font)
            max_text_width = max(max_text_width, text_width)

        # Check status indicator widths
        for status_item in status_items:
            text_width = tmp_img.textlength(status_item["name"], font=font)
            max_text_width = max(max_text_width, text_width)

        # Check electricity network widths
        for electricity_item in electricity_items:
            text_width = tmp_img.textlength(electricity_item["name"], font=font)
            max_text_width = max(max_text_width, text_width)

        # Check player marker width
        for player_item in player_items:
            text_width = tmp_img.textlength(player_item["name"], font=font)
            max_text_width = max(max_text_width, text_width)

        # Calculate base column width
        shape_sample_size = item_height
        column_width = int(max_text_width + shape_sample_size + 3 * padding)

        # Organize items into columns
        # Estimate height per section
        terrain_height = 0
        if "water" in [r["type"] for r in resource_types]:
            terrain_height = item_height + category_spacing + item_height + item_spacing

        resources_height = 0
        resource_count = len([r for r in resource_types if r["type"] != "water"])
        if resource_count > 0:
            resources_height = (
                item_height
                + category_spacing
                + resource_count * (item_height + item_spacing)
            )

        natural_height = 0
        if natural_types:
            natural_height = (
                item_height
                + category_spacing
                + len(natural_types) * (item_height + item_spacing)
            )

        entities_height = (
            item_height
            + category_spacing
            + len(all_entities) * (item_height + item_spacing)
        )

        # Add height for status indicators
        status_height = 0
        if status_items:
            status_height = (
                item_height
                + category_spacing
                + len(status_items) * (item_height + item_spacing)
            )

        # Add height for electricity networks
        electricity_height = 0
        if electricity_items:
            electricity_height = (
                item_height
                + category_spacing
                + len(electricity_items) * (item_height + item_spacing)
            )

        # Add height for player marker
        player_marker_height = (
            item_height
            + category_spacing
            + len(player_items) * (item_height + item_spacing)
        )

        # Add height for origin marker if enabled
        origin_height = 0
        if self.config.style["origin_marker_enabled"]:
            origin_height = item_height + item_spacing

        total_height = (
            terrain_height
            + resources_height
            + natural_height
            + entities_height
            + status_height
            + electricity_height
            + player_marker_height
            + origin_height
        )

        # Target height (use 80% of image height as maximum)
        target_height = int(img_height * 0.8) if img_height > 0 else 800

        # Calculate number of columns needed
        num_columns = max(1, math.ceil(total_height / target_height))

        # Calculate legend width based on columns
        legend_width = num_columns * column_width + padding

        # Estimate height per column (fairly distribute items)
        height_per_column = total_height / num_columns
        legend_height = int(height_per_column + 2 * padding)

        return {
            "width": legend_width,
            "height": legend_height,
            "position": "right_top",
            "num_columns": num_columns,
            "column_width": column_width,
            "all_entities": all_entities,
            "entity_shapes": entity_shapes,
            "resource_types": resource_types,
            "natural_types": natural_types,
            "status_items": status_items,
            "electricity_items": electricity_items,
            "player_items": player_items,
        }

    def draw_combined_legend(
        self,
        draw: ImageDraw.ImageDraw,
        img_width: int,
        img_height: int,
        font: ImageFont.ImageFont,
        resources_present: Optional[Set[str]] = None,
        natural_elements_present: Optional[Set[str]] = None,
        statuses_present: Optional[Set[EntityStatus]] = None,
        electricity_networks: Optional[Dict[int, tuple]] = None,
    ) -> None:
        """Draw a combined legend showing entity types with their actual shapes and colors"""
        if not self.config.style["legend_enabled"]:
            return

        # Get legend settings
        padding = self.config.style["legend_padding"]
        item_height = self.config.style["legend_item_height"]
        item_spacing = self.config.style["legend_item_spacing"]
        category_spacing = item_spacing * 2

        # Calculate legend dimensions
        dimensions = self.calculate_legend_dimensions(
            img_width,
            img_height,
            resources_present,
            natural_elements_present,
            statuses_present,
            electricity_networks,
        )
        legend_width = dimensions["width"]
        legend_height = dimensions["height"]
        num_columns = dimensions["num_columns"]
        column_width = dimensions["column_width"]
        all_entities = dimensions.get("all_entities", [])
        resource_types = dimensions.get("resource_types", [])
        natural_types = dimensions.get("natural_types", [])
        status_items = dimensions.get("status_items", [])
        electricity_items = dimensions.get("electricity_items", [])
        player_items = dimensions.get("player_items", [])

        # Get entity shapes
        entities_by_category, entity_shapes = (
            self.color_manager.get_entities_by_category()
        )

        # Position the legend at the right side
        legend_x = img_width - legend_width - padding
        legend_y = padding

        # Draw legend background with consistent styling (unaffected by zoom)
        draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, legend_y + legend_height],
            fill=self.config.style["legend_bg_color"],
            outline=self.config.style["legend_border_color"],
            width=1,
        )

        # Create a list of sections to distribute across columns
        sections = []

        # Add terrain section if water is present
        water_items = [r for r in resource_types if r["type"] == "water"]
        if water_items:
            water_section = {
                "title": "TERRAIN",
                "items": [
                    {
                        "name": "Water",
                        "color": self.config.get_category_color("water"),
                        "shape": "square",
                        "is_water": True,
                    }
                ],
            }
            sections.append(water_section)

        # Add resources section if any resources are present (except water)
        resource_items = [r for r in resource_types if r["type"] != "water"]
        if resource_items:
            resource_section = {"title": "RESOURCES", "items": []}

            for resource in resource_items:
                resource_type = resource["type"]
                resource_name = resource["name"]

                # Determine the shape and special properties
                shape = self.config.get_category_shape(resource_type)
                color = self.config.get_category_color(resource_type)

                item = {"name": resource_name, "color": color, "shape": shape}

                # Add special properties based on resource type
                if resource_type in ["iron-ore", "copper-ore"]:
                    item["has_dots"] = True
                elif resource_type == "uranium-ore":
                    item["is_uranium"] = True
                elif resource_type == "crude-oil":
                    item["is_oil"] = True

                resource_section["items"].append(item)

            sections.append(resource_section)

        # Add natural elements section if any trees or rocks are present
        if natural_types:
            natural_section = {"title": "NATURAL", "items": []}

            for natural in natural_types:
                natural_type = natural["type"]
                natural_name = natural["name"]

                # Determine the shape and special properties
                shape = self.config.get_category_shape(natural_type)
                color = self.config.get_category_color(natural_type)

                item = {"name": natural_name, "color": color, "shape": shape}

                # Add special properties based on natural type
                if natural_type == "tree":
                    item["is_tree"] = True
                elif natural_type == "rock":
                    item["is_rock"] = True

                natural_section["items"].append(item)

            sections.append(natural_section)

        # Add all entities in a single section
        entities_section = {"title": "ENTITIES", "items": []}

        for entity_name, count in all_entities:
            display_name = entity_name.replace("-", " ").title()
            display_text = f"{display_name} ({count})"
            color = self.color_manager.entity_colors[entity_name]

            # Get the correct shape for this entity
            shape_type = entity_shapes.get(entity_name, "square")

            entities_section["items"].append(
                {"name": display_text, "color": color, "shape": shape_type}
            )

        sections.append(entities_section)

        # Add status indicators section if enabled
        if status_items:
            status_section = {"title": "STATUS", "items": []}

            for status_item in status_items:
                status = status_item["status"]
                status_name = status_item["name"]

                # Get the status color from config
                status_color = self.config.get_status_color(status)

                status_section["items"].append(
                    {
                        "name": status_name,
                        "status_color": status_color,
                        "is_status": True,
                    }
                )

            sections.append(status_section)

        # Add electricity networks section if present
        if electricity_items:
            electricity_section = {"title": "ELECTRICITY", "items": []}

            for electricity_item in electricity_items:
                network_name = electricity_item["name"]
                network_color = electricity_item["color"]

                electricity_section["items"].append(
                    {
                        "name": network_name,
                        "color": network_color,
                        "shape": "circle",
                        "is_electricity": True,
                    }
                )

            sections.append(electricity_section)

        if player_items:
            player_section = {"title": "MARKERS", "items": []}

            for player_item in player_items:
                player_section["items"].append(
                    {"name": player_item["name"], "is_player": True}
                )

            sections.append(player_section)

        # Add origin marker if enabled
        if self.config.style["origin_marker_enabled"]:
            # Check if we already have a MARKERS section
            markers_section = next(
                (s for s in sections if s["title"] == "MARKERS"), None
            )

            if markers_section:
                # Add to existing MARKERS section
                markers_section["items"].append(
                    {"name": "Origin (0,0)", "is_origin": True}
                )
            else:
                # Create new MARKERS section
                origin_section = {
                    "title": "MARKERS",
                    "items": [{"name": "Origin (0,0)", "is_origin": True}],
                }
                sections.append(origin_section)

        # Calculate approximate height of each section
        section_heights = []
        for section in sections:
            height = item_height + category_spacing  # Title height
            height += len(section["items"]) * (
                item_height + item_spacing
            )  # Items height
            section_heights.append(height)

        # Distribute sections across columns to balance heights
        columns = [[] for _ in range(num_columns)]
        column_heights = [0] * num_columns

        # Distribute sections to columns, always placing the shortest column first
        for i, section in enumerate(sections):
            shortest_col = column_heights.index(min(column_heights))
            columns[shortest_col].append(i)
            column_heights[shortest_col] += section_heights[i]

        # Draw each column
        for col_index, column in enumerate(columns):
            col_x = legend_x + col_index * column_width + padding
            col_y = legend_y + padding

            for section_index in column:
                section = sections[section_index]

                # Draw section title
                draw.text(
                    (col_x, col_y + item_height / 2),
                    section["title"],
                    fill=self.config.style["text_color"],
                    anchor="lm",
                    font=font,
                )
                col_y += item_height + category_spacing

                # Draw section items
                for item in section["items"]:
                    shape_sample_size = item_height
                    shape_x = col_x
                    shape_y = col_y

                    # Draw shape based on item type
                    if "is_origin" in item and item["is_origin"]:
                        # Draw origin marker
                        marker_size = item_height / 2.5
                        marker_color = self.config.style["origin_marker_color"]
                        center_x = col_x + shape_sample_size / 2
                        center_y = col_y + shape_sample_size / 2

                        # Draw a circle with crosshair
                        draw.ellipse(
                            [
                                center_x - marker_size,
                                center_y - marker_size,
                                center_x + marker_size,
                                center_y + marker_size,
                            ],
                            outline=marker_color,
                            width=2,
                        )

                        draw.line(
                            [
                                center_x - marker_size,
                                center_y,
                                center_x + marker_size,
                                center_y,
                            ],
                            fill=marker_color,
                            width=2,
                        )
                        draw.line(
                            [
                                center_x,
                                center_y - marker_size,
                                center_x,
                                center_y + marker_size,
                            ],
                            fill=marker_color,
                            width=2,
                        )
                    elif "is_player" in item and item["is_player"]:
                        # Draw player marker (crosshair)
                        marker_size = item_height / 2.5
                        marker_color = self.config.style["player_indicator_color"]
                        center_x = col_x + shape_sample_size / 2
                        center_y = col_y + shape_sample_size / 2

                        # Draw a distinctive player marker (crosshair inside circle)
                        draw.ellipse(
                            [
                                center_x - marker_size,
                                center_y - marker_size,
                                center_x + marker_size,
                                center_y + marker_size,
                            ],
                            fill=marker_color,
                        )
                        # Add crosshair in center
                        draw.line(
                            [
                                center_x,
                                center_y - marker_size,
                                center_x,
                                center_y + marker_size,
                            ],
                            fill=(0, 0, 0),
                            width=2,
                        )
                        draw.line(
                            [
                                center_x - marker_size,
                                center_y,
                                center_x + marker_size,
                                center_y,
                            ],
                            fill=(0, 0, 0),
                            width=2,
                        )
                    elif "is_status" in item and item["is_status"]:
                        # Draw status indicator
                        status_color = item.get(
                            "status_color", (255, 0, 255)
                        )  # Default to magenta if missing

                        # Draw a small triangle in top-left of sample square as a status indicator
                        sample_box_size = shape_sample_size * 0.8
                        box_x = shape_x + (shape_sample_size - sample_box_size) / 2
                        box_y = shape_y + (shape_sample_size - sample_box_size) / 2

                        # Draw sample entity box
                        draw.rectangle(
                            [
                                box_x,
                                box_y,
                                box_x + sample_box_size,
                                box_y + sample_box_size,
                            ],
                            fill=(120, 120, 120),  # Generic entity color
                            outline=(0, 0, 0),
                        )

                        # Draw status triangle indicator
                        triangle_size = sample_box_size / 2
                        draw.polygon(
                            [
                                (box_x, box_y),
                                (box_x + triangle_size, box_y),
                                (box_x, box_y + triangle_size),
                            ],
                            fill=status_color,
                        )
                    elif "is_electricity" in item and item["is_electricity"]:
                        # Draw electricity network indicator
                        network_color = item.get("color", (200, 200, 200))

                        # Draw a semi-transparent circle to represent electricity coverage
                        center_x = shape_x + shape_sample_size / 2
                        center_y = shape_y + shape_sample_size / 2
                        outer_radius = shape_sample_size * 0.45
                        inner_radius = shape_sample_size * 0.15

                        # Semi-transparent outer circle for coverage area
                        transparent_color = network_color + (100,)  # Add alpha value
                        draw.ellipse(
                            [
                                center_x - outer_radius,
                                center_y - outer_radius,
                                center_x + outer_radius,
                                center_y + outer_radius,
                            ],
                            fill=transparent_color,
                        )

                        # Solid inner circle for pole
                        draw.ellipse(
                            [
                                center_x - inner_radius,
                                center_y - inner_radius,
                                center_x + inner_radius,
                                center_y + inner_radius,
                            ],
                            fill=network_color,
                            outline=(0, 0, 0),
                        )
                    else:
                        # Get shape and color
                        shape_type = item.get("shape", "square")
                        color = item.get("color", (200, 200, 200))

                        # First draw the backing rectangle to show entity space
                        # Create a lighter, semi-transparent version of the shape color for the backing rectangle
                        r, g, b = color
                        lightness_factor = 0.6
                        backing_r = int(r + (255 - r) * lightness_factor)
                        backing_g = int(g + (255 - g) * lightness_factor)
                        backing_b = int(b + (255 - b) * lightness_factor)
                        backing_color = (
                            backing_r,
                            backing_g,
                            backing_b,
                            120,
                        )  # Semi-transparent

                        # Draw backing rectangle
                        draw.rectangle(
                            [
                                shape_x,
                                shape_y,
                                shape_x + shape_sample_size,
                                shape_y + shape_sample_size,
                            ],
                            fill=backing_color,
                            outline=(0, 0, 0),
                        )

                        # Draw the actual shape slightly smaller to fit within backing rectangle
                        shrink_factor = 0.85
                        shape_center_x = shape_x + shape_sample_size / 2
                        shape_center_y = shape_y + shape_sample_size / 2
                        smaller_size = shape_sample_size * shrink_factor
                        smaller_x1 = shape_center_x - smaller_size / 2
                        smaller_y1 = shape_center_y - smaller_size / 2
                        smaller_x2 = shape_center_x + smaller_size / 2
                        smaller_y2 = shape_center_y + smaller_size / 2

                        # Draw the basic shape (use the smaller coordinates for the actual shape)
                        self.shape_renderer.draw_shape(
                            draw,
                            smaller_x1,
                            smaller_y1,
                            smaller_x2,
                            smaller_y2,
                            shape_type,
                            color,
                        )

                        # Add special details for different types
                        if "is_water" in item and item["is_water"]:
                            # Draw water cross-hatching
                            hatch_spacing = max(2, shape_sample_size // 5)
                            for i in range(0, shape_sample_size, hatch_spacing):
                                # Draw diagonal lines (one direction)
                                draw.line(
                                    [
                                        (shape_x, shape_y + i),
                                        (shape_x + min(i, shape_sample_size), shape_y),
                                    ],
                                    fill=(
                                        min(color[0] + 30, 255),
                                        min(color[1] + 30, 255),
                                        min(color[2] + 40, 255),
                                    ),
                                    width=1,
                                )
                                # Draw diagonal lines (other direction)
                                draw.line(
                                    [
                                        (shape_x + i, shape_y + shape_sample_size),
                                        (
                                            shape_x + shape_sample_size,
                                            shape_y
                                            + shape_sample_size
                                            - min(i, shape_sample_size),
                                        ),
                                    ],
                                    fill=(
                                        min(color[0] + 30, 255),
                                        min(color[1] + 30, 255),
                                        min(color[2] + 40, 255),
                                    ),
                                    width=1,
                                )

                        elif "has_dots" in item and item["has_dots"]:
                            # Add texture dots for ores
                            dot_size = shape_sample_size / 8
                            dot_color = (
                                min(color[0] + 30, 255),
                                min(color[1] + 30, 255),
                                min(color[2] + 30, 255),
                            )

                            dot_positions = [
                                (
                                    shape_x + shape_sample_size / 4,
                                    shape_y + shape_sample_size / 4,
                                ),
                                (
                                    shape_x + 3 * shape_sample_size / 4,
                                    shape_y + shape_sample_size / 4,
                                ),
                                (
                                    shape_x + shape_sample_size / 2,
                                    shape_y + shape_sample_size / 2,
                                ),
                                (
                                    shape_x + shape_sample_size / 4,
                                    shape_y + 3 * shape_sample_size / 4,
                                ),
                                (
                                    shape_x + 3 * shape_sample_size / 4,
                                    shape_y + 3 * shape_sample_size / 4,
                                ),
                            ]

                            for dot_x, dot_y in dot_positions:
                                draw.ellipse(
                                    [
                                        dot_x - dot_size,
                                        dot_y - dot_size,
                                        dot_x + dot_size,
                                        dot_y + dot_size,
                                    ],
                                    fill=dot_color,
                                    outline=None,
                                )

                        elif "is_uranium" in item and item["is_uranium"]:
                            # Draw radiation symbol
                            center_x = shape_x + shape_sample_size / 2
                            center_y = shape_y + shape_sample_size / 2
                            inner_radius = shape_sample_size * 0.25

                            # Draw center dot
                            draw.ellipse(
                                [
                                    center_x - inner_radius,
                                    center_y - inner_radius,
                                    center_x + inner_radius,
                                    center_y + inner_radius,
                                ],
                                fill=(0, 0, 0),
                            )

                            # Draw radiation "blades"
                            blade_length = shape_sample_size * 0.4
                            for angle in [0, 2.0944, 4.18879]:  # 0, 120, 240 degrees
                                end_x = center_x + blade_length * math.cos(angle)
                                end_y = center_y + blade_length * math.sin(angle)
                                mid_x = center_x + inner_radius * math.cos(angle)
                                mid_y = center_y + inner_radius * math.sin(angle)

                                draw.polygon(
                                    [
                                        (center_x, center_y),
                                        (mid_x, mid_y),
                                        (end_x, end_y),
                                    ],
                                    fill=(30, 120, 30),
                                )

                        elif "is_oil" in item and item["is_oil"]:
                            # Add oil "bubbles"
                            center_x = shape_x + shape_sample_size / 2
                            center_y = shape_y + shape_sample_size / 2
                            small_radius = shape_sample_size / 8
                            offsets = [
                                (shape_sample_size / 5, 0),
                                (0, shape_sample_size / 5),
                                (-shape_sample_size / 5, 0),
                                (0, -shape_sample_size / 5),
                            ]

                            for dx, dy in offsets:
                                draw.ellipse(
                                    [
                                        center_x + dx - small_radius,
                                        center_y + dy - small_radius,
                                        center_x + dx + small_radius,
                                        center_y + dy + small_radius,
                                    ],
                                    fill=(
                                        min(color[0] + 40, 255),
                                        min(color[1] + 40, 255),
                                        min(color[2] + 40, 255),
                                    ),
                                )

                        elif "is_tree" in item and item["is_tree"]:
                            # Draw a stylized tree in the legend
                            center_x = shape_x + shape_sample_size / 2
                            center_y = shape_y + shape_sample_size / 2

                            # Draw trunk
                            trunk_width = shape_sample_size / 5
                            trunk_height = shape_sample_size / 2
                            trunk_color = (101, 67, 33)  # Brown

                            draw.rectangle(
                                [
                                    center_x - trunk_width / 2,
                                    center_y - trunk_height / 2 + trunk_height / 4,
                                    center_x + trunk_width / 2,
                                    center_y + trunk_height / 2,
                                ],
                                fill=trunk_color,
                            )

                            # Draw foliage (simple circle for legend)
                            foliage_radius = shape_sample_size / 3

                            draw.ellipse(
                                [
                                    center_x - foliage_radius,
                                    center_y - foliage_radius - trunk_height / 4,
                                    center_x + foliage_radius,
                                    center_y + foliage_radius - trunk_height / 4,
                                ],
                                fill=color,
                            )

                        elif "is_rock" in item and item["is_rock"]:
                            # Draw a stylized rock in the legend
                            center_x = shape_x + shape_sample_size / 2
                            center_y = shape_y + shape_sample_size / 2
                            rock_radius = shape_sample_size / 2.5

                            # Draw irregular polygon for rock
                            num_points = 7  # Use a fixed number for the legend
                            points = []

                            for i in range(num_points):
                                angle = 2 * math.pi * i / num_points
                                # Use slightly irregular radius for natural look
                                point_radius = rock_radius * (0.9 + (0.2 * (i % 3) / 2))
                                px = center_x + math.cos(angle) * point_radius
                                py = center_y + math.sin(angle) * point_radius
                                points.append((px, py))

                            # Draw the rock
                            draw.polygon(
                                points,
                                fill=color,
                                outline=(
                                    min(color[0] - 30, 255),
                                    min(color[1] - 30, 255),
                                    min(color[2] - 30, 255),
                                ),
                            )

                    # Draw item label
                    text_x = shape_x + shape_sample_size + padding / 2
                    text_y = col_y + shape_sample_size / 2
                    draw.text(
                        (text_x, text_y),
                        item["name"],
                        fill=self.config.style["text_color"],
                        anchor="lm",
                        font=font,
                    )

                    col_y += item_height + item_spacing

                # Add spacing between sections
                col_y += item_spacing
