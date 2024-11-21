import asyncio
from typing import List, Tuple, Union

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.logger import FactorioLogger
from datasetgen.mcts.program import Program
from factorio_entities import Entity, EntityGroup
from factorio_instance import FactorioInstance


class FactorioEvaluator:
    def __init__(self, db_client: DBClient, instances: List[FactorioInstance], value_accrual_time=10):
        self.db = db_client
        self.instances = instances[:-1]  # Main instances
        self.holdout = instances[-1]  # Holdout instance
        self.value_accrual_time = value_accrual_time  # Time to accrue value before evaluating
        self.logger = FactorioLogger(len(instances))
        self.logger.start()

    def set_sampling_status(self):
        for i in range(len(self.instances)):
            self.logger.update_instance(i, status="sampling")

    async def evaluate_batch(self, programs: List[Program], start_state: GameState) -> List[Program]:
        try:
            # Reset holdout to same starting state
            self.holdout.reset(start_state)
            self.logger.update_instance(len(self.instances), status="running", program_id=None)
            holdout_future = asyncio.create_task(self._run_holdout())

            # Evaluate programs from same starting state
            eval_futures = []
            for i, (prog, inst) in enumerate(zip(programs, self.instances)):
                inst.reset(start_state)  # All instances start from same state
                self.logger.update_instance(i, program_id=prog.id, status="resetting")
                eval_futures.append(self._evaluate_single(i, prog, inst))

            # Wait for all evaluations
            eval_results = await asyncio.gather(*eval_futures)
            holdout_value = await holdout_future

            self.logger.update_instance(len(self.instances),
                                        status="completed",
                                        current_reward=holdout_value)

            # Update programs with relative rewards
            for i, (program, (raw_reward, state, response, entities)) in enumerate(zip(programs, eval_results)):
                relative_reward = raw_reward - holdout_value

                self.logger.update_instance(
                    i,
                    status="completed",
                    raw_reward=raw_reward,
                    holdout_value=holdout_value,
                    relative_reward=relative_reward,
                    total_programs=self.logger.instances[i].total_programs + 1,
                )

                # First update program state and conversation
                program.value = relative_reward
                program.state = state
                program.raw_reward = raw_reward
                program.holdout_value = holdout_value
                program.conversation.add_result(program.code, relative_reward, response, state, entities)
                program.response = response

            # Return updated programs
            return programs
        except Exception as e:
            for i in range(len(self.instances) + 1):
                self.logger.update_instance(
                    i,
                    status="error",
                    error_count=self.logger.instances[i].error_count + 1
                )
            raise e

    async def _evaluate_single(self, instance_id: int, program: Program, instance: FactorioInstance) -> Tuple[
        float, GameState, str, List[Union[Entity, EntityGroup]]]:
        try:
            start_entities = instance.get_entities()
            start_inventory = instance.inspect_inventory()
            self.logger.update_instance(instance_id, status="starting value")
            initial_value, _ = instance.score()

            self.logger.update_instance(instance_id, status="executing")
            reward, _, result = instance.eval(program.code, timeout=60)

            self.logger.update_instance(instance_id, status="capturing state")
            state = GameState.from_instance(instance)
            entities = instance.get_entities()
            final_inventory = instance.inspect_inventory()

            # Check to see if the inventories are different
            # If so, we put a hint in the code and result
            if start_inventory.__dict__ != final_inventory.__dict__ and 'error' not in result.lower():
                program.code += '\nprint(f"Inventory changed to {inspect_inventory()}")'
                result += f'\n'+str(len(program.code.split('\n')))+f': (\'Inventory changed to {final_inventory}\',)'

            # Check to see if the entities are different
            # If so, we put a hint in the code and result
            if start_entities != entities and 'error' not in result.lower():
                program.code += '\nprint(f"Entities on the map: {get_entities()}")\n'
                result += "\n"+str(len(program.code.split('\n')))+f': (\'Entities on the map: {entities}\',)'

            self.logger.update_instance(instance_id, status="accruing value")
            await asyncio.sleep(self.value_accrual_time)

            score, _ = instance.score()
            final_reward = score - initial_value

            self.logger.update_instance(
                instance_id,
                status="accrued value",
                current_reward=final_reward,
                raw_reward=final_reward,
                final_entities=len(entities),
                start_entities=len(start_entities),
                total_programs=self.logger.instances[instance_id].total_programs + 1,
                start_inventory_count=sum([v for k, v in start_inventory.__dict__.items() if v > 0]),
                final_inventory_count=sum([v for k, v in final_inventory.__dict__.items() if v > 0])
            )

            if "error" in result.lower():
                self.logger.update_instance(
                    instance_id,
                    status="error",
                    error_count=self.logger.instances[instance_id].error_count + 1
                )

            return final_reward, state, result, entities

        except Exception as e:
            self.logger.update_instance(
                instance_id,
                status="error",
                error_count=self.logger.instances[instance_id].error_count + 1
            )
            raise e

    async def _run_holdout(self) -> float:
        """Run holdout instance for same duration as programs"""
        try:
            initial_entities = self.holdout.get_entities()
            start_inventory = self.holdout.inspect_inventory()

            initial_value, _ = self.holdout.score()
            self.logger.update_instance(len(self.instances), status="accruing value")
            await asyncio.sleep(self.value_accrual_time)
            entities = self.holdout.get_entities()
            reward, _ = self.holdout.score()
            final_inventory = self.holdout.inspect_inventory()

            self.logger.update_instance(len(self.instances),
                                        status="accrued value",
                                        final_entities=len(entities),
                                        start_entities=len(initial_entities),
                                        total_programs=self.logger.instances[len(self.instances)].total_programs + 1,
                                        start_inventory_count=sum([v for k, v in start_inventory.__dict__.items() if v > 0]),
                                        final_inventory_count=sum([v for k, v in final_inventory.__dict__.items() if v > 0]))

            return reward - initial_value
        except Exception as e:
            self.logger.update_instance(
                len(self.instances),
                status="error",
                error_count=self.logger.instances[len(self.instances)].error_count + 1
            )
            raise e

    def __del__(self):
        """Clean up logger on deletion"""
        self.logger.stop()