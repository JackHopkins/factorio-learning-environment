import asyncio
from copy import deepcopy
from typing import List, Tuple, Optional

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.program import Program
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
        for program, (raw_reward, state, response) in zip(programs, eval_results):
            relative_reward = raw_reward - holdout_value
            print(f"Program {program.id}: raw={raw_reward}, relative={relative_reward}")

            # First update program state and conversation
            program.value = relative_reward
            program.state = state
            program.raw_reward = raw_reward
            program.holdout_value = holdout_value
            program.conversation.add_result(program.code, relative_reward, response, state)

            # Then save to DB with updated conversation
            await self.db.update_program(program.id, {
                'value': relative_reward,
                'raw_reward': raw_reward,
                'holdout_value': holdout_value,
                'state_json': state.to_raw(),
                'conversation_json': program.conversation.model_dump_json()
            })

        return programs

    async def _evaluate_single(self, program: Program, instance: FactorioInstance) -> Tuple[float, GameState, str]:
        reward, _, result  = instance.eval(program.code, timeout=60)
        state = GameState.from_instance(instance)
        return reward, state, result

    async def _run_holdout(self) -> float:
        """Run holdout instance for same duration as programs"""
        await asyncio.sleep(10)  # Same timeout as program evaluation
        reward, _ = self.holdout.score()
        return reward