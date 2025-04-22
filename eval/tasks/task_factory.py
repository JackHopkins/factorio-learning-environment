from pathlib import Path

from eval.tasks.default_task import DefaultTask
from eval.tasks.progressive_throughput_task import ProgressiveThroughputTask
from eval.tasks.task_abc import TaskABC
from eval.tasks.throughput_task import ThroughputTask
from eval.tasks.timebounded_throughput_task import TimeboundedThroughputTask

TASK_FOLDER = Path( "..","..", "tasks", "task_definitions")
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
            "timebounded_throughput": TimeboundedThroughputTask,
            "progressive_throughput": ProgressiveThroughputTask
        }
        task_type = input_json["task_type"]
        task_config = input_json["config"]
        if task_type in task_type_mapping:
            task_class = task_type_mapping[task_type]
            return task_class(**task_config)
        else:
            raise ValueError(f"Task key {task_type} not recognized")