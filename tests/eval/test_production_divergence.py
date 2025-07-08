import unittest

from fle.env import FactorioInstance
from fle.env.utils.profits import eval_program_with_achievements

test_string = """
pos = nearest(Resource.Stone)
move_to(pos)
harvest_resource(pos, 10)
craft_item(Prototype.StoneFurnace, 1)
pos = nearest(Resource.Coal)
move_to(pos)
harvest_resource(pos, 10)
pos = nearest(Resource.CopperOre)
move_to(pos)
harvest_resource(pos, 10)
pos = Position(x = 0, y = 0)
move_to(pos)
furnace = place_entity(Prototype.StoneFurnace, position = pos)
insert_item(Prototype.CopperOre, furnace, 5)
insert_item(Prototype.Coal, furnace, 5)
sleep(16)
"""

test_string_1 = """
pos = nearest(Resource.Stone)
move_to(pos)
harvest_resource(pos, 10)
craft_item(Prototype.StoneFurnace, 1)
pos = nearest(Resource.Coal)
move_to(pos)
harvest_resource(pos, 10)
pos = nearest(Resource.IronOre)
move_to(pos)
harvest_resource(pos, 10)
pos = Position(x = 0, y = 0)
move_to(pos)
furnace = place_entity(Prototype.StoneFurnace, position = pos)
insert_item(Prototype.IronOre, furnace, 5)
insert_item(Prototype.Coal, furnace, 5)
sleep(16)
extract_item(Prototype.IronPlate, furnace.position, 10)
"""


class TestProductionDivergence(unittest.TestCase):
    def test_achievements(self):
        instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            # cache_scripts=False,
            inventory={},
        )
        instance.speed(10)

        _, _, _, achievements = eval_program_with_achievements(instance, test_string_1)
        ground_truth_achievement = {
            "static": {"stone-furnace": 1, "coal": 10, "stone": 10, "iron-ore": 10},
            "dynamic": {"iron-plate": 5},
        }

        assert achievements == ground_truth_achievement
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        ground_truth_achievement = {
            "static": {"stone-furnace": 1, "coal": 10, "stone": 10, "copper-ore": 10},
            "dynamic": {"copper-plate": 5},
        }
        assert achievements == ground_truth_achievement


if __name__ == "__main__":
    unittest.main()
