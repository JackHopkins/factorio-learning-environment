import asyncio
from typing import List, Tuple

from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.program import Program


class FactorioEvaluator:
    def __init__(self, instances: List['FactorioInstance']):
        self.instances = instances[:-1]  # Main instances
        self.holdout = instances[-1]  # Holdout for advantage computation

    async def evaluate_programs(self,
                                programs: List[Program],
                                timeout: int = 60) -> Tuple[List[float], List[GameState], List[str]]:
        """Evaluate programs across Factorio instances"""

        async def evaluate_single(program: Program,
                                  instance: 'FactorioInstance') -> Tuple[float, GameState, str]:
            # Capture initial state
            initial_state = GameState.from_instance(instance)

            # Execute program
            reward, result, response = instance.eval(program.code, timeout=timeout)

            # Capture final state
            final_state = GameState.from_instance(instance)

            return reward, final_state, response

        # Run evaluations in parallel
        tasks = []
        for prog, inst in zip(programs, self.instances):
            task = evaluate_single(prog, inst)
            tasks.append(task)

        # Run holdout
        holdout_task = evaluate_single(programs[0], self.holdout)

        # Gather results
        print(f"Running {len(tasks)} evaluations...")
        results = await asyncio.gather(*tasks)
        holdout_result = await holdout_task

        # Compute advantages
        rewards = []
        states = []
        responses = []

        for result in results:
            reward, state, response = result
            rewards.append(reward - holdout_result[0])  # Relative to holdout
            states.append(state)
            responses.append(response)

        return rewards, states, responses
