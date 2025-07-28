#!/usr/bin/env python3
"""
Factorio Blueprint Renderer - Extended with Resource Support
Renders Factorio blueprints including resource patches
"""
import copy
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
from typing import Dict, List, Optional, Union, Any

from fle.env import Entity, EntityCore, UndergroundBelt, EntityStatus
from fle.env.tools.admin.render.constants import BACKGROUND_COLOR, GRID_LINE_WIDTH, GRID_COLOR, DEFAULT_ROCK_VARIANTS, \
    OIL_RESOURCE_VARIANTS, RENDERERS, DEFAULT_SCALING
from fle.env.tools.admin.render.utils import (
    entities_to_grid, resources_to_grid, get_resource_variant,
    get_resource_volume, is_tree_entity, find_fle_sprites_dir,
    is_rock_entity, flatten_entities
)
from fle.env.tools.admin.render.entity_grid import EntityGridView
from fle.env.tools.admin.render.image_resolver import ImageResolver
from fle.env.tools.admin.render.renderer_manager import renderer_manager
from fle.env.tools.admin.render.renderers.tree import build_available_trees_index, get_tree_variant
from fle.env.tools.admin.render.profiler import profiler, profile_method





class Renderer:
    """Factorio Blueprint representation."""

    @profile_method(include_args=True)
    def __init__(self,
                 entities: Union[List[Dict], List[Entity]] = [],
                 resources: List[Dict] = [],
                 water_tiles: List[Dict] = [],
                 sprites_dir: Optional[Path] = None):
        """Initialize renderer with blueprint data.
        
        Args:
            data: Blueprint data containing entities, resources, and water tiles
            sprites_dir: Optional directory path for sprite files
        """
        self.icons = []

        flattened_entities = list(flatten_entities(entities)) #data.get('entities', [])

        # Find minimum coordinates across all items
        min_x, min_y = self._find_min_coordinates(flattened_entities, resources, water_tiles)

        # Store the offset for normalization
        self.offset_x = min_x
        self.offset_y = min_y

        # Normalize all coordinates by subtracting the minimum
        self.entities = self._normalize_positions(flattened_entities)
        self.resources = self._normalize_positions(resources)
        self.water_tiles = self._normalize_positions(water_tiles)

        self.resources = resources #data.get('resources', [])
        self.water_tiles = water_tiles #data.get('water_tiles', [])

        self.entity_grid = entities_to_grid(self.entities)
        self.resource_grid = resources_to_grid(self.resources)
        
        self.sprites_dir = self._resolve_sprites_dir(sprites_dir)
        self.available_trees = build_available_trees_index(self.sprites_dir)
        self.tree_variants = self._precompute_tree_variants()
        self._sort_entities_for_rendering()

    @profile_method()
    def _resolve_sprites_dir(self, sprites_dir: Optional[Path]) -> Path:
        """Resolve sprites directory location."""
        if sprites_dir is not None:
            return sprites_dir
            
        possible_dirs = [
            Path(".fle/sprites"),
            Path("sprites"),
            Path("images"),
        ]
        
        for dir_path in possible_dirs:
            if dir_path.exists():
                return dir_path
                
        return find_fle_sprites_dir()

    @profile_method()
    def _render_alert_overlays(self, img: Image.Image, entities, size: Dict, scaling: float, image_resolver) -> None:
        """Render alert overlays for entities with non-normal status."""

        # Status to alert icon mapping
        status_alert_mapping = {
            EntityStatus.NO_POWER: 'alert-no-electricity',
            EntityStatus.LOW_POWER: 'alert-no-electricity',
            EntityStatus.NO_FUEL: 'alert-no-fuel',
            EntityStatus.EMPTY: 'alert-warning',
            EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK: 'alert-disconnected',
            EntityStatus.CHARGING: 'alert-recharge-needed',
            EntityStatus.DISCHARGING: 'alert-recharge-needed',
            EntityStatus.FULLY_CHARGED: None,  # No alert for fully charged
            EntityStatus.NO_RECIPE: 'alert-no-building-materials',
            EntityStatus.NO_INGREDIENTS: 'alert-no-building-materials',
            EntityStatus.NOT_CONNECTED: 'alert-disconnected',
            EntityStatus.NO_INPUT_FLUID: 'alert-no-fluid',
            EntityStatus.NO_RESEARCH_IN_PROGRESS: 'alert-warning',
            EntityStatus.NO_MINABLE_RESOURCES: 'alert-warning',
            EntityStatus.LOW_INPUT_FLUID: 'alert-no-fluid',
            EntityStatus.FLUID_INGREDIENT_SHORTAGE: 'alert-no-fluid',
            EntityStatus.FULL_OUTPUT: 'alert-no-storage',
            EntityStatus.FULL_BURNT_RESULT_OUTPUT: 'alert-no-storage',
            EntityStatus.ITEM_INGREDIENT_SHORTAGE: 'alert-no-building-materials',
            EntityStatus.MISSING_REQUIRED_FLUID: 'alert-no-fluid',
            EntityStatus.MISSING_SCIENCE_PACKS: 'alert-no-building-materials',
            EntityStatus.WAITING_FOR_SOURCE_ITEMS: 'alert-logistic-delivery',
            EntityStatus.WAITING_FOR_SPACE_IN_DESTINATION: 'alert-no-storage',
            EntityStatus.PREPARING_ROCKET_FOR_LAUNCH: 'alert-warning',
            EntityStatus.WAITING_TO_LAUNCH_ROCKET: 'alert-warning',
            EntityStatus.LAUNCHING_ROCKET: 'alert-warning',
            EntityStatus.NO_AMMO: 'alert-no-ammo',
            EntityStatus.LOW_TEMPERATURE: 'alert-warning',
            EntityStatus.NOT_CONNECTED_TO_RAIL: 'alert-disconnected',
        }

        for entity in entities:
            # Handle both Entity objects and dicts
            if hasattr(entity, 'status'):
                status = entity.status
                entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity.__dict__
            elif isinstance(entity, dict) and 'status' in entity:
                status = entity['status']
                if isinstance(status, str):
                    status = EntityStatus.from_string(status)
                entity_dict = entity
            else:
                continue  # Skip entities without status

            # Not being plugged in takes precedence over no power.
            if status == EntityStatus.NO_POWER:
                if hasattr(entity, 'electrical_id'):
                    if not entity.electrical_id:
                        status = EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK
                elif isinstance(entity, dict) and 'electrical_id' in entity:
                    if not entity['electrical_id']:
                        status = EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK


            # Skip if status is NORMAL or WORKING
            if status in (EntityStatus.NORMAL, EntityStatus.WORKING):
                continue

            # Get the appropriate alert icon
            alert_name = status_alert_mapping.get(status, 'alert-warning')
            if not alert_name:
                continue

            # Load the alert icon
            alert_icon = image_resolver(alert_name, False)
            if not alert_icon:
                # Try with icon_ prefix as fallback
                alert_icon = image_resolver(f"icon_{alert_name}", False)
                if not alert_icon:
                    profiler.increment_counter('alert_icon_not_found')
                    continue

            # Get entity position and size
            pos = entity_dict.get('position', {})
            if hasattr(pos, 'x'):
                x, y = pos.x, pos.y
            else:
                x = pos.get('x', 0)
                y = pos.get('y', 0)

            if hasattr(entity, 'tile_dimensions'):
                entity_size = (entity.tile_dimensions.tile_width, entity.tile_dimensions.tile_height)
            else:
                entity_size = renderer_manager.get_entity_size(entity)

            # Scale the alert icon to 2x its original size
            scale_factor = 0.5 if entity_size[0] + entity_size[1] > 2 else 0.25
            new_width = int(alert_icon.width * scale_factor)
            new_height = int(alert_icon.height * scale_factor)
            alert_icon = alert_icon.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert alert icon to RGBA if it isn't already
            if alert_icon.mode != 'RGBA':
                alert_icon = alert_icon.convert('RGBA')

            # Apply 50% alpha by modifying the alpha channel
            pixels = alert_icon.load()
            for y_pixel in range(new_height):
                for x_pixel in range(new_width):
                    r, g, b, a = pixels[x_pixel, y_pixel]
                    # Reduce alpha to 50% of its original value
                    pixels[x_pixel, y_pixel] = (r, g, b, int(a * 0.75))

            # Calculate position for alert overlay
            # Place alert in top-right corner of entity
            relative_x = x + abs(size['minX']) + 0.5
            relative_y = y + abs(size['minY']) + 0.5

            # Calculate pixel position
            # Offset to place icon in top-right of entity
            # Adjust offset for the larger icon size
            icon_offset_x = 0#(entity_size[0] / 2) * scaling - new_width * 0.6
            icon_offset_y = 0#-(entity_size[1] / 2) * scaling - new_height * 0.2

            start_x = int((relative_x * scaling + scaling / 2) - new_width / 2 + icon_offset_x)
            start_y = int((relative_y * scaling + scaling / 2) - new_height / 2 + icon_offset_y)

            # Paste the alert icon with alpha channel
            img.paste(alert_icon, (start_x, start_y), alert_icon)

            profiler.increment_counter('alert_overlays_rendered')

    @profile_method()
    def _precompute_tree_variants(self) -> Dict:
        """Pre-calculate tree variants for sorting."""
        tree_variants = {}
        
        for e in self.entities:
            entity = e.model_dump() if not isinstance(e, dict) else e

            if not is_tree_entity(entity['name']):
                continue
                
            x = entity['position']['x']
            y = entity['position']['y']
            tree_type = entity['name'].split('-')[-1] if '-' in entity['name'] else '01'

            if 'dead' not in entity['name'] and 'dry' not in entity['name']:
                variation, _ = get_tree_variant(x, y, tree_type, self.available_trees)
                tree_variants[id(entity)] = variation
            else:
                tree_variants[id(entity)] = 'z'  # Sort after all regular trees
                
        return tree_variants

    @profile_method()
    def _sort_entities_for_rendering(self) -> None:
        """Sort entities for proper rendering order."""

        self.entities.sort(key=lambda e: (
            not is_tree_entity(e.name),  # Trees first
            -ord(self.tree_variants.get(id(e), 'a')) if is_tree_entity(e.name) else 0,
            not e.name.endswith('inserter'),
            e.position.y,
            e.position.x
        ))

    @profile_method()
    def get_size(self) -> Dict:
        """Calculate blueprint bounds including resources and trees."""
        bounds = self._calculate_bounds()

        # Calculate actual content dimensions (not including origin distance)
        content_width = bounds['max_width'] - bounds['min_width']
        content_height = bounds['max_height'] - bounds['min_height']

        return {
            'minX': bounds['min_width'],
            'minY': bounds['min_height'],
            'maxX': bounds['max_width'],
            'maxY': bounds['max_height'],
            'width': math.ceil(content_width),
            'height': math.ceil(content_height)
        }

    def _get_position(self, item: Any) -> Optional[Dict[str, float]]:
        """Extract position from an item, handling both dict and object formats.

        Returns position as dict with 'x' and 'y' keys, or None if no position found.
        """
        # Handle water tiles which have x,y directly
        if isinstance(item, dict) and 'x' in item and 'y' in item and 'position' not in item:
            return {'x': item['x'], 'y': item['y']}

        # Handle items with position attribute/key
        if hasattr(item, 'position'):
            pos = item.position
            if hasattr(pos, 'x') and hasattr(pos, 'y'):
                return {'x': pos.x, 'y': pos.y}
            elif isinstance(pos, dict):
                return pos
        elif isinstance(item, dict) and 'position' in item:
            return item['position']

        return None

    def _set_position(self, item: Any, x: float, y: float) -> Any:
        """Set position on an item, handling both dict and object formats.

        Returns a copy of the item with updated position.
        """
        item_copy = copy.deepcopy(item)

        # Handle water tiles which have x,y directly
        if isinstance(item_copy, dict) and 'x' in item_copy and 'y' in item_copy and 'position' not in item_copy:
            item_copy['x'] = x
            item_copy['y'] = y
        # Handle items with position attribute
        elif hasattr(item_copy, 'position'):
            if hasattr(item_copy.position, 'x') and hasattr(item_copy.position, 'y'):
                item_copy.position.x = x
                item_copy.position.y = y
            elif isinstance(item_copy.position, dict):
                item_copy.position['x'] = x
                item_copy.position['y'] = y
        # Handle dict items with position key
        elif isinstance(item_copy, dict) and 'position' in item_copy:
            item_copy['position']['x'] = x
            item_copy['position']['y'] = y

        return item_copy

    def _find_min_coordinates(self, entities: List[Any], resources: List[Any], water_tiles: List[Any]) -> tuple[
        float, float]:
        """Find minimum x and y coordinates across all items."""
        min_x, min_y = float('inf'), float('inf')

        # Check all items for minimum coordinates
        all_items = list(entities) + list(resources) + list(water_tiles)

        for item in all_items:
            pos = self._get_position(item)
            if pos:
                min_x = min(min_x, pos['x'])
                min_y = min(min_y, pos['y'])

        # If no positions found, default to 0,0
        if min_x == float('inf'):
            min_x = 0
        if min_y == float('inf'):
            min_y = 0

        return min_x, min_y

    def _normalize_positions(self, items: List[Any]) -> List[Any]:
        """Normalize positions of all items by subtracting minimum coordinates."""
        normalized = []

        for item in items:
            pos = self._get_position(item)
            if pos:
                # Create normalized copy with adjusted position
                normalized_item = self._set_position(
                    item,
                    pos['x'] - self.offset_x,
                    pos['y'] - self.offset_y
                )
                normalized.append(normalized_item)
            else:
                # No position to normalize, keep as is
                normalized.append(copy.deepcopy(item))

        return normalized

    def _calculate_bounds(self) -> Dict:
        """Calculate the bounding box for all entities and resources."""
        min_width = min_height = 0
        max_width = max_height = 0

        # Check entities
        for entity in self.entities:
            pos = entity.position
            size = renderer_manager.get_entity_size(entity)
            min_width = min(min_width, pos.x - size[0] / 2)
            min_height = min(min_height, pos.y - size[1] / 2)
            max_width = max(max_width, pos.x + size[0] / 2)
            max_height = max(max_height, pos.y + size[1] / 2)

        # Check resources (they are 1x1)
        for resource in self.resources:
            pos = resource['position']
            min_width = min(min_width, pos['x'] - 0.5)
            min_height = min(min_height, pos['y'] - 0.5)
            max_width = max(max_width, pos['x'] + 0.5)
            max_height = max(max_height, pos['y'] + 0.5)

        return {
            'min_width': min_width,
            'min_height': min_height,
            'max_width': max_width,
            'max_height': max_height
        }

    @profile_method(include_args=True)
    def render(self, width: int, height: int, image_resolver) -> Image.Image:
        """Render blueprint to image.
        
        Args:
            width: Output image width
            height: Output image height
            image_resolver: Function to resolve sprite images
            
        Returns:
            Rendered PIL Image
        """
        size = self.get_size()
        scaling = min(width / (size['width'] + 2), height / (size['height'] + 2))

        img = self._create_base_image(width, height)
        self._draw_grid(img, size, scaling, width, height)
        
        # Separate entities for proper rendering order
        tree_entities = [e.model_dump() if not isinstance(e, dict) else e for e in self.entities if is_tree_entity(e.name)]
        rock_entities = [e.model_dump() if not isinstance(e, dict) else e for e in self.entities if is_rock_entity(e.name)]
        player_entities = [e for e in self.entities if not is_tree_entity(e.name) and not is_rock_entity(e.name)]

        # Expand consolidate underground belts into pairs
        player_entities = self._disintegrate_underground_belts(player_entities)

        grid_view = EntityGridView(self.entity_grid, 0, 0, self.available_trees)
        
        # Record entity counts for profiling
        profiler.increment_counter('total_entities', len(self.entities))
        profiler.increment_counter('tree_entities', len(tree_entities))
        profiler.increment_counter('rock_entities', len(rock_entities))
        profiler.increment_counter('player_entities', len(player_entities))
        profiler.increment_counter('resources', len(self.resources))
        profiler.increment_counter('water_tiles', len(self.water_tiles))

        # Render in order: resources -> tree shadows -> trees -> entity shadows -> rails -> entities
        self._render_resources(img, size, scaling, image_resolver)
        self._render_water_tiles(img, size, scaling, image_resolver)
        self._render_tree_shadows(img, tree_entities, size, scaling, grid_view, image_resolver)
        self._render_trees(img, tree_entities, size, scaling, grid_view, image_resolver)
        self._render_decoratives(img, rock_entities, size, scaling, image_resolver)

        self._render_entity_shadows(img, player_entities, size, scaling, grid_view, image_resolver)
        self._render_rails(img, player_entities, size, scaling, image_resolver)
        self._render_entities(img, player_entities, size, scaling, grid_view, image_resolver)

        # This is needed for belts
        self._render_visible_inventories(img, player_entities, size, scaling, grid_view, image_resolver)

        # This should be last so alerts appear on top of everything
        self._render_alert_overlays(img, player_entities, size, scaling, image_resolver)
        return img

    def _disintegrate_underground_belts(self, player_entities):
        entities = []
        for entity in player_entities:
            if isinstance(entity, UndergroundBelt):
                # input
                entities.append(entity)
                # output
                output = copy.deepcopy(entity)
                output.is_input = False
                output.position = output.output_position
                entities.append(output)
            else:
                entities.append(entity)
        return entities

    @profile_method()
    def _create_base_image(self, width: int, height: int) -> Image.Image:
        """Create base image with background color."""
        return Image.new('RGB', (width, height), BACKGROUND_COLOR)

    @profile_method()
    def _draw_grid(self, img: Image.Image, size: Dict, scaling: float, width: int, height: int) -> None:
        """Draw grid lines on the image."""
        draw = ImageDraw.Draw(img)
        
        for i in range(1, size['width'] + 2):
            x = i * scaling - GRID_LINE_WIDTH / 2
            draw.rectangle([x, 0, x + GRID_LINE_WIDTH, height], fill=GRID_COLOR)

        for i in range(1, size['height'] + 2):
            y = i * scaling - GRID_LINE_WIDTH / 2
            draw.rectangle([0, y, width, y + GRID_LINE_WIDTH], fill=GRID_COLOR)
    
    @profile_method()
    def _render_resources(self, img: Image.Image, size: Dict, scaling: float, image_resolver) -> None:
        """Render resource patches."""
        for resource in self.resources:
            pos = resource['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            if resource['name'] == 'crude-oil':
                volume = 1
                variant = get_resource_variant(pos['x'], pos['y'], max_variants=OIL_RESOURCE_VARIANTS)
            else:
                volume = get_resource_volume(resource.get('amount', 10000))
                variant = get_resource_variant(pos['x'], pos['y'])

            sprite_name = f"{resource['name']}_{variant}_{volume}"
            image = image_resolver(sprite_name, False)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)

    def _render_decoratives(self, img: Image.Image, decoratives: List[Dict], size: Dict, scaling: float, image_resolver) -> None:
        """Render decoratives."""
        for decorative in decoratives:
            pos = decorative['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            variant = get_resource_variant(pos['x'], pos['y'], max_variants=DEFAULT_ROCK_VARIANTS)

            sprite_name = f"{decorative['name']}_{variant}"
            image = image_resolver(sprite_name, False)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)
            else:
                while not image and variant < DEFAULT_ROCK_VARIANTS:
                    variant = variant + 1
                    sprite_name = f"{decorative['name']}_{variant}"
                    image = image_resolver(sprite_name, False)
                    if image:
                        self._paste_image(img, image, relative_x, relative_y, scaling)
                        break

    @profile_method()
    def _render_water_tiles(self, img: Image.Image, size: Dict, scaling: float, image_resolver) -> None:
        """Render water tiles."""
        for water in self.water_tiles:
            pos = water
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            volume = 1
            variant = get_resource_variant(pos['x'], pos['y'], max_variants=OIL_RESOURCE_VARIANTS)

            sprite_name = f"{water['name']}_{variant}_{volume}"
            image = image_resolver(sprite_name, False)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)
    
    @profile_method()
    def _render_tree_shadows(self, img: Image.Image, tree_entities, size: Dict, scaling: float, grid_view, image_resolver) -> None:
        """Render tree shadows."""
        for tree in tree_entities:
            pos = tree['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])
            renderer = renderer_manager.get_renderer(tree['name'])
            
            if renderer and hasattr(renderer, 'render_shadow'):
                shadow_image = renderer.render_shadow(tree, grid_view, image_resolver)
                if shadow_image:
                    self._paste_image(img, shadow_image, relative_x, relative_y, scaling)
    
    @profile_method()
    def _render_trees(self, img: Image.Image, tree_entities, size: Dict, scaling: float, grid_view, image_resolver) -> None:
        """Render trees."""
        for tree in tree_entities:
            pos = tree['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])
            renderer = renderer_manager.get_renderer(tree['name'])
            
            if renderer and hasattr(renderer, 'render'):
                tree_image = renderer.render(tree, grid_view, image_resolver)
                if tree_image:
                    self._paste_image(img, tree_image, relative_x, relative_y, scaling)
    
    @profile_method()
    def _render_entity_shadows(self, img: Image.Image, non_tree_entities, size: Dict, scaling: float, grid_view, image_resolver) -> None:
        """Render entity shadows."""
        for entity in non_tree_entities:
            entity = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            pos = entity['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])
            image = None

            if entity['name'] in RENDERERS:
                renderer = renderer_manager.get_renderer(entity['name'])
                if renderer and hasattr(renderer, 'render_shadow'):

                    if 'direction' in entity:
                        entity['direction'] = int(entity['direction'].value)
                    image = renderer.render_shadow(entity, grid_view, image_resolver)
            else:
                image = image_resolver(entity['name'], True)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)

    @profile_method()
    def _render_visible_inventories(self, img: Image.Image, entities, size: Dict, scaling: float, grid_view, image_resolver) -> None:
        """Render entity shadows."""
        for entity in entities:
            entity = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            pos = entity['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])
            image = None

            if entity['name'] in RENDERERS:
                renderer = renderer_manager.get_renderer(entity['name'])
                if renderer and hasattr(renderer, 'render_inventory'):
                    image = renderer.render_inventory(entity, grid_view, image_resolver)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)
    
    @profile_method()
    def _render_rails(self, img: Image.Image, non_tree_entities, size: Dict, scaling: float, image_resolver) -> None:
        """Render rail entities with multiple passes."""
        passes = [1, 2, 3, 3.5, 4, 5]
        
        for pass_num in passes:
            for entity in non_tree_entities:
                entity = entity.model_dump() if hasattr(entity, 'model_dump') else entity
                if entity['name'] not in ['straight-rail', 'curved-rail', 'rail-signal', 'rail-chain-signal']:
                    continue

                pos = entity['position']
                relative_x = pos['x'] + abs(size['minX']) + 0.5
                relative_y = pos['y'] + abs(size['minY']) + 0.5
                direction = entity.get('direction', 0)
                image = None

                if entity.name == 'straight-rail':
                    if direction in [0, 4]:
                        image = image_resolver(f"{entity.name}_vertical_pass_{int(pass_num)}", False)
                    elif direction in [2, 6]:
                        image = image_resolver(f"{entity.name}_horizontal_pass_{int(pass_num)}", False)

                if image:
                    self._paste_image(img, image, relative_x, relative_y, scaling)
    
    @profile_method()
    def _render_entities(self, img: Image.Image, non_tree_entities, size: Dict, scaling: float, grid_view, image_resolver) -> None:
        """Render non-rail entities."""
        for entity in non_tree_entities:
            if entity.name in ['straight-rail', 'curved-rail']:
                continue

            pos = entity.position
            relative_x = pos.x + abs(size['minX']) + 0.5
            relative_y = pos.y + abs(size['minY']) + 0.5

            grid_view.set_center(pos.x, pos.y)
            image = None

            if entity.name in RENDERERS:
                renderer = renderer_manager.get_renderer(entity.name)
                if renderer and hasattr(renderer, 'render'):
                    entity_dict = entity.model_dump()
                    if 'direction' in entity_dict:
                        entity_dict['direction'] = int(entity_dict['direction'].value)
                    image = renderer.render(entity_dict, grid_view, image_resolver)
            else:
                image = image_resolver(entity.name, False)

            if image:
                self._paste_image(img, image, relative_x, relative_y, scaling)

    @profile_method()
    def _paste_image(self, img: Image.Image, sprite: Image.Image, relative_x: float, relative_y: float, scaling: float) -> None:
        """Paste a sprite image onto the main image at the specified position."""
        start_x = int((relative_x * scaling + scaling / 2) - sprite.width / 2)
        start_y = int((relative_y * scaling + scaling / 2) - sprite.height / 2)
        mask = sprite if sprite.mode == 'RGBA' else None
        img.paste(sprite, (start_x, start_y), mask)


def main():
    """Example usage"""
    sprites_dir = Path("../.fle/sprites")
    image_resolver = ImageResolver(str(sprites_dir))

    with open("/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/fle/agents/data/sprites/sample_blueprint.json", "r") as f:
        blueprint_json = json.loads(f.read().strip())

    blueprint = Renderer(blueprint_json, sprites_dir)
    size = blueprint.get_size()
    width = (size['width'] + 2) * DEFAULT_SCALING
    height = (size['height'] + 2) * DEFAULT_SCALING

    image = blueprint.render(width, height, image_resolver)
    image.show()
    print(f"Blueprint rendered ({width}x{height})")


if __name__ == "__main__":
    main()