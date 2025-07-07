from fle.eval.tasks import ThroughputTask
from fle.eval.tasks import DefaultTask
from fle.eval.tasks import TaskABC
from fle.eval.tasks import UnboundedThroughputTask
from pathlib import Path
import json
import os

TASK_FOLDER = Path(os.path.dirname(__file__), "task_definitions")


class TaskFactory:
    def __init__(self):
        pass

    @staticmethod
    def create_task(task_path) -> TaskABC:
        task_path = Path(TASK_FOLDER, task_path)
        with open(task_path, "r") as f:
            input_json = json.load(f)

        task_type_mapping = {
            "throughput": ThroughputTask,
            "default": DefaultTask,
            "unbounded_throughput": UnboundedThroughputTask,
        }
        task_type = input_json["task_type"]
        task_config = input_json["config"]
        if task_type in task_type_mapping:
            task_class = task_type_mapping[task_type]
            return task_class(**task_config)
        else:
            raise ValueError(f"Task key {task_type} not recognized")
