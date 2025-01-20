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
                                  'burner-mining-drill': 5}
    instance.reset()
    instance.speed(10)
    yield instance.namespace
    #instance.reset()
    #instance.speed(1)

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
    belts = []

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
        belts.extend(game.connect_entities(inserter.drop_position, next_inserter.drop_position, Prototype.TransportBelt))

        # Update the drill reference for the next iteration
        drill = next_drill
        inserter = next_inserter
        next_drill_inserter = drill_inserter

    # Connect the drop position of the final drill block to the inserter that is loading it with coal
    belts.extend(game.connect_entities(next_inserter.drop_position, next_drill_inserter.pickup_position, Prototype.TransportBelt))

    # Connect that inserter to the inserter that is loading the first drill with coal
    belts.extend(game.connect_entities(next_drill_inserter.pickup_position, first_drill_inserter.pickup_position, Prototype.TransportBelt))

    # Connect the first drill inserter to the drop point of the first inserter
    belts.extend(game.connect_entities(belts[-1].belts[-1].output_position, belts[0].belts[0].input_position, Prototype.TransportBelt))

    game.rotate_entity(belts[-1].belts[-1], Direction.RIGHT)
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


def test_another_self_fueling_coal_belt(game):
    # Find the nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    assert coal_patch is not None, "No coal patch found nearby"
    assert coal_patch.size >= 25, f"Coal patch too small: {coal_patch.size} tiles (need at least 25)"

    # Place 5 burner mining drills in a line
    drills = []
    inserters = []
    game.move_to(coal_patch.bounding_box.center)
    for i in range(5):
        drill_position = Position(x=coal_patch.bounding_box.left_top.x + i * 2, y=coal_patch.bounding_box.center.y)

        drill = game.place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, drill_position)
        inserter = game.place_entity_next_to(Prototype.BurnerInserter, drill_position, direction=Direction.UP, spacing=0)
        inserter = game.rotate_entity(inserter, Direction.DOWN)
        assert drill is not None, f"Failed to place burner mining drill at {drill_position}"
        assert inserter is not None, f"Failed to place inserter at {drill_position}"
        drills.append(drill)
        inserters.append(inserter)


    print(f"Placed {len(drills)} burner mining drills")

    # Place transport belt parallel to the drills
    belt_start = Position(x=drills[0].drop_position.x, y=drills[0].drop_position.y)
    belt_end = Position(x=drills[-1].drop_position.x, y=drills[0].drop_position.y)
    belt_entities = game.connect_entities(belt_start, belt_end, Prototype.TransportBelt)
    assert len(belt_entities) > 0, "Failed to place transport belt"

    belt_to_last_inserter = game.connect_entities(belt_end, inserters[-1].pickup_position, Prototype.TransportBelt)
    assert len(belt_to_last_inserter) > 0, "Failed to connect belt to last inserter"

    belt_to_first_inserter = game.connect_entities(inserters[-1].pickup_position, inserters[0].pickup_position, Prototype.TransportBelt)
    assert len(belt_to_first_inserter) > 0, "Failed to connect belt to first inserter"

    belt_to_close_loop = game.connect_entities(inserters[0].pickup_position, belt_start, Prototype.TransportBelt)
    assert len(belt_to_close_loop) > 0, "Failed to connect belt to close the loop"

    print(f"Placed {len(belt_entities)} transport belt segments")

    print("Completed the belt loop")

    # Verify the setup
    inspection = game.inspect_entities(coal_patch.bounding_box.center, radius=15)
    assert len([e for e in inspection.entities if
                e.name == Prototype.BurnerMiningDrill.value[0]]) == 5, "Not all burner mining drills were placed"
    assert len([e for e in inspection.entities if
                e.name == Prototype.BurnerInserter.value[0]]) == 5, "Not all inserters were placed"
    # sum all inspected entities with the name transport-belt
    total_belts = sum([e.quantity if e.quantity else 1 for e in inspection.entities if e.name == Prototype.TransportBelt.value[0]])

    assert total_belts >= 15, "Not enough transport belt segments were placed"

    print("All components verified")

    # Kickstart the system by placing coal on the belt
    game.move_to(drills[0].position)
    coal_placed = game.insert_item(Prototype.Coal, drills[0], quantity=10)
    assert coal_placed is not None, "Failed to place coal on the belt"

    print("System kickstarted with coal")
    print("Self-fueling belt of 5 burner mining drills successfully set up")
