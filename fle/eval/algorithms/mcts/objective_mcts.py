import asyncio
import json
from typing import List

import psycopg2
import tenacity
from fle.agents.formatters.conversation_formatter_abc import (
    ConversationFormatter,
    DefaultFormatter,
)
from fle.agents.llm.api_factory import APIFactory
from tenacity import retry, retry_if_exception_type, wait_exponential

from fle.commons.db_client import DBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program
from fle.eval.evaluator import Evaluator

from .mcts import MCTS
from .samplers.db_sampler import DBSampler
from .samplers.objective_sampler import ObjectiveTreeSampler

OBJECTIVE_PLANNING_PROMPT = """
Your goal is to automate an increasingly complex factory process.
Identify an appropriate next step given your previous steps, and the feedback from the environment to achieve this goal. Each step should be indexed with N+1. 
Develop thorough step-by-step plans for how you can achieve your objective, and then create the python script that will achieve it. Do not repeat yourself.
If the environment indicates that your have successfully completed all the steps for the the current objective, simply write 'Objective: ' to move onto the next one. 
"""


class ObjectiveMCTS(MCTS):
    def __init__(
        self,
        api_factory: "APIFactory",
        db_client: DBClient,
        evaluator: Evaluator,
        sampler: DBSampler,
        system_prompt: str,
        initial_state: GameState,
        formatter: ConversationFormatter = DefaultFormatter(),
        version=1,
        version_description="",
        logit_bias=[],
        presence_penalty=0,
        frequency_penalty=0,
        objective_model: str = "ft:gpt-4o-mini-2024-07-18:paperplane-ai:plans-tree:AcZ8gHSo",
    ):
        self.logit_bias = logit_bias
        self.objective_tree_sampler = ObjectiveTreeSampler(
            APIFactory(model=objective_model)
        )
        super().__init__(
            api_factory,
            db_client,
            evaluator,
            sampler,
            system_prompt,
            initial_state,
            formatter,
            version,
            version_description,
            presence_penalty,
            frequency_penalty,
        )

    async def _get_objectives(self, conversation: Conversation) -> List[str]:
        if len(conversation.messages) == 0:
            previous_objectives = []
        elif "objectives" not in conversation.messages[-1].metadata:
            previous_objectives = []
        elif not conversation.messages[-1].metadata["objectives"]:
            previous_objectives = []
        else:
            previous_objectives = conversation.messages[-1].metadata["objectives"]

        objective = await self.objective_tree_sampler.sample_tree(
            previous_objectives, number=1
        )

        return previous_objectives + objective

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_programs_batch(
        self,
        conversation: Conversation,
        generation_params: GenerationParameters,
        meta={},
    ) -> List[Program]:
        """Generate multiple programs in a single API call using 'n' parameter"""

        # Initialize objectives if not provided
        if "objectives" not in meta:
            objectives = await self._get_objectives(conversation)
            meta["objectives"] = objectives
            objective = objectives[-1]
            self._append_inventory_check_messages(conversation, objective)
            conversation.messages[-1].metadata = {
                **conversation.messages[-1].metadata,
                "objectives": objectives,
            }

        # Prepare messages for LLM
        formatted_messages = self.formatter.to_llm_messages(
            self.formatter.format_conversation(conversation)
        )

        # Validate Claude-specific constraints
        if "claude" in generation_params.model:
            assert generation_params.n == 1, "Number of samples must be 1 for Claude"

        try:
            # Generate completions
            response = await self._generate_llm_response(
                formatted_messages, generation_params
            )
            return await self._process_llm_response(
                response, conversation, generation_params, meta
            )

        except Exception as e:
            print(f"Batch program generation failed: {str(e)}")
            return []

    def _append_inventory_check_messages(
        self, conversation: Conversation, objective: str
    ):
        """Append inventory check messages to the conversation"""
        conversation.messages.extend(
            [
                Message(
                    role="assistant",
                    content=f'"""\nObjective: {objective}\n"""\nprint("Inventory: ", inspect_inventory())\nprint("Entities: ", get_entities())\n',
                    metadata={"objectives": [objective]},
                ),
                Message(
                    role="user",
                    content="Execution Result: \n0: ('Inventory: ', {})\n1: ('Entities: ': {})",
                    metadata={"objectives": [objective]},
                ),
            ]
        )

    async def _generate_llm_response(
        self, formatted_messages: list, params: GenerationParameters
    ):
        """Generate response from LLM with given parameters"""
        return await self.llm.acall(
            messages=formatted_messages,
            n_samples=params.n,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
            logit_bias=params.logit_bias,
            stop_sequences=params.stop_sequences,
            model=params.model,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
        )

    async def _process_llm_response(
        self,
        response,
        conversation: Conversation,
        params: GenerationParameters,
        meta: dict,
    ) -> List[Program]:
        """Process LLM response and create Program objects"""
        programs = []
        try:
            messages = conversation.model_dump()["messages"]
        except Exception:
            messages = conversation.dict()["messages"]

        if "claude" in params.model:
            programs = await self._handle_claude_response(
                response, messages, meta, params.model
            )
        else:
            programs = await self._handle_openai_response(
                response, messages, meta, params
            )

        return programs

    async def _handle_claude_response(self, response, messages, meta, model):
        """Handle Claude-specific response format"""
        programs = []
        code, text_response = self._extract_code_from_choice(response)

        if not code:
            objectives = await self._get_objectives(
                Conversation(messages=[Message(**msg.dict()) for msg in messages])
            )
            code = f'"""\nObjective: {objectives[-1]}\n"""'

        if code:
            # Create a new conversation for this program
            new_conversation = Conversation(
                messages=[Message(**msg.dict()) for msg in messages]
            )
            # Get objectives for this specific conversation
            objectives = await self._get_objectives(new_conversation)
            # Append inventory check messages to this conversation only
            self._append_inventory_check_messages(new_conversation, objectives[-1])

            program = self._create_program(
                code=code,
                messages=new_conversation.messages,
                conversation=new_conversation,
                response_content=response.message.content,
                token_usage=self._get_token_usage(response),
                model=model,
                text_response=text_response,
                meta={**meta, "objectives": objectives},
            )
            programs.append(program)
        return programs

    async def _handle_openai_response(self, response, messages, meta, params):
        """Handle OpenAI response format with multiple choices"""
        programs = []

        for choice in response.choices:
            code, text_response = self._extract_code_from_choice(choice)
            objectives = messages[-1]["metadata"]["objectives"]
            if not code:
                # Create new conversation for each program
                new_conversation = Conversation(
                    messages=[Message(**msg) for msg in messages]
                )
                objectives = await self._get_objectives(new_conversation)
                code = f'"""\nObjective: {objectives[-1]}\n"""'

            if code:
                # Create new conversation for this program
                new_conversation = Conversation(
                    messages=[Message(**msg) for msg in messages]
                )

                program = self._create_program(
                    code=code,
                    messages=new_conversation.messages,
                    conversation=new_conversation,
                    response_content=choice.message.content,
                    token_usage=self._get_token_usage(response, divide_by_n=params.n),
                    model=params.model,
                    text_response=text_response,
                    meta={**meta, "objectives": objectives},
                )
                programs.append(program)
        return programs

    def _create_program(
        self,
        code,
        messages,
        conversation,
        response_content,
        token_usage,
        model,
        text_response,
        meta,
    ):
        """Create a Program object with given parameters"""
        program = Program(
            id=hash(
                (
                    code,
                    json.dumps(
                        [
                            msg.__dict__ if isinstance(msg, Message) else msg
                            for msg in messages
                        ]
                    ),
                )
            ),
            code=code,
            conversation=conversation,
            response=response_content,
            token_usage=token_usage.get("total"),
            completion_token_usage=token_usage.get("completion"),
            prompt_token_usage=token_usage.get("prompt"),
            version=self.version,
            version_description=self.version_description,
            meta={"text_response": text_response, "model": model},
        )
        if meta:
            program.meta.update(meta)
        return program

    def _get_token_usage(self, response, divide_by_n=1):
        """Extract token usage from response"""
        if not hasattr(response, "usage"):
            return {"total": None, "completion": None, "prompt": None}

        return {
            "total": response.usage.total_tokens // divide_by_n,
            "completion": response.usage.completion_tokens // divide_by_n,
            "prompt": response.usage.prompt_tokens // divide_by_n,
        }

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
            await self.run_iteration(samples_per_iteration, skip_failures)
            self.evaluator.logger.update_progress()

    @tenacity.retry(
        retry=retry_if_exception_type(psycopg2.Error),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=tenacity.stop_after_attempt(3),
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
                conversation = Conversation(
                    messages=[
                        Message(role="system", content=self.system_prompt),
                        Message(
                            role="user",
                            content=OBJECTIVE_PLANNING_PROMPT,
                            metadata={
                                "objectives": ["1. Automate resource production"]
                            },
                        ),
                    ]
                )

            self.evaluator.set_sampling_status()
            generation_parameters = GenerationParameters(
                n=samples_per_iteration,
                model=self.llm.model,
                stop_sequences=["Objective:"],
                logit_bias=self.logit_bias,
                presence_penalty=0.7,
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

        except Exception as e:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                print(f"Max retries ({self.max_retries}) reached. Error: {str(e)}")
                self.retry_count = 0
                raise e
            raise e
