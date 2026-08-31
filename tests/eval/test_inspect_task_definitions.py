from fle.eval.inspect.integration import eval_set
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import (
    THROUGHPUT_TASKS,
)


def test_every_throughput_task_has_an_inspect_definition() -> None:
    missing = [name for name in THROUGHPUT_TASKS if not hasattr(eval_set, name)]

    assert missing == []
