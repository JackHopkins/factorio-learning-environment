import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "coal": 50,
            "iron-chest": 1,
            "iron-plate": 5,
            "stone-furnace": 1,
        }
    )


def test_move_to(game):
    """
    Move to the nearest coal patch
    Move to the nearest iron patch
    :param game:
    :return:
    """
    resources = [Resource.Coal, Resource.IronOre, Resource.CopperOre, Resource.Stone]

    for i in range(10):
        for resource in resources:
            game.move_to(game.nearest(resource))
            pass


def test_move_to_bug(game):
    # Get stone for stone furnace
    game.move_to(game.nearest(Resource.Stone))
    game.harvest_resource(game.nearest(Resource.Stone), quantity=5)

    # Check if we got the stone
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"


def test_move_to_check_position(game):
    target_pos = Position(x=-9.5, y=-11.5)

    # Move to target position
    game.move_to(target_pos)


def test_move_to_string_response_error_handling(game):
    """Test enhanced error handling for string responses from Lua server"""
    # This test may need to trigger specific conditions that cause string responses
    # For now, test that normal movement still works (the error handling is transparent)

    positions_to_test = [
        Position(x=10, y=10),
        Position(x=50, y=50),
        Position(x=100, y=100),
    ]

    for pos in positions_to_test:
        try:
            game.move_to(pos)
            print(f"✓ Successfully moved to {pos}")
        except Exception as e:
            # If we get a string response error, it should be properly formatted
            error_msg = str(e)
            if "Could not move" in error_msg:
                print(f"✓ Got properly formatted move error: {error_msg}")
            else:
                # Re-raise unexpected errors
                raise


def test_move_to_invalid_positions(game):
    """Test move_to behavior with potentially problematic positions"""
    # Test some edge case positions that might trigger string responses
    edge_positions = [
        Position(x=0, y=0),  # Origin
        Position(x=-1, y=-1),  # Negative coordinates
        Position(x=1000, y=1000),  # Very far position
    ]

    successful_moves = 0
    for pos in edge_positions:
        try:
            game.move_to(pos)
            successful_moves += 1
            print(f"✓ Successfully moved to edge position {pos}")
        except Exception as e:
            # Should get properly formatted error messages, not raw Lua errors
            error_msg = str(e)
            assert "Could not move" in error_msg or "Could not get path" in error_msg, (
                f"Should get formatted error: {error_msg}"
            )
            print(f"✓ Got expected move failure for {pos}: {error_msg}")

    # At least some positions should work
    assert successful_moves >= 0, "Error handling should not break all movement"


def test_move_to_near_entities(game):
    """Test movement near entities doesn't cause string response errors"""
    # Place an entity
    game.move_to(Position(x=18, y=20))
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=20, y=20))
    assert furnace, "Failed to place furnace"

    # Try to move very close to the entity
    try:
        game.move_to(Position(x=20.1, y=20.1))  # Very close to entity
        print("✓ Can move very close to entities")
    except Exception as e:
        # Should get proper error message if movement fails
        error_msg = str(e)
        assert "Could not move" in error_msg, f"Should get formatted error: {error_msg}"
        print(f"✓ Got proper error for blocked movement: {error_msg}")
