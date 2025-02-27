from typing import Any, Dict, List
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.throughput_task import ThroughputTask
from eval.tasks.default_task import DefaultTask
from eval.tasks.task_abc import TaskABC
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


        task_type = input_json["task_type"]
        task_config = input_json["config"]
        if task_type == "throughput":
            return ThroughputTask(**task_config)
        elif task_type == "default":
            return DefaultTask(**task_config)
        else:
            raise ValueError(f"Task key {task_type} not recognized")