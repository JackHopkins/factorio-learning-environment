import random
from asyncio import sleep

from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.image_utils import save_rendered_image
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.env import Position, Resource, Prototype


@solver
def render_terrain() -> Solver:

    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        x,y = state.metadata['x'], state.metadata['y']
        request = f'/c game.surfaces[0].request_to_generate_chunks({{{x*16}, {y*16}}}, 16)'
        instance.rcon_client.send_command(request)
        instance.rcon_client.send_command(f'/c game.player.surface.force_generate_chunk_requests()')
        await sleep(0.5)
        instance.namespace.move_to(Position(x=x*16, y=y*16))

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

        # Use a larger radius to capture entities for the square image
        # Since we're making square images, we need √2 * radius to ensure corner coverage
        capture_radius = int(64 * 1.414) + 1  # 91 tiles
        visible_radius = 32  # The actual visible area we want to render
        
        # For now, use the visible radius directly since max_render_radius centers at (0,0) in normalized space
        # TODO: Update renderer to support centering the trim area at player position
        image, renderer = instance.namespace._render(radius=visible_radius,
                                                     position=nearest,
                                                     return_renderer=True,
                                                     max_render_radius=32)
        image_id = save_rendered_image(image, metadata=state.metadata, is_map=True)
        entities = instance.namespace.get_entities(radius=visible_radius, position=nearest)

        # Move back
        instance.namespace.move_to(Position(x=x * 16, y=y * 16))

        state.metadata['image'] = image_id
        state.metadata['renderer'] = renderer
        state.metadata['entities'] = entities
        state.metadata['instance'] = instance

        return state

    return solve