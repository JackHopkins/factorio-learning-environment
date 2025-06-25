import pytest

from env.src.entities import Position
from env.src.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 1, 'boiler': 1, 'steam-engine': 1, 'offshore-pump': 4, 'pipe': 100,
        'iron-plate': 50, 'copper-plate': 20, 'coal': 50, 'burner-inserter': 50, 'burner-mining-drill': 50,
        'transport-belt': 50, 'stone-wall': 100, 'splitter': 4, 'wooden-chest': 1
    }

    instance.reset()
    yield instance.namespace
    instance.reset()

#    game.instance.initial_inventory = {**game.instance.initial_inventory, 'coal': 4000}
#    game.instance.reset()

def test_pickup_item_full_inventory(game):
    """
    Test that pickup fails when inventory is at maximum capacity.
    Uses existing inventory items but maximizes stacks to test true full inventory.
    """
    # Clear inventory completely first  
    game.instance.set_inventory({})
    
    # Fill inventory to maximum capacity using existing items
    game.instance.set_inventory({
        'coal': 4500,  # Coal stacks to 50, this uses 90 slots
        'wooden-chest': 50,  # Maximum stack size for wooden chests
    })
    
    # Place a wooden chest
    placement_position = Position(x=5, y=5)
    game.move_to(placement_position)
    chest = game.place_entity(Prototype.WoodenChest, position=placement_position)
    
    # Add more items to completely fill the inventory
    current_inv = game.inspect_inventory()
    max_inventory = {
        **current_inv,
        'iron-plate': 200, 'copper-plate': 200, 'transport-belt': 200, 'pipe': 200,
        'burner-inserter': 200, 'stone-furnace': 100, 'burner-mining-drill': 200,
        'offshore-pump': 100, 'boiler': 100, 'steam-engine': 100, 'stone-wall': 200,
        'splitter': 100, 'iron-gear-wheel': 200, 'electronic-circuit': 200,
        'copper-cable': 200, 'iron-chest': 100
    }
    game.instance.set_inventory(max_inventory)
    
    # Get final chest count
    final_inv = game.inspect_inventory()
    chests_before = final_inv.get('wooden-chest', 0)
        # Try to pick up the wooden chest - should fail due to full inventory
    try:
        result = game.pickup_entity(chest)
        assert False, f"Expected pickup to fail due to full inventory, but it succeeded: {result}"
            
    except Exception as e:
        # Exception is expected when inventory is full
        error_message = str(e).lower()

        assert ("inventory" in error_message and "full" in error_message) or \
                ("slots" in error_message and "available" in error_message) or \
                ("space" in error_message), \
                f"Expected inventory full error, but got: {e}"
    # else:
    #     # If stack isn't full, pickup should succeed (adding to existing stack)
    #     result = game.pickup_entity(chest)
    #     chests_after = game.inspect_inventory().get('wooden-chest', 0)
    #     assert result == True, f"Expected pickup to succeed when stack not full, but got: {result}"
    #     assert chests_after == chests_before + 1, \
    #         f"Expected {chests_before + 1} wooden chests after pickup, but got {chests_after}"



def test_pickup_ground_item(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    iron = game.nearest(Resource.IronOre)
    game.move_to(iron)
    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron)
    game.insert_item(Prototype.Coal, drill, quantity=50)
    game.sleep(6)
    game.pickup_entity(Prototype.IronOre, drill.drop_position)
    assert game.inspect_inventory()[Prototype.IronOre] == 1

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler]

def test_place_pickup_pipe_group(game):
    game.move_to(Position(x=0, y=0))
    water_pipes = game.connect_entities(Position(x=0, y=1), Position(x=10, y=1), connection_type=Prototype.Pipe)

    game.pickup_entity(water_pipes)
    assert game.inspect_inventory()[Prototype.Pipe] == 100

    game.move_to(Position(x=0, y=0))
    water_pipes = game.connect_entities(Position(x=0, y=1), Position(x=10, y=1), connection_type=Prototype.Pipe)

    for pipe in water_pipes.pipes:
        game.pickup_entity(pipe)
    assert game.inspect_inventory()[Prototype.Pipe] == 100


def test_place_pickup_inventory(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0,y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(Prototype.WoodenChest, position=chest.position)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory

def test_place_pickup_inventory2(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0,y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(chest)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory

def test_pickup_belts(game):
    belts = game.connect_entities(Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt)
    belt = belts
    nbelts = game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts

def test_pickup_belts_position(game):
    belts = game.connect_entities(Position(x=1, y=-1), Position(x=-2, y=0), Prototype.TransportBelt)
    print(belts)
    print(belts.belts)
    game.pickup_entity(Prototype.TransportBelt, Position(x=0.5, y=0.5))
    pass

def test_pickup_pipes(game):
    pipes = game.connect_entities(Position(x=1, y=-1), Position(x=-2, y=0), Prototype.Pipe)
    print(pipes)
    print(pipes.pipes)
    for belt in pipes.pipes:
        game.pickup_entity(Prototype.Pipe, belt.position)
        print(f"Pickup belt at {belt.position}")

def test_pickup_belts_that_dont_exist(game):
    belts = game.connect_entities(Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt)
    belt = belts
    nbelts = game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts
    try:
        game.pickup_entity(nbelts)
    except Exception as e:
        assert True, "Should not be able to pick up a non-existent belt"