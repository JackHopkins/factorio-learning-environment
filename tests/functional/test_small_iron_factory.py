import pytest
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 5,
        "iron-chest": 2,
        "burner-inserter": 20,
        "coal": 100,
        "transport-belt": 200,
        "burner-mining-drill": 10,
    }
    instance.reset(all_technologies_researched=True)
    # instance.execute_transaction()
    yield instance.namespace


def test_basic_iron_smelting_chain(game):
    # Place iron ore patch
    iron_ore_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )
    assert iron_ore_patch, "No iron ore patch found"
    print(f"Iron ore patch found at {iron_ore_patch.bounding_box.center}")

    # Place burner mining drill on iron ore patch
    game.move_to(iron_ore_patch.bounding_box.center)
    drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        direction=Direction.RIGHT,
        position=iron_ore_patch.bounding_box.center,
    )
    assert drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {drill.position}")

    # Fuel the burner mining drill
    drill_with_coal = game.insert_item(Prototype.Coal, drill, quantity=5)
    assert drill_with_coal.fuel.get(Prototype.Coal, 0) > 0, (
        "Failed to fuel burner mining drill"
    )
    print(
        f"Inserted {drill_with_coal.fuel.get(Prototype.Coal, 0)} coal into burner mining drill"
    )

    # Place stone furnace next to drill
    furnace = game.place_entity_next_to(
        Prototype.StoneFurnace,
        reference_position=drill.position,
        direction=Direction.RIGHT,
    )
    assert furnace, "Failed to place stone furnace"
    print(f"Stone furnace placed at {furnace.position}")

    # Fuel the stone furnace
    furnace_with_coal = game.insert_item(Prototype.Coal, furnace, quantity=5)
    assert furnace_with_coal.fuel.get(Prototype.Coal, 0) > 0, (
        "Failed to fuel stone furnace"
    )
    print(
        f"Inserted {furnace_with_coal.fuel.get(Prototype.Coal, 0)} coal into stone furnace"
    )

    # Place inserter next to furnace
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.RIGHT,
    )
    assert inserter, "Failed to place inserter"
    print(f"Inserter placed at {inserter.position}")

    # Fuel the inserter
    inserter_with_coal = game.insert_item(Prototype.Coal, inserter, quantity=2)
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"
    print(
        f"Inserted {inserter_with_coal.fuel.get(Prototype.Coal, 0)} coal into inserter"
    )

    # Place chest next to inserter
    chest = game.place_entity_next_to(
        Prototype.WoodenChest,
        reference_position=inserter.position,
        direction=Direction.RIGHT,
    )
    assert chest, "Failed to place chest"
    print(f"Chest placed at {chest.position}")

    # Verify setup
    game.sleep(60)  # Wait for the system to produce some iron plates

    chest_inventory = game.inspect_inventory(chest)
    iron_plates = chest_inventory.get(Prototype.IronPlate, 0)
    assert iron_plates > 0, (
        "No iron plates produced after 60 seconds. Check fuel levels and connections."
    )
    print(f"Success! {iron_plates} iron plates produced and stored in the chest.")


def test_steel_smelting_chain(game):
    """
    Test steel smelting chain:
    - Burner drill mines iron ore
    - Furnace1 smelts iron ore into iron plates
    - Inserter moves iron plates from furnace1 to furnace2
    - Furnace2 smelts iron plates into steel

    Layout:
    [Drill] -> [Furnace1] -> [Inserter1] -> [Chest] -> [Inserter2] -> [Furnace2]

    We use a chest as intermediate storage since direct inserter-to-furnace
    has positioning constraints in Factorio.
    """
    # Find the nearest iron ore patch
    iron_ore_position = game.nearest(Resource.IronOre)
    game.move_to(iron_ore_position)
    assert iron_ore_position, "No iron ore patch found"

    # Place burner mining drill on iron ore patch, facing right so it outputs to the right
    burner_drill = game.place_entity(
        Prototype.BurnerMiningDrill, Direction.RIGHT, iron_ore_position
    )
    assert burner_drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {burner_drill.position}")

    # Place first stone furnace to receive iron ore from drill
    furnace1 = game.place_entity_next_to(
        Prototype.StoneFurnace, burner_drill.position, Direction.RIGHT, spacing=0
    )
    assert furnace1, "Failed to place first stone furnace"
    print(f"First stone furnace placed at {furnace1.position}")

    # Place inserter to take iron plates FROM furnace1
    inserter1 = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace1.position, Direction.RIGHT, spacing=0
    )
    assert inserter1, "Failed to place inserter1"
    print(f"Inserter1 placed at {inserter1.position}")
    print(f"  pickup: {inserter1.pickup_position}, drop: {inserter1.drop_position}")

    # Place chest next to inserter1 (this acts as intermediate storage)
    chest = game.place_entity_next_to(
        Prototype.IronChest, inserter1.position, Direction.RIGHT, spacing=0
    )
    assert chest, "Failed to place chest"
    print(f"Chest placed at {chest.position}")

    # Place inserter2 next to chest to feed into furnace2
    inserter2 = game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=0
    )
    assert inserter2, "Failed to place inserter2"
    print(f"Inserter2 placed at {inserter2.position}")
    print(f"  pickup: {inserter2.pickup_position}, drop: {inserter2.drop_position}")

    # Place second furnace next to inserter2
    furnace2 = game.place_entity_next_to(
        Prototype.StoneFurnace, inserter2.position, Direction.RIGHT, spacing=0
    )
    assert furnace2, "Failed to place second stone furnace"
    print(f"Second stone furnace placed at {furnace2.position}")

    # Add fuel to entities
    game.insert_item(Prototype.Coal, burner_drill, 10)
    game.insert_item(Prototype.Coal, furnace1, 10)
    game.insert_item(Prototype.Coal, furnace2, 10)
    game.insert_item(Prototype.Coal, inserter1, 5)
    game.insert_item(Prototype.Coal, inserter2, 5)

    # Check states at intervals
    print("\n--- Checking states ---")
    game.sleep(30)
    f1 = game.get_entity(Prototype.StoneFurnace, furnace1.position)
    f2 = game.get_entity(Prototype.StoneFurnace, furnace2.position)
    ins1 = game.get_entity(Prototype.BurnerInserter, inserter1.position)
    ins2 = game.get_entity(Prototype.BurnerInserter, inserter2.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)
    print("After 30s:")
    print(f"  Furnace1: status={f1.status}, result={f1.furnace_result}")
    print(f"  Chest inventory: {game.inspect_inventory(ch)}")
    print(
        f"  Furnace2: status={f2.status}, source={f2.furnace_source}, result={f2.furnace_result}"
    )
    print(f"  Inserter1: status={ins1.status}")
    print(f"  Inserter2: status={ins2.status}")

    game.sleep(30)
    f1 = game.get_entity(Prototype.StoneFurnace, furnace1.position)
    f2 = game.get_entity(Prototype.StoneFurnace, furnace2.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)
    print("After 60s:")
    print(f"  Furnace1: status={f1.status}, result={f1.furnace_result}")
    print(f"  Chest inventory: {game.inspect_inventory(ch)}")
    print(
        f"  Furnace2: status={f2.status}, source={f2.furnace_source}, result={f2.furnace_result}"
    )

    furnace_inventory = game.inspect_inventory(furnace2)
    steel = furnace_inventory.get(Prototype.SteelPlate, 0)
    assert steel > 0, (
        "No steel produced after 60 seconds. Check fuel levels and connections."
    )

    print("Steel smelting chain setup complete and verified")


def test_build_iron_plate_factory(game):
    WIDTH_SPACING = 1  # Spacing between entities in our factory the x-axis

    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(
        Prototype.BurnerMiningDrill,
        Direction.DOWN,
        iron_ore_patch.bounding_box.left_top,
    )

    # Place an iron chest above the drill and insert coal
    chest = game.place_entity_next_to(
        Prototype.IronChest,
        miner.position,
        Direction.UP,
        spacing=miner.dimensions.height,
    )
    game.insert_item(Prototype.Coal, chest, 50)

    # Place an inserter to insert coal into the drill to get started
    game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.DOWN, spacing=0
    )

    # Place an inserter to insert coal into the chest
    coal_chest_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.UP, spacing=0
    )
    coal_chest_inserter = game.rotate_entity(coal_chest_inserter, Direction.DOWN)

    # Place an inserter to insert coal into the coal belt to power the drills
    coal_belt_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=0
    )
    coal_belt_inserter = game.rotate_entity(coal_belt_inserter, Direction.RIGHT)

    iron_drill_coal_belt_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.LEFT, spacing=0
    )

    # Place a transport belt from the miner's output
    iron_belt_start = miner.position.down()  # , Direction.DOWN, spacing=0)

    furnaces = []
    # Place 5 stone furnaces along the belt
    furnace_line_start = game.place_entity_next_to(
        Prototype.StoneFurnace, miner.position, Direction.DOWN, spacing=2
    )
    furnaces.append(furnace_line_start)
    current_furnace = furnace_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(
            Prototype.StoneFurnace,
            current_furnace.position,
            Direction.RIGHT,
            spacing=WIDTH_SPACING,
        )
        furnaces.append(current_furnace)

    # Connect furnaces with transport belt
    above_current_furnace = Position(
        x=current_furnace.position.x, y=current_furnace.position.y - 2.5
    )
    iron_belt = game.connect_entities(
        iron_belt_start, above_current_furnace, Prototype.TransportBelt
    )

    game.connect_entities(
        iron_drill_coal_belt_inserter.drop_position, iron_belt, Prototype.TransportBelt
    )

    # next_coal_belt_position = coal_belt_start.position #coal_belt_start
    # Place a transport belt form the coal belt inserter to the end of the
    # coal_belt_start = game.place_entity_next_to(Prototype.TransportBelt, coal_belt_inserter.position, Direction.RIGHT,
    #                                             spacing=0)
    iron_belt = game.connect_entities(
        coal_belt_inserter.position,
        coal_belt_inserter.position.right(10),
        Prototype.TransportBelt,
    )

    # Place 4 more drills
    miners = [miner]
    for i in range(3):
        miner = game.place_entity_next_to(
            Prototype.BurnerMiningDrill,
            miner.position,
            Direction.RIGHT,
            spacing=WIDTH_SPACING,
        )
        miner = game.rotate_entity(miner, Direction.DOWN)
        miners.append(miner)

        # Connect furnaces with coal belt
        above_current_drill = Position(
            x=miner.position.x, y=miner.position.y - miner.dimensions.height - 1
        )
        # game.connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)
        game.move_to(Position(x=miner.drop_position.x, y=above_current_drill.y + 1))
        miner_coal_inserter = game.place_entity(
            Prototype.BurnerInserter,
            Direction.UP,
            Position(x=miner.drop_position.x, y=above_current_drill.y + 1),
        )
        miner_coal_inserter = game.rotate_entity(miner_coal_inserter, Direction.DOWN)

    # game.connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)

    # Place inserters for each furnace
    for i in range(4):
        furnace_pos = (
            furnaces[i].position
        )  # Position(x=miners[i].drop_position.x, y=furnace_line_start.position.y + 1)
        game.move_to(furnace_pos)
        game.place_entity_next_to(Prototype.BurnerInserter, furnace_pos, Direction.DOWN)
        ins = game.place_entity_next_to(
            Prototype.BurnerInserter, furnace_pos, Direction.UP
        )
        game.rotate_entity(ins, Direction.DOWN)

    # Place output belt for iron plates
    output_belt = game.connect_entities(
        Position(
            x=furnace_line_start.position.x, y=furnace_line_start.position.y + 2.5
        ),
        Position(x=current_furnace.position.x, y=furnace_line_start.position.y + 2.5),
        Prototype.TransportBelt,
    )

    # Place a chest at the end of the output belt
    output_chest = game.place_entity_next_to(
        Prototype.IronChest, output_belt.outputs[0].position, Direction.RIGHT, spacing=1
    )

    # Place an inserter to move plates from belt to chest
    game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, output_chest.position.left()
    )

    # Find nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Move to the top left of the coal patch
    game.move_to(coal_patch.bounding_box.left_top)

    # Place a burner mining drill on the coal patch
    coal_miner = game.place_entity(
        Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top
    )

    # Connect coal to furnaces with transport belt
    game.connect_entities(
        coal_miner.drop_position, coal_chest_inserter, Prototype.TransportBelt
    )

    # Insert coal into the coal miner
    game.insert_item(Prototype.Coal, coal_miner, 50)

    # Connect the coal belt back to the miner to keep it fueled
    reinserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        Position(x=coal_miner.position.x - 1, y=coal_miner.position.y - 1),
        Direction.LEFT,
        spacing=0,
    )
    reinserter = game.rotate_entity(reinserter, Direction.RIGHT)
    print("Simple iron plate factory has been built!")
