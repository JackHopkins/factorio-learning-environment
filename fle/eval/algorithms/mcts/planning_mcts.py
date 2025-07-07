import ast
import asyncio
import json
import os
from typing import List, Optional, Tuple

from fle.eval.algorithms.mcts.mcts import MCTS
from fle.eval.algorithms.mcts.planning_models import (
    InitialPlanOutput,
    LanguageOutput,
    PlanOutput,
    Step,
    TaskOutput,
)
from tenacity import retry, wait_exponential

from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program


def get_mining_setup(instance):
    mining_setup = instance.namespace.get_entities()
    if len(mining_setup) == 0:
        mining_setup = "There are no entities on the map"
    else:
        mining_setup = f"The following entities comprise your factory: {mining_setup}"
    return mining_setup


class PlanningMCTS(MCTS):
    def __init__(
        self,
        *args,
        planning_model,
        executor_model,
        objective_model,
        step_executor_prompt_path,
        step_generator_prompt_path,
        step_judge_prompt_path,
        example_plan_prompt_path,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.planning_model = planning_model
        self.executor_model = executor_model
        self.objective_model = objective_model
        self.api_description = self.evaluator.instances[0].get_system_prompt()
        self.step_executor_prompt_path = step_executor_prompt_path
        self.step_generator_prompt_path = step_generator_prompt_path
        self.step_judge_prompt_path = step_judge_prompt_path
        self.example_plan_prompt_path = example_plan_prompt_path
        self.step_executor_system_prompt, self.step_executor_user_prompt = (
            self.read_in_prompts(step_executor_prompt_path)
        )
        self.step_generator_system_prompt, self.step_generator_user_prompt = (
            self.read_in_prompts(step_generator_prompt_path)
        )
        self.step_judge_system_prompt, self.step_judge_user_prompt = (
            self.read_in_prompts(step_judge_prompt_path)
        )
        self.example_plan_system_prompt, self.example_plan_user_prompt = (
            self.read_in_prompts(example_plan_prompt_path)
        )

        # format the 2 system prompts
        self.step_executor_system_prompt = self.step_executor_system_prompt.format(
            schema=self.api_description
        )
        self.example_plan_system_prompt = self.example_plan_system_prompt.format(
            schema=self.api_description
        )

        self.max_steps_per_objective = 12
        self.number_of_steps_for_judge = 3

    def read_in_prompts(self, path):
        system_prompt_path = os.path.join(path, "system_prompt.md")
        user_prompt_path = os.path.join(path, "user_prompt.md")
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
        with open(user_prompt_path, "r") as f:
            user_prompt = f.read()
        return system_prompt, user_prompt

    def _split_into_chunks(self, program_code: str) -> List[Program]:
        """Split the program code into chunks based on docstrings."""

        program_code = program_code.replace(
            "from factorio_instance import *", ""
        ).strip()
        lines = program_code.splitlines()
        chunks = []
        module = ast.parse(program_code)

        # Find all docstrings and their positions
        docstring_positions = []
        for node in module.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                docstring_positions.append(
                    (node.lineno - 1, node.end_lineno - 1, node.value.s)
                )

        if not docstring_positions:
            return []

        # Handle everything before first docstring
        first_docstring_start = docstring_positions[0][0]
        if first_docstring_start > 0:
            preamble = lines[:first_docstring_start]
            if any(
                line.strip() for line in preamble
            ):  # If there's any non-empty content
                chunks.append(
                    Program(
                        code="\n".join(preamble), conversation=Conversation(messages=[])
                    )
                )

        # Process each chunk
        for i, (start_pos, end_pos, docstring) in enumerate(docstring_positions):
            chunk_lines = []

            # Add docstring lines
            chunk_lines.extend(lines[start_pos : end_pos + 1])

            # Add code lines until next docstring or end
            if i < len(docstring_positions) - 1:
                next_start = docstring_positions[i + 1][0]
                chunk_lines.extend(lines[end_pos + 1 : next_start])
            else:
                # For last chunk, add all remaining lines
                chunk_lines.extend(lines[end_pos + 1 :])

            # Create program for this chunk
            if chunk_lines:
                chunks.append(
                    Program(
                        code="\n".join(chunk_lines),
                        conversation=Conversation(messages=[]),
                    )
                )

        return chunks

    async def _evaluate_step(
        self, step: Step, start_state: GameState, instance_id: int, parent_id
    ) -> Tuple[List[Program], float]:
        # self.evaluator.holdout.reset(start_state)
        # holdout_future = asyncio.create_task(self.evaluator._run_holdout())
        entity_list = []
        try:
            instance = self.evaluator.instances[instance_id]
            step.start_state = GameState.from_instance(instance)
            self.evaluator.logger.update_instance(instance_id, status="executing")

            (
                reward,
                state,
                response,
                entities,
                achievements,
                ticks,
            ) = await self.evaluator._evaluate_single(
                instance_id, step.program, instance
            )
            entity_list.append(entities)
            step.end_state = state
            step.reward = reward

        except Exception as e:
            print(f"Error during evaluation: {e}")
            raise e  # Propagate the exception to handle it elsewhere if needed.

        # holdout_value = await holdout_future
        step.program.value = step.reward - (
            abs(self.error_penalty) if "error" in response else 0
        )
        step.program.achievements = achievements
        step.program.raw_reward = step.reward
        step.program.holdout_value = step.program.value
        step.program.state = step.end_state
        step.program.response = response
        step.program.parent_id = parent_id
        step.program.conversation.add_result(
            step.program.code, response, score=step.reward, advantage=step.reward
        )
        return step, step.program.value, entity_list

    def get_inventory_dict(self, inventory):
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        return inventory_dict

    async def _get_tasks(
        self, parent: Program = None, samples_per_iteration: int = 1
    ) -> List[LanguageOutput]:
        start_state = (
            parent.state if parent else self.initial_state
        )  # We should make this random as well tbh
        # reset the first instance
        self.evaluator.instances[0].reset(start_state)
        # get the mining setup
        mining_setup = get_mining_setup(self.evaluator.instances[0])
        starting_inventory = self.evaluator.instances[0].inspect_inventory()
        conversation = Conversation(
            messages=[
                Message(role="system", content=self.system_prompt),
                Message(
                    role="user",
                    content=f"Your starting inventory is {starting_inventory}. Your initial mining setup is: {mining_setup}. Create a useful task that you can carry out in the current game and the python script to achieve the task",
                ),
            ]
        )
        generation_params = GenerationParameters(
            model=self.objective_model, n=samples_per_iteration, stop_sequences=["\n"]
        )
        inventory_dict = self.get_inventory_dict(starting_inventory)
        game_state_str = GameState.from_instance(self.evaluator.instances[0]).entities
        tasks = await self._generate_natural_language_batch(
            conversation,
            generation_params,
            meta={
                "type": "objective_generation",
                "inventory": inventory_dict,
                "mining_setup": mining_setup,
                "game_state": game_state_str,
            },
        )
        task_outputs = []
        for task in tasks:
            # get everything until the first newline
            task_string = task.response.split("\n")[0].strip()
            task_string = (
                task_string.lower()
                .replace("sure! the task i will carry out is", "")
                .strip()
            )
            if "." in task_string:
                task_string = task_string.split(".")[0]
            task_outputs.append(TaskOutput(task=task_string, language_output=task))

        return task_outputs, start_state

    async def generate_plans(
        self, task_outputs: List[TaskOutput]
    ) -> List[InitialPlanOutput]:
        generation_params = GenerationParameters(
            model=self.executor_model, stop_sequences=["```"]
        )
        conversations_to_process = [
            Conversation(
                messages=[
                    Message(role="system", content=self.example_plan_system_prompt),
                    Message(
                        role="user",
                        content=self.example_plan_user_prompt.format(
                            task=task_output.task
                        ),
                    ),
                ]
            )
            for task_output in task_outputs
        ]

        initial_plans = [
            asyncio.ensure_future(
                self._generate_natural_language_batch(
                    conversation,
                    generation_params,
                    meta={"type": "initial_plan_generation"},
                )
            )
            for conversation in conversations_to_process
        ]
        # initial_plans = [self._generate_natural_language_batch(conversation, generation_params, meta={"type": "initial_plan_generation"}) for conversation in conversations_to_process]

        responses = await asyncio.gather(*initial_plans)
        plan_outputs = {}
        for idx, response in enumerate(responses):
            initial_plan = response[0].response.strip()
            new_line_idx = initial_plan.rfind("\n")
            if new_line_idx != -1:
                initial_plan = initial_plan[:new_line_idx].strip()
            initial_plan_output = InitialPlanOutput(
                initial_plan=initial_plan, language_output=response[0]
            )
            # plan id coincides with instance id it will be evaluated on
            plan_output = PlanOutput(
                task=task_outputs[idx],
                initial_plan=initial_plan_output,
                meta={"plan_id": idx},
            )
            plan_outputs[idx] = plan_output

        return plan_outputs

    def format_log_string(self, plan_output: PlanOutput):
        return (
            "\n\n".join(plan_output.logs)
            if plan_output.logs
            else "The agent has not yet interacted with the world"
        )

    async def generate_next_step_candidates(
        self, plan_outputs: dict[int, PlanOutput]
    ) -> List[PlanOutput]:
        generation_params = GenerationParameters(
            model=self.planning_model, max_tokens=4096
        )
        conversations_to_process = []
        for instance_id, plan_output in plan_outputs.items():
            if plan_output.success:
                continue
            instance = self.evaluator.instances[instance_id]
            mining_setup = get_mining_setup(instance)
            starting_inventory = instance.inspect_inventory()
            starting_inventory_dict = self.get_inventory_dict(starting_inventory)
            log_str = self.format_log_string(plan_output)
            objective = plan_output.task.task
            initial_plan = plan_output.initial_plan.initial_plan
            user_message = self.step_generator_user_prompt.format(
                mining_setup=mining_setup,
                starting_inventory=starting_inventory,
                logs=log_str,
                objective=objective,
                plan=initial_plan,
            )
            conversations_to_process += [
                (
                    Conversation(
                        messages=[
                            Message(
                                role="system", content=self.step_generator_system_prompt
                            ),
                            Message(role="user", content=user_message),
                        ]
                    ),
                    plan_output.meta["plan_id"],
                )
            ] * self.number_of_steps_for_judge

        step_outputs = [
            asyncio.ensure_future(
                self._generate_natural_language_batch(
                    conversation[0],
                    generation_params,
                    meta={
                        "type": "next_step_candidates",
                        "plan_id": conversation[1],
                        "mining_setup": mining_setup,
                        "starting_inventory": starting_inventory_dict,
                    },
                )
            )
            for conversation in conversations_to_process
        ]
        responses = await asyncio.gather(*step_outputs)
        step_output_objects = {}
        for idx, response in enumerate(responses):
            output = response[0]
            plan_id = output.meta["plan_id"]
            step_output = output.response.strip()
            # first check if the step says it is a success
            # We need to create a new step object
            if plan_id not in step_output_objects:
                step_output_objects[plan_id] = Step(candidate_language_outputs=[])
            step_output_objects[plan_id].candidate_language_outputs.append(output)
            if "#output" in step_output.lower() and "#step" not in step_output.lower():
                step_output = step_output.lower().split("#output")[-2].strip()
                # put the success flag in the plan_output as True
                plan_outputs[plan_id].success = True
                plan_outputs[plan_id].final_output = step_output
                step_output_objects[plan_id].final_step = step_output

        for plan_id, step_output in step_output_objects.items():
            plan_outputs[plan_id].steps.append(step_output)

        return plan_outputs

    async def get_next_step_with_judge(
        self, plan_outputs: dict[int, PlanOutput]
    ) -> List[PlanOutput]:
        generation_params = GenerationParameters(
            model=self.planning_model, max_tokens=4096
        )
        conversations_to_process = []
        for instance_id, plan_output in plan_outputs.items():
            if plan_output.success:
                continue
            # This should be done more efficiently,this should be gotten from the step to process
            instance = self.evaluator.instances[instance_id]
            mining_setup = get_mining_setup(instance)
            starting_inventory = instance.inspect_inventory()
            log_str = self.format_log_string(plan_output)
            objective = plan_output.task.task
            initial_plan = plan_output.initial_plan.initial_plan
            step_to_process = plan_output.steps[-1].candidate_language_outputs
            step_candidate_str = ""
            for step_idx, step_candidate in enumerate(step_to_process):
                step_candidate_str += f"Step {step_idx}\n{step_candidate.response}\n\n"
            user_message = self.step_judge_user_prompt.format(
                objective=objective,
                starting_inventory=starting_inventory,
                mining_setup=mining_setup,
                logs=log_str,
                plan=initial_plan,
                analysis_step_str=step_candidate_str,
            )
            conversations_to_process.append(
                (
                    Conversation(
                        messages=[
                            Message(
                                role="system", content=self.step_judge_system_prompt
                            ),
                            Message(role="user", content=user_message),
                        ]
                    ),
                    plan_output.meta["plan_id"],
                )
            )

        step_outputs = [
            asyncio.ensure_future(
                self._generate_natural_language_batch(
                    conversation[0],
                    generation_params,
                    meta={"type": "next_step_judge", "plan_id": conversation[1]},
                )
            )
            for conversation in conversations_to_process
        ]
        responses = await asyncio.gather(*step_outputs)
        for idx, response in enumerate(responses):
            output = response[0]
            plan_id = output.meta["plan_id"]
            step_output = output.response.strip()
            # add the output to the last step
            plan_outputs[plan_id].steps[-1].judge_language_output_step = output
            plan_outputs[plan_id].steps[-1].judge_step_str = step_output

            # split it by #step
            if "#STEP" in step_output:
                step = step_output.split("#STEP")[-2].strip()
            elif "OUTPUT" in step_output:
                step = step_output.split("OUTPUT")[-1].strip()
            else:
                step = None
            if step:
                plan_outputs[plan_id].steps[-1].final_step = step

        return plan_outputs

    async def get_next_step_programs(
        self, plan_outputs: dict[int, PlanOutput]
    ) -> List[PlanOutput]:
        generation_params = GenerationParameters(
            model=self.executor_model, temperature=0.5, max_tokens=4096
        )
        conversations_to_process = []
        for instance_id, plan_output in plan_outputs.items():
            if plan_output.success:
                continue
            instance = self.evaluator.instances[instance_id]
            mining_setup = get_mining_setup(instance)
            starting_inventory = instance.inspect_inventory()
            executor_objective = plan_output.steps[-1].final_step
            user_message = self.step_executor_user_prompt.format(
                task=executor_objective,
                starting_inventory=starting_inventory,
                mining_setup=mining_setup,
            )
            conversations_to_process.append(
                (
                    Conversation(
                        messages=[
                            Message(
                                role="system", content=self.step_executor_system_prompt
                            ),
                            Message(role="user", content=user_message),
                        ]
                    ),
                    plan_output.meta["plan_id"],
                )
            )

        step_outputs = [
            asyncio.ensure_future(
                self._generate_programs_batch(
                    conversation[0],
                    generation_params,
                    meta={"type": "next_step_program", "plan_id": conversation[1]},
                )
            )
            for conversation in conversations_to_process
        ]
        responses = await asyncio.gather(*step_outputs)
        for idx, response in enumerate(responses):
            output = response[0]
            plan_id = output.meta["plan_id"]
            # add the output program to the last step
            plan_outputs[plan_id].steps[-1].program = output
        return plan_outputs

    async def search(
        self, n_iterations: int, samples_per_iteration: int, skip_failures: bool = False
    ):
        for iteration in range(n_iterations):
            parent = await self.sampler.sample_parent(version=self.version)

            tasks, start_state = await self._get_tasks(parent, samples_per_iteration)
            plans = await self.generate_plans(tasks)
            for step_idx in range(self.max_steps_per_objective):
                if step_idx == 0:
                    # reset the instances
                    for instance_id, instance in enumerate(self.evaluator.instances):
                        instance.reset(start_state)
                self.evaluator.set_status(f"Getting candidates for step {step_idx}")
                plans = await self.generate_next_step_candidates(plans)
                self.evaluator.set_status(f"Judging candidates for step {step_idx}")
                plans = await self.get_next_step_with_judge(plans)
                self.evaluator.set_status(f"Generating programs for step {step_idx}")
                plans = await self.get_next_step_programs(plans)

                # Process programs in parallel
                eval_futures = []
                for instance_id, plan_object in plans.items():
                    if plan_object.success:
                        continue
                    self.evaluator.instances[instance_id].reset(start_state)
                    latest_program = plan_object.steps[-1].program
                    # logging purposes
                    self.evaluator.logger.update_instance(
                        instance_id,
                        program_id=latest_program.id,
                        status="starting to evaluate",
                    )

                    # Create evaluation future for this program
                    # TODO Skip failures ???
                    eval_futures.append(
                        self._process_last_step(
                            plan=plan_object,
                            start_state=start_state,
                            instance_id=instance_id,
                            parent_id=parent.id if parent else None,
                            skip_failures=skip_failures,
                        )
                    )

                # Wait for all programs to complete
                await asyncio.gather(*eval_futures)
                self.evaluator.logger.update_progress()

            # Save the plans
            for plan in plans.values():
                if plan.success:
                    self.save_plan(plan)

    def save_plan(self, plan: PlanOutput):
        # we need to save all the programs but we need to add some meta fields
        objective = plan.task.task
        initial_plan = plan.initial_plan.initial_plan
        parent_id = None
        for step in plan.steps:
            candidate_step_meta = []
            for candidate_step in step.candidate_language_outputs:
                try:
                    messages = candidate_step.conversation.model_dump()["messages"]
                except:
                    messages = candidate_step.conversation.dict()["messages"]
                output = candidate_step.response
                start_state = step.start_state
                candidate_step_meta.append(
                    {
                        "output": output,
                        "messages": messages,
                    }
                )
                mining_setup = candidate_step.meta["mining_setup"]
                starting_inventory = candidate_step.meta["starting_inventory"]
            judge_messages = step.judge_language_output_step.conversation.model_dump()[
                "messages"
            ]
            executor_step = step.final_step
            meta = {
                "objective": objective,
                "initial_plan": initial_plan,
                "candidate_steps": candidate_step_meta,
                "judge_messages": judge_messages,
                "executor_step": executor_step,
                "start_state": start_state,
                "mining_setup": mining_setup,
                "starting_inventory": starting_inventory,
                "final_output": plan.final_output,
            }

            program = step.program
            program.meta = meta
            program.parent_id = parent_id
            self.db.create_program(program)
            parent_id = program.id

    async def _process_last_step(
        self,
        plan: PlanOutput,
        start_state: GameState,
        instance_id: int,
        parent_id: Optional[int],
        skip_failures: bool,
    ):
        try:
            step_to_process = plan.steps[-1]
            step_to_process, _, entity_list = await self._evaluate_step(
                step_to_process, start_state, instance_id, parent_id
            )
            plan.steps[-1] = step_to_process
            log_str = f"Step {len(plan.steps)}: {step_to_process.final_step}\n{step_to_process.program.response}"
            plan.logs.append(log_str)
            return plan

        except Exception as e:
            print(f"Failed to evaluate program on instance {instance_id}: {str(e)}")
            # pop the last step from plan
            plan.steps.pop()
            return plan

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_natural_language_batch(
        self,
        conversation: Conversation,
        generation_params: GenerationParameters,
        meta: dict,
    ) -> List[LanguageOutput]:
        """Generate multiple programs in a single API call using 'n' parameter"""
        formatted_messages = self.formatter.to_llm_messages(
            self.formatter.format_conversation(conversation)
        )
        if "claude" in generation_params.model:
            assert generation_params.n == 1, "Number of samples must be 1 for Claude"

        try:
            # Single API call to generate n_samples completions
            response = self.llm.call(
                messages=formatted_messages,
                n_samples=generation_params.n,
                temperature=generation_params.temperature,
                max_tokens=generation_params.max_tokens,
                logit_bias=generation_params.logit_bias,
                stop_sequences=generation_params.stop_sequences,
                model=generation_params.model,
            )

            outputs = []
            try:
                messages = conversation.model_dump()["messages"]
            except:
                messages = conversation.dict()["messages"]

            # Process all choices from the response
            if "claude" in generation_params.model:
                str_output = response.content[0].text
                outputs.append(
                    LanguageOutput(
                        id=hash((str_output, json.dumps(messages))),
                        response=str_output,  # I think this could also be multiple
                        conversation=conversation,
                        token_usage=response.usage.output_tokens
                        + response.usage.input_tokens
                        if hasattr(response, "usage")
                        else None,
                        completion_token_usage=response.usage.output_tokens
                        if hasattr(response, "usage")
                        else None,
                        prompt_token_usage=response.usage.input_tokens
                        if hasattr(response, "usage")
                        else None,
                        version=self.version,
                        version_description=self.version_description,
                        meta=meta,
                    )
                )
            else:
                # Handle OpenAI response format with multiple choices
                for choice in response.choices:
                    str_output = choice.message.content
                    outputs.append(
                        LanguageOutput(
                            id=hash((str_output, json.dumps(messages))),
                            response=str_output,
                            conversation=conversation,
                            token_usage=response.usage.total_tokens
                            // generation_params.n
                            if hasattr(response, "usage")
                            else None,
                            completion_token_usage=response.usage.completion_tokens
                            // generation_params.n
                            if hasattr(response, "usage")
                            else None,
                            prompt_token_usage=response.usage.prompt_tokens
                            // generation_params.n
                            if hasattr(response, "usage")
                            else None,
                            version=self.version,
                            version_description=self.version_description,
                            meta=meta,
                        )
                    )

            return outputs
        except Exception as e:
            print(f"Batch program generation failed: {str(e)}")
            return []
