import random

from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.image_utils import save_rendered_image
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.env import Position, Resource, Prototype


@solver
def render_terrain() -> Solver:

    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        x,y = state.metadata['x'], state.metadata['y']
        request = f'/c game.surfaces[0].request_to_generate_chunks({{{x*32}, {y*32}}}, 5)'
        instance.rcon_client.send_command(request)
        instance.rcon_client.send_command(f'/c game.player.surface.force_generate_chunk_requests()')

        instance.namespace.move_to(Position(x=x*32, y=y*32))

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

        image, renderer = instance.namespace._render(radius=32, return_renderer=True)
        image_id = save_rendered_image(image, metadata=state.metadata, is_map=True)
        entities = instance.namespace.get_entities(radius=32)


        state.metadata['image'] = image_id
        state.metadata['renderer'] = renderer
        state.metadata['entities'] = entities
        state.metadata['instance'] = instance

        return state

    return solve