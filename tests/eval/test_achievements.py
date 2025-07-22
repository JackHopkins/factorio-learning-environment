import unittest

from fle.env import FactorioInstance
from fle.env.utils.achievements import eval_program_with_achievements


class TestAchievements(unittest.TestCase):
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

        test_string_1 = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.IronOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.IronOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(16)\nextract_item(Prototype.IronPlate, furnace.position, 10)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string_1)
        ground_truth_achievement = {
            "static": {"stone-furnace": 1, "coal": 10, "stone": 10, "iron-ore": 10},
            "dynamic": {"iron-plate": 5},
        }

        assert achievements == ground_truth_achievement

        instance.reset()
        test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(16)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        ground_truth_achievement = {
            "static": {"stone-furnace": 1, "coal": 10, "stone": 10, "copper-ore": 10},
            "dynamic": {"copper-plate": 5},
        }
        assert achievements == ground_truth_achievement

        instance.reset()
        test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(16)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        ground_truth_achievement = {
            "static": {"stone-furnace": 1, "coal": 10, "stone": 10, "copper-ore": 10},
            "dynamic": {"copper-plate": 5},
        }
        assert achievements == ground_truth_achievement


if __name__ == "__main__":
    unittest.main()
