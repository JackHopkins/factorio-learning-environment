import asyncio
import json
from typing import Optional, List, Dict

from tenacity import wait_exponential, retry

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
                 version_description=""
                 ):

        self.llm = llm_factory
        self.db = db_client
        self.evaluator = evaluator
        self.system_prompt = system_prompt
        self.initial_state = initial_state
        self.version = version
        self.version_description=version_description
        self.formatter = formatter

    def _verify_response_is_python(self, content):
        code = content
        # Parse into an AST to verify that this is a program
        try:
            ast = compile(code, filename="<ast>", mode="exec")
        except SyntaxError:
            # Take the last line off and try again
            code = code.rsplit('\n', 1)[0] + '\n'
            ast = compile(code, filename="<ast>", mode="exec")

        return code

    def _extract_code_from_choice(self, choice) -> Optional[str]:
        """Extract code from a single completion choice"""
        code = ""
        try:
            content = choice.message.content
            code = self._verify_response_is_python(content)
            return code
        except Exception as e:
            try:
                content = choice.message.content
                code = content.split('```python')[1].split('```')[0].strip()
                code = self._verify_response_is_python(code)
                return code
            except Exception as e1:
                # Sometimes it samples a leading line, before writing unblocked python code.
                content = "\n".join(choice.message.content.split("\n")[1:])
                try:
                    code = self._verify_response_is_python(content)
                    return code
                except Exception as e2:
                    try:
                        code = content.split('from factorio_instance import *')[1].strip()
                        code = self._verify_response_is_python(code)
                        return code
                    except Exception as e2:
                        print(f"Failed to extract code from choice after removing leading line and factorio_instance import: {str(e2)}")
                        return None
                    print(f"Failed to extract code from choice after removing leading line: {str(e2)}")
                print(f"Failed to extract code from choice: {str(e1)}")

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_programs_batch(self, conversation: Conversation, n_samples: int, logit_bias: Optional[Dict[str, float]] = None) -> List[Program]:
        """Generate multiple programs in a single API call using 'n' parameter"""
        formatted_messages = self.formatter.to_llm_messages(
            self.formatter.format_conversation(conversation)
        )
        if "claude" in self.llm.model:
            assert n_samples == 1, "Number of samples must be 1 for Claude"

        try:
            # Single API call to generate n_samples completions
            response = self.llm.call(
                messages=formatted_messages,
                max_tokens=2048,
                n=n_samples,
                temperature=0.7,  # Adjust as needed
                logit_bias=logit_bias
            )

            programs = []
            messages = conversation.model_dump()['messages']

            # Process all choices from the response
            if "claude" in self.llm.model:

                # Handle Claude response format
                code = self._extract_code_from_choice(response)
                if code:
                    programs.append(Program(
                        id=hash((code, json.dumps(messages))),
                        code=code,
                        conversation=conversation,
                        token_usage=response.usage.total_tokens if hasattr(response, 'usage') else None,
                        completion_token_usage=response.usage.completion_tokens if hasattr(response, 'usage') else None,
                        prompt_token_usage=response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                        version=self.version,
                        version_description=self.version_description
                    ))
            else:
                # Handle OpenAI response format with multiple choices
                for choice in response.choices:
                    code = self._extract_code_from_choice(choice)
                    if code:
                        programs.append(Program(
                            id=hash((code, json.dumps(messages))),
                            code=code,
                            conversation=conversation,
                            token_usage=response.usage.total_tokens // n_samples if hasattr(response,
                                                                                            'usage') else None,
                            completion_token_usage=response.usage.completion_tokens // n_samples if hasattr(response,
                                                                                                            'usage') else None,
                            prompt_token_usage=response.usage.prompt_tokens // n_samples if hasattr(response,
                                                                                                    'usage') else None,
                            version=self.version,
                            version_description=self.version_description
                        ))

            return programs

        except Exception as e:
            print(f"Batch program generation failed: {str(e)}")
            return []

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

            self.evaluator.set_sampling_status()
            # Generate multiple programs from same parent
            programs = await self._generate_programs_batch(conversation, samples_per_iteration)
            if not programs:
                self.evaluator.logger.update_progress()
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
                self.evaluator.logger.update_progress()
                continue

            self.evaluator.logger.update_progress()