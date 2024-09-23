import pytest
from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 5,
        'iron-chest': 2,
        'burner-inserter': 20,
        'coal': 100,
        'transport-belt': 200,
        'burner-mining-drill': 10
    }
    instance.reset()
    yield instance


def test_build_iron_plate_factory(game):

    WIDTH_SPACING = 1 # Spacing between entities in our factory the x-axis

    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.left_top)

    # Place an iron chest above the drill and insert coal
    chest = game.place_entity_next_to(Prototype.IronChest, miner.position, Direction.UP, spacing=miner.dimensions.height)
    game.insert_item(Prototype.Coal, chest, 50)

    # Place an inserter to insert coal into the drill to get started
    coal_drill_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.DOWN, spacing=0)

    # Place an inserter to insert coal into the chest
    coal_chest_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.UP, spacing=0)
    coal_chest_inserter = game.rotate_entity(coal_chest_inserter, Direction.DOWN)

    # Place an inserter to insert coal into the coal belt to power the drills
    coal_belt_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=0)
    coal_belt_inserter = game.rotate_entity(coal_belt_inserter, Direction.RIGHT)

    iron_drill_coal_belt_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT, spacing=0)

    # Place a transport belt form the coal belt inserter to the end of the
    coal_belt_start = game.place_entity_next_to(Prototype.TransportBelt, coal_belt_inserter.position, Direction.RIGHT, spacing=0)

    # Place a transport belt from the miner's output
    iron_belt_start = game.place_entity_next_to(Prototype.TransportBelt, miner.position, Direction.DOWN, spacing=0)

    # Place 5 stone furnaces along the belt
    furnace_line_start = game.place_entity_next_to(Prototype.StoneFurnace, miner.position, Direction.DOWN,
                                                   spacing=2)
    current_furnace = furnace_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT,
                                                    spacing=WIDTH_SPACING)

    # Connect furnaces with transport belt
    above_current_furnace = Position(x=current_furnace.position.x, y=current_furnace.position.y - 2.5)
    iron_belt = game.connect_entities(iron_belt_start.position, above_current_furnace, Prototype.TransportBelt)

    coal_to_iron_belt = game.connect_entities(iron_drill_coal_belt_inserter.drop_position, iron_belt[0].input_position, Prototype.TransportBelt)

    next_coal_belt_position = coal_belt_start.position

    # Place 4 more drills
    miners = [miner]
    for i in range(3):
        miner = game.place_entity_next_to(Prototype.BurnerMiningDrill, miner.position, Direction.RIGHT,
                                                     spacing=WIDTH_SPACING)
        miner = game.rotate_entity(miner, Direction.DOWN)
        miners.append(miner)

        # Connect furnaces with coal belt
        above_current_drill = Position(x=miner.position.x, y=miner.position.y - miner.dimensions.height - 1)
        game.connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)

        miner_coal_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=miner.drop_position.x, y=above_current_drill.y + 1))
        miner_coal_inserter = game.rotate_entity(miner_coal_inserter, Direction.DOWN)
        next_coal_belt_position = above_current_drill

    # Place inserters for each furnace
    for i in range(4):
        furnace_pos = Position(x=miners[i].drop_position.x, y=furnace_line_start.position.y + 1)
        game.move_to(furnace_pos)
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - (current_furnace.dimensions.height + 2)))
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - 1))

    # Place output belt for iron plates
    output_belt = game.connect_entities(Position(x=furnace_line_start.position.x, y=furnace_line_start.position.y + 2.5),
                          Position(x=current_furnace.position.x, y=furnace_line_start.position.y + 2.5), Prototype.TransportBelt)

    # Place a chest at the end of the output belt
    output_chest = game.place_entity_next_to(Prototype.IronChest,
                                             Position(x=output_belt[-1].output_position.x, y=output_belt[-1].position.y),
                                             Direction.RIGHT, spacing=1)

    # Place an inserter to move plates from belt to chest
    game.place_entity(Prototype.BurnerInserter, Direction.RIGHT,
                      Position(x=output_chest.position.x-1, y=output_chest.position.y))

    # Find nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Move to the top left of the coal patch
    game.move_to(coal_patch.bounding_box.left_top)

    # Place a burner mining drill on the coal patch
    coal_miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Connect coal to furnaces with transport belt
    game.connect_entities(coal_miner.drop_position, coal_chest_inserter.pickup_position, Prototype.TransportBelt)

    # Insert coal into the coal miner
    game.insert_item(Prototype.Coal, coal_miner, 50)

    # Connect the coal belt back to the miner to keep it fueled
    reinserter = game.place_entity_next_to(Prototype.BurnerInserter, Position(x=coal_miner.position.x-1, y=coal_miner.position.y-1), Direction.LEFT, spacing=0)
    reinserter = game.rotate_entity(reinserter, Direction.RIGHT)
    print("Simple iron plate factory has been built!")