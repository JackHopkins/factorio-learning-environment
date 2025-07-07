import pickle
import unittest

from fle.eval.algorithms.mcts.chunked_mcts import ChunkedMCTS
from fle.commons.models.game_state import GameState
from fle.env.game_types import Prototype
from fle.env import FactorioInstance

FULL_PROGRAM = """
# First, let's gather some basic resources to start building our factory
# We'll need to find and mine iron ore and coal to get started

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Harvest some iron ore
iron_ore_harvested = 0
while iron_ore_harvested < 50:
    iron_ore_harvested += harvest_resource(iron_ore_position, 10)

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
move_to(coal_position)

# Harvest some coal
coal_harvested = 0
while coal_harvested < 20:
    coal_harvested += harvest_resource(coal_position, 10)

# Now that we have some resources, let's craft a burner mining drill
# Check if we have enough iron plates and iron gear wheels
inventory = inspect_inventory()
if inventory.get(Prototype.IronPlate, 0) < 3:
    # Craft iron plates from iron ore
    craft_item(Prototype.IronPlate, 3 - inventory.get(Prototype.IronPlate, 0))

if inventory.get(Prototype.IronGearWheel, 0) < 1:
    # Craft iron gear wheels from iron plates
    craft_item(Prototype.IronGearWheel, 1 - inventory.get(Prototype.IronGearWheel, 0))

# Craft the burner mining drill
craft_item(Prototype.BurnerMiningDrill)

# Place the burner mining drill on the iron ore patch
burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.DOWN, position=iron_ore_position)

# Fuel the burner mining drill with coal
insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

# Now let's set up a basic smelting setup
# Place a stone furnace next to the burner mining drill
furnace_position = Position(x=burner_mining_drill.position.x + 2, y=burner_mining_drill.position.y)
stone_furnace = place_entity(Prototype.StoneFurnace, direction=Direction.DOWN, position=furnace_position)

# Fuel the stone furnace with coal
insert_item(Prototype.Coal, stone_furnace, quantity=5)

# Place an inserter to move iron ore from the burner mining drill to the stone furnace
inserter_position = Position(x=burner_mining_drill.position.x + 1, y=burner_mining_drill.position.y)
burner_inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=inserter_position)

# Fuel the inserter with coal
insert_item(Prototype.Coal, burner_inserter, quantity=2)

# Place a transport belt to move iron plates from the stone furnace to a chest
belt_position = Position(x=stone_furnace.position.x + 1, y=stone_furnace.position.y)
transport_belt = place_entity(Prototype.TransportBelt, direction=Direction.RIGHT, position=belt_position)

# Place a chest to store the iron plates
chest_position = Position(x=transport_belt.position.x + 1, y=transport_belt.position.y)
iron_chest = place_entity(Prototype.IronChest, direction=Direction.RIGHT, position=chest_position)

# Place an inserter to move iron plates from the stone furnace to the transport belt
inserter2_position = Position(x=stone_furnace.position.x, y=stone_furnace.position.y + 1)
burner_inserter2 = place_entity(Prototype.BurnerInserter, direction=Direction.DOWN, position=inserter2_position)

# Fuel the second inserter with coal
insert_item(Prototype.Coal, burner_inserter2, quantity=2)

# Wait for the system to produce some iron plates
sleep(30)

# Check the chest to see if iron plates have been produced
chest_inventory = inspect_inventory(iron_chest)
iron_plates_in_chest = chest_inventory.get(Prototype.IronPlate, 0)

# Verify that the system is working
assert iron_plates_in_chest > 0, "No iron plates were produced in the chest"
print(f"Successfully produced {iron_plates_in_chest} iron plates and stored them in the chest")
"""

FULL_PROGRAM_2 = """
# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Place the burner mining drill on the iron ore patch
burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.DOWN, position=iron_ore_position)

# Fuel the burner mining drill with coal
insert_item(Prototype.Coal, burner_mining_drill, quantity=5)
"""


class TestSaveLoadPythonNamespace(unittest.TestCase):
    """
    FactorioInstance exposes a Python namespace for the agent to persist variables.
    These tests verify that the namespace can be saved and loaded correctly into new instances.
    """

    def setUp(self):
        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={
                "boiler": 1,
                "burner-mining-drill": 1,
                "coal": 50,
                "transport-belt": 10,
            },
        )

    def test_save_load_simple_variable_namespace(self):
        self.instance.eval("x=2")
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )

        self.instance.reset(game_state)
        self.instance.eval("assert x == 2")

    def test_load_in_all_variable_values(self):
        game_state_raw = {
            "entities": "eJyrrgUAAXUA+Q==",
            "inventory": {"coal": 50, "iron-ore": 50},
            "namespace": "800495d6090000000000007d94288c046576616c948c086275696c74696e73948c046576616c9493948c08456c6c6970736973948c086275696c74696e73948c08456c6c69707369739493948c0546616c736594898c044e6f6e65944e8c0e4e6f74496d706c656d656e7465649468068c0e4e6f74496d706c656d656e7465649493948c045472756594888c036162739468028c036162739493948c03616c6c9468028c03616c6c9493948c03616e799468028c03616e799493948c0561736369699468028c0561736369699493948c0362696e9468028c0362696e9493948c0a627265616b706f696e749468028c0a627265616b706f696e749493948c0863616c6c61626c659468028c0863616c6c61626c659493948c036368729468028c036368729493948c07636f6d70696c659468028c07636f6d70696c659493948c09636f70797269676874948c0d5f736974656275696c74696e73948c085f5072696e7465729493942981947d94288c0e5f5072696e7465725f5f6e616d6594682a8c0e5f5072696e7465725f5f64617461945833010000436f707972696768742028632920323030312d3230323120507974686f6e20536f66747761726520466f756e646174696f6e2e0a416c6c205269676874732052657365727665642e0a0a436f707972696768742028632920323030302042654f70656e2e636f6d2e0a416c6c205269676874732052657365727665642e0a0a436f707972696768742028632920313939352d3230303120436f72706f726174696f6e20666f72204e6174696f6e616c20526573656172636820496e6974696174697665732e0a416c6c205269676874732052657365727665642e0a0a436f707972696768742028632920313939312d3139393520537469636874696e67204d617468656d6174697363682043656e7472756d2c20416d7374657264616d2e0a416c6c205269676874732052657365727665642e948c0f5f5072696e7465725f5f6c696e6573944e8c135f5072696e7465725f5f66696c656e616d6573945d9475628c076372656469747394682d2981947d94286830683668318c9e202020205468616e6b7320746f204357492c20434e52492c2042654f70656e2e636f6d2c205a6f706520436f72706f726174696f6e20616e6420612063617374206f662074686f7573616e64730a20202020666f7220737570706f7274696e6720507974686f6e20646576656c6f706d656e742e2020536565207777772e707974686f6e2e6f726720666f72206d6f726520696e666f726d6174696f6e2e9468334e68345d9475628c0764656c617474729468028c0764656c617474729493948c036469729468028c036469729493948c066469766d6f649468028c066469766d6f649493948c04657865639468028c04657865639493948c046578697494682b8c07517569747465729493942981947d94288c046e616d659468478c03656f66948c114374726c2d442028692e652e20454f46299475628c06666f726d61749468028c06666f726d61749493948c07676574617474729468028c07676574617474729493948c07676c6f62616c739468028c07676c6f62616c739493948c07686173617474729468028c07686173617474729493948c04686173689468028c04686173689493948c0468656c7094682b8c075f48656c7065729493942981948c036865789468028c036865789493948c0269649468028c0269649493948c05696e7075749468028c05696e7075749493948c0a6973696e7374616e63659468028c0a6973696e7374616e63659493948c0a6973737562636c6173739468028c0a6973737562636c6173739493948c04697465729468028c04697465729493948c036c656e9468028c036c656e9493948c076c6963656e736594682d2981947d94286830687768318c275365652068747470733a2f2f7777772e707974686f6e2e6f72672f7073662f6c6963656e73652f9468334e68345d94288c722f4c6962726172792f446576656c6f7065722f436f6d6d616e644c696e65546f6f6c732f4c6962726172792f4672616d65776f726b732f507974686f6e332e6672616d65776f726b2f56657273696f6e732f332e392f6c69622f707974686f6e332e392f2e2e2f4c4943454e53452e747874948c6e2f4c6962726172792f446576656c6f7065722f436f6d6d616e644c696e65546f6f6c732f4c6962726172792f4672616d65776f726b732f507974686f6e332e6672616d65776f726b2f56657273696f6e732f332e392f6c69622f707974686f6e332e392f2e2e2f4c4943454e5345948c6f2f4c6962726172792f446576656c6f7065722f436f6d6d616e644c696e65546f6f6c732f4c6962726172792f4672616d65776f726b732f507974686f6e332e6672616d65776f726b2f56657273696f6e732f332e392f6c69622f707974686f6e332e392f4c4943454e53452e747874948c6b2f4c6962726172792f446576656c6f7065722f436f6d6d616e644c696e65546f6f6c732f4c6962726172792f4672616d65776f726b732f507974686f6e332e6672616d65776f726b2f56657273696f6e732f332e392f6c69622f707974686f6e332e392f4c4943454e5345948c0d2e2f4c4943454e53452e747874948c092e2f4c4943454e5345946575628c066c6f63616c739468028c066c6f63616c739493948c036d61789468028c036d61789493948c036d696e9468028c036d696e9493948c046e6578749468028c046e6578749493948c036f63749468028c036f63749493948c046f70656e948c02696f948c046f70656e9493948c036f72649468028c036f72649493948c03706f779468028c03706f779493948c057072696e749468028c057072696e749493948c04717569749468492981947d9428684c689e684d684e75628c04726570729468028c04726570729493948c05726f756e649468028c05726f756e649493948c07736574617474729468028c07736574617474729493948c06736f727465649468028c06736f727465649493948c0373756d9468028c0373756d9493948c04766172739468028c04766172739493948c0d636f616c5f706f736974696f6e948c11666163746f72696f5f656e746974696573948c08506f736974696f6e9493942981947d94288c085f5f646963745f5f947d94288c0178944740338000000000008c01799447c027000000000000758c125f5f707964616e7469635f65787472615f5f944e8c175f5f707964616e7469635f6669656c64735f7365745f5f948f942868bc68bb908c145f5f707964616e7469635f707269766174655f5f944e75628c0e636f616c5f686172766573746564944b328c0e69726f6e5f686172766573746564944b328c0d69726f6e5f706f736974696f6e9468b62981947d942868b97d942868bb47c02700000000000068bc4740338000000000007568bd4e68be8f942868bc68bb9068c04e7562752e",
            "timestamp": 1735481767.4378161,
        }
        game_state = GameState.parse(game_state_raw)
        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )
        self.instance.reset(game_state)
        ngame_state = GameState.from_instance(self.instance)
        nvars = pickle.loads(ngame_state.namespaces[0])

        assert "coal_position" in nvars and nvars["coal_position"]

    def test_save_load_items_on_ground(self):
        MINER = """
move_to(nearest(Resource.IronOre))
miner = place_entity(Prototype.BurnerMiningDrill, Direction.UP, nearest(Resource.IronOre))
insert_item(Prototype.Coal, miner)
sleep(15)
pickup_entity(miner)
"""
        self.instance.eval(MINER)
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )

        self.instance.reset(game_state)
        response = self.instance.eval(
            "pickup_entity(Prototype.IronOre, miner.drop_position)"
        )
        assert "Error" not in response

    def test_save_load_items_on_belt(self):
        MINER = """
move_to(nearest(Resource.IronOre))
miner = place_entity(Prototype.BurnerMiningDrill, Direction.UP, nearest(Resource.IronOre))
insert_item(Prototype.Coal, miner)
belt = place_entity(Prototype.TransportBelt, Direction.UP, miner.drop_position)
sleep(15)
pickup_entity(miner)
"""
        response = self.instance.eval(MINER)
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )

        self.instance.reset(game_state)
        response = self.instance.eval(
            "pickup_entity(Prototype.TransportBelt, belt.position)"
        )
        assert "Error" not in response

        assert self.instance.namespace.inspect_inventory()[Prototype.IronOre] == 4

    def test_save_load_simple_variable_namespace_with_exception(self):
        self.instance.eval(
            "boiler = place_entity(Prototype.Boiler, Direction.UP, Position(x=0, y=0))"
        )
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )

        self.instance.reset(game_state)
        _, _, response = self.instance.eval("print(boiler.position)")

        assert "Error" not in response
        pass

    def test_save_load_simple_variable_namespace2(self):
        self.instance.eval(
            "boiler = place_entity(Prototype.Boiler, Direction.UP, Position(x=0, y=0))"
        )
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )
        self.instance.reset()
        self.instance.reset(game_state)
        self.instance.eval("assert boiler")
        resp2 = self.instance.eval("print(boiler)")
        assert "error" not in resp2

    def test_declare_load_function_definition(self):
        self.instance.eval('def myfunc():\n  return "hello world"')

        _, _, resp2 = self.instance.eval("print(myfunc())")
        assert "hello world" in resp2

        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={},
        )
        self.instance.reset()
        self.instance.reset(game_state)
        _, _, resp3 = self.instance.eval("print(myfunc())")
        assert "hello world" in resp3

    def test_full_program(self):
        splitter = ChunkedMCTS(None, None, None, "", None, initial_state=None)
        parts = splitter._split_into_chunks(FULL_PROGRAM)

        for part in parts:
            resp = self.instance.eval(part.code)

            game_state = GameState.from_instance(self.instance)

            self.instance = FactorioInstance(
                address="localhost",
                bounding_box=200,
                tcp_port=27000,
                fast=True,
                inventory={},
            )
            self.instance.reset()
            self.instance.reset(game_state)

            print(resp)

    def test_drill_inventory(self):
        resp = self.instance.eval(FULL_PROGRAM_2)

        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            inventory={"coal": 50},
        )
        self.instance.reset()
        self.instance.reset(game_state)

        print(resp)

    def test_save_load_research_new_instance(self):
        # Save game state including research
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            fast=True,
            all_technologies_researched=False,
            inventory={},
        )
        self.instance.reset()

        # Verify that there are no technologies here
        n_game_state = GameState.from_instance(self.instance)

        game_state_techs = (
            game_state.research.technologies.values()
        )  # Has everything researched
        n_game_state_techs = (
            n_game_state.research.technologies.values()
        )  # Has nothing researched

        for i, j in zip(game_state_techs, n_game_state_techs):
            assert i.name == j.name

            # Late game techs may be infinite and therefore are always not yet researched
            skip = False
            for k in i.prerequisites:
                if k == "space-science-pack":
                    skip = True

            if not skip:
                assert i.researched, f"Technology {i.name} should be researched"
                assert not j.researched, f"Technology {j.name} should not be researched"

        self.instance.reset(game_state)
        k_game_state = GameState.from_instance(self.instance)
        k_game_state_techs = k_game_state.research.technologies.values()

        for tech in k_game_state_techs:
            skip = False
            for k in tech.prerequisites:
                if k == "space-science-pack":
                    skip = True
            if not skip:
                assert tech.researched


if __name__ == "__main__":
    unittest.main()
