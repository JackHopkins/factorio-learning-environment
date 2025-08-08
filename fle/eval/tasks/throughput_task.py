from typing import Any, Dict, List, Optional
from fle.env import Entity
from fle.env import FactorioInstance
from fle.eval.tasks import TaskABC
from fle.env.utils.achievements import eval_program_with_achievements
from fle.agents import TaskResponse


class ThroughputTask(TaskABC):
    def __init__(
        self,
        trajectory_length,
        goal_description: str,
        task_key: str,
        throughput_entity: Entity,
        quota: int,
        holdout_wait_period: int,
        pre_holdout_wait_period: int = 0,
        agent_instructions: Optional[List[str]] = None,
    ):
        # Import constants from the module to avoid circular imports
        from fle.eval.tasks import (
            LAB_PLAY_POPULATED_STARTING_INVENTORY,
            CRAFTING_STATISTICS,
            BOUNDED_INSTRUCTIONS,
        )

        goal_description += f"\n{BOUNDED_INSTRUCTIONS}"
        goal_description += "\n\n##Useful statistics\n" + CRAFTING_STATISTICS
        super().__init__(
            trajectory_length,
            starting_inventory=LAB_PLAY_POPULATED_STARTING_INVENTORY,
            goal_description=goal_description,
            task_key=task_key,
            all_technology_reserached=True,
            agent_instructions=agent_instructions,
        )
        self.throughput_entity = throughput_entity
        self.quota = quota
        self.holdout_wait_period = holdout_wait_period
        self.starting_game_state = None
        self.pre_holdout_wait_period = pre_holdout_wait_period

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
            success=max_achieved_throughput >= self.quota,
            meta={"achievements": max_achievements},
        )

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.goal_description,
            "throughput_entity": self.throughput_entity,
            "quota": self.quota,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw()
            if self.starting_game_state
            else None,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def enhance_response_with_task_output(
        self, response: str, task_response: TaskResponse
    ) -> str:
        task_throughputs = task_response.meta.get("achievements", None)
        if task_throughputs:
            response += f"\n\nHere is the current throughput of your factory: {task_throughputs['dynamic']} created per 60 seconds"

        return response
