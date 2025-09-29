import random

from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.image_utils import save_rendered_image
from fle.env import Position, Resource


@solver
def render_terrain(instance) -> Solver:

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        x,y = state.metadata['x'], state.metadata['y']
        step = 32
        request = f'/c game.surfaces[0].request_to_generate_chunks({{{x*step}, {y*step}}}, 16)'
        r = instance.rcon_client.send_command(request)
        r1 = instance.rcon_client.send_command(f'/c game.player.surface.force_generate_chunk_requests()')
        try:
            instance.namespace.move_to(Position(x=x*step, y=y*step))
        except Exception as e:
            state.metadata['instance'] = instance
            state.metadata['renderer'] = None
            return state

        nearest = None
        attempt = 0

        # We move between map features.
        bag = [Resource.IronOre,
               Resource.Water,
               Resource.Stone,
               Resource.CrudeOil,
               Resource.CopperOre,
               Resource.Coal,
               Resource.Wood]

        while nearest is None and bag:
            choice = random.choice(bag)
            try:
                nearest = instance.namespace.nearest(choice)
                instance.namespace.move_to(nearest)
                print("nearest:", nearest)
            except Exception as e:
                attempt += 1
                bag.remove(choice)
                continue

        visible_radius = 32  # The actual visible area we want to render
        
        # Get the player's current position
        player_position = instance.namespace.player_location
        character_position = {'x': player_position.x, 'y': player_position.y}
        
        # For   now, use the visible radius directly since max_render_radius centers at (0,0) in normalized space
        # TODO: Update renderer to support centering the trim area at player position
        image, renderer = instance.namespace._render(radius=visible_radius,
                                                     position=nearest,
                                                     return_renderer=True,
                                                     max_render_radius=32)
        
        # Add the actual position coordinates to metadata for image naming
        if nearest:
            state.metadata['position'] = {'x': int(nearest.x), 'y': int(nearest.y)}
        else:
            # Fallback to original position if no resource was found
            state.metadata['position'] = {'x': int(x * step), 'y': int(y * step)}
        
        # Add character position to metadata for ground truth
        state.metadata['character_position'] = character_position
            
        image_id = save_rendered_image(image, metadata=state.metadata, is_map=True)
        entities = instance.namespace.get_entities(radius=visible_radius, position=nearest)

        # Move back
        instance.namespace.move_to(Position(x=x * step, y=y * step))

        state.metadata['image'] = image_id
        state.metadata['renderer'] = renderer
        state.metadata['entities'] = entities
        state.metadata['instance'] = instance

        return state

    return solve