from typing import Any, Dict, List, Optional
from fle.env import Entity
from fle.env import FactorioInstance
from fle.eval.tasks import TaskABC
from fle.env.utils.achievements import eval_program_with_achievements
from fle.agents import TaskResponse
from fle.env.system_prompt import SystemPromptBuilder


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
        system_prompt_builder: Optional[SystemPromptBuilder] = None,
    ):
        # Import constants from the module to avoid circular imports
        from fle.eval.tasks import (
            LAB_PLAY_POPULATED_STARTING_INVENTORY,
            CRAFTING_STATISTICS,
        )

        # Store raw task description for flexible system prompt generation
        self.base_goal_description = goal_description
        self.statistics = CRAFTING_STATISTICS
        self.system_prompt_builder = system_prompt_builder

        # For backward compatibility, still create the old-style goal_description
        # if no custom builder is provided
        if system_prompt_builder is None:
            from fle.eval.tasks import BOUNDED_INSTRUCTIONS

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

    def build_system_prompt(
        self, agent_idx: Optional[int] = None, num_agents: int = 1
    ) -> str:
        """Generate a customized system prompt for this task."""
        if self.system_prompt_builder is not None:
            # Use custom builder if provided
            builder = self.system_prompt_builder
            if num_agents > 1 and agent_idx is not None:
                builder = builder.with_multiagent(agent_idx, num_agents)
            return builder.build()
        else:
            # Use default throughput task builder
            builder = SystemPromptBuilder.for_throughput_task(
                task_description=self.base_goal_description,
                statistics=self.statistics,
                quota=self.quota,
                entity=self.throughput_entity,
            )
            if num_agents > 1 and agent_idx is not None:
                builder = builder.with_multiagent(agent_idx, num_agents)
            return builder.build()
