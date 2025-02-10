from typing import Any, Dict, List, Union
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.task_abc import TaskABC
from env.src.utils.achievements import eval_program_with_achievements
from eval.open.model.game_state import GameState
import copy

LAB_PLAY_POPULATED_STARTING_INVENTORY = {"coal": 500, "burner-mining-drill": 10, "wooden-chest": 10, "burner-inserter": 10, "transport-belt": 500,
                                "stone-furnace": 10, "boiler": 4, "offshore-pump": 3, "steam-engine": 2,
                                "iron-gear-wheel": 22, "iron-plate": 19, "copper-plate": 52, "electronic-circuit": 99,
                                "iron-ore": 62, "stone": 50, "electric-mining-drill": 10, "small-electric-pole": 500, "pipe": 100,
                                "assembling-machine-1": 5, "electric-furnace": 10}



class ThroughputTask(TaskABC):
    def __init__(self, maximum_steps, starting_inventory: Union[Inventory, Dict], task: str,
                  throughput_entity: Entity, quota: int, holdout_wait_period: int, pre_holdout_wait_period: int = 0):
        super().__init__(maximum_steps, starting_inventory, task=task)
        self.throughput_entity = throughput_entity
        self.quota = quota
        self.holdout_wait_period = holdout_wait_period
        self.starting_game_state = None
        self.pre_holdout_wait_period = pre_holdout_wait_period
    
    def verify(self, score: float, step: int, instance: FactorioInstance, step_statistics: Dict) -> bool:
        # wait the pre-holdout period
        instance.sleep(self.pre_holdout_wait_period)
        result_list, result, error,  achievements = eval_program_with_achievements(program = f"sleep({self.holdout_wait_period})", instance=instance)
        dynamic_achievements = achievements["dynamic"]
        return dynamic_achievements.get(self.throughput_entity, 0) >= self.quota, achievements
            
    def _to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "throughput_entity": self.throughput_entity,
            "quota": self.quota,
            "maximum_steps": self.maximum_steps,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw(),
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def setup(self, instance):
        """setup function"""
        self.setup_instance(instance)
        self.starting_game_state = GameState.from_instance(instance)