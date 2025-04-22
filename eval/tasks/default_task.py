from typing import Any, Dict, List, Union
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.task_abc import TaskABC
from env.src.utils.achievements import eval_program_with_achievements
from models.game_state import GameState
import copy
from agents import TaskResponse


class DefaultTask(TaskABC):
    def __init__(self, trajectory_length, goal_description: str, task_key: str):
        super().__init__(trajectory_length, starting_inventory = {}, 
                         goal_description=goal_description, 
                         task_key = task_key,
                         all_technology_researched=False)
        self.starting_game_state = None
        
    
    def verify(self, score: float, instance: FactorioInstance, step_statistics: Dict) -> TaskResponse:
        return TaskResponse(success = False,
                            meta = {})
            
    def _to_dict(self) -> Dict[str, Any]:
        return {
            "goal_description": self.goal_description,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw() if self.starting_game_state else None,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass