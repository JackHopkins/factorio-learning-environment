from fle.eval.tasks import TaskABC


class TaskFactory:
    def __init__(self):
        pass

    @staticmethod
    def create_task(task_path) -> TaskABC:
        """Create a task from a Python-based definition.

        Args:
            task_path: Task key (e.g., "iron_plate_throughput")

        Returns:
            TaskABC instance
        """
        from fle.eval.tasks.task_definitions.task_registry import create_task

        return create_task(task_path)
