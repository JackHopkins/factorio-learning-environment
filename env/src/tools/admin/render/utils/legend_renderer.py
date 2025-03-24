from typing import Dict, List, Tuple, Any
from PIL import ImageDraw, ImageFont

from render_config import RenderConfig
from color_manager import ColorManager
from entity_categorizer import EntityCategorizer
from shape_renderer import ShapeRenderer


class LegendRenderer:
    """Renders legends for Factorio entities visualization"""

    def __init__(self, config: RenderConfig, color_manager: ColorManager,
                 categorizer: EntityCategorizer, shape_renderer: ShapeRenderer):
        self.config = config
        self.color_manager = color_manager
        self.categorizer = categorizer
        self.shape_renderer = shape_renderer

    def calculate_legend_dimensions(self, img_width: int, img_height: int) -> Dict[str, Any]:
        """
        Calculate the dimensions of the legend without actually drawing it

        Args:
            img_width: Width of the original map image
            img_height: Height of the original map image

        Returns:
            Dict with width, height, and position of the legend
        """
        # Create a temporary image and drawing context to measure text
        tmp_img = ImageDraw.Draw(ImageDraw.Image.new('RGBA', (1, 1), (0, 0, 0, 0)))

        # Try to load a font for text measurement
        try:
            font = ImageFont.truetype("arial.ttf", size=10)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size=10)
            except IOError:
                font = ImageFont.load_default()

        # Set up legend dimensions
        padding = self.config.style["legend_padding"]
        item_height = self.config.style["legend_item_height"]
        item_spacing = self.config.style["legend_item_spacing"]
        category_spacing = item_spacing * 2

        # Get entities by category from color manager
        entities_by_category = self.color_manager.get_entities_by_category()
        sorted_categories = sorted(entities_by_category.keys())

        # Calculate legend dimensions
        total_items = sum(len(entities) for entities in entities_by_category.values())
        total_categories = len(entities_by_category)

        # Measure text widths to determine legend width
        max_text_width = 0
        for category in sorted_categories:
            # Check category title width
            category_width = tmp_img.textlength(category.upper(), font=font)
            max_text_width = max(max_text_width, category_width)

            # Check entity name widths
            for entity_name, count in entities_by_category[category]:
                display_name = entity_name.replace('-', ' ').title()
                display_text = f"{display_name} ({count})"
                text_width = tmp_img.textlength(display_text, font=font)
                max_text_width = max(max_text_width, text_width)

        # Calculate legend dimensions
        shape_sample_size = item_height
        legend_width = int(max_text_width + shape_sample_size + 3 * padding)

        # Add extra width for origin marker if enabled
        if self.config.style["origin_marker_enabled"]:
            total_items += 1

        legend_height = int(
            total_items * (item_height + item_spacing) +
            total_categories * (item_height + category_spacing) +
            2 * padding
        )

        # Determine the best position for the legend (outside the map)
        # Prioritize right side, then bottom if right side would make the image too wide
        if legend_width < img_width * 0.4:  # If legend width is reasonable, put it on the right
            position = "right_top"
        else:
            position = "bottom"  # Otherwise put it at the bottom

        return {
            "width": legend_width,
            "height": legend_height,
            "position": position
        }

    def draw_combined_legend(self, draw: ImageDraw.ImageDraw, img_width: int, img_height: int,
                             font: ImageFont.ImageFont) -> None:
        """Draw a combined legend showing entity types with their shapes and colors"""
        if not self.color_manager.entity_colors or not self.config.style["legend_enabled"]:
            return

        # Set up legend dimensions
        padding = self.config.style["legend_padding"]
        item_height = self.config.style["legend_item_height"]
        item_spacing = self.config.style["legend_item_spacing"]
        category_spacing = item_spacing * 2

        # Get entities by category
        entities_by_category = self.color_manager.get_entities_by_category()
        sorted_categories = sorted(entities_by_category.keys())

        # Calculate legend dimensions
        total_items = sum(len(entities) for entities in entities_by_category.values())
        total_categories = len(entities_by_category)

        # Measure text widths to determine legend width
        max_text_width = 0
        for category in sorted_categories:
            # Check category title width
            category_width = draw.textlength(category.upper(), font=font)
            max_text_width = max(max_text_width, category_width)

            # Check entity name widths
            for entity_name, count in entities_by_category[category]:
                display_name = entity_name.replace('-', ' ').title()
                display_text = f"{display_name} ({count})"
                text_width = draw.textlength(display_text, font=font)
                max_text_width = max(max_text_width, text_width)

        # Calculate legend dimensions
        shape_sample_size = item_height
        legend_width = int(max_text_width + shape_sample_size + 3 * padding)
        legend_height = int(
            total_items * (item_height + item_spacing) +
            total_categories * (item_height + category_spacing) +
            2 * padding
        )

        # Determine legend position
        position = self.config.style["legend_position"]
        if position == "top_left":
            legend_x, legend_y = padding, padding
        elif position == "top_right":
            legend_x, legend_y = img_width - legend_width - padding, padding
        elif position == "bottom_left":
            legend_x, legend_y = padding, img_height - legend_height - padding
        else:  # bottom_right (default)
            legend_x, legend_y = img_width - legend_width - padding, img_height - legend_height - padding

        # Draw legend background
        draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, legend_y + legend_height],
            fill=self.config.style["legend_bg_color"],
            outline=self.config.style["legend_border_color"],
            width=1
        )

        # Draw legend items by category
        y_offset = legend_y + padding

        for category in sorted_categories:
            # Draw category header
            draw.text(
                (legend_x + padding, y_offset + item_height / 2),
                category.upper(),
                fill=self.config.style["text_color"],
                anchor="lm",
                font=font
            )

            # Draw category shape sample
            shape_type = self.config.get_category_shape(category)
            shape_color = self.config.get_category_color(category)
            shape_x = legend_x + legend_width - padding - shape_sample_size
            shape_y = y_offset

            self.shape_renderer.draw_shape(
                draw,
                shape_x,
                shape_y,
                shape_x + shape_sample_size,
                shape_y + shape_sample_size,
                shape_type,
                shape_color
            )

            y_offset += item_height + category_spacing

            # Draw entities in this category
            for entity_name, count in entities_by_category[category]:
                # Draw entity color sample - using the entity's shape
                color = self.color_manager.entity_colors[entity_name]

                shape_x = legend_x + padding
                shape_y = y_offset

                self.shape_renderer.draw_shape(
                    draw,
                    shape_x,
                    shape_y,
                    shape_x + shape_sample_size,
                    shape_y + shape_sample_size,
                    shape_type,
                    color
                )

                # Draw text
                display_name = entity_name.replace('-', ' ').title()
                display_text = f"{display_name} ({count})"
                text_x = shape_x + shape_sample_size + padding
                text_y = y_offset + shape_sample_size / 2
                draw.text(
                    (text_x, text_y),
                    display_text,
                    fill=self.config.style["text_color"],
                    anchor="lm",
                    font=font
                )

                y_offset += item_height + item_spacing

        # Add origin marker in legend if enabled
        if self.config.style["origin_marker_enabled"]:
            y_offset += category_spacing

            # Draw origin marker label
            draw.text(
                (legend_x + padding, y_offset + item_height / 2),
                "ORIGIN",
                fill=self.config.style["text_color"],
                anchor="lm",
                font=font
            )

            # Draw origin marker sample
            marker_size = item_height / 2.5
            marker_color = self.config.style["origin_marker_color"]
            center_x = legend_x + legend_width - padding - shape_sample_size / 2
            center_y = y_offset + item_height / 2

            # Draw a circle with crosshair
            draw.ellipse(
                [center_x - marker_size, center_y - marker_size,
                 center_x + marker_size, center_y + marker_size],
                outline=marker_color, width=2
            )

            draw.line(
                [center_x - marker_size, center_y, center_x + marker_size, center_y],
                fill=marker_color, width=2
            )
            draw.line(
                [center_x, center_y - marker_size, center_x, center_y + marker_size],
                fill=marker_color, width=2
            )