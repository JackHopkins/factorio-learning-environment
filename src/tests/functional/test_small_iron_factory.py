import pytest
from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 5,
        'iron-chest': 2,
        'burner-inserter': 12,
        'coal': 100,
        'transport-belt': 100,
        'burner-mining-drill': 2
    }
    instance.reset()
    yield instance


def test_build_iron_plate_factory(game):
    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.left_top)

    # Place an iron check above the drill and insert coal
    chest = game.place_entity_next_to(Prototype.IronChest, miner.position, Direction.UP, spacing=miner.dimensions.height)
    game.insert_item(Prototype.Coal, chest, 50)

    # Place an inserter to insert coal into the drill
    coal_drill_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.DOWN, spacing=0)

    # Place an inserter to insert coal into the coal belt
    coal_belt_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=1)
    game.rotate_entity(coal_belt_inserter, Direction.RIGHT)

    # Place a transport belt form the coal belt inserter to the end of the
    coal_belt_start = game.place_entity_next_to(Prototype.TransportBelt, coal_belt_inserter.drop_position, Direction.RIGHT, spacing=0)

    # Place a transport belt from the miner's output
    iron_belt_start = game.place_entity_next_to(Prototype.TransportBelt, miner.drop_position, Direction.DOWN, spacing=0)

    # Place 5 stone furnaces along the belt
    furnace_line_start = game.place_entity_next_to(Prototype.StoneFurnace, miner.drop_position, Direction.DOWN,
                                                   spacing=3)
    current_furnace = furnace_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT,
                                                    spacing=2)

    # Connect furnaces with transport belt
    above_current_furnace = Position(x=current_furnace.position.x, y=current_furnace.position.y - current_furnace.dimensions.height - 1)
    game.connect_entities(iron_belt_start.position, above_current_furnace, Prototype.TransportBelt)

    next_coal_belt_position = coal_belt_start.position

    # Place 4 more drills
    miners = [miner]
    for i in range(3):
        miner = game.place_entity_next_to(Prototype.BurnerMiningDrill, miner.position, Direction.RIGHT,
                                                     spacing=2)
        miner = game.rotate_entity(miner, Direction.DOWN)
        miners.append(miner)

        # Connect furnaces with coal belt
        above_current_drill = Position(x=miner.position.x, y=miner.position.y - miner.dimensions.height - 1)
        game.connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)

        next_coal_belt_position = above_current_drill

    # Place inserters for each furnace
    for i in range(4):
        furnace_pos = Position(x=miners[i].drop_position.x, y=furnace_line_start.position.y + 2)
        game.move_to(furnace_pos)
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - (current_furnace.dimensions.height + 2)))
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - 1))

    # Place output belt for iron plates
    output_belt_start = game.place_entity_next_to(furnace_line_start.position, Direction.UP, spacing=2)
    game.connect_entities(output_belt_start.position,
                          Position(x=current_furnace.position.x, y=output_belt_start.position.y),
                          Prototype.TransportBelt)

    # Place a chest at the end of the output belt
    output_chest = game.place_entity_next_to(Prototype.IronChest,
                                             Position(x=current_furnace.position.x, y=output_belt_start.position.y),
                                             Direction.UP, spacing=1)

    # Place an inserter to move plates from belt to chest
    game.place_entity(Prototype.BurnerInserter, Direction.DOWN,
                      Position(x=output_chest.position.x, y=output_chest.position.y - 1))

    # Find nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Place a burner mining drill on the coal patch
    coal_miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Connect coal to furnaces with transport belt
    game.connect_entities(coal_miner.drop_position, furnace_line_start.position, Prototype.TransportBelt)

    # Add some initial coal to get the system started
    game.insert_item(Prototype.Coal, miner, 5)
    game.insert_item(Prototype.Coal, coal_miner, 5)
    for i in range(5):
        furnace_pos = Position(x=furnace_line_start.position.x + i * 2, y=furnace_line_start.position.y)
        inserter_up = game.get_entity(Prototype.BurnerInserter, Position(x=furnace_pos.x, y=furnace_pos.y + 1))
        inserter_down = game.get_entity(Prototype.BurnerInserter, Position(x=furnace_pos.x, y=furnace_pos.y - 1))
        game.insert_item(Prototype.Coal, inserter_up, 1)
        game.insert_item(Prototype.Coal, inserter_down, 1)

    print("Simple iron plate factory has been built!")