import unittest

from factorio_instance import FactorioInstance
#
#embedded_function = """
#def inspect_inventory_wrapper():
#    return inspect_inventory()
#    
#inspect_inventory_wrapper()
#"""
#
#expected_result = "{'iron-chest': 2, 'transport-belt': 50, 'burner-inserter': 32, 'small-electric-pole': 10, 'pipe': 15, 'boiler': 1, 'steam-engine': 1, 'burner-mining-drill': 3, 'electric-mining-drill': 1, 'stone-furnace': 9, 'assembling-machine-1': 1, 'coal': 50, 'iron-plate': 50, 'copper-plate': 50}"
#
#inventory = {
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
#}
#instance = FactorioInstance(address='localhost',
#                            bounding_box=200,
#                            tcp_port=27015,
#                            fast=True,
#                            inventory=inventory)
class TestEval(unittest.TestCase):
    def test_nested_functions(self):

        score, goal, result = instance.eval_with_error("inspect_inventory()")

        assert result[3:] == expected_result

        score, goal, result = instance.eval_with_error(embedded_function)

        assert result[3:] == expected_result

    def test_builtin_functions(self):
        score, goal, result = instance.eval_with_error("len('hello')")

        assert result[3:] == '5'

        score, goal, result = instance.eval_with_error("len([1,2,3,4,5])")

        assert result[3:] == '5'

        score, goal, result = instance.eval_with_error("len({'a': 1, 'b': 2, 'c': 3})")

        assert result[3:] == '3'

        score, goal, result = instance.eval_with_error("len((1,2,3,4,5))")

        assert result[3:] == '5'

        score, goal, result = instance.eval_with_error("len({1,2,3,4,5})")

        assert result[3:] == '5'


def test_exceptions():
    inventory = {
        'iron-plate': 50,
        'coal': 100,
        'copper-plate': 50,
        'iron-chest': 2,
        'burner-mining-drill': 3,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 9,
        'transport-belt': 500,
        'boiler': 1,
        'burner-inserter': 32,
        'pipe': 15,
        'steam-engine': 1,
        'small-electric-pole': 10,
        'iron-ore': 10
    }

    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                # cache_scripts=False,
                                inventory=inventory)

    test_string = \
"""
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
        'iron-plate': 50,
        'coal': 100,
        'copper-plate': 50,
        'iron-chest': 2,
        'burner-mining-drill': 3,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 9,
        'transport-belt': 500,
        'boiler': 1,
        'burner-inserter': 32,
        'pipe': 15,
        'steam-engine': 1,
        'small-electric-pole': 10,
        'iron-ore': 10
    }

    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                # cache_scripts=False,
                                inventory=inventory)
    test_string = \
"""
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


def test_chest_inventory():
    inventory = {
        'iron-plate': 50,
        'coal': 100,
        'copper-plate': 50,
        'iron-chest': 2,
        'burner-mining-drill': 3,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 9,
        'transport-belt': 500,
        'boiler': 1,
        'burner-inserter': 32,
        'pipe': 15,
        'steam-engine': 1,
        'small-electric-pole': 10,
        'iron-ore': 10
    }

    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                # cache_scripts=False,
                                inventory=inventory)
    test_string = \
"""
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
if __name__ == '__main__':
    unittest.main()
