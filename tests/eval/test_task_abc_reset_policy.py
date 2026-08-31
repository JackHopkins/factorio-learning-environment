from fle.commons.models.game_state import GameState
from fle.eval.tasks.task_abc import TaskABC


class RecordingTaskInstance:
    def __init__(self) -> None:
        self.initial_inventory = {}
        self.all_technologies_researched = False
        self.effective_reset_values: list[bool] = []

    def reset(self, all_technologies_researched: bool | None = None) -> None:
        effective_value = (
            self.all_technologies_researched
            if all_technologies_researched is None
            else all_technologies_researched
        )
        self.effective_reset_values.append(effective_value)


def test_task_setup_persists_technology_policy_for_later_reset(monkeypatch) -> None:
    monkeypatch.setattr(GameState, "from_instance", lambda instance: object())
    instance = RecordingTaskInstance()
    task = TaskABC(
        trajectory_length=64,
        starting_inventory={"oil-refinery": 5},
        goal_description="test",
        task_key="test",
        all_technology_reserached=True,
    )

    task.setup(instance)
    instance.reset()

    assert instance.initial_inventory == {"oil-refinery": 5}
    assert instance.all_technologies_researched is True
    assert instance.effective_reset_values == [True, True]
