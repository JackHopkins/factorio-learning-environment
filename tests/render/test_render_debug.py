"""
Debug tests to diagnose rendering issues.
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


def test_simple_splitter_and_belts(clear_terrain):
    """Simplest test - one splitter with belts."""
    game = clear_terrain

    # Place a single splitter at y=0
    game.move_to(Position(x=0, y=0))
    splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )
    print(f"Splitter placed at: {splitter.position}")

    # Place belts AFTER the splitter (output side - north of splitter)
    belt1 = game.place_entity(
        Prototype.TransportBelt, position=Position(x=-0.5, y=-1), direction=Direction.UP
    )
    belt2 = game.place_entity(
        Prototype.TransportBelt, position=Position(x=0.5, y=-1), direction=Direction.UP
    )
    print(f"Belt 1 at: {belt1.position}")
    print(f"Belt 2 at: {belt2.position}")

    # Place more belts going north
    for y in range(-4, -1):
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
        print(f"Belt at y={y}: left={b1.position}, right={b2.position}")

    # Render
    image = game._render(position=Position(x=0, y=-2), radius=8)
    # image.show()
    assert image is not None


def test_splitter_with_input_and_output_belts(clear_terrain):
    """Test splitter with both input and output belts."""
    game = clear_terrain

    # Place splitter
    game.move_to(Position(x=0, y=0))
    splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )
    print(f"Splitter at: {splitter.position}")

    # Input belts (south of splitter, coming IN)
    for y in range(1, 4):
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
        print(f"Input belt at y={y}: left={b1.position}, right={b2.position}")

    # Output belts (north of splitter, going OUT)
    for y in range(-3, 0):
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
        print(f"Output belt at y={y}: left={b1.position}, right={b2.position}")

    # Render
    image = game._render(position=Position(x=0, y=0), radius=8)
    # image.show()
    assert image is not None


def test_print_entity_positions(clear_terrain):
    """Debug test to print all entity positions."""
    game = clear_terrain

    # Place splitter
    game.move_to(Position(x=0, y=0))
    splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )
    print(f"\nSplitter placed: {splitter}")
    print(f"Splitter position: {splitter.position}")

    # Place some belts - avoid overlapping by using correct y positions
    belts = []
    for y in [-2, -1, 2, 3]:  # Skip the splitter area (y=0, y=1)
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
        belts.extend([b1, b2])
        print(
            f"Belt at y={y}: left=({b1.position.x}, {b1.position.y}), right=({b2.position.x}, {b2.position.y})"
        )

    # Get all entities and print
    entities = game.get_entities()
    print("\n=== ALL ENTITIES (raw) ===")
    for e in entities:
        print(f"  Type: {type(e).__name__}")
        if hasattr(e, "belts"):
            for belt in e.belts:
                print(
                    f"    Belt: {belt.name} at ({belt.position.x}, {belt.position.y}) dir={belt.direction}"
                )
        elif hasattr(e, "position"):
            print(f"    {e.name} at ({e.position.x}, {e.position.y})")

    # Now let's check what's in the entity_grid after rendering
    from fle.env.tools.admin.render.utils import entities_to_grid

    # Get entities for rendering (flatten them)
    all_entities = list(game.get_entities())
    print("\n=== ENTITY GRID DEBUG ===")

    # Create the grid
    from fle.env.tools.admin.render.utils import flatten_entities

    flattened = list(flatten_entities(all_entities))
    print(f"Flattened entities: {len(flattened)}")
    for e in flattened:
        print(f"  {e.name} at ({e.position.x}, {e.position.y})")

    grid = entities_to_grid(flattened)
    print(f"\nGrid keys (x): {sorted(grid.keys())}")
    for x in sorted(grid.keys()):
        print(f"  x={x}: y values = {sorted(grid[x].keys())}")

    # Check what's actually at (0, 0.5) in the grid
    print("\n=== CHECKING GRID LOOKUP ===")
    if 0.0 in grid and 0.5 in grid[0.0]:
        entity = grid[0.0][0.5]
        print(f"Entity at (0, 0.5): {entity}")
        entity_dict = entity.model_dump() if hasattr(entity, "model_dump") else entity
        print(f"Entity dict: {entity_dict}")
        print(
            f"Entity direction: {entity_dict.get('direction')} (type: {type(entity_dict.get('direction'))})"
        )

    # Test the is_splitter function directly
    from fle.env.tools.admin.render.entity_grid import EntityGridView

    grid_view = EntityGridView(grid, -0.5, -0.5, {})

    # Get entity at relative (0.5, 1) which should be (0, 0.5)
    entity_at_south = grid_view.get_relative(0.5, 1)
    print(f"\nEntity at relative (0.5, 1) from (-0.5, -0.5): {entity_at_south}")
    if entity_at_south:
        print(
            f"  direction: {entity_at_south.get('direction')} (type: {type(entity_at_south.get('direction'))})"
        )

    # Test is_splitter
    from fle.env.tools.admin.render.renderers.transport_belt import is_splitter
    from fle.env.tools.admin.render.constants import NORTH

    result = is_splitter(entity_at_south, NORTH)
    print(f"  is_splitter(entity, NORTH={NORTH}): {result}")

    # Render
    image = game._render(position=Position(x=0, y=0), radius=6)
    # image.show()
    assert image is not None
