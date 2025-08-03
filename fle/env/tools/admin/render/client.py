from typing import Dict, Optional, Union, List, Tuple
from fle.commons.models.rendered_image import RenderedImage
from fle.env import Position, Layer
from fle.env.tools import Tool
from fle.env.tools.admin.render.constants import DEFAULT_SCALING
from fle.env.tools.admin.render.decoder import Decoder
from fle.env.tools.admin.render.image_resolver import ImageResolver
from fle.env.tools.admin.render.renderer import Renderer
from fle.env.tools.agent.get_entities.client import GetEntities
from fle.env.tools.admin.render.profiler import profiler, profile_method


class Render(Tool):
    def __init__(self, *args):
        super().__init__(*args)
        self.image_resolver = ImageResolver(".fle/sprites")
        self.decoder = Decoder()
        self.get_entities = GetEntities(*args)

    @profile_method(include_args=True)
    def _get_map_entities(self, include_status, radius, compression_level):
        # Execute the Lua function with compression level
        try:
            result, _, elapsed = self.execute(
                self.player_index,
                include_status,
                radius,
                compression_level,
                return_elapsed=True
            )


            # Decode the optimized format if necessary
            decoded_result = self._decode_optimized_format(result)

            return decoded_result
        except Exception as e:
            result, _, elapsed = self.execute(
                self.player_index,
                include_status,
                radius,
                compression_level,
                return_elapsed=True
            )
            pass

    @profile_method(include_args=True)
    def __call__(self,
                 include_status: bool = False,
                 radius: int = 64,
                 position: Optional[Position] = None,
                 layers: Layer = Layer.ALL,
                 compression_level: str = 'binary',
                 blueprint: Union[str, List[Dict]] = None,
                 return_renderer=False,
                 max_render_radius: Optional[float] = None) -> Union[RenderedImage, Tuple[RenderedImage, Renderer]]:
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
            blueprint: Either a Base64 encoded blueprint, or a decoded blueprint
            return_renderer: Whether to return the renderer, which contains the entities that were renderered

        Returns:
            RenderedImage containing the visual representation of the area
        """
        assert isinstance(include_status, bool), "Include status must be boolean"
        assert isinstance(radius, (int, float)), "Radius must be a number"

        if not blueprint:
            # Create renderer with decoded data
            renderer = self.get_renderer_from_map(include_status, radius, compression_level, max_render_radius)
        else:
            renderer = self.get_renderer_from_blueprint(blueprint)


        # Calculate render size
        size = renderer.get_size()
        if size['width'] == 0 or size['height'] == 0:
            raise Exception("Nothing to render.")

        width = size['width'] * DEFAULT_SCALING
        height = size['height'] * DEFAULT_SCALING

        # Render the blueprint
        image = renderer.render(width, height, self.image_resolver)

        if return_renderer:
            return RenderedImage(image), renderer
        else:
            return RenderedImage(image)

    def get_renderer_from_blueprint(self, blueprint):
        if isinstance(blueprint, str):
            raise NotImplementedError()
            # entities = blueprint['entities']
            # renderer = Renderer(
            #     entities=entities
            # )
        else:
            if not 'entities' in blueprint:
                raise ValueError("Blueprint passed with no entities")

            entities = blueprint['entities']
            renderer = Renderer(
                entities=entities
            )
        return renderer

    def get_renderer_from_map(self,
                             include_status: bool = False,
                             radius: int = 64,
                             compression_level: str = 'binary',
                             max_render_radius: Optional[float] = None,
                             ) -> Renderer:

        result = self._get_map_entities(include_status, radius, compression_level)

        #ent = self.get_entities(radius=radius)
        #if ent:
        #    pass

        # Parse the Lua dictionaries
        entities = self.parse_lua_dict(result['entities'])

        character_position = [c['position'] for c in list(filter(lambda x:x['name']=='character', entities))]

        #ent.extend(entities)
        water_tiles = result['water_tiles']


        resources = result['resources']

        # Create renderer with decoded data
        renderer = Renderer(
            entities=entities,
            water_tiles=water_tiles,
            resources=resources,
            max_render_radius=max_render_radius
        )
        return renderer

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
                water_binary = self.decoder.decode_base64_urlsafe(result['water_binary'])
                water_runs = self.decoder.decode_water_binary(water_binary)
                water_tiles = self.decoder.decode_water_runs(water_runs)

            # Decode binary resource data
            resources = []
            if 'resources_binary' in result:
                resources_binary = self.decoder.decode_base64_urlsafe(result['resources_binary'])
                resource_patches = self.decoder.decode_resources_binary(resources_binary)
                resources = self.decoder.decode_resource_patches(resource_patches)

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
            water_tiles = self.decoder.decode_water_runs(water_runs)
            resources = self.decoder.decode_resource_patches(resource_patches)

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