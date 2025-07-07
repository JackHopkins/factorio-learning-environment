import unittest

from fle.commons.cluster_ips import get_local_container_ips
from fle.env import FactorioInstance

embedded_function = """
def inspect_inventory_wrapper():
   return inspect_inventory()

print(inspect_inventory_wrapper())
"""

expected_result = "{'iron-chest': 2, 'transport-belt': 50, 'burner-inserter': 32, 'small-electric-pole': 10, 'pipe': 15, 'boiler': 1, 'steam-engine': 1, 'burner-mining-drill': 3, 'electric-mining-drill': 1, 'stone-furnace': 9, 'assembling-machine-1': 1, 'coal': 50, 'iron-plate': 50, 'copper-plate': 50}"
#
# inventory = {
#    'iron-plate': 50,
#    'coal': 50,
#    'copper-plate': 50,
#    'iron-chest': 2,
#    'burner-mining-drill': 3,
#    'electric-mining-drill': 1,
#    'assembling-machine-1': 1,
#    'stone-furnace': 9,
#    'transport-belt': 50,
#    'boiler': 1,
#    'burner-inserter': 32,
#    'pipe': 15,
#    'steam-engine': 1,
#    'small-electric-pole': 10
# }
# instance = FactorioInstance(address='localhost',
#                            bounding_box=200,
#                            tcp_port=27015,
#                            fast=True,
#                            inventory=inventory)


def test_nested_functions():
    ips, udp_ports, tcp_ports = get_local_container_ips()
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=tcp_ports[-1],
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error("print(inspect_inventory())")

    assert result[3:] == "(Inventory({}),)"

    score, goal, result = instance.eval_with_error(embedded_function)

    assert result[3:] == "(Inventory({}),)"


def test_builtin_functions():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error("print(len('hello'))")

    assert result[4:-2] == "5"

    score, goal, result = instance.eval_with_error("print(len([1,2,3,4,5]))")

    assert result[4:-2] == "5"

    score, goal, result = instance.eval_with_error(
        "print(len({'a': 1, 'b': 2, 'c': 3}))"
    )

    assert result[4:-2] == "3"

    score, goal, result = instance.eval_with_error("print(len((1,2,3,4,5)))")

    assert result[4:-2] == "5"

    score, goal, result = instance.eval_with_error("print(len({1,2,3,4,5}))")

    assert result[4:-2] == "5"


def test_math():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error("print(sqrt(100))", timeout=60)
    assert "10" in result


def test_loop_print():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error(
        "for i in range(3):\n\tprint(i)", timeout=60
    )
    assert "2: (0,)\n2: (1,)\n2: (2,)" in result


def test_name_error():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error(
        "an_existing_variable=10\nprint(none_existing_variable)", timeout=60
    )
    assert "an_existing_variable" in result


def test_sleep():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error("time.sleep(10)", timeout=60)
    assert "10" in result


def test_prototype_attribute_error():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )

    score, goal, result = instance.eval_with_error(
        "print(Prototype.AssemblingMachine)", timeout=60
    )
    assert "AssemblingMachine1" in result


def test_exceptions():
    inventory = {
        "iron-plate": 50,
        "coal": 100,
        "copper-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 500,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
        "iron-ore": 10,
    }

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory=inventory,
    )

    test_string = """
# Check initial inventory
iron_position = nearest(Resource.Stone)
move_to(iron_position)
print(f"Moved to iron patch at {iron_position}")
harvest_resource(iron_position, 20)

craft_item(Prototype.StoneFurnace, 3)

# 1. Place a stone furnace
stone_furnace = place_entity(Prototype.WoodenChest, Direction.UP, iron_position)
assert stone_furnace is not None, "Failed to place stone furnace"

insert_item(Prototype.Coal, stone_furnace, 5)
insert_item(Prototype.IronOre, stone_furnace, 5)
sleep(1)
# print("Inserted coal and iron ore into the furnace")

furnaces = get_entities({Prototype.StoneFurnace})
print(furnaces)
"""

    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


def test_chest_inventory():
    inventory = {
        "iron-plate": 50,
        "coal": 100,
        "copper-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 500,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
        "iron-ore": 10,
    }

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory=inventory,
    )
    test_string = """
# Check initial inventory
iron_position = nearest(Resource.Stone)
move_to(iron_position)
print(f"Moved to iron patch at {iron_position}")
harvest_resource(iron_position, 20)


chest= place_entity(Prototype.IronChest, Direction.UP, iron_position)
insert_item(Prototype.Coal, chest, 5)
chests = get_entities()
print(chests)
"""
    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


def test_try_catch():
    inventory = {
        "iron-plate": 50,
        "coal": 100,
        "copper-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 500,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
        "iron-ore": 10,
    }

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory=inventory,
    )
    test_string = """
try:
    if inspect_inventory().get(Prototype.AssemblingMachine1, 0) > 0:
        assembling_machine_position = Position(x=2, y=1)
        assembling_machine = place_entity(Prototype.AssemblingMachine1, position=assembling_machine_position)
        print(f"Assembling Machine placed at {assembling_machine_position}.")
    else:
        print("Assembling Machine not available in inventory, cannot place.")
except Exception as e:
    print(f"Failed placing Assembling Machine: {e}")
    """
    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


def test_type_annotations_mixed_depth_prints():
    instance = FactorioInstance(
        address="localhost", bounding_box=200, tcp_port=27000, fast=True
    )
    # cache_scripts=False,
    test_string = """
print("Re-evaluating precise point harvest attempts.")

# Attempt narrower search positions, targeting manual adaptability requirements:
for dx in [-1, 0, 1]:
    for dy in [-1, 0, 1]:
        trial_position: Position = Position(x=-15.5 + dx, y=24.5 + dy)
        move_to(trial_position)
        print(f"Testing move and harvest at location: {trial_position}")
        try:
            harvested_iron_ore: int = harvest_resource(trial_position, quantity=5, radius=3)
            print(f"Collected iron ore: {harvested_iron_ore} at {trial_position}.")
            raise Exception("Oh no")
        except Exception as e:
            print(f"Failed at {trial_position}: {e}")

"""
    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


def test_mixed_hard():
    inventory = {
        "iron-plate": 50,
        "coal": 100,
        "copper-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 500,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
        "iron-ore": 10,
    }

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        inventory=inventory,
    )
    # cache_scripts=False,
    test_string = """
# Move to the center of the valid stone patch
move_to(Position(x=-15.5, y=-15.5))

# Initialize the amount of stone collected
current_stone = 0

# Attempt to harvest stone
for _ in range(3):  # Only try harvesting three times
    if current_stone < 10:
        stone_to_harvest = 10 - current_stone
        harvested = harvest_resource(Position(x=-15.5, y=-15.5), quantity=stone_to_harvest, radius=10)
        current_stone += harvested
        if current_stone >= 10:
            break  # Exit the loop once enough stone is gathered
    sleep(1)
else:
    # If the loop completes without gathering enough stone
    raise Exception("Failed to gather enough stone within the expected timeframe.")

# With enough stones gathered, attempt to craft a Stone Furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, "Failed to craft a Stone Furnace after gathering stones."

# Move to a suitable location to place and use the furnace
furnace_position = Position(x=0.0, y=0.0)
move_to(furnace_position)

# Place the Stone Furnace
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
assert furnace, "Failed to place the Stone Furnace."

# Insert coal and iron ore to begin smelting
insert_item(Prototype.Coal, furnace, quantity=5)
insert_item(Prototype.IronOre, furnace, quantity=10)

# Monitor the smelting process
for _ in range(30):
    furnace_inventory = inspect_inventory(furnace)
    if furnace_inventory.get(Prototype.IronPlate, 0) >= 10:
        break
    print("Sleeping")
    sleep(100)
else:
    raise Exception("Smelting did not complete in the expected timeframe.")

# Extract and verify the production of iron plates
produced_iron_plates = extract_item(Prototype.IronPlate, furnace.position, quantity=10)
assert produced_iron_plates == 10, f"Expected 10 iron plates, but got {produced_iron_plates}."
"""
    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


def test_mixed_hard2():
    inventory = {
        "iron-plate": 50,
        "coal": 100,
        "copper-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 500,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
        "iron-ore": 10,
    }

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        inventory=inventory,
    )
    # cache_scripts=False,
    test_string = """
# Specify the drill drop position
drill_drop_position = Position(x=20.5, y=21.5)

# Define the offsets for the adjacent positions
offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]

for dx, dy in offsets:
    candidate_position = Position(x=drill_drop_position.x + dx, y=drill_drop_position.y + dy)
    print(f"Trying to place Iron Chest at {candidate_position}")
    
    try:
        # Check if we can place the Iron Chest at the candidate position
        if can_place_entity(Prototype.IronChest, position=candidate_position):
            move_to(candidate_position)
            # Attempt to place the Iron Chest
            # Note: The function itself simply places, no attribute checks here
            placed_chest = place_entity(Prototype.IronChest, position=candidate_position)
            print(f"Iron Chest placed at {candidate_position}")
            # Exit loop on success
            break
        else:
            print(f"Cannot place Iron Chest at {candidate_position}")
    except AttributeError as attr_err:
        print(f"AttributeError: {attr_err}")
        print("Verify API call structure and returned result expectations.")
    except Exception as e:
        print(f"An error occurred during placement at {candidate_position}: {e}")

# Perform final check for the inventory state
inventory_after_attempt = inspect_inventory()
print("Final inventory state:", inventory_after_attempt)

# Evaluate entities on the map
try:
    entities_on_map = get_entities()
    print("Entities presently on the map:", entities_on_map)
except Exception as e_map_error:
    print(f"Error verifying map entities: {e_map_error}")
"""
    score, goal, result = instance.eval_with_error(test_string, timeout=60)

    pass


if __name__ == "__main__":
    unittest.main()
