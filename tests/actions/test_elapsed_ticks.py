import pytest
import time

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-ore": 100,
        "coal": 100,
        "stone": 100,
        "wood": 50,
        "iron-plate": 50,
        "transport-belt": 20,
        "stone-furnace": 2,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_sleep_elapsed_ticks_and_timing(game):
    """Test that sleep adds correct ticks and sleeps for appropriate real-world time."""
    # Test at normal speed (1x)
    game.instance.set_speed_and_unpause(1.0)

    # Get initial elapsed ticks
    initial_ticks = game.instance.get_elapsed_ticks()

    # Sleep for 2 seconds and measure real-world time
    sleep_seconds = 2
    start_time = time.time()
    game.sleep(sleep_seconds)
    end_time = time.time()
    real_sleep_time = end_time - start_time

    # Check elapsed ticks - should add 2 * 60 = 120 ticks
    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    assert ticks_added == sleep_seconds * 60, (
        f"Expected {sleep_seconds * 60} ticks, got {ticks_added}"
    )
    assert abs(real_sleep_time - sleep_seconds) < 0.1, (
        f"Expected ~{sleep_seconds}s sleep, got {real_sleep_time:.2f}s"
    )


def test_sleep_with_different_game_speeds(game):
    """Test sleep timing at different game speeds."""
    sleep_seconds = 1

    # Test at 2x speed
    game.instance.set_speed_and_unpause(2.0)
    initial_ticks = game.instance.get_elapsed_ticks()

    start_time = time.time()
    game.sleep(sleep_seconds)
    end_time = time.time()
    real_sleep_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Should still add 60 ticks (standard time)
    assert ticks_added == sleep_seconds * 60, (
        f"Expected {sleep_seconds * 60} ticks, got {ticks_added}"
    )
    # Should sleep for 0.5 seconds in real-world time (1/2 speed)
    expected_real_time = sleep_seconds / 2.0
    assert abs(real_sleep_time - expected_real_time) < 0.1, (
        f"Expected ~{expected_real_time}s sleep, got {real_sleep_time:.2f}s"
    )

    # Test at 10x speed
    game.instance.set_speed_and_unpause(10.0)
    initial_ticks = game.instance.get_elapsed_ticks()

    start_time = time.time()
    game.sleep(sleep_seconds)
    end_time = time.time()
    real_sleep_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Should still add 60 ticks (standard time)
    assert ticks_added == sleep_seconds * 60, (
        f"Expected {sleep_seconds * 60} ticks, got {ticks_added}"
    )
    # Should sleep for 0.1 seconds in real-world time (1/10 speed)
    expected_real_time = sleep_seconds / 10.0
    assert abs(real_sleep_time - expected_real_time) < 0.05, (
        f"Expected ~{expected_real_time}s sleep, got {real_sleep_time:.2f}s"
    )


def test_move_to_elapsed_ticks_and_timing(game):
    """Test that move_to adds correct ticks and sleeps appropriately."""
    game.instance.set_speed_and_unpause(1.0)  # Normal speed for baseline

    # Get initial position and ticks
    initial_pos = Position(x=0, y=0)
    game.move_to(initial_pos)
    initial_ticks = game.instance.get_elapsed_ticks()

    # Move to a position 5 tiles away
    target_pos = Position(x=initial_pos.x + 5, y=initial_pos.y)

    start_time = time.time()
    game.move_to(target_pos)
    end_time = time.time()
    real_time = end_time - start_time

    # Check ticks added
    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Movement should add ticks based on distance and player speed
    # Character speed is ~0.15 tiles/tick, so 5 tiles should take ~33-34 ticks
    expected_ticks = 5 / 0.15  # Distance / speed
    assert 25 <= ticks_added <= 40, (
        f"Expected ~{expected_ticks:.0f} ticks for 5-tile movement, got {ticks_added}"
    )

    # Real-world sleep should be proportional to ticks at current speed
    expected_real_time = ticks_added / 60  # ticks / (60 ticks/second)
    assert abs(real_time - expected_real_time) < 0.5, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_move_to_with_different_speeds(game):
    """Test move_to timing at different game speeds."""
    target_pos = Position(x=3, y=3)

    # Test at 5x speed
    game.instance.set_speed_and_unpause(5.0)
    initial_ticks = game.instance.get_elapsed_ticks()

    start_time = time.time()
    game.move_to(target_pos)
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Should sleep for (ticks_added / 60) / 5.0 seconds in real-world time
    expected_real_time = ticks_added / 60 / 5.0
    assert abs(real_time - expected_real_time) < 0.2, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_craft_item_elapsed_ticks_and_timing(game):
    """Test that craft_item adds correct ticks and sleeps appropriately."""
    game.instance.set_speed_and_unpause(1.0)  # Normal speed

    initial_ticks = game.instance.get_elapsed_ticks()

    # Craft iron gear wheels (recipe energy: 0.5 seconds = 30 ticks each)
    quantity = 3

    start_time = time.time()
    game.craft_item(Prototype.IronGearWheel, quantity)
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Each iron gear wheel takes 0.5 seconds = 30 ticks
    expected_ticks = quantity * 30
    assert ticks_added == expected_ticks, (
        f"Expected {expected_ticks} ticks for {quantity} iron gear wheels, got {ticks_added}"
    )

    # Real-world sleep should match ticks at current speed
    expected_real_time = ticks_added / 60  # ticks / (60 ticks/second)
    assert abs(real_time - expected_real_time) < 0.5, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_craft_item_with_different_speeds(game):
    """Test craft_item timing at different game speeds."""
    # Test at 3x speed
    game.instance.set_speed_and_unpause(3.0)

    initial_ticks = game.instance.get_elapsed_ticks()

    start_time = time.time()
    game.craft_item(Prototype.IronGearWheel, 2)  # 2 * 30 = 60 ticks
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Should add 60 ticks regardless of speed
    assert ticks_added == 60, f"Expected 60 ticks, got {ticks_added}"

    # Should sleep for 60/60/3 = 0.33 seconds in real-world time
    expected_real_time = 60 / 60 / 3.0
    assert abs(real_time - expected_real_time) < 0.2, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_harvest_resource_elapsed_ticks_and_timing(game):
    """Test that harvest_resource adds correct ticks and sleeps appropriately."""
    game.instance.set_speed_and_unpause(1.0)  # Normal speed

    # Find iron ore to harvest
    iron_ore_pos = game.nearest(Resource.IronOre)
    game.move_to(iron_ore_pos)

    initial_ticks = game.instance.get_elapsed_ticks()

    # Harvest 1 unit (iron ore mining time is typically 1 second = 60 ticks)
    start_time = time.time()
    game.harvest_resource(iron_ore_pos, quantity=1)
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Iron ore typically takes 60 ticks to mine
    # But might vary, so allow some range
    assert 50 <= ticks_added <= 80, (
        f"Expected ~60 ticks for iron ore harvest, got {ticks_added}"
    )

    # Real-world sleep should match ticks at current speed
    expected_real_time = ticks_added / 60  # ticks / (60 ticks/second)
    assert abs(real_time - expected_real_time) < 0.5, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_harvest_resource_with_different_speeds(game):
    """Test harvest_resource timing at different game speeds."""
    # Test at 4x speed
    game.instance.set_speed_and_unpause(4.0)

    iron_ore_pos = game.nearest(Resource.IronOre)
    game.move_to(iron_ore_pos)
    initial_ticks = game.instance.get_elapsed_ticks()

    start_time = time.time()
    game.harvest_resource(iron_ore_pos, quantity=1)
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    # Should sleep for (ticks_added / 60) / 4.0 seconds in real-world time
    expected_real_time = ticks_added / 60 / 4.0
    assert abs(real_time - expected_real_time) < 0.3, (
        f"Expected ~{expected_real_time:.2f}s real time, got {real_time:.2f}s"
    )


def test_multiple_actions_cumulative_ticks(game):
    """Test that multiple actions accumulate ticks correctly."""
    game.instance.set_speed_and_unpause(2.0)  # 2x speed

    # Ensure player starts at origin for consistent test results
    game.move_to(Position(x=0, y=0))

    initial_ticks = game.instance.get_elapsed_ticks()

    # Perform multiple actions
    start_time = time.time()

    # Sleep for 1 second (should add 60 ticks)
    game.sleep(1)

    # Craft 1 iron gear wheel (should add 30 ticks)
    game.craft_item(Prototype.IronGearWheel, 1)

    # Move a short distance (should add ~20 ticks)
    game.move_to(Position(x=2, y=2))

    end_time = time.time()
    total_real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    total_ticks_added = final_ticks - initial_ticks

    # Should add approximately 60 + 30 + ~20 = ~110 ticks
    assert 100 <= total_ticks_added <= 120, (
        f"Expected ~110 total ticks, got {total_ticks_added}"
    )

    # Real-world time should be total_ticks / 60 / 2.0 seconds
    expected_real_time = total_ticks_added / 60 / 2.0
    assert abs(total_real_time - expected_real_time) < 0.5, (
        f"Expected ~{expected_real_time:.2f}s total real time, got {total_real_time:.2f}s"
    )


def test_elapsed_ticks_persistence(game):
    """Test that elapsed ticks persist across multiple tool calls."""
    game.instance.set_speed_and_unpause(1.0)

    # Get baseline
    initial_ticks = game.instance.get_elapsed_ticks()

    # First action: sleep 1 second
    game.sleep(1)
    after_sleep_ticks = game.instance.get_elapsed_ticks()

    # Second action: craft item
    game.craft_item(Prototype.IronGearWheel, 1)
    after_craft_ticks = game.instance.get_elapsed_ticks()

    # Verify cumulative addition
    sleep_ticks = after_sleep_ticks - initial_ticks
    craft_ticks = after_craft_ticks - after_sleep_ticks
    total_ticks = after_craft_ticks - initial_ticks

    assert sleep_ticks == 60, f"Sleep should add 60 ticks, got {sleep_ticks}"
    assert craft_ticks == 30, f"Craft should add 30 ticks, got {craft_ticks}"
    assert total_ticks == 90, f"Total should be 90 ticks, got {total_ticks}"


def test_zero_speed_handling(game):
    """Test that tools handle zero/very low speed gracefully."""
    # Test with very low speed (but not zero to avoid division by zero)
    game.instance.set_speed_and_unpause(0.5)

    initial_ticks = game.instance.get_elapsed_ticks()

    # Sleep for 0.5 seconds - should still add 30 ticks
    start_time = time.time()
    game.sleep(0.5)
    end_time = time.time()
    real_time = end_time - start_time

    final_ticks = game.instance.get_elapsed_ticks()
    ticks_added = final_ticks - initial_ticks

    assert ticks_added == 30, f"Expected 30 ticks for 0.5s sleep, got {ticks_added}"
    # At 0.5x speed, should sleep for 0.5/0.5 = 1 second real time
    assert abs(real_time - 1) < 0.2, f"Expected ~1s real time, got {real_time:.2f}s"
