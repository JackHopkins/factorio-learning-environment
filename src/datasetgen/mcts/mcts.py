import asyncio
import json
from typing import Optional, List

import psycopg2
import tenacity
from tenacity import wait_exponential, retry, retry_if_exception_type

from datasetgen.mcts.model.conversation import Conversation, Message, GenerationParameters
from datasetgen.mcts.conversation_formatter import ConversationFormatter, DefaultFormatter, PLANNING_ADDITION_PROMPT
from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.factorio_evaluator import FactorioEvaluator
from datasetgen.mcts.model.game_state import GameState
from datasetgen.mcts.model.program import Program
from datasetgen.mcts.samplers.db_sampler import DBSampler


class MCTS:
    def __init__(self,
                 llm_factory: 'LLMFactory',
                 db_client: DBClient,
                 evaluator: FactorioEvaluator,
                 sampler: DBSampler,
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
        self.sampler = sampler
        self.version = version
        self.version_description=version_description
        self.formatter = formatter
        self.retry_count = 0
        self.max_retries = 3

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
            return code, None
        except Exception as e:
            try:
                content = choice.message.content
                content_split = content.split('```python')
                code = content_split[1].split('```')[0].strip()
                text_response = content_split[0].strip()
                code = self._verify_response_is_python(code)
                return code, text_response
            except Exception as e1:
                # Sometimes it samples a leading line, before writing unblocked python code.
                content = "\n".join(choice.message.content.split("\n")[1:])
                try:
                    code = self._verify_response_is_python(content)
                    return code, None
                except Exception as e2:
                    try:
                        content_split = content.split('from factorio_instance import *')
                        code = content_split[1].strip()
                        text_response = content_split[0].strip()
                        code = self._verify_response_is_python(code)
                        return code, text_response
                    except Exception as e2:
                        #print(f"Failed to extract code from choice after removing leading line and factorio_instance import: {str(e2)} \n\n`{content}`")
                        chain_of_thoughts = '"""\n'+content.strip().strip("\"")+'\n"""'
                        return chain_of_thoughts, content.strip()
                    #print(f"Failed to extract code from choice after removing leading line: {str(e2)}")
                print(f"Failed to extract code from choice: {str(e1)}")

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_programs_batch(self, conversation: Conversation, 
                                       generation_params: GenerationParameters,
                                       meta = {}
                                       ) -> List[Program]:
        """Generate multiple programs in a single API call using 'n' parameter"""
        formatted_messages = self.formatter.to_llm_messages(
            self.formatter.format_conversation(conversation)
        )
        if "claude" in generation_params.model:
            assert generation_params.n == 1, "Number of samples must be 1 for Claude"

        try:
            # Single API call to generate n_samples completions
            response = await self.llm.acall(
                messages=formatted_messages,
                n_samples=generation_params.n,
                temperature=generation_params.temperature,
                max_tokens=generation_params.max_tokens,
                logit_bias=generation_params.logit_bias,
                stop_sequences=generation_params.stop_sequences,
                model = generation_params.model,
                presency_penalty=generation_params.presency_penalty
            )

            programs = []
            try:
                messages = conversation.model_dump()['messages']
            except Exception as e:
                messages = conversation.dict()['messages']

            # Process all choices from the response
            if "claude" in generation_params.model:

                # Handle Claude response format
                code, text_response = self._extract_code_from_choice(response)
                if code:
                    programs.append(Program(
                        id=hash((code, json.dumps(messages))),
                        code=code,
                        conversation=conversation,
                        response = response.message.content,
                        token_usage=response.usage.total_tokens if hasattr(response, 'usage') else None,
                        completion_token_usage=response.usage.completion_tokens if hasattr(response, 'usage') else None,
                        prompt_token_usage=response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                        version=self.version,
                        version_description=self.version_description,
                        meta = {"text_response": text_response,
                                "model": generation_params.model}
                    ))
                    if meta:
                        programs[0].meta.update(meta)
            else:
                # Handle OpenAI response format with multiple choices
                for choice in response.choices:
                    code, text_response  = self._extract_code_from_choice(choice)
                    if code:
                        programs.append(Program(
                            id=hash((code, json.dumps(messages))),
                            code=code,
                            conversation=conversation,
                            response = choice.message.content,
                            token_usage=response.usage.total_tokens // generation_params.n if hasattr(response,
                                                                                            'usage') else None,
                            completion_token_usage=response.usage.completion_tokens // generation_params.n if hasattr(response,
                                                                                                            'usage') else None,
                            prompt_token_usage=response.usage.prompt_tokens // generation_params.n if hasattr(response,
                                                                                                    'usage') else None,
                            version=self.version,
                            version_description=self.version_description,
                            meta = {"text_response": text_response,
                                    "model": generation_params.model}
                        ))
                        if meta:
                            programs[-1].meta.update(meta)

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
            await self.run_iteration(samples_per_iteration, skip_failures)
            self.evaluator.logger.update_progress()

    @tenacity.retry(
        retry=retry_if_exception_type(psycopg2.Error),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=tenacity.stop_after_attempt(3)
    )
    async def run_iteration(self, samples_per_iteration, skip_failures):
        """Run a single MCTS iteration with retries for concurrent operations"""
        try:
            parent = await self.sampler.sample_parent(version=self.version)
            if parent:
                start_state = parent.state
                conversation = parent.conversation
            else:
                start_state = self.initial_state
                conversation = Conversation(messages=[
                    Message(role="system", content=self.system_prompt),
                    Message(role="user",
                            content=f"Inventory: {json.dumps(start_state.inventory.__dict__)}\n\n{PLANNING_ADDITION_PROMPT}")
                ])

            self.evaluator.set_sampling_status()
            generation_parameters = GenerationParameters(n = samples_per_iteration,
                                                         model = self.llm.model,
                                                         presency_penalty=0.7)
            # Generate multiple programs from same parent
            programs = await self._generate_programs_batch(conversation, generation_parameters)
            if not programs:
                return

            programs = [p for p in programs if p is not None]
            for program in programs:
                program.parent_id = parent.id if parent else None

            evaluated_programs = await self.evaluator.evaluate_batch(programs, start_state)

            # Use a connection pool or new connections for parallel saves
            save_tasks = []
            for program in evaluated_programs:
                if program.state is not None:
                    if not skip_failures or program.value is not None:
                        save_tasks.append(self.db.create_program(program))

            if save_tasks:
                await asyncio.gather(*save_tasks)

        except Exception as e:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                print(f"Max retries ({self.max_retries}) reached. Error: {str(e)}")
                self.retry_count = 0
                raise e
            raise e
