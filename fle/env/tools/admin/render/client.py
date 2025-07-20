from fle.env import Position, Layer
from fle.env.tools import Tool
from fle.commons.models.rendered_image import RenderedImage
from fle.env.tools.admin.render.renderer import Renderer
from fle.env.tools.admin.render.image_resolver import ImageResolver
from fle.env.tools.admin.render.constants import DEFAULT_SCALING


class Render(Tool):
    def __init__(self, *args):
        super().__init__(*args)
        self.image_resolver = ImageResolver(".fle/sprites")


    def __call__(self, include_status: bool = False, radius=50, position: Position = None, layers: Layer = Layer.ALL) -> RenderedImage:
        """
        Returns information about all entities, tiles, and resources within 500 tiles of the player.
        
        Args:
            include_status: Whether to include status information for entities (optional)
            
        Returns:
            Dictionary containing:
            - entities: List of all entities with:
                - name: Entity name/type
                - position: Position object with x,y coordinates  
                - direction: Direction the entity is facing (if applicable)
                - status: Entity status (if include_status is True and available)
            - water_tiles: List of water tiles with:
                - x: X coordinate
                - y: Y coordinate
                - name: Tile type (water, deepwater, etc.)
            - resources: List of resource patches with:
                - name: Resource type (iron-ore, copper-ore, etc.)
                - position: Position object with x,y coordinates
                - amount: Resource amount in the patch
        """
        result, _, elapsed = self.execute(self.player_index, include_status, radius, return_elapsed=True)
        
        entities = self.parse_lua_dict(result.get("entities", []))
        water = self.parse_lua_dict(result.get("water_tiles", []))
        resources = self.parse_lua_dict(result.get("resources", []))

        renderer = Renderer({"entities": entities, "water_tiles": water, "resources": resources})

        # Calculate render size
        size = renderer.get_size()
        if size['width'] == 0 or size['height'] == 0:
            raise Exception("Nothing to render.")

        width = (size['width'] + 2) * DEFAULT_SCALING
        height = (size['height'] + 2) * DEFAULT_SCALING
        # Render the blueprint
        image = renderer.render(width, height, self.image_resolver)

        return RenderedImage(image)



