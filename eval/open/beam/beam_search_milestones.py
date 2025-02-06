from typing import List, Optional, Any, Tuple
import asyncio
import logging
from eval.open.db_client import DBClient
from eval.open.mcts.supervised_task_executor_abc import SupervisedTaskExecutorABC, PlanningGroupV2
from eval.open.mcts.planning_models import PlanOutput, TaskOutput, Step, InitialPlanOutput
from eval.open.model.game_state import GameState
from eval.open.model.program import Program
from instance import FactorioInstance
from eval.tasks import OpenEndedTaskConfig
from eval.open.mcts.parallel_supervised_config import SupervisedExecutorConfig
from eval.open.model.conversation import Conversation, GenerationParameters, Message
from tenacity import retry, wait_exponential
from eval.open.mcts.planning_mcts import get_mining_setup
import copy
logger = logging.basicConfig(level=logging.INFO)




class MilestonesBeamSearchExecutor(SupervisedTaskExecutorABC):
    def __init__(self,
                 instances: List[FactorioInstance],
                 db_client: DBClient,
                 formatter: Any,
                 llm_factory: Any,
                 config: SupervisedExecutorConfig,
                 version=None,
                 version_description=""
                 ):
        """
        Initialize parallel planning MCTS

        Args:
            instances: List of Factorio instances to distribute
            db_client: Database client
            llm_factory: Factory for creating language models
            config: Configuration parameters including model paths and prompts
        """

        super().__init__(instances, db_client, llm_factory, config, version, version_description)

        # Initialize other attributes from config
        self.max_steps_per_objective = config.supervised_kwargs["max_steps_per_objective"]


        self.model_to_evaluate = config.model_to_evaluate
        self.system_prompt = config.supervised_kwargs["system_prompt"]
        self.formatter = formatter
        

        self.beam_unification_steps = config.supervised_kwargs.get("beam_unification_steps", 0)
    async def generate_plans(self, task: OpenEndedTaskConfig, 
                             nr_of_beams: int,
                             instances,
                             start_state) -> List[InitialPlanOutput]:
        
        plan_outputs = {}
        for idx in range(nr_of_beams):
            instance = instances[idx]
            instance.reset(start_state)
            # plan id coincides with instance id it will be evaluated on
            plan_output = PlanOutput(task=TaskOutput(task=task.task), meta={"plan_id": idx})
            entities = instance.namespace.get_entities()
            output = f"1: ('Inventory: {start_state.inventory}')\n2: ('Entities on the map: {entities}')"
            first_dummy_program = Program(code="print(f'Inventory: {inspect_inventory()}')\n"
                                                              "print(f'Entities: {get_entities()}')\n", 
                                                              conversation=Conversation(messages=[]),
                                                              response=output,
                                                              meta = {"type": "initial_dummy"})
            first_step = Step(program=first_dummy_program, 
                              start_state=self.config.initial_state,
                              end_state=start_state,)
            plan_output.steps.append(first_step)
            plan_outputs[idx] = plan_output
            

        return plan_outputs
    

    async def _run_group_search(self, group: PlanningGroupV2, 
                                task: OpenEndedTaskConfig, 
                                n_iterations: int, 
                                skip_failures: bool = False,
                                run_id: str = ""):
        """Run parallel planning search across all groups"""
        """
        Need to check again over what to do mcts exactly
        """
        try:
            results = []
            for iteration in range(n_iterations):
                
                start_state = self.config.initial_state
                start_state.inventory = task.starting_inventory
                saved_step_ids = []
                output_dicts = {}
                for step_idx in range(self.max_steps_per_objective):
                    if step_idx == 0:
                        group.plans = await self.generate_plans(task, 
                                                                nr_of_beams=len(group.active_instances),
                                                                instances = group.evaluator.instances,
                                                                start_state=start_state)

                    plans = await self._process_group_step(group, step_idx, skip_failures, start_state, parent = None, task = task)
                    
                    for plan in plans:
                        try:
                            # Save the step
                            step_to_save = plan.steps[-1]
                            # lets first try to only save the steps that are final
                            if step_to_save.program.id not in saved_step_ids:
                                output_dict = await self.save_step(plan, step_to_save,
                                                    original_parent=None,
                                                    run_id=run_id)
                                saved_step_ids.append(step_to_save.program.id)
                                plan_idx = plan.meta["plan_id"]
                                if plan_idx not in output_dicts:
                                    output_dicts[plan_idx] = []
                                output_dicts[plan_idx].append(output_dict)
                        except Exception as e:
                            print("Could not save step - possibly missing (in case of skipping errors)")
                            print(e)

                    if self.beam_unification_steps > 0 and (step_idx +1)%self.beam_unification_steps == 0:
                        try:
                            group = self.unify_beams(group, task)
                        except Exception as e:
                            print(F"Error during beam unification: {str(e)}")
                    group.evaluator.logger.update_progress()
                results.append(output_dicts)
        except Exception as e:
            print(f"Error during parallel search: {str(e)}")
            raise
        finally:
            self.cleanup()
            return results


    def unify_beams(self, group, task):
        # We do simple best of n unification
        throughput_entity = task.throughput_entity
        plan_outputs = group.plans
        throughputs = {}
        for instance_id, plan_output in plan_outputs.items():
            last_step = plan_output.steps[-1]
            if last_step.program.meta.get("holdout_achievements", None):
                throughput = last_step.program.meta["holdout_achievements"]["dynamic"].get(throughput_entity, 0)
            else:
                throughput = 0
            throughputs[instance_id] = throughput
        # get the minimum throughput
        min_throughput = min(throughputs.values())
        max_throughput = max(throughputs.values())
        if min_throughput == max_throughput:
            return group
        # get the instance with the maximum throughput
        max_instance_id = max(throughputs, key=throughputs.get)
        # we need to override all plans with the chosen plan
        chosen_plan = plan_outputs[max_instance_id]
        # also need to reset the instances to the new game state
        instance = group.evaluator.instances[max_instance_id]
        instance_game_state = GameState.from_instance(instance)
        for instance_id, plan_output in group.plans.items():
            group.plans[instance_id] = copy.deepcopy(chosen_plan)
            group.plans[instance_id].meta["plan_id"] = instance_id
            group.evaluator.instances[instance_id].reset(instance_game_state)
        return group

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_next_step(self, group, task) -> List[PlanOutput]:
        plan_outputs = group.plans
        generation_params = GenerationParameters(
            model=self.model_to_evaluate,
            max_tokens=4096,
            temperature = 0.3
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
            conversation = Conversation(messages=[Message(role="system", content=system_message)])
            for step in steps:
                assistant_str = step.program.meta["text_response"] if step.program.meta.get("text_response", None) else ""
                if assistant_str:
                    assistant_str += f"\n```python\n{step.program.code}```"
                else:
                    assistant_str = f"```python\n{step.program.code}```"
                assistant_message = Message(role = "assistant", content=assistant_str)
                user_message = Message(role = "user", content=step.program.response)
                conversation.messages += [assistant_message, user_message]
            conversations_to_process += [(conversation,
                                          {"plan_id": instance_id,
                                           "mining_setup": mining_setup,
                                           "starting_inventory": starting_inventory_dict})]

        step_outputs = [asyncio.ensure_future(self._generate_programs_batch(conversation[0], generation_params,
                                                                                    meta={
                                                                                        "type": "step_programs",
                                                                                        "plan_id": conversation[1]["plan_id"],
                                                                                        "mining_setup": conversation[1]["mining_setup"],
                                                                                        "starting_inventory": conversation[1]["starting_inventory"]}))
                        for conversation in conversations_to_process]
        responses = await asyncio.gather(*step_outputs)
        step_output_objects = {}
        for idx, response in enumerate(responses):
            output = response[0]
            plan_id = output.meta["plan_id"]
            # We need to create a new step object
            step_output_objects[plan_id] = Step(candidate_language_outputs=[], start_state=start_states[plan_id])
            # extra postprocessing step, change all <Step> and <STEP> to <step>
            # same with <Objective_completed> and <OBJECTIVE_COMPLETED>
            # makes it more robust
            step_output_objects[plan_id].sampled_programs.append(output)

        for plan_id, step_output in step_output_objects.items():
            plan_outputs[plan_id].steps.append(step_output)

        return plan_outputs
    

    async def _process_group_step(self, group: PlanningGroupV2, step_idx: int, 
                                  skip_failures: bool, start_state: GameState, parent: Program,
                                  task: OpenEndedTaskConfig) -> List[PlanOutput]:
        """Process a single step for a group"""
        try:
            # Generate candidates
            group.evaluator.set_status(f"Getting candidates for step {step_idx}")
            group.plans = await self.generate_next_step(group, task)

            # Evaluate programs in parallel across instances
            eval_futures = []
            completed_plans = []
            for instance_id, (instance, plan) in enumerate(zip(group.active_instances, group.plans.values())):

                group.evaluator.logger.update_instance(instance_id, status="evaluating")

                eval_futures.append(self._process_last_step(
                    plan=plan,
                    start_state=start_state,
                    group=group,
                    instance_id=instance_id,
                    parent_id=parent.id if parent else None,
                    skip_failures=skip_failures,
                    task=task
                ))

            return await asyncio.gather(*eval_futures) + completed_plans

        except Exception as e:
            print(f"Error in group {group.group_id}, step {step_idx}: {str(e)}")
            raise

    async def _evaluate_step(self,
                             step: Step,
                             start_state: GameState,
                             group: PlanningGroupV2,
                             instance_id: int,
                             parent_id) -> Tuple[Step, float, List]:
        """Modified to work with instance groups"""
        entity_list = []

        try:
            instance = group.active_instances[instance_id]
            group.evaluator.logger.update_instance(instance_id, status="executing")
            for program in step.sampled_programs:
                # reset the instance to the start state
                instance.reset(step.start_state)
                final_reward, state, result, entities, achievements, ticks, error = await group.evaluator._evaluate_single(
                    instance_id,
                    program,
                    instance
                )
                if not isinstance(program, Program):
                    print(f"Weird program 2: {program}")
                if error:
                    print(f"Error in group {group.group_id}, instance {instance_id}: {error}")
                step.program = program
                if not error:
                    break
            entity_list.append(entities)
            step.end_state = state
            step.reward = final_reward
            post_production_flows = instance.namespace._get_production_stats()
            step.program.meta["post_production_flows"] = post_production_flows
            step.program.meta["profits"] = -1
        except Exception as e:
            print(f"Error during evaluation in group {group.group_id}, instance {instance_id}: {e}")
            raise e

        step.program.raw_reward = step.reward
        step.program.state = step.end_state
        step.program.response = result
        step.program.parent_id = parent_id
        step.program.achievements = achievements
        return step, entity_list

    async def save_step(self, plan: PlanOutput, step: Step, original_parent: Program, run_id: str):
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
        meta = {"objective": objective, 
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
                }

        program = step.program
        program.meta = meta
        program.parent_id = parent_id
        await self.db_client.create_program(program)
        output_dict = {"step_nr": len(plan.steps),
                        "holdout_achievements" : step.program.meta.get("holdout_achievements", None),
                        "program_id": program.id
                        }
        return output_dict

    async def _process_last_step(self, plan: PlanOutput,
                                 start_state: GameState,
                                 group: PlanningGroupV2,
                                 instance_id: int,
                                 parent_id: Optional[int],
                                 skip_failures: bool,
                                 task: OpenEndedTaskConfig) -> PlanOutput:
        try:
            step_to_process = plan.steps[-1]
            if len(step_to_process.sampled_programs) == 0:
                # pop the last step from plan
                plan.steps.pop()
                return plan
            step_to_process, entity_list = await self._evaluate_step(step_to_process, start_state, group, instance_id,
                                                                              parent_id)
            if skip_failures and "error" in step_to_process.program.response.lower():
                raise Exception("Found error in response. Skipping step.")
            
            plan.steps[-1] = step_to_process
            achievements = self.get_throughput(plan=plan, group=group)
            plan.steps[-1].program.meta["holdout_achievements"] = achievements
            throughput_entity = task.throughput_entity
            throughput = achievements["dynamic"].get(throughput_entity, 0)
            #throughput_str = f"Current throughput of {throughput_entity}: {throughput} created per 60 seconds"
            throughput_str = f"Here is the current througphut of your factory: {achievements['dynamic']} created per 60 seconds"
            plan.steps[-1].program.response += f"\n{throughput_str}"
            return plan


        except Exception as e:
            print(f"Failed to evaluate program on instance {instance_id}: {str(e)}")
            # pop the last step from plan
            plan.steps.pop()
            return plan
    

    def get_throughput(self, 
                            plan: PlanOutput,
                            group: PlanningGroupV2) -> bool:
        sleep_seconds = 60
        instance_id = plan.meta["plan_id"]
        instance = group.evaluator.instances[instance_id]
        check_state = plan.steps[-1].end_state
        instance.reset(check_state)
        result, achievements, post_production_flows = group.evaluator._evaluate_for_achievements(code = f"sleep({sleep_seconds})", instance=instance)

        return achievements