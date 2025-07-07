from typing import Any, Dict, List, Optional
from fle.env import Entity
from fle.env import FactorioInstance
from fle.eval.tasks import TaskABC
from fle.eval.tasks import LAB_PLAY_POPULATED_STARTING_INVENTORY, CRAFTING_STATISTICS
from fle.env.utils.achievements import eval_program_with_achievements
from fle.agents import TaskResponse


INSTRUCTIONS = """
You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. Create the largest factory as you can that automatically creates the target entity
    
After each step the throughput of the factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response. Iteratively expand your factory, i.e first make a small factory step by step and then expand the factory in subsequent steps .
"""


class UnboundedThroughputTask(TaskABC):
    def __init__(
        self,
        trajectory_length,
        goal_description: str,
        task_key: str,
        throughput_entity: Entity,
        holdout_wait_period: int,
        pre_holdout_wait_period: int = 0,
        show_number_of_steps_left_in_prompt=False,
        include_stats=True,
        use_populated_inventory=True,
        unlock_all_research=True,
        agent_instructions: Optional[List[str]] = None,
    ) -> None:
        goal_description += f"\n{INSTRUCTIONS}"
        if include_stats:
            goal_description += "\n\n##Useful statistics\n" + CRAFTING_STATISTICS
        if show_number_of_steps_left_in_prompt:
            goal_description += (
                f"\n\nIn total you have {trajectory_length} steps to build your factory"
            )
        starting_inventory = (
            LAB_PLAY_POPULATED_STARTING_INVENTORY if use_populated_inventory else {}
        )
        super().__init__(
            trajectory_length,
            starting_inventory=starting_inventory,
            goal_description=goal_description,
            task_key=task_key,
            all_technology_reserached=unlock_all_research,
            agent_instructions=agent_instructions,
        )
        self.throughput_entity = throughput_entity
        self.holdout_wait_period = holdout_wait_period
        self.starting_game_state = None
        self.pre_holdout_wait_period = pre_holdout_wait_period
        self.show_number_of_steps_left_in_prompt = show_number_of_steps_left_in_prompt

    def verify(
        self, score: float, instance: FactorioInstance, step_statistics: Dict
    ) -> TaskResponse:
        max_achieved_throughput = 0
        max_achievements = None
        # wait the pre-holdout period
        # instance.namespace.sleep(self.pre_holdout_wait_period)
        while True:
            result_list, result, error, achievements = eval_program_with_achievements(
                program=f"sleep({self.holdout_wait_period})", instance=instance
            )
            if max_achievements is None:
                max_achievements = achievements
            dynamic_achievements = achievements["dynamic"]
            target_throughput = dynamic_achievements.get(self.throughput_entity, 0)
            if target_throughput > max_achieved_throughput:
                max_achieved_throughput = target_throughput
                max_achievements = achievements
            else:
                break
        return TaskResponse(
            success=False,
            meta={
                "achievements": max_achievements,
                "nr_of_steps_left": self.trajectory_length
                - step_statistics["current_step_id"]
                - 1,
            },
        )

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.goal_description,
            "throughput_entity": self.throughput_entity,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw()
            if self.starting_game_state
            else None,
            "show_number_of_steps_left_in_prompt": self.show_number_of_steps_left_in_prompt,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def enhance_response_with_task_output(
        self, response: str, task_response: TaskResponse
    ) -> str:
        task_throughputs = task_response.meta.get("achievements", None)
        number_of_steps_left = task_response.meta.get("nr_of_steps_left", None)
        if task_throughputs:
            response += f"\n\nHere is the current throughput of your factory: {task_throughputs['dynamic']} created per 60 seconds"
        if self.show_number_of_steps_left_in_prompt and number_of_steps_left:
            response += f"\n\nYou have: {number_of_steps_left} steps left to build or expand your factory"

        return response
