from typing import Any, Dict, List, Optional
from fle.env import Entity
from fle.env import FactorioInstance
from fle.eval.tasks import TaskABC
from fle.env.utils.achievements import eval_program_with_achievements
from fle.agents import TaskResponse

LAB_PLAY_POPULATED_STARTING_INVENTORY = {
    "coal": 500,
    "burner-mining-drill": 50,
    "wooden-chest": 10,
    "burner-inserter": 50,
    "inserter": 50,
    "transport-belt": 500,
    "stone-furnace": 10,
    "boiler": 2,
    "offshore-pump": 2,
    "steam-engine": 2,
    "electric-mining-drill": 50,
    "medium-electric-pole": 500,
    "pipe": 500,
    "assembling-machine-2": 10,
    "electric-furnace": 10,
    "pipe-to-ground": 100,
    "underground-belt": 100,
    "pumpjack": 10,
    "oil-refinery": 5,
    "chemical-plant": 5,
    "storage-tank": 10,
}

INSTRUCTIONS = """You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. You are also given the target throughput that the factory must achieve
After each step the throughput of the factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response."""


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
        goal_description += f"\n{INSTRUCTIONS}"
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
            meta={},
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
