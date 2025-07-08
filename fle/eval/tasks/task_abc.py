from typing import Dict, List, Optional
from fle.env import Inventory
from fle.env import FactorioInstance
from fle.agents import TaskResponse
from fle.commons.models.game_state import GameState


class TaskABC:
    def __init__(
        self,
        trajectory_length,
        starting_inventory: Inventory,
        goal_description: str,
        task_key: str,
        all_technology_reserached: bool = False,
        agent_instructions: Optional[List[str]] = None,
    ):
        self.trajectory_length = trajectory_length
        self.starting_inventory = starting_inventory
        self.goal_description = goal_description
        self.task_key = task_key
        self.all_technology_reserached = all_technology_reserached
        self.agent_instructions = agent_instructions

    def get_agent_instructions(self, agent_idx: int) -> Optional[str]:
        if self.agent_instructions is None:
            return None
        elif agent_idx >= len(self.agent_instructions):
            raise IndexError(
                f"Agent index {agent_idx} is out of bounds for agent instructions"
            )
        else:
            return self.agent_instructions[agent_idx]

    def verify(
        self, score: float, step: int, instance: FactorioInstance, step_statistics: Dict
    ) -> TaskResponse:
        """Verify if the task is completed based on the current state.

        Args:
            score (float): The current score/reward value
            step (int): The current step number
            instance (FactorioInstance): The Factorio game instance
            step_statistics (Dict): Dictionary containing statistics about the current step

        Returns:
            TaskResponse: Response object indicating task completion status and metadata
        """
        pass

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def enhance_response_with_task_output(
        self, response: str, task_response: TaskResponse
    ) -> str:
        """Add task specific information to the environment response"""
        return response

    def setup(self, instance):
        """setup function"""
        instance.initial_inventory = self.starting_inventory
        instance.all_technologies_researched = self.all_technology_reserached
        instance.reset()
        self.setup_instance(instance)
        self.starting_game_state = GameState.from_instance(instance)
