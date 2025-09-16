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
        """Create a task from either a JSON file or Python-based definition.

        Args:
            task_path: Either a path to a JSON file (e.g., "lab_play/task.json")
                      or a Python task key (e.g., "iron_plate_throughput")

        Returns:
            TaskABC instance
        """
        # Check if it's a Python-based throughput task (no .json extension)
        if not task_path.endswith(".json"):
            try:
                from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import (
                    get_throughput_task,
                )

                task_config = get_throughput_task(task_path)
                config_dict = task_config.to_dict()
                task_type = config_dict.pop("task_type")
                config_dict.pop("num_agents", None)  # Remove if present

                if task_type == "throughput":
                    return ThroughputTask(**config_dict)
                else:
                    raise ValueError(
                        f"Unsupported task type from Python config: {task_type}"
                    )
            except (ImportError, KeyError):
                # Fall through to try as JSON path
                pass

        # Try loading as JSON file (backward compatibility)
        task_path = Path(TASK_FOLDER, task_path)
        with open(task_path, "r") as f:
            input_json = json.load(f)

        task_type_mapping = {
            "throughput": ThroughputTask,
            "default": DefaultTask,
            "unbounded_throughput": UnboundedThroughputTask,
        }
        task_type = input_json["task_type"]
        if "num_agents" in input_json:
            del input_json["num_agents"]
        if "task_type" in input_json:
            del input_json["task_type"]
        if task_type in task_type_mapping:
            task_class = task_type_mapping[task_type]
            return task_class(**input_json)
        else:
            raise ValueError(f"Task key {task_type} not recognized")
