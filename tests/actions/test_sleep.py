import time
import pytest


@pytest.mark.parametrize("speed", range(10))  # 10 independent items
def test_sleep(game, speed):
    game.instance.set_speed(speed)
    start = time.time()
    game.sleep(10)
    elapsed = time.time() - start
    assert elapsed * speed - 10 < 1, f"Sleep behaved unexpectedly at speed {speed}"
