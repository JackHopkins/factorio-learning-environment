from types import SimpleNamespace

import pytest

from fle.env.entities import Inventory
from fle.env.game_types import Prototype
from fle.env.tools.agent.wait.client import Wait


class FakeInstance:
    def __init__(self):
        self.elapsed_ticks = 0
        self.game_tick = 100

    def get_elapsed_ticks(self):
        return self.elapsed_ticks

    def get_speed(self):
        return 1_000_000_000


def make_wait(counts):
    instance = FakeInstance()
    namespace = SimpleNamespace(instance=instance)
    reads = iter(counts)
    namespace.inspect_inventory = lambda _entity: Inventory(
        **{"stone-brick": next(reads)}
    )
    tool = Wait.__new__(Wait)
    tool.game_state = namespace

    def execute(ticks):
        instance.elapsed_ticks += ticks
        instance.game_tick += ticks
        return instance.game_tick, 0

    tool.execute = execute
    return tool


def test_wait_advances_requested_ticks_without_condition():
    result = make_wait([])(ticks=900, poll_ticks=300)

    assert result == {
        "requested_ticks": 900,
        "waited_ticks": 900,
        "simulation_ticks_advanced": 900,
        "action_ticks_charged": 900,
        "condition_met": None,
        "observed": None,
    }


def test_wait_stops_when_inventory_condition_is_met():
    entity = object()
    result = make_wait([0, 2, 5])(
        ticks=900,
        until={
            "inventory": {
                "entity": entity,
                "item": Prototype.StoneBrick,
                "at_least": 5,
            }
        },
        poll_ticks=300,
    )

    assert result["waited_ticks"] == 600
    assert result["condition_met"] is True
    assert result["observed"]["count"] == 5


@pytest.mark.parametrize("ticks", [0, -1, 1.5, True])
def test_wait_rejects_invalid_ticks(ticks):
    with pytest.raises(ValueError, match="ticks must be a positive integer"):
        make_wait([])(ticks=ticks)
