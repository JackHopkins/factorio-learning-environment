import asyncio
import copy
import json
from asyncio import sleep
from random import random
from typing import List

import psycopg2
import tenacity
from fle.agents.formatters.conversation_formatter_abc import (
    ConversationFormatter,
    DefaultFormatter,
)
from fle.agents.llm.parsing import PythonParser
from tenacity import retry, retry_if_exception_type, wait_exponential

from fle.commons.db_client import DBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program

from fle.eval.evaluator import Evaluator
from fle.eval.algorithms.mcts.samplers import DBSampler


class MCTS:
    def __init__(
        self,
        api_factory: "APIFactory",  # noqa
        db_client: DBClient,
        evaluator: Evaluator,
        sampler: DBSampler,
        system_prompt: str,
        initial_state: GameState,
        formatter: ConversationFormatter = DefaultFormatter(),
        version=1,
        version_description="",
        presence_penalty=0,
        frequency_penalty=0,
        error_penalty=0,
        maximum_lookback=20,
    ):
        self.llm = api_factory
        self.db = db_client
        self.evaluator = evaluator
        self.system_prompt = system_prompt
        self.initial_state = initial_state
        self.sampler = sampler
        self.version = version
        self.version_description = version_description
        self.formatter = formatter
        self.retry_count = 0
        self.max_retries = 3
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.error_penalty = error_penalty
        self.maximum_lookback = maximum_lookback
        self.parser = PythonParser()

    # def _verify_response_is_python(self, content):
    #     code = content
    #     # Parse into an AST to verify that this is a program
    #     try:
    #         ast = compile(code, filename="<ast>", mode="exec")
    #     except SyntaxError:
    #         # Take the last line off and try again
    #         code = code.rsplit('\n', 1)[0] + '\n'
    #         ast = compile(code, filename="<ast>", mode="exec")
    #         #return self._verify_response_is_python(code)
    #
    #     return code
    #
    # def _extract_code_from_choice(self, choice) -> Optional[str]:
    #     """Extract code from a single completion choice"""
    #     if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
    #         content = choice.message.content
    #     elif hasattr(choice, 'text'):
    #         content = choice.text
    #     else:
    #         raise RuntimeError('Incorrect message format')
    #
    #     try:
    #         code = self._verify_response_is_python(content)
    #         return code, content
    #     except Exception as e:
    #         try:
    #             # Get all text between triple backticks with regex: ```\n?python(.+\n?)```
    #             code = re.findall(r'(?s)```(python)?\s*(.*?)\s*```', content)[0][1]
    #
    #             #code = content.replace("```python", "").replace('```', '')
    #             code = self._verify_response_is_python(code)
    #             return code, content
    #         except Exception as e1:
    #             # Sometimes it samples a leading line, before writing unblocked python code.
    #             code = "\n".join(content.split("\n")[1:])
    #             try:
    #                 code = self._verify_response_is_python(code)
    #                 return code, content
    #             except Exception as e2:
    #                 try:
    #                     content_split = content.split('from factorio_instance import *')
    #                     code = content_split[1].strip()
    #                     text_response = content_split[0].strip()
    #                     code = self._verify_response_is_python(code)
    #                     return code, text_response
    #                 except Exception as e3:
    #                     code = content.strip().replace('```python',"").replace('```', '')
    #                     docstring_delimiters = code.count('"""')
    #                     print(f"Failed to extract code from choice: {str(code)}")
    #                     if docstring_delimiters < 2:
    #                         code = code.replace('"""', '')
    #                     if code.count('```') == 1:
    #                         code = code.replace('```', '')
    #                     try:
    #                         code = self._verify_response_is_python(code)
    #                     except Exception as e4:
    #                         # As a last ditch, just wrap in docstrings
    #                         code = code.replace('"""', "").replace("#", "")
    #                         code = f'"""\n{code}\n"""'
    #
    #                     return code, content.strip()
    #                 #print(f"Failed to extract code from choice after removing leading line: {str(e2)}")
    #             print(f"Failed to extract code from choice: {str(e1)}")
    #             return None

    def _is_model_compatible_with_n_samples(self, model):
        """Check if the model is compatible with generating n samples in a single call"""
        return "gpt" in model or "o1" in model or "gemini" in model

    @retry(wait=wait_exponential(multiplier=1, min=3, max=30))
    async def _generate_programs_batch(
        self,
        conversation: Conversation,
        generation_params: GenerationParameters,
        meta={},
    ) -> List[Program]:
        """Generate multiple programs either through OpenAI's n parameter or parallel calls"""
        conversation = copy.deepcopy(conversation)

        formatted = await self.formatter.format_conversation(conversation)
        formatted_messages = self.formatter.to_llm_messages(formatted)
        # system_message = formatted_messages[0]

        # Take the most recent messages up to maximum_lookback, excluding the system message
        # recent_messages = formatted_messages[1:][-self.db.max_conversation_length:]

        # Combine system message with recent messages
        # formatted_messages = [system_message, *recent_messages]

        try:
            messages = conversation.model_dump()["messages"]
        except Exception:
            messages = conversation.dict()["messages"]

        try:
            if self._is_model_compatible_with_n_samples(
                generation_params.model
            ) and hasattr(self.llm, "acall"):
                # Use OpenAI's native n parameter support
                response = await self.llm.acall(
                    messages=formatted_messages,
                    n_samples=generation_params.n,
                    temperature=generation_params.temperature,
                    max_tokens=generation_params.max_tokens,
                    logit_bias=generation_params.logit_bias,
                    stop_sequences=generation_params.stop_sequences,
                    model=generation_params.model,
                    presence_penalty=self.presence_penalty,
                    frequency_penalty=self.frequency_penalty,
                )
                return await self._process_openai_response(
                    response, conversation, generation_params, messages, meta
                )
            else:
                # Make parallel calls for other providers
                # conversation.messages = formatted_messages
                return await self._generate_parallel(
                    conversation, generation_params, formatted_messages, messages, meta
                )
        except Exception as e:
            print(f"Batch program generation failed: {str(e)}")
            raise e

    async def _generate_parallel(
        self, conversation, generation_params, formatted_messages, messages, meta
    ) -> List[Program]:
        """Generate n programs in parallel for providers that don't support batch generation"""

        async def single_generation():
            try:
                response = await self.llm.acall(
                    messages=formatted_messages,
                    n_samples=1,  # Force single sample
                    temperature=generation_params.temperature,
                    max_tokens=generation_params.max_tokens,
                    logit_bias=generation_params.logit_bias,
                    stop_sequences=generation_params.stop_sequences,
                    model=generation_params.model,
                    presence_penalty=self.presence_penalty,
                    frequency_penalty=self.frequency_penalty,
                )
                if (
                    "sonnet" in generation_params.model
                    or "gemini" in generation_params.model
                    and len(formatted_messages) > 32
                ):
                    await sleep(
                        2 + random() * 2
                    )  # Sleep with jitter to avoid rate limiting issues
                return response
            except Exception as e:
                print(f"Single generation failed: {str(e)}")
                return None

        # Generate n responses in parallel
        responses = await asyncio.gather(
            *[single_generation() for _ in range(generation_params.n)],
            return_exceptions=True,
        )

        # Process successful responses
        programs = []
        for response in responses:
            if response is not None and not isinstance(response, Exception):
                program = await self._create_program(
                    response, conversation, messages, generation_params.model, meta
                )
                if program:
                    programs.append(program)

        return programs

    async def _create_program(
        self, response, conversation, messages, model, meta
    ) -> Program:
        """Create a Program instance from a single response"""
        if hasattr(response, "choices"):
            choice = response.choices[0]  # Assuming only one choice per call
            input_tokens = (
                response.usage.prompt_tokens if hasattr(response, "usage") else 0
            )
            output_tokens = (
                response.usage.completion_tokens if hasattr(response, "usage") else 0
            )
            total_tokens = input_tokens + output_tokens
        else:
            choice = response.content[0]
            input_tokens = (
                response.usage.input_tokens if hasattr(response, "usage") else 0
            )
            output_tokens = (
                response.usage.output_tokens if hasattr(response, "usage") else 0
            )
            total_tokens = input_tokens + output_tokens

        try:
            code, text_response = self.parser.extract_code(choice)
        except Exception as e:
            print(f"Failed to extract code from choice: {str(e)}")
            code = None

        if not code:
            return None

        program = Program(
            id=hash((code, json.dumps(messages))),
            code=code,
            conversation=conversation,
            response=code,
            token_usage=total_tokens,
            completion_token_usage=output_tokens,
            prompt_token_usage=input_tokens,
            version=self.version,
            model=model,
            version_description=self.version_description,
            meta={"text_response": text_response, "model": model},
            depth=len(messages)
            - 2,  # -2 because of the first 2 messages being system and initial user message
        )

        if meta:
            program.meta.update(meta)

        return program

    async def _process_openai_response(
        self, response, conversation, generation_params, messages, meta
    ) -> List[Program]:
        """Process OpenAI's response with multiple choices"""
        programs = []
        total_tokens = completion_tokens = prompt_tokens = 0
        if hasattr(response, "usage"):
            total_tokens = (
                response.usage.total_tokens
                if response.usage.total_tokens
                else response.usage.totalTokens
            )
            completion_tokens = (
                response.usage.completion_tokens
                if response.usage.completion_tokens
                else response.usage.completionTokens
            )
            prompt_tokens = (
                response.usage.prompt_tokens
                if response.usage.prompt_tokens
                else response.usage.promptTokens
            )

        for choice in response.choices:
            code, text_response = self.parser.extract_code(choice)
            if code:
                programs.append(
                    Program(
                        id=hash((code, json.dumps(messages))),
                        code=code,
                        conversation=conversation,
                        response=choice.message.content,
                        token_usage=total_tokens // generation_params.n,
                        completion_token_usage=completion_tokens // generation_params.n,
                        prompt_token_usage=prompt_tokens // generation_params.n,
                        version=self.version,
                        version_description=self.version_description,
                        meta={
                            "text_response": text_response,
                            "model": generation_params.model,
                        },
                    )
                )
                if meta:
                    programs[-1].meta.update(meta)
        return programs

    async def search(
        self, n_iterations: int, samples_per_iteration: int, skip_failures: bool = False
    ):
        """
        Search for the best program using Monte Carlo Tree Search (MCTS).
        :param n_iterations: Number of iterations to perform.
        :param samples_per_iteration: Number of programs to sample per iteration.
        :param skip_failures: Whether to skip saving failed program generations.
        """

        for iteration in range(n_iterations):
            print(f"Starting iteration {iteration}")
            await self.run_iteration(
                samples_per_iteration, skip_failures, iteration, n_iterations
            )
            self.evaluator.logger.update_progress()

    @tenacity.retry(
        retry=retry_if_exception_type(psycopg2.Error),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=tenacity.stop_after_attempt(3),
    )
    async def run_iteration(
        self, samples_per_iteration, skip_failures, iteration, n_iterations
    ):
        """Run a single MCTS iteration with retries for concurrent operations"""
        try:
            parent = await self.sampler.sample_parent(
                version=self.version, maximum_lookback=self.maximum_lookback
            )
            if parent:
                start_state = parent.state
                conversation = parent.conversation
            else:
                start_state = self.initial_state
                self.evaluator.instances[0].reset(start_state)
                entities = self.evaluator.instances[0].get_entities()
                conversation = Conversation(
                    messages=[
                        Message(role="system", content=self.system_prompt),
                        # Message(role="user", content=PLANNING_ADDITION_PROMPT),
                        Message(
                            role="assistant",
                            content="print(f'Inventory: {inspect_inventory()}')\n"
                            "print(f'Entities: {get_entities()}')\n",
                        ),
                        Message(
                            role="user",
                            content=f"1: ('Inventory: {start_state.inventories[0].__dict__}')\n"
                            f"2: ('Entities: {entities}')",
                        ),
                    ]
                )

            self.evaluator.set_sampling_status()
            self.evaluator.set_iteration(iteration, n_iterations)
            generation_parameters = GenerationParameters(
                n=samples_per_iteration, model=self.llm.model, presence_penalty=0.7
            )
            # Generate multiple programs from same parent
            programs = await self._generate_programs_batch(
                conversation, generation_parameters
            )
            if not programs:
                return

            programs = [p for p in programs if p is not None]
            for program in programs:
                program.parent_id = parent.id if parent else None

            evaluated_programs = await self.evaluator.evaluate_batch(
                programs, start_state
            )

            # Use a connection pool or new connections for parallel saves
            save_tasks = []
            for program in evaluated_programs:
                if program.state is not None:
                    if not skip_failures or program.value is not None:
                        save_tasks.append(self.db.create_program(program))

            if save_tasks:
                await asyncio.gather(*save_tasks)

                # Visit parent
                await self.sampler.visit(parent.id, len(save_tasks))

        except Exception as e:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                print(f"Max retries ({self.max_retries}) reached. Error: {str(e)}")
                self.retry_count = 0
                raise e
            raise e
