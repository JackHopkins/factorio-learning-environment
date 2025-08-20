import time

def test_sleep(game):
    for i in range(10):
        game.instance.set_speed(i)
        speed = game.instance.get_speed()
        start_time = time.time()
        game.sleep(10)
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        assert elapsed_seconds * speed - 10 < 1, (
            f"Sleep function did not work as expected for speed {i}"
        )
