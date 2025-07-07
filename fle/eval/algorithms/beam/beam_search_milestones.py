import asyncio
import logging
from typing import Any, List, Optional, Tuple

from eval.algorithms.mcts import (
    InitialPlanOutput,
    PlanningGroupV2,
    PlanOutput,
    Step,
    SupervisedExecutorConfig,
    SupervisedTaskExecutorABC,
    TaskOutput,
)
from tenacity import retry, wait_exponential

from fle.commons.db_client import DBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program
from fle.env import FactorioInstance
from fle.eval.tasks import ThroughputTask

from ..mcts import get_mining_setup

logger = logging.basicConfig(level=logging.INFO)


class MilestonesBeamSearchExecutor(SupervisedTaskExecutorABC):
    def __init__(
        self,
        instances: List[FactorioInstance],
        db_client: DBClient,
        formatter: Any,
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

        super().__init__(
            instances, db_client, api_factory, config, version, version_description
        )

        self.model_to_evaluate = config.model_to_evaluate
        self.system_prompt = config.supervised_kwargs["system_prompt"]
        self.formatter = formatter

        self.beam_unification_steps = config.supervised_kwargs.get(
            "beam_unification_steps", 0
        )

    async def generate_plans(
        self, task: ThroughputTask, nr_of_beams: int, instances
    ) -> List[InitialPlanOutput]:
        plan_outputs = {}
        for idx in range(nr_of_beams):
            instance = instances[idx]
            instance.reset(task.starting_game_state)
            # plan id coincides with instance id it will be evaluated on
            plan_output = PlanOutput(
                task=TaskOutput(task=task.task), meta={"plan_id": idx}
            )
            entities = instance.namespace.get_entities()
            inventory = instance.namespace.inspect_inventory()
            dummy_program_code = "print(f'Inventory: {inspect_inventory()}')\nprint(f'Entities: {get_entities()}')\n"
            output = f"('Inventory: {inventory}')\n('Entities on the map: {entities}')"
            first_dummy_program = Program(
                code=dummy_program_code,
                conversation=Conversation(messages=[]),
                response=output,
                meta={"type": "initial_dummy"},
            )
            first_step = Step(
                program=first_dummy_program,
                start_state=task.starting_game_state,
                end_state=task.starting_game_state,
            )
            plan_output.steps.append(first_step)
            plan_outputs[idx] = plan_output

        return plan_outputs

    async def _run_group_search(
        self,
        group: PlanningGroupV2,
        task: ThroughputTask,
        n_iterations: int,
        skip_failures: bool = False,
        run_id: str = "",
    ):
        """Run parallel planning search across all groups"""
        """
        Need to check again over what to do mcts exactly
        """
        try:
            results = []
            for iteration in range(n_iterations):
                saved_step_ids = []
                output_dicts = {}
                for step_idx in range(task.maximum_steps):
                    if step_idx == 0:
                        group.plans = await self.generate_plans(
                            task,
                            nr_of_beams=len(group.active_instances),
                            instances=group.evaluator.instances,
                        )

                    plans = await self._process_group_step(
                        group, step_idx, skip_failures, parent=None, task=task
                    )

                    for plan in plans:
                        try:
                            # Save the step
                            step_to_save = plan.steps[-1]
                            # lets first try to only save the steps that are final
                            if step_to_save.program.id not in saved_step_ids:
                                output_dict = await self.save_step(
                                    plan,
                                    step_to_save,
                                    original_parent=None,
                                    run_id=run_id,
                                )
                                saved_step_ids.append(step_to_save.program.id)
                                plan_idx = plan.meta["plan_id"]
                                if plan_idx not in output_dicts:
                                    output_dicts[plan_idx] = []
                                output_dicts[plan_idx].append(output_dict)
                        except Exception as e:
                            print(
                                "Could not save step - possibly missing (in case of skipping errors)"
                            )
                            print(e)

                    group.evaluator.logger.update_progress()
                results.append(output_dicts)
        except Exception as e:
            print(f"Error during parallel search: {str(e)}")
            raise
        finally:
            self.cleanup()
            return results

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_next_step(self, group, task) -> List[PlanOutput]:
        plan_outputs = group.plans
        generation_params = GenerationParameters(
            model=self.model_to_evaluate, max_tokens=4096, temperature=0.5
        )
        conversations_to_process = []
        start_states = {}
        for instance_id, plan_output in plan_outputs.items():
            instance = group.evaluator.instances[instance_id]
            start_state_to_reset_to = plan_output.steps[-1].end_state

            instance.reset(start_state_to_reset_to)
            starting_state = GameState.from_instance(instance)
            start_states[instance_id] = starting_state
            mining_setup = get_mining_setup(instance)
            starting_inventory = instance.namespace.inspect_inventory()
            starting_inventory_dict = self.get_inventory_dict(starting_inventory)

            steps = plan_output.steps
            system_message = self.system_prompt
            system_message += f"\n\nOBJECTIVE\n\nThe factory you MUST create as follows\nOBJECTIVE: {task.task}."
            conversation = Conversation(
                messages=[Message(role="system", content=system_message)]
            )
            for step in steps:
                assistant_str = (
                    step.program.meta["text_response"]
                    if step.program.meta.get("text_response", None)
                    else ""
                )
                if assistant_str:
                    assistant_str += f"\n```python\n{step.program.code}```"
                else:
                    assistant_str = f"```python\n{step.program.code}```"
                assistant_message = Message(role="assistant", content=assistant_str)
                user_message = Message(role="user", content=step.program.response)
                conversation.messages += [assistant_message, user_message]
            conversations_to_process += [
                (
                    conversation,
                    {
                        "plan_id": instance_id,
                        "mining_setup": mining_setup,
                        "starting_inventory": starting_inventory_dict,
                    },
                )
            ]

        step_outputs = [
            asyncio.ensure_future(
                self._generate_programs_batch(
                    conversation[0],
                    generation_params,
                    meta={
                        "type": "step_programs",
                        "plan_id": conversation[1]["plan_id"],
                        "mining_setup": conversation[1]["mining_setup"],
                        "starting_inventory": conversation[1]["starting_inventory"],
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
            # We need to create a new step object
            step_output_objects[plan_id] = Step(
                candidate_language_outputs=[], start_state=start_states[plan_id]
            )
            # extra postprocessing step, change all <Step> and <STEP> to <step>
            # same with <Objective_completed> and <OBJECTIVE_COMPLETED>
            # makes it more robust
            step_output_objects[plan_id].sampled_programs.append(output)

        for plan_id, step_output in step_output_objects.items():
            plan_outputs[plan_id].steps.append(step_output)

        return plan_outputs

    async def _process_group_step(
        self,
        group: PlanningGroupV2,
        step_idx: int,
        skip_failures: bool,
        parent: Program,
        task: ThroughputTask,
    ) -> List[PlanOutput]:
        """Process a single step for a group"""
        try:
            # Generate candidates
            group.evaluator.set_status(f"Getting candidates for step {step_idx}")
            group.plans = await self.generate_next_step(group, task)

            # Evaluate programs in parallel across instances
            eval_futures = []
            completed_plans = []
            for instance_id, (instance, plan) in enumerate(
                zip(group.active_instances, group.plans.values())
            ):
                group.evaluator.logger.update_instance(instance_id, status="evaluating")

                eval_futures.append(
                    self._process_last_step(
                        plan=plan,
                        group=group,
                        instance_id=instance_id,
                        parent_id=parent.id if parent else None,
                        skip_failures=skip_failures,
                        task=task,
                    )
                )

            return await asyncio.gather(*eval_futures) + completed_plans

        except Exception as e:
            print(f"Error in group {group.group_id}, step {step_idx}: {str(e)}")
            raise

    async def _evaluate_step(
        self, step: Step, group: PlanningGroupV2, instance_id: int, parent_id
    ) -> Tuple[Step, float, List]:
        """Modified to work with instance groups"""
        entity_list = []

        try:
            instance = group.active_instances[instance_id]
            group.evaluator.logger.update_instance(instance_id, status="executing")
            for program in step.sampled_programs:
                # reset the instance to the start state
                instance.reset(step.start_state)
                (
                    final_reward,
                    state,
                    result,
                    entities,
                    achievements,
                    ticks,
                ) = await group.evaluator._evaluate_single(
                    instance_id, program, instance
                )
                print(f"\nOutput for instance {instance_id}: {result}\n")
                step.program = program
            entity_list.append(entities)
            step.end_state = state
            step.reward = final_reward
            post_production_flows = instance.namespace._get_production_stats()
            step.program.meta["post_production_flows"] = post_production_flows
            step.program.meta["profits"] = -1
        except Exception as e:
            print(
                f"Error during evaluation in group {group.group_id}, instance {instance_id}: {e}"
            )
            raise e

        step.program.raw_reward = step.reward
        step.program.state = step.end_state
        step.program.response = result
        step.program.parent_id = parent_id
        step.program.achievements = achievements
        return step, entity_list

    async def save_step(
        self, plan: PlanOutput, step: Step, original_parent: Program, run_id: str
    ):
        candidate_step_meta = []
        # first we check if judge has been done on this step
        # If not, then its the final output step
        # we need to save all the programs but we need to add some meta fields
        objective = plan.task.task
        initial_plan = plan.initial_plan.initial_plan if plan.initial_plan else None
        parent_id = original_parent.id if original_parent else None

        # find the step before `step` in the plan to get the `parent_id`
        for current_step, next_step in zip(plan.steps[:-1], plan.steps[1:]):
            if next_step.program.id == step.program.id:
                parent_id = current_step.program.id

        post_production_flows = step.program.meta["post_production_flows"]
        node_profit = step.program.meta["profits"]
        meta = {
            "objective": objective,
            "initial_plan": initial_plan,
            "candidate_steps": candidate_step_meta,
            "text_response": step.program.meta["text_response"],
            "final_output": plan.final_output,
            "type": "step",
            "search_type": "beam_search_supervised_task",
            "full_production_flows": post_production_flows,
            "step_idx": len(plan.steps),
            "sampled_state_id": original_parent.id if original_parent else None,
            "profits": {"node_profit": node_profit},
            "run_id": run_id,
            "mining_setup": step.program.meta["mining_setup"],
            "starting_inventory": step.program.meta["starting_inventory"],
            "holdout_achievements": step.program.meta.get("holdout_achievements", None),
            "task_success": step.program.meta.get("task_success", None),
        }

        program = step.program
        program.meta = meta
        program.parent_id = parent_id
        await self.db_client.create_program(program)
        output_dict = {
            "step_nr": len(plan.steps),
            "holdout_achievements": step.program.meta.get("holdout_achievements", None),
            "program_id": program.id,
            "task_success": step.program.meta.get("task_success", None),
        }
        return output_dict

    async def _process_last_step(
        self,
        plan: PlanOutput,
        group: PlanningGroupV2,
        instance_id: int,
        parent_id: Optional[int],
        skip_failures: bool,
        task: ThroughputTask,
    ) -> PlanOutput:
        try:
            step_to_process = plan.steps[-1]
            if len(step_to_process.sampled_programs) == 0:
                # pop the last step from plan
                plan.steps.pop()
                return plan
            step_to_process, entity_list = await self._evaluate_step(
                step_to_process, group, instance_id, parent_id
            )
            if skip_failures and "error" in step_to_process.program.response.lower():
                raise Exception("Found error in response. Skipping step.")

            plan.steps[-1] = step_to_process
            task_success, achievements = self.evaluate_task(
                plan=plan, group=group, task=task
            )
            plan.steps[-1].program.meta["holdout_achievements"] = achievements
            plan.steps[-1].program.meta["task_success"] = task_success
            throughput_str = f"Here is the current througphut of your factory: {achievements['dynamic']} created per 60 seconds"
            plan.steps[-1].program.response += f"\n{throughput_str}"
            return plan

        except Exception as e:
            print(f"Failed to evaluate program on instance {instance_id}: {str(e)}")
            # pop the last step from plan
            plan.steps.pop()
            return plan

    def evaluate_task(
        self, plan: PlanOutput, group: PlanningGroupV2, task: ThroughputTask
    ) -> bool:
        instance_id = plan.meta["plan_id"]
        instance = group.evaluator.instances[instance_id]
        check_state = plan.steps[-1].end_state
        instance.reset(check_state)

        task_success, achievements = task.verify(
            score=plan.steps[-1].program.value,
            step=len(plan.steps),
            instance=instance,
            step_statistics=plan.steps[-1].program.meta["post_production_flows"],
        )

        return task_success, achievements
