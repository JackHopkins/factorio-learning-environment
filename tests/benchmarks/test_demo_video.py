# import json
# import time

# import pytest

# from fle.env.entities import Position
# from fle.env import FactorioInstance
# from fle.env.game_types import Prototype
# from fle.env.utils.profits import eval_program_with_profits

# @pytest.fixture()
# def game():
#     instance = FactorioInstance(address='localhost',
#                                 tcp_port=27000,
#                                 cache_scripts=False,
#                                 fast=False,
#                                 inventory={
#         'burner-mining-drill': 2,
#         'stone-furnace': 1,
#         'burner-inserter': 5,
#         'transport-belt': 100,
#         'iron-chest': 1,
#         'iron-plate': 10,
#         'coal': 50,
#     })
#     yield instance.namespace
#     instance.reset()


# def evaluate_jsonl_programs(jsonl_file):
#         programs = []
#         with open(jsonl_file, "r") as f:
#             for line in f.readlines():
#                 program = json.loads(line)
#                 programs.append(program)
#         instance = FactorioInstance(address='localhost',
#                                 bounding_box=200,
#                                 tcp_port=27000,
#                                 fast=True,
#                                 #cache_scripts=False,
#                                 inventory={})

#         instance.speed(10)
#         time.sleep(5)
#         profit_config = {"max_static_unit_profit_cap": 5,
#                                                     "dynamic_profit_multiplier": 10}
#         profit_strings = []
#         for program in programs:
#             for node_idx, node in enumerate(program):
#                 step_type = node["meta"]["type"]
#                 if step_type == "completed_objective":
#                     continue
#                 code = node["code"]
#                 _, _, _, profits = eval_program_with_profits(instance, code, profit_config)
#                 executor_step = node["meta"]["executor_step"]["input_step"]
#                 response = node["response"]
#                 profit_str = f"Step {node_idx}: {executor_step} - {profits}"
#                 profit_strings.append(profit_str)
#                 #print(f"Step {node_idx} - {executor_step}")
#                 #print(f"Response: {response}")
#                 #print(f"\n")
#                 #end_production_flows = node["meta"]["production_flows"]
#         for profit_str in profit_strings:
#             print(profit_str)

# def test_inspect_inventory(game):
#     #game.add_command('create_grass')
#     #game.execute_transaction()
#     #game.craft_item(Prototype.IronChest)
#     #inventory = game.inspect_inventory()
#     prompt = game.instance.get_system_prompt()
#     furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
#     game.move_to(game.nearest(Prototype.Coal))
#     game.harvest_resource(game.nearest(Prototype.Coal), quantity=10)
#     game.insert_item(Prototype.Coal, furnace, quantity=5)
#     game.inspect_inventory(furnace)

#     pass

# def test_harvest_resources(game):
#     game.move_to(game.nearest(Prototype.Coal))
#     game.harvest_resource(game.nearest(Prototype.Coal), quantity=10)
#     pass
