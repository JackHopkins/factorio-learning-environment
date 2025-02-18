from typing import Any, Dict, List
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance

class TaskABC:
    def __init__(self, trajectory_length, starting_inventory: Inventory, task: str):
        self.trajectory_length = trajectory_length
        self.starting_inventory = starting_inventory
        self.task = task
    
    def verify(self, score: float, step: int, instance: FactorioInstance, step_statistics: Dict) -> bool:
        """ Return true is the task is completed"""
        pass
    def setup(self, instance):
        """Code to provision the task environment"""
        pass