"""
Tests for belts between splitters - verifies that get_entities returns all belts
including those that connect to splitters.
"""

import pytest
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "splitter": 20,
        "transport-belt": 100,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def clear_terrain(game):
    """Clear cliffs and rocks before each test"""
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end "
        "for _, rock in pairs(game.surfaces[1].find_entities_filtered{type='simple-entity'}) do "
        "if rock.name:find('rock') then rock.destroy() end "
        "end"
    )
    return game


def test_belts_between_splitters_are_returned(clear_terrain):
    """
    Test that belts placed between splitters are returned by get_entities.

    This was a bug where belts connecting to splitters were not being included
    in the entity list because the belt grouping algorithm only walked belt-to-belt
    connections and didn't account for belts that connect to splitters.
    """
    game = clear_terrain

    # Create a chain of splitters with belts between them
    # Splitter positions: y=0, y=3, y=6, y=9
    # Belt positions between each pair of splitters

    placed_belt_positions = []

    for i in range(4):
        y_pos = i * 3
        game.move_to(Position(x=0, y=y_pos))
        game.place_entity(
            Prototype.Splitter, position=Position(x=0, y=y_pos), direction=Direction.UP
        )

        # Place belts between splitters (except after the last one)
        if i < 3:
            # Belts at y_pos - 1 and y_pos - 2 (north of current splitter, before next splitter)
            for y_offset in [-1, -2]:
                y = y_pos + y_offset
                b1 = game.place_entity(
                    Prototype.TransportBelt,
                    position=Position(x=-0.5, y=y),
                    direction=Direction.UP,
                )
                b2 = game.place_entity(
                    Prototype.TransportBelt,
                    position=Position(x=0.5, y=y),
                    direction=Direction.UP,
                )
                placed_belt_positions.append((b1.position.x, b1.position.y))
                placed_belt_positions.append((b2.position.x, b2.position.y))

    # We placed 3 pairs of splitters with 2 belts each side = 3 * 2 * 2 = 12 belts
    expected_belt_count = 12
    assert len(placed_belt_positions) == expected_belt_count, (
        f"Expected to place {expected_belt_count} belts, but placed {len(placed_belt_positions)}"
    )

    # Get all entities
    entities = game.get_entities()

    # Count all belts (they may be in BeltGroups)
    found_belt_positions = set()
    for entity in entities:
        if hasattr(entity, "belts"):
            # It's a BeltGroup
            for belt in entity.belts:
                found_belt_positions.add((belt.position.x, belt.position.y))
        elif hasattr(entity, "name") and "belt" in entity.name:
            found_belt_positions.add((entity.position.x, entity.position.y))

    # Check that all placed belts are found
    placed_set = set(placed_belt_positions)
    missing_belts = placed_set - found_belt_positions

    assert len(missing_belts) == 0, (
        f"Missing {len(missing_belts)} belts: {missing_belts}"
    )
    assert len(found_belt_positions) >= expected_belt_count, (
        f"Expected at least {expected_belt_count} belts, found {len(found_belt_positions)}"
    )

    print(f"\nSUCCESS: All {expected_belt_count} belts between splitters were found!")
    print(f"Placed belt positions: {sorted(placed_belt_positions)}")
    print(f"Found belt positions: {sorted(found_belt_positions)}")


def test_belts_between_splitters_render_correctly(clear_terrain):
    """
    Test that belts between splitters render correctly.
    """
    game = clear_terrain

    # Create a chain of splitters with belts between them
    for i in range(4):
        y_pos = i * 3
        game.move_to(Position(x=0, y=y_pos))
        game.place_entity(
            Prototype.Splitter, position=Position(x=0, y=y_pos), direction=Direction.UP
        )

        if i < 3:
            for y_offset in [-1, -2]:
                y = y_pos + y_offset
                game.place_entity(
                    Prototype.TransportBelt,
                    position=Position(x=-0.5, y=y),
                    direction=Direction.UP,
                )
                game.place_entity(
                    Prototype.TransportBelt,
                    position=Position(x=0.5, y=y),
                    direction=Direction.UP,
                )

    # Render and show
    image = game._render(position=Position(x=0, y=4), radius=15)
    # image.show()
    assert image is not None


def test_single_belt_pair_between_two_splitters(clear_terrain):
    """
    Simplified test: just two splitters with belts between them.
    """
    game = clear_terrain

    # Place first splitter
    game.move_to(Position(x=0, y=0))
    s1 = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )
    print(f"Splitter 1 at: {s1.position}, outputs: {s1.output_positions}")

    # Place second splitter
    game.move_to(Position(x=0, y=3))
    s2 = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=3), direction=Direction.UP
    )
    print(f"Splitter 2 at: {s2.position}, inputs: {s2.input_positions}")

    # Place belts between them
    # Splitter 1 outputs at y=-0.5, splitter 2 inputs at y=4.5
    # So we need belts at y=0.5, 1.5, 2.5, 3.5 to connect them
    # Wait - let's check actual positions

    # With splitter 1 at y=0, outputs are at y=-0.5
    # With splitter 2 at y=3, inputs are at y=4.5
    # Belts between: we placed at y=-1 and y=-2 in original test
    # That means actual positions y=-0.5 and y=-1.5

    placed_belts = []
    for y in [-1, -2]:
        b1 = game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        b2 = game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )
        placed_belts.extend([b1, b2])
        print(
            f"Placed belts at y={y}: left=({b1.position.x}, {b1.position.y}), right=({b2.position.x}, {b2.position.y})"
        )

    # Get entities
    entities = game.get_entities()

    # Print all entities for debugging
    print("\n=== ALL ENTITIES ===")
    total_belts = 0
    for e in entities:
        if hasattr(e, "belts"):
            print(f"BeltGroup with {len(e.belts)} belts:")
            for belt in e.belts:
                print(f"  - {belt.name} at ({belt.position.x}, {belt.position.y})")
                total_belts += 1
        else:
            print(f"{e.name} at ({e.position.x}, {e.position.y})")

    print(f"\nTotal belts found: {total_belts}")
    assert total_belts >= 4, f"Expected at least 4 belts, found {total_belts}"

    # Render
    image = game._render(position=Position(x=0, y=1), radius=8)
    # image.show()
    assert image is not None


def test_belt_count_matches_placed(clear_terrain):
    """
    Test that the number of belts returned matches the number placed.
    """
    game = clear_terrain

    # Place splitters
    game.move_to(Position(x=0, y=0))
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    game.move_to(Position(x=0, y=5))
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=5), direction=Direction.UP
    )

    # Place a line of belts
    placed_count = 0
    for y in range(-3, 5):
        if y not in [0, 1]:  # Skip splitter area
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=-0.5, y=y),
                direction=Direction.UP,
            )
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=0.5, y=y),
                direction=Direction.UP,
            )
            placed_count += 2

    print(f"Placed {placed_count} belts")

    # Get entities and count belts
    entities = game.get_entities()
    found_count = 0
    for e in entities:
        if hasattr(e, "belts"):
            found_count += len(e.belts)

    print(f"Found {found_count} belts")

    # All placed belts should be found
    assert found_count == placed_count, (
        f"Placed {placed_count} belts but found {found_count}"
    )
