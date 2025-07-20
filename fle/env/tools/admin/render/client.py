from fle.env import Position, Layer
from fle.env.tools import Tool
from fle.commons.models.rendered_image import RenderedImage
from fle.env.tools.admin.render.decoder import Decoder
from fle.env.tools.admin.render.renderer import Renderer
from fle.env.tools.admin.render.image_resolver import ImageResolver
from fle.env.tools.admin.render.constants import DEFAULT_SCALING
from typing import Dict, List, Any, Optional
import base64


class Render(Tool):
    def __init__(self, *args):
        super().__init__(*args)
        self.image_resolver = ImageResolver(".fle/sprites")
        self.decoder = Decoder()

    def _decode_water_runs(self, water_runs: List[Dict]) -> List[Dict]:
        """
        Decode run-length encoded water tiles back to individual tiles.

        Args:
            water_runs: List of water runs with format:
                - t: tile type (water, deepwater, etc.)
                - x: starting x coordinate
                - y: y coordinate
                - l: length of the run

        Returns:
            List of individual water tiles in original format
        """
        tiles = []
        for run in water_runs:
            tile_type = run.get('t', 'water')
            start_x = run.get('x', 0)
            y = run.get('y', 0)
            length = run.get('l', 1)

            # Expand the run into individual tiles
            for x in range(start_x, start_x + length):
                tiles.append({
                    'x': x,
                    'y': y,
                    'name': tile_type
                })

        return tiles

    def _decode_resource_patches(self, resource_patches: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Decode patch-based resources back to individual resource entities.

        Args:
            resource_patches: Dictionary mapping resource types to patches.
                Each patch has:
                - c: center position [x, y]
                - e: list of entities as [dx, dy, amount] relative to center

        Returns:
            List of individual resource entities in original format
        """
        resources = []

        for resource_type, patches in resource_patches.items():
            for patch in patches:
                center = patch.get('c', [0, 0])
                entities = patch.get('e', [])

                # Convert relative positions to absolute
                for entity in entities:
                    if len(entity) >= 3:
                        dx, dy, amount = entity[0], entity[1], entity[2]
                        resources.append({
                            'name': resource_type,
                            'position': {
                                'x': center[0] + dx,
                                'y': center[1] + dy
                            },
                            'amount': amount
                        })

        return resources

    def _decode_base64_urlsafe(self, data: str) -> bytes:
        """
        Decode URL-safe Base64 (using - and _ instead of + and /)

        Args:
            data: URL-safe Base64 encoded string

        Returns:
            Decoded bytes
        """
        # Replace URL-safe characters with standard Base64 characters
        standard_b64 = data.replace('-', '+').replace('_', '/')
        return base64.b64decode(standard_b64)

    def _decode_optimized_format(self, result: Dict) -> Dict:
        """
        Decode the optimized format based on the version.

        Args:
            result: The raw result from the Lua execution

        Returns:
            Dictionary with decoded entities, water_tiles, and resources
        """
        meta = result.get('meta', {})
        format_version = meta.get('format', 'v1')

        if format_version == 'v2-binary':
            # Handle binary compressed format
            entities = result.get('entities', [])

            # Decode binary water data
            water_tiles = []
            if 'water_binary' in result:
                water_binary = self._decode_base64_urlsafe(result['water_binary'])
                water_runs = self.decoder.decode_water_binary(water_binary)
                water_tiles = self._decode_water_runs(water_runs)

            # Decode binary resource data
            resources = []
            if 'resources_binary' in result:
                resources_binary = self._decode_base64_urlsafe(result['resources_binary'])
                resource_patches = self.decoder.decode_resources_binary(resources_binary)
                resources = self._decode_resource_patches(resource_patches)

            return {
                'entities': entities,
                'water_tiles': water_tiles,
                'resources': resources
            }
        elif format_version == 'v2':
            # Handle optimized format
            entities = result.get('entities', [])
            water_runs = result.get('water', [])
            resource_patches = result.get('resources', {})

            # Decode compressed data
            water_tiles = self._decode_water_runs(water_runs)
            resources = self._decode_resource_patches(resource_patches)

            return {
                'entities': entities,
                'water_tiles': water_tiles,
                'resources': resources
            }
        else:
            # Handle legacy format
            return {
                'entities': result.get('entities', []),
                'water_tiles': result.get('water_tiles', []),
                'resources': result.get('resources', [])
            }

    def __call__(self, include_status: bool = False, radius: int = 50,
                 position: Optional[Position] = None,
                 layers: Layer = Layer.ALL,
                 compression_level: str = 'binary') -> RenderedImage:
        """
        Returns information about all entities, tiles, and resources within the specified radius of the player.

        Args:
            include_status: Whether to include status information for entities (optional)
            radius: Search radius around the player (default: 50)
            position: Center position for the search (optional, defaults to player position)
            layers: Which layers to include in the render
            compression_level: Compression level to use ('none', 'standard', 'binary', 'maximum')
                - 'none': No compression, raw data
                - 'standard': Run-length encoding for water, patch-based for resources (default)
                - 'binary': Binary encoding with base64 transport
                - 'maximum': Same as binary, reserved for future improvements

        Returns:
            RenderedImage containing the visual representation of the area
        """
        # Execute the Lua function with compression level
        result, _, elapsed = self.execute(
            self.player_index,
            include_status,
            radius,
            compression_level,
            return_elapsed=True
        )

        # Decode the optimized format if necessary
        decoded_result = self._decode_optimized_format(result)

        # Parse the Lua dictionaries
        entities = self.parse_lua_dict(decoded_result['entities'])
        water_tiles = decoded_result['water_tiles']
        resources = decoded_result['resources']

        # Create renderer with decoded data
        renderer = Renderer({
            "entities": entities,
            "water_tiles": water_tiles,
            "resources": resources
        })

        # Calculate render size
        size = renderer.get_size()
        if size['width'] == 0 or size['height'] == 0:
            raise Exception("Nothing to render.")

        width = (size['width'] + 2) * DEFAULT_SCALING
        height = (size['height'] + 2) * DEFAULT_SCALING

        # Render the blueprint
        image = renderer.render(width, height, self.image_resolver)

        return RenderedImage(image)