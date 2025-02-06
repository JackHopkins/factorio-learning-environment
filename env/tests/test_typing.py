import unittest

from entities import Position, BurnerMiningDrill, AssemblingMachine
from game_types import Prototype


class TestActions(unittest.TestCase):
    def test_fuel(self):
        lua_response = {
            "name": "assembling-machine-1",
            "position": {"x": 0, "y": 0},
            "direction": 0,
            "energy": 0,
            "type": "assembling-machine",
            "dimensions": {"x": 0, "y": 0},
            "tile_dimensions": {"x": 0, "y": 0},
            "recipe": {
                "name": "iron-plate",
                "ingredients": [{"name": "iron-ore", "count": 1}],
            }
        }
        assembling_machine: AssemblingMachine = AssemblingMachine(**lua_response)
        from controllers.get_entity import GetEntity
        get_entity = GetEntity(None, None)

        get_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
        burner_mining_drill = BurnerMiningDrill(**lua_response)

        print(burner_mining_drill.json())
        print(burner_mining_drill.drop_position)


if __name__ == '__main__':
    unittest.main()
