import random

from inspect_ai.solver import Solver, solver, TaskState, Generate

from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.env import Position, Resource


@solver
def generate_terrain_questions(multiple_choice: bool = False) -> Solver:

    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        x,y = state.metadata['x'], state.metadata['y']
        request = f'/c game.surfaces[0].request_to_generate_chunks({{{x*64}, {y*64}}}, 5)'
        instance.rcon_client.send_command(request)
        instance.rcon_client.send_command(f'/c game.player.surface.force_generate_chunk_requests()')
        instance.namespace.move_to(Position(x=x*64, y=y*64))
        nearest = instance.namespace.nearest(random.choice([Resource.IronOre,
                                                            Resource.Water,
                                                            Resource.Stone,
                                                            Resource.CrudeOil,
                                                            Resource.CopperOre,
                                                            Resource.Coal,
                                                            Resource.Wood]))

        instance.namespace.move_to(nearest)
        print("nearest:", nearest)

        try:
            instance.namespace._render().show()
        except Exception as e:
            print(e)

        return state

    return solve