import inspect
import os
from pathlib import Path

from eval.tasks.default_task import DefaultTask
from eval.tasks.progressive_throughput_task import ProgressiveThroughputTask
from eval.tasks.task_abc import TaskABC
from eval.tasks.throughput_task import ThroughputTask
from eval.tasks.timebounded_throughput_task import TimeboundedThroughputTask

TASK_FOLDER = Path( "..","..", "tasks", "task_definitions")
import json

class TaskFactory:
    """
    Factory for creating task instances from configuration files.
    Includes robust path resolution to find task definition files.
    """

    @staticmethod
    def create_task(task_path) -> TaskABC:
        """
        Create a task instance from a task definition file.

        Args:
            task_path: Path or filename of the task definition JSON file

        Returns:
            TaskABC: An instance of the appropriate task class

        Raises:
            FileNotFoundError: If the task file cannot be found
            ValueError: If the task type is not recognized
        """
        # Resolve the task path
        resolved_path = TaskFactory._resolve_task_path(task_path)

        if not resolved_path:
            raise FileNotFoundError(f"Task file not found: {task_path}. Tried multiple possible locations.")

        # Load and parse the task definition
        with open(resolved_path, 'r') as f:
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
            raise ValueError(f"Task type '{task_type}' not recognized")

    @staticmethod
    def _resolve_task_path(task_path):
        """
        Resolve the task path by trying multiple possible locations.

        Args:
            task_path: The task path or filename provided

        Returns:
            str: The resolved absolute path to the task file, or None if not found
        """
        # Convert to Path object for easier manipulation
        task_path_obj = Path(task_path)

        # If it's an absolute path and exists, use it directly
        if task_path_obj.is_absolute() and task_path_obj.exists():
            return str(task_path_obj)

        # Get the directory of this module
        try:
            # Using inspect to get the file of the TaskFactory class
            factory_file = inspect.getfile(TaskFactory)
            factory_dir = Path(os.path.dirname(os.path.abspath(factory_file)))
        except (TypeError, ValueError):
            # Fallback if inspect doesn't work (e.g., in interactive sessions)
            factory_dir = Path(os.getcwd())

        # Project root is likely two levels up from the factory file
        # (assuming structure like project_root/eval/tasks/task_factory.py)
        project_root = factory_dir.parents[2] if len(factory_dir.parents) >= 2 else factory_dir

        # Multiple potential locations to check
        potential_paths = [
            # Original path as provided
            task_path_obj,

            # Relative to the factory module
            factory_dir / task_path_obj,
            factory_dir / "task_definitions" / task_path_obj,

            # Standard location in project structure
            project_root / "eval" / "tasks" / "task_definitions" / task_path_obj,

            # Additional potential locations
            factory_dir.parent / "task_definitions" / task_path_obj,
            Path("eval") / "tasks" / "task_definitions" / task_path_obj,
            Path.cwd() / "eval" / "tasks" / "task_definitions" / task_path_obj
        ]

        # Try each path
        for path in potential_paths:
            if path.exists():
                return str(path)

        # If we reach here, we couldn't find the file
        print("Task file not found. Tried the following paths:")
        for path in potential_paths:
            print(f"  - {path}")

        return None

    @staticmethod
    def list_available_tasks(directory=None):
        """
        List all available task definition files.

        Args:
            directory: Optional directory to search. If None, uses default locations.

        Returns:
            List[str]: Names of available task files
        """
        task_files = []

        # If directory is provided, just look there
        if directory:
            search_dirs = [Path(directory)]
        else:
            # Otherwise, try multiple possible locations
            try:
                factory_file = inspect.getfile(TaskFactory)
                factory_dir = Path(os.path.dirname(os.path.abspath(factory_file)))
            except (TypeError, ValueError):
                factory_dir = Path(os.getcwd())

            project_root = factory_dir.parents[2] if len(factory_dir.parents) >= 2 else factory_dir

            search_dirs = [
                factory_dir / "task_definitions",
                project_root / "eval" / "tasks" / "task_definitions",
                factory_dir.parent / "task_definitions",
                Path("eval") / "tasks" / "task_definitions",
                Path.cwd() / "eval" / "tasks" / "task_definitions"
            ]

        # Search each directory for JSON files
        for directory in search_dirs:
            if directory.exists():
                task_files.extend([f.name for f in directory.glob("*.json")])

        return sorted(list(set(task_files)))  # Remove duplicates and sort