import asyncio
import json
from typing import Optional, List

from datasetgen.mcts.conversation import Conversation, Message
from datasetgen.mcts.conversation_formatter import ConversationFormatter, DefaultFormatter, PLANNING_ADDITION_PROMPT
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
                 initial_state: GameState,
                 formatter: ConversationFormatter = DefaultFormatter(),
                 version=1,
                 ):

        self.llm = llm_factory
        self.db = db_client
        self.evaluator = evaluator
        self.system_prompt = system_prompt
        self.initial_state = initial_state
        self.version = version
        self.formatter = formatter

    def _extract_code(self, response) -> str:
        content = response.content if "claude" in self.llm.model else response.choices[0].message.content
        try:
            content = content.split('```python')[1].split('```')[0].strip()
        except IndexError as e:
            pass
        # Parse into an AST to verify that this is a program
        try:
            ast = compile(content, filename="<ast>", mode="exec")
        except SyntaxError as e:
            # Take the last line off and try again
            content = content.rsplit('\n', 1)[0] + '\n'
            try:
                ast = compile(content, filename="<ast>", mode="exec")
            except SyntaxError as e1:
                raise ValueError(f"Invalid Python code: {content}") from e

        return content.strip()


    async def _generate_programs_batch(self, conversation: Conversation, n_samples: int) -> List[Program]:
        tasks = []
        messages = conversation.model_dump()['messages']
        formatted_messages = self.formatter.to_llm_messages(
            self.formatter.format_conversation(conversation)
        )

        async def generate_single():
            try:
                response = self.llm.call(messages=formatted_messages)
                code = self._extract_code(response)
                completion_token_usage = response.usage.completion_tokens if hasattr(response, 'usage') else None
                prompt_token_usage = response.usage.prompt_tokens if hasattr(response, 'usage') else None
                token_usage = response.usage.total_tokens if hasattr(response, 'usage') else None
                id_ = hash((code, json.dumps(messages))) # create an ID by hashing the code and conversation
                return Program(
                    id=id_,
                    code=code,
                    conversation=conversation,
                    token_usage=token_usage,
                    completion_token_usage=completion_token_usage,
                    prompt_token_usage=prompt_token_usage,
                    version=self.version
                )
            except Exception as e:
                print(f"Program generation failed: {str(e)}")
                return None

        for _ in range(n_samples):
            tasks.append(generate_single())

        return [p for p in await asyncio.gather(*tasks) if p is not None]

    async def search(self,
                     n_iterations: int,
                     samples_per_iteration: int,
                     skip_failures: bool = False):
        """
        Search for the best program using Monte Carlo Tree Search (MCTS).
        :param n_iterations: Number of iterations to perform.
        :param samples_per_iteration: Number of programs to sample per iteration.
        :param skip_failures: Whether to skip saving failed program generations.
        """

        for iteration in range(n_iterations):
            print(f"Starting iteration {iteration}")

            # Sample single parent for this iteration
            parent = await self.db.sample_parent(version=self.version)
            if parent:
                print(
                    f"Sampling parent with id: {parent.id}, and reward: {parent.value} and trace length: {len(parent.conversation.messages)}")
                start_state = parent.state
                conversation = parent.conversation
            else:
                print("Sampling from initial state")
                start_state = self.initial_state
                conversation = Conversation(messages=[
                    Message(role="system", content=self.system_prompt),
                    Message(role="user",
                            content=f"Inventory: {json.dumps(start_state.inventory.__dict__)}\n\n{PLANNING_ADDITION_PROMPT}")
                ])

            # Generate multiple programs from same parent
            programs = await self._generate_programs_batch(conversation, samples_per_iteration)
            if not programs:
                continue

            # Filter out None programs
            programs = [p for p in programs if p is not None]

            # Set parent IDs
            for program in programs:
                program.parent_id = parent.id if parent else None

            try:
                # Evaluate all programs against same holdout first
                print(f"Evaluating {len(programs)} programs against holdout")
                evaluated_programs = await self.evaluator.evaluate_batch(programs, start_state)

                # Only save programs that were successfully evaluated
                for program in evaluated_programs:
                    if program.state is not None:
                        if skip_failures and program.value is not None:
                            await self.db.create_program(program)
                        else:
                            await self.db.create_program(program)
                    else:
                        print(f"Skipping program save due to missing evaluation data")

            except Exception as e:
                print(f"Evaluation failed for batch: {str(e)}")
                continue