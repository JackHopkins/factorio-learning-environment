import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'stone-furnace': 1,
                                  'iron-chest': 3,
                                  'burner-inserter': 6,
                                  'coal': 50,
                                  'transport-belt': 50,
                                  'burner-mining-drill': 3}
    instance.reset()
    yield instance
    instance.reset()

def test_build_auto_refilling_coal_system(game):
    num_drills = 3

    # Start at the origin
    game.move_to(Position(x=0, y=0))

    # Find the nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Move to the center of the coal patch
    game.move_to(coal_patch.bounding_box.left_top)

    # Place the first drill
    drill = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Place a chest next to the first drill to collect coal
    chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, drill.drop_position)

    # Connect the first drill to the chest with an inserter
    inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)
    first_inserter = inserter

    # Place an inserter south of the drill to insert coal into the drill
    drill_bottom_y = drill.position.y + drill.dimensions.height
    drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=drill.position.x, y=drill_bottom_y))
    drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)
    first_drill_inserter = drill_inserter

    # Start the transport belt from the chest
    game.move_to(inserter.drop_position)

    drills = []

    # Place additional drills and connect them to the belt
    for i in range(1, num_drills):
        # Place the next drill
        next_drill = game.place_entity_next_to(Prototype.BurnerMiningDrill, drill.position, Direction.RIGHT, spacing=2)
        next_drill = game.rotate_entity(next_drill, Direction.UP)
        drills.append(next_drill)

        try:
            # Place a chest next to the next drill to collect coal
            chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, next_drill.drop_position)
        except Exception as e:
            print(f"Could not place chest next to drill: {e}")

        # Place an inserter to connect the chest to the transport belt
        next_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)

        # Place an insert underneath the drill to insert coal into the drill
        drill_bottom_y = next_drill.position.y + next_drill.dimensions.height
        drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=next_drill.position.x, y=drill_bottom_y))
        drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)

        # Extend the transport belt to the next drill
        game.connect_entities(inserter.drop_position, next_inserter.drop_position, Prototype.TransportBelt)

        # Update the drill reference for the next iteration
        drill = next_drill
        inserter = next_inserter
        next_drill_inserter = drill_inserter

    # Connect the drop position of the final drill block to the inserter that is loading it with coal
    game.connect_entities(next_inserter.drop_position, next_drill_inserter.pickup_position, Prototype.TransportBelt)

    # Connect that inserter to the inserter that is loading the first drill with coal
    game.connect_entities(next_drill_inserter.pickup_position, first_drill_inserter.pickup_position, Prototype.TransportBelt)

    # Connect the first drill inserter to the drop point of the first inserter
    game.connect_entities(first_drill_inserter.pickup_position, first_inserter.drop_position, Prototype.TransportBelt)

    # Initialize the system by adding some coal to each drill and inserter
    for drill in drills:
        game.insert_item(Prototype.Coal, drill, 5)

    print(f"Auto-refilling coal mining system with {num_drills} drills has been built!")

def test_simple_automated_drill(game):
    # Find nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    assert coal_patch, "No coal patch found nearby"

    # Place coal burner mining drill
    drill_position = coal_patch.bounding_box.center
    game.move_to(drill_position)
    drill = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, drill_position)
    assert drill, f"Failed to place burner mining drill at {drill_position}"
    print(f"Placed burner mining drill at {drill.position}")

    # Place inserter next to the drill
    inserter_position = Position(x=drill.position.x, y=drill.position.y+1)
    inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, inserter_position)
    assert inserter, f"Failed to place inserter at {inserter_position}"
    print(f"Placed inserter at {inserter.position}")

    # Verify inserter is facing the drill
    assert inserter.direction.name == Direction.UP.name, f"Inserter is not facing the drill. Current direction: {inserter.direction}"

    # Place transport belt connecting drill to inserter
    belt_start = drill.drop_position
    belt_end = inserter.pickup_position
    belts = game.connect_entities(belt_start, belt_end, Prototype.TransportBelt)
    assert belts, f"Failed to place transport belt from {belt_start} to {belt_end}"
    print(f"Placed {len(belts)} transport belt(s) from drill to inserter")

    # Verify the setup
    entities = game.inspect_entities(drill.position, radius=5)
    assert entities.get_entity(Prototype.BurnerMiningDrill), "Burner mining drill not found in setup"
    assert entities.get_entity(Prototype.BurnerInserter), "Inserter not found in setup"
    assert any(e.name == "transport-belt" for e in entities.entities), "Transport belts not found in setup"

    print("Successfully set up coal mining loop with burner mining drill, inserter, and transport belts")
