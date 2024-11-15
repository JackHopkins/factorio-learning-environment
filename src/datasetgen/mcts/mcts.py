import asyncio
import json
from typing import Optional, List

from datasetgen.mcts.conversation import Conversation, Message
from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.factorio_evaluator import FactorioEvaluator
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.program import Program


class MCTS:
    def __init__(self,
                 llm_factory: 'LLMFactory',
                 db_client: DBClient,
                 evaluator: FactorioEvaluator,
                 system_prompt: str,
                 initial_state: GameState):

        self.llm = llm_factory
        self.db = db_client
        self.evaluator = evaluator
        self.system_prompt = system_prompt
        self.initial_state = initial_state

    def _extract_code(self, response) -> str:
        content = response.content if "claude" in self.llm.model else response.choices[0].message.content
        return content.split('```python')[1].split('```')[0].strip()

    async def _generate_programs_batch(self, conversation: Conversation, n_samples: int) -> List[Program]:
        tasks = []
        messages = conversation.model_dump()['messages']

        async def generate_single():
            try:
                response = self.llm.call(messages=messages)
                code = self._extract_code(response)
                completion_token_usage = response.usage.completion_tokens if hasattr(response, 'usage') else None
                prompt_token_usage = response.usage.prompt_tokens if hasattr(response, 'usage') else None
                token_usage = response.usage.total_tokens if hasattr(response, 'usage') else None
                return Program(
                    code=code,
                    conversation=conversation,
                    token_usage=token_usage,
                    completion_token_usage=completion_token_usage,
                    prompt_token_usage=prompt_token_usage
                )
            except Exception as e:
                print(f"Program generation failed: {str(e)}")
                return None

        for _ in range(n_samples):
            tasks.append(generate_single())

        return [p for p in await asyncio.gather(*tasks) if p is not None]

    async def search(self, n_iterations: int, samples_per_iteration: int, timeout=60):
        for iteration in range(n_iterations):
            print(f"Starting iteration {iteration}")

            # Sample single parent for this iteration
            parent = await self.db.sample_parent()
            if parent:
                print(f"Sampling parent with id: {parent.id}, and reward: {parent.value} and trace length: {len(parent.conversation.messages)}")
                start_state = parent.state
                conversation = parent.conversation
            else:
                print("Sampling from initial state")
                start_state = self.initial_state
                conversation = Conversation(messages=[
                    Message(role="system", content=self.system_prompt),
                    Message(role="user", content=f"Inventory: {json.dumps(start_state.inventory.__dict__)}\n\nCreate a useful task that you can carry out in the current game and the python script to achieve the task.") #inventory
                ])

            # Generate multiple programs from same parent
            programs = await self._generate_programs_batch(conversation, samples_per_iteration)
            for program in programs:
                program.parent_id = parent.id if parent else None
                await self.db.create_program(program)

            # Evaluate all programs against same holdout
            if programs:
                print(f"Evaluating {len(programs)} programs against holdout")
                await self.evaluator.evaluate_batch(programs, start_state)