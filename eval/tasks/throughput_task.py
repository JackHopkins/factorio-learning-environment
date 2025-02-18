from typing import Any, Dict, List, Union
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.task_abc import TaskABC
from env.src.utils.achievements import eval_program_with_achievements
from models.game_state import GameState
import copy
from agents.utils import TaskResponse

LAB_PLAY_POPULATED_STARTING_INVENTORY = {"coal": 500, "burner-mining-drill": 50, "wooden-chest": 10, "burner-inserter": 50,"inserter": 50, "transport-belt": 500,
                                "stone-furnace": 10, "boiler": 2, "offshore-pump": 2, "steam-engine": 2,
                                "electric-mining-drill": 50, "small-electric-pole": 500, "pipe": 500,
                                "assembling-machine-2": 10, "electric-furnace": 10, "pipe-to-ground": 100, "underground-belt": 100,
                                "pumpjack": 10, "oil-refinery": 5, "chemical-plant": 5, "storage-tank": 10,
                                #"solar-panel": 50,
                                }



class ThroughputTask(TaskABC):
    def __init__(self, trajectory_length, starting_inventory: Union[Inventory, Dict], task: str,
                  throughput_entity: Entity, quota: int, holdout_wait_period: int, pre_holdout_wait_period: int = 0):
        super().__init__(trajectory_length, starting_inventory, task=task)
        self.throughput_entity = throughput_entity
        self.quota = quota
        self.holdout_wait_period = holdout_wait_period
        self.starting_game_state = None
        self.pre_holdout_wait_period = pre_holdout_wait_period
    
    def verify(self, score: float, instance: FactorioInstance, step_statistics: Dict) -> TaskResponse:
        max_achieved_throughput = 0
        max_achievements = None
        # wait the pre-holdout period
        instance.namespace.sleep(self.pre_holdout_wait_period)
        while True:
            result_list, result, error,  achievements = eval_program_with_achievements(program = f"sleep({self.holdout_wait_period})", instance=instance)
            if max_achievements is None:
                max_achievements = achievements
            dynamic_achievements = achievements["dynamic"]
            target_throughput = dynamic_achievements.get(self.throughput_entity, 0)
            if target_throughput > max_achieved_throughput:
                max_achieved_throughput = target_throughput
                max_achievements = achievements
            else:
                break
        return TaskResponse(success = max_achieved_throughput >= self.quota,
                            meta = {"achievements": max_achievements})
            
    def _to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "throughput_entity": self.throughput_entity,
            "quota": self.quota,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw() if self.starting_game_state else None,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def setup(self, instance):
        """setup function"""
        instance.initial_inventory = self.starting_inventory
        instance.reset()
        self.setup_instance(instance)
        self.starting_game_state = GameState.from_instance(instance)