import asyncio
import copy
from typing import List, Tuple, Union, Dict

from fle.commons.db_client import DBClient
from fle.commons.models.achievements import ProductionFlows
from fle.commons.models.game_state import GameState
from fle.commons.models.program import Program
from fle.env.entities import Entity, EntityGroup
from fle.env import FactorioInstance
from fle.env.utils.profits import get_achievements


class SimpleFactorioEvaluator:
    def __init__(
        self,
        db_client: DBClient,
        instance: FactorioInstance,
        value_accrual_time=10,
        error_penalty=10,
        logger=None,
    ):
        self.db = db_client
        self.instance = instance  # Main instance
        # self.holdout = instances[-1]  # Holdout instance
        self.value_accrual_time = (
            value_accrual_time  # Time to accrue value before evaluating
        )
        self.error_penalty = error_penalty  # Penalty for errors during evaluation

        if logger:
            self.port_to_group = logger.port_to_group

    async def evaluate(
        self,
        program: Program,
        start_state: GameState,
        task,
        agent_idx: int,
        step_statistics: dict = {},
    ) -> Program:
        try:
            self.instance.reset(start_state)
            (
                raw_reward,
                state,
                response,
                entities,
                achievements,
                flows,
                ticks,
                error_occurred,
            ) = await self._evaluate_single(program, agent_idx)
            # enchance step statistics with the flows
            if not isinstance(flows, dict):
                step_statistics.update(flows.to_dict())
            else:
                step_statistics.update(flows)
            task_response = task.verify(
                score=raw_reward,
                instance=self.instance,
                step_statistics=step_statistics,
            )
            relative_reward = raw_reward  # - holdout_value

            program.value = relative_reward
            program.state = state
            program.raw_reward = raw_reward
            program.ticks = ticks
            conversation = copy.deepcopy(program.conversation)

            final_response = task.enhance_response_with_task_output(
                response, task_response
            )
            conversation.add_result(
                f"```python\n{program.code}\n```",
                final_response,
                score=raw_reward,
                advantage=relative_reward,
                objectives=program.meta["objectives"]
                if "objectives" in program.meta
                else [],
            )  #
            program.conversation = conversation
            program.response = final_response
            program.achievements = achievements
            program.flows = flows

            program.meta["task_response"] = task_response.dict()
            program.meta["error_occurred"] = error_occurred
            return program, task_response

        except Exception as e:
            print(e)
            raise e

    async def _evaluate_single(
        self, program: Program, agent_idx: int
    ) -> Tuple[
        float,
        GameState,
        str,
        List[Union[Entity, EntityGroup]],
        Dict,
        ProductionFlows,
        int,
    ]:
        # tcp_port = instance_port

        try:
            # Get initial state information
            start_entities = self.instance.namespaces[agent_idx].get_entities()
            start_inventory = self.instance.namespaces[agent_idx].inspect_inventory()
            # start_production_flows = instance.namespace._get_production_stats()
            start_production_flows = ProductionFlows.from_dict(
                self.instance.namespaces[agent_idx]._get_production_stats()
            )

            initial_value, start_time = self.instance.namespaces[agent_idx].score()
            reward, time, result = self.instance.eval(
                program.code, agent_idx=agent_idx, timeout=60
            )
            # Check if there was an error in the program execution
            error_occurred = (
                "error" in result.lower() or "exception: " in result.lower()
            )
            entities = self.instance.namespaces[agent_idx].get_entities()
            final_inventory = self.instance.namespaces[agent_idx].inspect_inventory()

            # Check to see if the inventories are different
            # If so, we manually put a hint in the generated code and result from the game
            get_inventory_code = 'print(f"Current inventory {inspect_inventory()}")'
            if (
                start_inventory.__dict__ != final_inventory.__dict__
                and not error_occurred
                and get_inventory_code not in program.code
                and "inspect_inventory()" not in program.code
            ):
                program.code += f"\n{get_inventory_code}"
                result += (
                    "\n"
                    + str(len(program.code.split("\n")))
                    + f": ('Current inventory {final_inventory}',)"
                )

            # Check to see if the entities are different
            # If they are, we put a hint in the code AND result
            get_entities_code = 'print(f"Entities on the map: {get_entities()}")'
            if (
                start_entities != entities
                and not error_occurred
                and get_entities_code not in program.code
                and "get_entities()" not in program.code
            ):
                program.code += f"\n{get_entities_code}\n"
                result += (
                    "\n"
                    + str(len(program.code.split("\n")))
                    + f": ('Entities on the map: {entities}',)"
                )

            result = result.rstrip() + "\n"

            if error_occurred:
                result += f"final: ('Current inventory: {final_inventory}',)\n"
                result += f"final: ('Entities on the map after the current step: {entities}',)"

            # Sleep for 3 seconds to get output flows
            await asyncio.sleep(self.value_accrual_time)
            state = GameState.from_instance(self.instance)
            score, _ = self.instance.first_namespace.score()
            final_reward = score - initial_value
            ticks = self.instance.get_elapsed_ticks()

            post_production_flows = ProductionFlows.from_dict(
                self.instance.first_namespace._get_production_stats()
            )

            achievements = get_achievements(
                start_production_flows.__dict__, post_production_flows.__dict__
            )
            flows = start_production_flows.get_new_flows(post_production_flows)  #

            return (
                final_reward,
                state,
                result,
                entities,
                achievements,
                flows,
                ticks,
                error_occurred,
            )

        except Exception as e:
            print("Error in _evaluate_single:")

            print(f"Error: {str(e)}")
            import traceback

            traceback.print_exc()
            raise e
