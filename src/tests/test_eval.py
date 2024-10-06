import unittest

from factorio_instance import FactorioInstance

embedded_function = """
def inspect_inventory_wrapper():
    return inspect_inventory()
    
inspect_inventory_wrapper()
"""

expected_result = "{'iron-chest': 2, 'transport-belt': 50, 'burner-inserter': 32, 'small-electric-pole': 10, 'pipe': 15, 'boiler': 1, 'steam-engine': 1, 'burner-mining-drill': 3, 'electric-mining-drill': 1, 'stone-furnace': 9, 'assembling-machine-1': 1, 'coal': 50, 'iron-plate': 50, 'copper-plate': 50}"

inventory = {
    'iron-plate': 50,
    'coal': 50,
    'copper-plate': 50,
    'iron-chest': 2,
    'burner-mining-drill': 3,
    'electric-mining-drill': 1,
    'assembling-machine-1': 1,
    'stone-furnace': 9,
    'transport-belt': 50,
    'boiler': 1,
    'burner-inserter': 32,
    'pipe': 15,
    'steam-engine': 1,
    'small-electric-pole': 10
}
instance = FactorioInstance(address='localhost',
                            bounding_box=200,
                            tcp_port=27015,
                            fast=True,
                            inventory=inventory)
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



if __name__ == '__main__':
    unittest.main()
