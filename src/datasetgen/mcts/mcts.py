from typing import List, Tuple, Optional
import numpy as np
import asyncio
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from datasetgen.mcts.conversation import Conversation
from datasetgen.mcts.factorio_evaluator import FactorioEvaluator
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.program import Program


@dataclass
class ProgramGenResult:
    program: Optional[Program]
    error: Optional[str]


class MCTS:
    def __init__(self,
                 llm_factory: 'LLMFactory',
                 evaluator: FactorioEvaluator,
                 initial_state: GameState,
                 system_prompt: str,
                 max_workers: int = 4):
        self.llm = llm_factory
        self.evaluator = evaluator
        self.initial_state = initial_state
        self.program_history: List[Program] = []
        self.system_prompt = system_prompt
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def _generate_single_program(self, conv: Conversation) -> ProgramGenResult:
        """Non-async version for running in thread pool"""
        try:
            response = self.llm.call(
                messages=conv.messages,
                temperature=0.8,
                max_tokens=1000
            )

            code = response.content if "claude" in self.llm.model else response.choices[0].message.content
            code = code.split('```python')[1].split('```')[0]
            return ProgramGenResult(Program(code=code, conversation=conv), None)
        except Exception as e:
            return ProgramGenResult(None, str(e))

    async def _generate_program_async(self, conv: Conversation) -> ProgramGenResult:
        """Run single program generation in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._generate_single_program,
            conv
        )

    async def _generate_programs_batch(self, n_samples: int) -> List[Program]:
        tasks = []
        best_reward = max(p.value for p in self.program_history)
        print(f"Best reward: {best_reward}")
        print(f"Generating {n_samples} new samples...")

        for _ in range(n_samples):
            if not self.program_history:
                conv = Conversation(self.initial_state, self.system_prompt)
            else:

                parent = self._select_parent()
                conv = Conversation(self.initial_state, self.system_prompt)
                conv.messages = parent.conversation.messages.copy()

            tasks.append(self._generate_program_async(conv))

        results = await asyncio.gather(*tasks)
        return [r.program for r in results if r.program is not None]

    async def search(self,
                     n_iterations: int,
                     samples_per_iteration: int,
                     timeout: int = 60) -> List[Program]:
        """Run parallel MCTS search to find best program sequences"""
        best_programs = []

        for iteration in range(n_iterations):
            # Generate programs in parallel
            print(f"Generating programs for iteration {iteration}")
            new_programs = await self._generate_programs_batch(samples_per_iteration)

            if not new_programs:
                print("No programs generated")
                continue

            # Evaluate programs
            rewards, states, responses = await self.evaluator.evaluate_programs(
                new_programs, timeout
            )

            # Update programs with results
            for prog, reward, state, response in zip(new_programs, rewards, states, responses):
                prog.value = reward
                prog.state = state
                prog.conversation.add_result(prog.code, reward, response, state)
                self.program_history.append(prog)

                if len(best_programs) < 5 or reward > best_programs[-1].value:
                    best_programs.append(prog)
                    best_programs.sort(key=lambda p: p.value, reverse=True)
                    best_programs = best_programs[:5]

        await self.executor.shutdown(wait=True)
        return best_programs

    def _select_parent(self) -> Program:
        """Select program to build upon using softmax over rewards"""
        recent = self.program_history[-20:]
        weights = np.array([p.value for p in recent])
        weights = np.exp(weights - np.max(weights))
        weights /= weights.sum()
        return np.random.choice(recent, p=weights)