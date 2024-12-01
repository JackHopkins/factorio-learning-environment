import time

import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance
    instance.reset()

def test_sleep(game):
    for i in range(10):
        game.speed(i)
        speed = game._speed
        start_time = time.time()
        game.sleep(10)
        end_time = time.time()
        elapsed_seconds = end_time-start_time
        assert elapsed_seconds*speed - 10 < 0.05, f"Sleep function did not work as expected for speed {i}"