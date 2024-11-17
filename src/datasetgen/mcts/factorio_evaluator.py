import asyncio
from copy import deepcopy
from typing import List, Tuple, Optional, Union

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.program import Program
from factorio_entities import Entity, EntityGroup
from factorio_instance import FactorioInstance


class FactorioEvaluator:
    def __init__(self, db_client: DBClient, instances: List[FactorioInstance]):
        self.db = db_client
        self.instances = instances[:-1]  # Main instances
        self.holdout = instances[-1]  # Holdout instance

    async def evaluate_batch(self, programs: List[Program], start_state: GameState) -> List[Program]:
        # Reset holdout to same starting state
        self.holdout.reset(start_state)
        holdout_future = asyncio.create_task(self._run_holdout())

        # Evaluate programs from same starting state
        eval_futures = []
        for prog, inst in zip(programs, self.instances):
            inst.reset(start_state)  # All instances start from same state
            eval_futures.append(self._evaluate_single(prog, inst))

        # Wait for all evaluations
        eval_results = await asyncio.gather(*eval_futures)
        holdout_value = await holdout_future

        print(f"Holdout value: {holdout_value}")

        # Update programs with relative rewards
        for program, (raw_reward, state, response, entities) in zip(programs, eval_results):
            relative_reward = raw_reward - holdout_value
            print(f"Program {program.id}: raw={raw_reward}, relative={relative_reward}")

            # First update program state and conversation
            program.value = relative_reward
            program.state = state
            program.raw_reward = raw_reward
            program.holdout_value = holdout_value
            program.conversation.add_result(program.code, relative_reward, response, state, entities)
            program.response = response

        # Filter out programs with no state - these are
        # Return updated programs
        return programs

    async def _evaluate_single(self, program: Program, instance: FactorioInstance) -> Tuple[float, GameState, str, List[Union[Entity, EntityGroup]]]:
        reward, _, result  = instance.eval(program.code, timeout=60)
        state = GameState.from_instance(instance)
        entities = instance.get_entities()
        return reward, state, result, entities

    async def _run_holdout(self) -> float:
        """Run holdout instance for same duration as programs"""
        await asyncio.sleep(10)  # Same timeout as program evaluation
        reward, _ = self.holdout.score()
        return reward