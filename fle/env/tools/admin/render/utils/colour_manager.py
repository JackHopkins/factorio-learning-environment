import colorsys
from typing import Dict, List, Tuple
from collections import defaultdict

from fle.env.entities import Entity, EntityStatus
from fle.env.game_types import prototype_by_name
from fle.env.tools.admin.render.utils.render_config import RenderConfig
from fle.env.tools.admin.render.utils.entity_categoriser import EntityCategoriser


class ColourManager:
    """Manages colors for Factorio entities based on their categories and status"""

    def __init__(self, config: RenderConfig, categorizer: EntityCategoriser):
        self.config = config
        self.categorizer = categorizer
        self.entity_colors: Dict[str, Tuple[int, int, int]] = {}
        self.entity_type_counts: Dict[str, int] = {}
        self.sorted_entity_types: List[str] = []

    def generate_high_contrast_colors(self, count: int) -> List[Tuple[int, int, int]]:
        """Generate a set of high-contrast colors using golden ratio method"""
        colors = []
        golden_ratio_conjugate = 0.618033988749895
        hue = 0.1  # Start with a pleasing hue

        for _ in range(count):
            # Generate HSV color with 100% saturation and 95% value
            hue = (hue + golden_ratio_conjugate) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)

            # Convert to RGB 0-255 range
            colors.append((int(r * 255), int(g * 255), int(b * 255)))

        return colors

    def assign_entity_colors(
        self, entities: List[Entity]
    ) -> Dict[str, Tuple[int, int, int]]:
        """Dynamically assign colors to entity types based on their categories"""
        # Reset state
        self.entity_colors = {}
        self.entity_type_counts = {}

        # Categorize entities and count occurrences
        entity_categories = {}
        for entity in entities:
            # Count occurrences of each entity type
            entity_name = entity.name
            self.entity_type_counts[entity_name] = (
                self.entity_type_counts.get(entity_name, 0) + 1
            )

            # Get category for this entity
            if entity_name not in entity_categories:
                category = self.categorizer.get_entity_category(entity)
                entity_categories[entity_name] = category

        # Get unique categories
        categories = set(entity_categories.values())

        # Assign known category colors
        for entity_name, category in entity_categories.items():
            if category in self.config.CATEGORY_COLORS:
                # Use predefined category color
                self.entity_colors[entity_name] = self.config.CATEGORY_COLORS[category]

        # Generate colors for any unknown categories
        unknown_categories = [
            c for c in categories if c not in self.config.CATEGORY_COLORS
        ]
        if unknown_categories:
            category_colors = {}
            colors = self.generate_high_contrast_colors(len(unknown_categories))
            for i, category in enumerate(unknown_categories):
                category_colors[category] = colors[i]

            # Assign these colors to entities
            for entity_name, category in entity_categories.items():
                if category in unknown_categories:
                    self.entity_colors[entity_name] = category_colors[category]

        # Sort entity types by count for legend display
        self.sorted_entity_types = sorted(
            self.entity_type_counts.keys(),
            key=lambda x: (-(self.entity_type_counts.get(x, 0)), x),
        )

        return self.entity_colors

    def get_entity_color(self, entity: Entity) -> Tuple[int, int, int]:
        """Get the color for an entity, accounting for status"""
        if entity.name not in self.entity_colors:
            # Assign a default color if this entity type wasn't in initial list
            hue = hash(entity.name) % 100 / 100.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
            self.entity_colors[entity.name] = (int(r * 255), int(g * 255), int(b * 255))

        base_color = self.entity_colors[entity.name]

        # For working entities, slightly brighten the color
        if entity.status == EntityStatus.WORKING:
            return tuple(min(c + 30, 255) for c in base_color)

        # For problem entities, slightly dim the color
        if entity.status in [
            EntityStatus.NO_POWER,
            EntityStatus.LOW_POWER,
            EntityStatus.NO_FUEL,
            EntityStatus.EMPTY,
        ]:
            return tuple(max(c - 50, 0) for c in base_color)

        return base_color

    def get_entities_by_category(
        self,
    ) -> Tuple[Dict[str, List[Tuple[str, int]]], Dict[str, str]]:
        """
        Group entity types by their categories with counts and provide shape information

        Returns:
            Tuple containing:
            - Dictionary mapping categories to lists of (entity_name, count) tuples
            - Dictionary mapping entity names to their shape types
        """
        entities_by_category = defaultdict(list)
        entity_shapes = {}

        # Find the category for each entity type and group them
        for entity_name in self.entity_type_counts.keys():
            # Determine appropriate category
            if entity_name in [
                "iron-ore",
                "copper-ore",
                "coal",
                "stone",
                "uranium-ore",
                "crude-oil",
            ]:
                category = entity_name
            elif entity_name == "water":
                category = "water"
            else:
                # For regular entities, get the actual category
                category = self.categorizer.get_entity_category(
                    prototype_by_name[entity_name]
                )

            # Get shape based on category
            shape_type = self.config.get_category_shape(category)
            entity_shapes[entity_name] = shape_type

            entities_by_category[category].append(
                (entity_name, self.entity_type_counts[entity_name])
            )

        # Sort entities within each category by count (descending)
        for category in entities_by_category:
            entities_by_category[category] = sorted(
                entities_by_category[category],
                key=lambda x: (-x[1], x[0]),  # Sort by count (descending), then name
            )

        return dict(entities_by_category), entity_shapes
