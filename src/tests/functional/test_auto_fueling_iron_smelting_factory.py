import pytest
from time import sleep

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'burner-mining-drill': 2,
        'stone-furnace': 1,
        'burner-inserter': 5,
        'transport-belt': 100,
        'iron-chest': 1,
        'coal': 50,
    }
    instance.reset()
    yield instance


def test_auto_fueling_iron_smelting_factory(game):
    """
    Builds an auto-fueling iron smelting factory:
    - Mines coal and iron ore.
    - Uses transport belts to deliver coal to fuel the iron miner and furnace.
    - Smelts iron ore into iron plates.
    - Stores iron plates in an iron chest.
    """
    # Move to the nearest coal resource and place a burner mining drill
    coal_position = game.nearest(Resource.Coal)
    game.move_to(coal_position)
    coal_drill = game.place_entity(Prototype.BurnerMiningDrill, position=coal_position, direction=Direction.DOWN)

    # Place a transport belt at the coal drill's drop position
    # coal_belt_start = game.place_entity(Prototype.TransportBelt, position=coal_drill.drop_position, direction=Direction.DOWN)

    # Find the nearest iron ore resource
    iron_position = game.nearest(Resource.IronOre)
    # Define an intermediate position to route the belt along X-axis to the iron ore
    intermediate_pos = Position(x=coal_drill.drop_position.x, y=iron_position.y)

    # Lay belts from coal belt start to the intermediate position (along Y-axis)
    try:
        coal_belt_part1 = game.connect_entities(coal_drill, intermediate_pos, connection_type=Prototype.TransportBelt)
    except Exception as e:
        print(e)

    # Lay belts from intermediate position to iron position (along X-axis)
    try:
        left_of_iron = Position(x=iron_position.x + 1, y=iron_position.y)
        coal_belt_part2 = game.connect_entities(coal_belt_part1[-1], left_of_iron, connection_type=Prototype.TransportBelt)
    except Exception as e:
        print(e)
    coal_belt = coal_belt_part1 + coal_belt_part2

    # Place the iron mining drill at iron_position, facing down
    move_to_iron = game.move_to(iron_position)
    iron_drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)

    # Place an inserter to fuel the iron drill from the coal belt
    inserter_position = Position(x=iron_drill.position.x + iron_drill.tile_dimensions.tile_width/2, y=iron_drill.position.y-1)
    try:
        iron_drill_fuel_inserter = game.place_entity(Prototype.BurnerInserter, position=inserter_position, direction=Direction.LEFT, exact=True)
    except Exception as e:
        print(e)
    # Extend coal belt to pass next to the furnace position
    furnace_position = Position(x=iron_drill.drop_position.x, y=iron_drill.drop_position.y + 1)

    # Place the furnace at the iron drill's drop position
    iron_furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_position)

    # Place an inserter to fuel the furnace from the coal belt
    furnace_fuel_inserter_position = Position(x=iron_furnace.position.x + 1, y=iron_furnace.position.y)
    furnace_fuel_inserter = game.place_entity(Prototype.BurnerInserter, position=furnace_fuel_inserter_position, direction=Direction.LEFT)

    coal_belt_to_furnace = game.connect_entities(iron_drill_fuel_inserter.pickup_position, furnace_fuel_inserter.pickup_position, connection_type=Prototype.TransportBelt)
    coal_belt.extend(coal_belt_to_furnace)

    # Place an inserter to transfer iron ore from the iron drill to the furnace
    ore_inserter_position = Position(x=iron_drill.drop_position.x, y=iron_drill.drop_position.y + 0.5)
    ore_inserter = game.place_entity(Prototype.BurnerInserter, position=ore_inserter_position, direction=Direction.UP)

    # Place an iron chest to store iron plates
    chest_position = Position(x=iron_furnace.position.x, y=iron_furnace.position.y + 1)
    iron_chest = game.place_entity(Prototype.IronChest, position=chest_position)

    # Place an inserter to transfer iron plates from the furnace to the chest
    #plate_inserter_position = Position(x=iron_furnace.position.x, y=iron_furnace.position.y + 0.5)
    #plate_inserter = game.place_entity(Prototype.BurnerInserter, position=plate_inserter_position, direction=Direction.DOWN)

    # Start the system by fueling the coal drill
    game.insert_item(Prototype.Coal, coal_drill, quantity=10)

    # Wait for some time to let the system produce iron plates
    sleep(60)  # Wait for 60 seconds

    # Check the iron chest to see if iron plates have been produced
    chest_inventory = game.inspect_inventory(iron_chest)
    iron_plates_in_chest = chest_inventory.get(Prototype.IronPlate, 0)

    # Assert that some iron plates have been produced
    assert iron_plates_in_chest > 0, "No iron plates were produced"

    print(f"Successfully produced {iron_plates_in_chest} iron plates.")