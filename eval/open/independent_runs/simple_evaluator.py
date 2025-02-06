import asyncio
import copy
from pathlib import Path
from typing import List, Tuple, Union, Dict

from eval.open.db_client import DBClient
from eval.open.model.game_state import GameState
from eval.open.model.program import Program
from entities import Entity, EntityGroup
from instance import FactorioInstance
from utils.profits import get_achievements


class SimpleFactorioEvaluator:
    def __init__(self,
                 db_client: DBClient,
                 instance: FactorioInstance,
                 value_accrual_time=10,
                 error_penalty=10,
                 logger=None):
        self.db = db_client
        self.instance = instance  # Main instances
        # self.holdout = instances[-1]  # Holdout instance
        self.value_accrual_time = value_accrual_time  # Time to accrue value before evaluating
        self.error_penalty = error_penalty  # Penalty for errors during evaluation

        if logger:
            self.port_to_group = logger.port_to_group
    async def evaluate(self, program: Program, start_state: GameState) -> Program:
        try:
            self.instance.reset(start_state)
            raw_reward, state, response, entities, achievements, ticks = await self._evaluate_single(self.instance.tcp_port, program, self.instance)

            relative_reward = raw_reward  # - holdout_value


            program.value = relative_reward
            program.state = state
            program.raw_reward = raw_reward
            program.ticks = ticks
            conversation = copy.deepcopy(program.conversation)

            conversation.add_result(program.code, response, score=raw_reward, advantage=relative_reward,
                                    objectives=program.meta[
                                        'objectives'] if 'objectives' in program.meta else [])  #
            program.conversation = conversation
            program.response = response
            program.achievements = achievements

            return program

        except Exception as e:
            print(e)
            raise e

    async def  _evaluate_single(self, instance_port: int, program: Program, instance: FactorioInstance) \
            -> Tuple[float, GameState, str, List[Union[Entity, EntityGroup]], Dict[str, Dict[str, int]], int]:

        tcp_port = instance_port

        try:
            # Get initial state information

            start_entities = instance.namespace.get_entities()
            start_inventory = instance.namespace.inspect_inventory()
            start_production_flows = instance.namespace._get_production_stats()
            initial_value, start_time = instance.namespace.score()
            reward, time, result = instance.eval(program.code, timeout=60)


            save_path = Path(f"../../../data/screenshots/{program.version}/{self.instance.tcp_port}/{int(((program.depth-1)/2)+1)}.png")
            self.instance.screenshot(save_path=save_path, center_on_factory=True)

            entities = instance.namespace.get_entities()
            final_inventory = instance.namespace.inspect_inventory()

            # Check to see if the inventories are different
            # If so, we manually put a hint in the generated code and result from the game
            get_inventory_code = 'print(f"Current inventory {inspect_inventory()}")'
            if (start_inventory.__dict__ != final_inventory.__dict__
                    and 'error' not in result.lower()
                    and get_inventory_code not in program.code
                    and 'inspect_inventory()' not in program.code):
                program.code += f'\n{get_inventory_code}'
                result += f'\n' + str(len(program.code.split('\n'))) + f': (\'Current inventory {final_inventory}\',)'

            # Check to see if the entities are different
            # If so, we put a hint in the code and result
            get_entities_code = 'print(f"Entities on the map: {get_entities()}")'
            if (start_entities != entities and 'error' not in result.lower()
                    and get_entities_code not in program.code
                    and 'get_entities()' not in program.code):
                program.code += f'\n{get_entities_code}\n'
                result += "\n" + str(len(program.code.split('\n'))) + f': (\'Entities on the map: {entities}\',)'

            result = result.rstrip() + "\n"

            if "error" in result.lower():
                result += f'final: (\'Current inventory: {final_inventory}\',)\n'
                result += f'final: (\'Entities on the map after the current step: {entities}\',)'

            # Sleep for 3 seconds to get output flows
            await asyncio.sleep(self.value_accrual_time)
            state = GameState.from_instance(instance)

            score, _ = instance.namespace.score()
            final_reward = score - initial_value
            ticks = instance.get_elapsed_ticks()

            post_production_flows = instance.namespace._get_production_stats()
            achievements = get_achievements(start_production_flows, post_production_flows)

            return final_reward, state, result, entities, achievements, ticks

        except Exception as e:
            print(f"Error in _evaluate_single:")

            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e