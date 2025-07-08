import json
import os
from typing import List, Dict, Optional, Any, Tuple
import asyncio
from math import floor
import logging
from dataclasses import dataclass
from rich.console import Console
from tenacity import retry, wait_exponential
import copy
from fle.commons.models.conversation import Conversation
from fle.commons.models.generation_parameters import GenerationParameters
from fle.agents.formatters.conversation_formatter_abc import DefaultFormatter
from fle.commons.db_client import DBClient
from fle.eval.evaluator import Evaluator
from fle.eval.algorithms.mcts.grouped_logger import GroupedFactorioLogger
from fle.eval.algorithms.mcts.parallel_supervised_config import SupervisedExecutorConfig
from fle.eval.algorithms.mcts.planning_models import (
    PlanOutput,
    TaskOutput,
    Step,
    LanguageOutput,
    InitialPlanOutput,
)
from fle.commons.models.game_state import GameState
from fle.commons.models.program import Program
from fle.env import FactorioInstance
from fle.eval.tasks import TaskABC

from abc import ABC, abstractmethod

logger = logging.basicConfig(level=logging.INFO)


@dataclass
class PlanningGroupV2:
    group_id: int
    evaluator: Evaluator
    active_instances: List[FactorioInstance]
    plans: Dict[int, PlanOutput] = None


class SupervisedTaskExecutorABC(ABC):
    def __init__(
        self,
        instances: List[FactorioInstance],
        db_client: DBClient,
        api_factory: Any,
        config: SupervisedExecutorConfig,
        version=None,
        version_description="",
    ):
        """
        Initialize parallel planning MCTS

        Args:
            instances: List of Factorio instances to distribute
            db_client: Database client
            api_factory: Factory for creating language models
            config: Configuration parameters including model paths and prompts
        """
        self.console = Console()
        self.config = config
        self.db_client = db_client
        self.llm = api_factory
        self.version = version
        self.version_description = version_description
        self.model_to_evaluate = config.model_to_evaluate
        self.formatter = DefaultFormatter()
        # Validate instance count
        self._validate_instance_count(len(instances), config.n_parallel)

        # Initialize logger
        instances_per_group = floor(len(instances) / config.n_parallel)
        self.logger = GroupedFactorioLogger(
            n_groups=config.n_parallel,
            instances_per_group=instances_per_group,
        )
        self.logger.start()

        # Create instance groups
        self.instance_groups = self._create_instance_groups(instances)

    def read_in_prompts(self, path):
        system_prompt_path = os.path.join(path, "system_prompt.md")
        user_prompt_path = os.path.join(path, "user_prompt.md")
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
        with open(user_prompt_path, "r") as f:
            user_prompt = f.read()
        return system_prompt, user_prompt

    def _create_instance_groups(
        self, instances: List["FactorioInstance"]
    ) -> List[PlanningGroupV2]:
        """Create instance groups for parallel execution"""
        instances_per_group = floor(len(instances) / self.config.n_parallel)
        groups = []

        for group_id in range(self.config.n_parallel):
            # Slice instances for this group
            start_idx = group_id * instances_per_group
            end_idx = start_idx + instances_per_group
            group_instances = instances[start_idx:end_idx]

            # Split into active instances
            active_instances = group_instances

            # Create evaluator for this group
            evaluator = Evaluator(
                db_client=self.db_client,
                instances=group_instances,
                value_accrual_time=3,
                logger=self.logger,
            )

            groups.append(
                PlanningGroupV2(
                    group_id=group_id,
                    evaluator=evaluator,
                    active_instances=active_instances,
                )
            )

        return groups

    def _validate_instance_count(self, total_instances: int, n_parallel: int):
        min_required = n_parallel * 2
        if total_instances < min_required:
            raise ValueError(
                f"Need at least {min_required} instances for {n_parallel} parallel searches "
                f"(got {total_instances})"
            )

        instances_per_group = floor(total_instances / n_parallel)
        if instances_per_group < 2:
            raise ValueError(
                f"Not enough instances per group (need at least 2, got {instances_per_group})"
            )

    async def search_supervised(
        self,
        n_iterations: int,
        task: TaskABC,
        skip_failures: bool = False,
        run_id: str = "",
    ):
        """
        Run truly parallel MCTS search across all groups

        Args:
            n_iterations: Number of iterations to run
            skip_failures: Whether to skip failed program generations
        """
        try:
            # Create group search tasks that will run in parallel
            search_tasks = []
            for group in self.instance_groups:
                # Each group search runs independently
                search_task = asyncio.create_task(
                    self._run_group_search(
                        group=group,
                        n_iterations=n_iterations,
                        skip_failures=skip_failures,
                        task=task,
                        run_id=run_id,
                    )
                )
                search_tasks.append(search_task)

            # Wait for ALL groups to complete, allowing them to run simultaneously
            results = await asyncio.gather(*search_tasks)

        except Exception as e:
            print(f"Error during parallel search: {str(e)}")
            raise
        finally:
            self.cleanup()
            # make the list of lists into a single list
            results = [item for sublist in results for item in sublist]
            return results

    async def generate_plans(
        self, task: TaskABC, nr_of_beams: int
    ) -> List[InitialPlanOutput]:
        plan_outputs = {}
        for idx in range(nr_of_beams):
            # plan id coincides with instance id it will be evaluated on
            plan_output = PlanOutput(
                task=TaskOutput(task=task.task), meta={"plan_id": idx}
            )
            plan_outputs[idx] = plan_output

        return plan_outputs

    @abstractmethod
    async def _run_group_search(
        self,
        group: PlanningGroupV2,
        task: TaskABC,
        n_iterations: int,
        skip_failures: bool = False,
    ):
        """Run parallel planning search across all groups"""
        """
        Need to check again over what to do mcts exactly
        """
        pass

    def cleanup(self):
        """Clean up resources"""
        self.logger.stop()
        for group in self.instance_groups:
            if hasattr(group.evaluator, "logger"):
                group.evaluator.logger.stop()

    def get_group_metrics(self, group_id: int) -> Dict[str, Any]:
        """Get metrics for a specific group"""
        if 0 <= group_id < len(self.instance_groups):
            group = self.instance_groups[group_id]
            return {
                "active_instances": len(group.active_instances),
                "total_programs": sum(
                    inst.total_programs
                    for inst in group.evaluator.logger.groups[
                        group_id
                    ].instances.values()
                ),
                "error_count": sum(
                    inst.error_count
                    for inst in group.evaluator.logger.groups[
                        group_id
                    ].instances.values()
                ),
            }
        return {}

    async def _evaluate_step(
        self,
        step: Step,
        start_state: GameState,
        group: PlanningGroupV2,
        instance_id: int,
        parent_id,
    ) -> Tuple[Step, float, List]:
        """Modified to work with instance groups"""
        entity_list = []

        try:
            instance = group.active_instances[instance_id]
            group.evaluator.logger.update_instance(instance_id, status="executing")
            for program in step.sampled_programs:
                instance.reset(step.start_state)
                if not isinstance(program, Program):
                    print(f"Weird program 1: {program}")
                # reset the instance to the start state
                instance.reset(step.start_state)
                (
                    reward,
                    state,
                    response,
                    entities,
                    achievements,
                    profits,
                    error,
                ) = await group.evaluator._evaluate_single(
                    instance_id, program, instance
                )
                if not isinstance(program, Program):
                    print(f"Weird program 2: {program}")
                if error:
                    print(
                        f"Error in group {group.group_id}, instance {instance_id}: {error}"
                    )
                step.program = program
                if not error:
                    break
            entity_list.append(entities)
            step.end_state = state
            step.reward = reward
            post_production_flows = instance.get_production_stats()
            step.program.meta["post_production_flows"] = post_production_flows
            step.program.meta["profits"] = profits
        except Exception as e:
            print(
                f"Error during evaluation in group {group.group_id}, instance {instance_id}: {e}"
            )
            raise e

        step.program.value = step.reward
        step.program.raw_reward = step.reward
        step.program.state = step.end_state
        step.program.response = response
        step.program.parent_id = parent_id
        step.program.achievements = achievements
        return step, entity_list

    async def _process_last_step(
        self,
        plan: PlanOutput,
        start_state: GameState,
        group: PlanningGroupV2,
        instance_id: int,
        parent_id: Optional[int],
        skip_failures: bool,
    ) -> PlanOutput:
        try:
            step_to_process = plan.steps[-1]
            step_to_process, entity_list = await self._evaluate_step(
                step_to_process, start_state, group, instance_id, parent_id
            )

            if skip_failures and "error" in step_to_process.program.response.lower():
                raise Exception("Found error in response. Skipping step.")

            plan.steps[-1] = step_to_process
            log_str = f"Step {len(plan.steps)}: {step_to_process.final_step}\n{step_to_process.program.response}"
            plan.logs.append(log_str)
            return plan

        except Exception as e:
            print(f"Failed to evaluate program on instance {instance_id}: {str(e)}")
            # pop the last step from plan
            plan.steps.pop()
            return plan

    def check_for_task_completion(
        self, task: TaskABC, plan: PlanOutput, group: PlanningGroupV2
    ) -> bool:
        sleep_seconds = 60
        instance_id = plan.meta["plan_id"]
        instance = group.evaluator.instances[instance_id]
        start_state = plan.steps[-1].start_state
        instance.reset(start_state)
        instance_inventory = instance.inspect_inventory()
        result, achievements, post_production_flows = (
            group.evaluator._evaluate_for_achievements(
                code=f"sleep({sleep_seconds})", instance=instance
            )
        )
        for check_dict in task.check_dicts:
            if check_dict["task_type"] == "craft":
                item = check_dict["item"]
                quantity = check_dict["quantity"]
                if instance_inventory[item] < quantity:
                    return False, post_production_flows
            elif check_dict["task_type"] == "dynamic":
                item = check_dict["item"]
                quantity = check_dict["quantity"]
                item_dynamic_value = achievements["dynamic"].get(item, 0)
                item_dynamic_value_per_second = item_dynamic_value
                if item_dynamic_value_per_second < quantity:
                    return False, post_production_flows
            elif check_dict["task_type"] == "production_flows_output":
                item = check_dict["item"]
                quantity = check_dict["quantity"]
                production_flows_output_item_value = post_production_flows[
                    "output"
                ].get(item, 0)
                if production_flows_output_item_value < quantity:
                    return False, post_production_flows
            elif check_dict["task_type"] == "production_flows_input":
                item = check_dict["item"]
                quantity = check_dict["quantity"]
                production_flows_output_item_value = post_production_flows["input"].get(
                    item, 0
                )
                if production_flows_output_item_value < quantity:
                    return False, post_production_flows
        return True, post_production_flows

    def _create_output_completed_program(
        self,
        plan: PlanOutput,
        parent_id: Optional[int],
        task: TaskABC,
        group: PlanningGroupV2,
    ) -> PlanOutput:
        if task.check_for_completion:
            check_result, post_production_flows = self.check_for_task_completion(
                task, plan, group
            )
            # pop the price list
            post_production_flows.pop("price_list", None)
        else:
            check_result = None
            post_production_flows = None
        objective = f"'{plan.task.task}'"
        python_code = f"print('Objective {objective} has been completed. Now lets prepare the next objective.')"
        program_parent_id = (
            plan.steps[-2].program.id if len(plan.steps) > 1 else parent_id
        )
        program = Program(
            id=hash((python_code, plan.task.task, program_parent_id)),
            code=python_code,
            conversation=Conversation(messages=[]),
            parent_id=program_parent_id,
            version=self.version,
            version_description=self.version_description,
            model=self.model_to_evaluate,
            meta={
                "objective": plan.task.task,
                "type": "completed_objective",
                "checked_result_correct": check_result,
                "nr_of_steps": len(plan.steps),
                "post_production_flows": post_production_flows,
            },
        )
        return program

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
            response = await self.llm.acall(
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

    def get_inventory_dict(self, inventory):
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        return inventory_dict

    def format_log_string(self, logs: list):
        return (
            "\n\n".join(logs)
            if logs
            else "The agent has not yet interacted with the world"
        )

    def _verify_response_is_python(self, content):
        code = content
        # Parse into an AST to verify that this is a program
        try:
            compile(code, filename="<ast>", mode="exec")
        except SyntaxError:
            # Take the last line off and try again
            code = code.rsplit("\n", 1)[0] + "\n"
            compile(code, filename="<ast>", mode="exec")

        return code

    def _extract_code_from_choice(self, input_str) -> Optional[str]:
        """Extract code from a single completion choice"""
        code = ""
        try:
            content = input_str
            code = self._verify_response_is_python(content)
            code = code.replace("from factorio_instance import *", "")
            return code, None
        except Exception:
            try:
                content = input_str
                content_split = content.split("```python")
                code = content_split[1].split("```")[0].strip()
                text_response = content_split[0].strip()
                code = self._verify_response_is_python(code)
                code = code.replace("from factorio_instance import *", "")
                code = code.strip()
                return code, text_response
            except Exception as e1:
                # Sometimes it samples a leading line, before writing unblocked python code.
                content = "\n".join(input_str.split("\n")[1:])
                try:
                    code = self._verify_response_is_python(content)
                    code = code.replace("from factorio_instance import *", "")
                    code = code.strip()
                    return code, None
                except Exception:
                    try:
                        content_split = content.split("from factorio_instance import *")
                        code = content_split[1].strip()
                        text_response = content_split[0].strip()
                        code = self._verify_response_is_python(code)
                        code = code.strip()
                        return code, text_response
                    except Exception:
                        return "", content.strip()
                    # print(f"Failed to extract code from choice after removing leading line: {str(e2)}")
                print(f"Failed to extract code from choice: {str(e1)}")

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_programs_batch(
        self,
        conversation: Conversation,
        generation_params: GenerationParameters,
        meta={},
    ) -> List[Program]:
        """Generate multiple programs in a single API call using 'n' parameter"""
        conversation = copy.deepcopy(conversation)

        formatted = await self.formatter.format_conversation(conversation)
        formatted_messages = self.formatter.to_llm_messages(formatted)
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
                model=generation_params.model,
                presence_penalty=generation_params.presence_penalty,
            )

            programs = []
            try:
                messages = conversation.model_dump()["messages"]
            except Exception:
                messages = conversation.dict()["messages"]

            # Process all choices from the response
            if "claude" in generation_params.model:
                # Handle Claude response format
                code, text_response = self._extract_code_from_choice(
                    response.content[0].text
                )
                programs.append(
                    Program(
                        id=hash((code, json.dumps(messages))),
                        code=code,
                        conversation=conversation,
                        response=response.content[0].text,
                        token_usage=response.usage.input_tokens
                        + response.usage.output_tokens
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
                        meta={
                            "text_response": text_response,
                            "model": generation_params.model,
                        },
                    )
                )
                if meta:
                    programs[0].meta.update(meta)
            else:
                # Handle OpenAI response format with multiple choices
                for choice in response.choices:
                    code, text_response = self._extract_code_from_choice(
                        choice.message.content
                    )
                    programs.append(
                        Program(
                            id=hash((code, json.dumps(messages))),
                            code=code,
                            conversation=conversation,
                            response=choice.message.content,
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
                            meta={
                                "text_response": text_response,
                                "model": generation_params.model,
                            },
                        )
                    )
                    if meta:
                        programs[-1].meta.update(meta)

            return programs

        except Exception as e:
            print(f"Batch program generation failed: {str(e)}")
            return []
