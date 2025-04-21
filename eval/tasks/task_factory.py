from typing import Any, Dict, List
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.throughput_task import ThroughputTask
from eval.tasks.default_task import DefaultTask
from eval.tasks.task_abc import TaskABC
from eval.tasks.unbounded_throughput_task import UnboundedThroughputTask
from pathlib import Path
TASK_FOLDER = Path("eval", "tasks", "task_definitions")
import json

class TaskFactory:
    def __init__(self):
        pass

    @staticmethod
    def create_task(task_path) -> TaskABC:
        task_path = Path(TASK_FOLDER, task_path)
        with open(task_path, 'r') as f:
            input_json = json.load(f)

        task_type_mapping = {
            "throughput": ThroughputTask,
            "default": DefaultTask,
            "unbounded_throughput": UnboundedThroughputTask
        }
        task_type = input_json["task_type"]
        task_config = input_json["config"]
        if task_type in task_type_mapping:
            task_class = task_type_mapping[task_type]
            return task_class(**task_config)
        else:
            raise ValueError(f"Task key {task_type} not recognized")