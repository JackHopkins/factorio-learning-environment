import unittest
from dataclasses import dataclass
from typing import Optional

from fle.eval.algorithms.mcts import ChunkedMCTS
from fle.commons.models import GameState


@dataclass
class ProgramChunk:
    docstring: str
    code: str
    state: Optional[GameState] = None
    reward: float = 0.0


FULL_PROGRAM = '''
from factorio_instance import *

"""
Objective: Craft 8 automation science packs

Planning:
1. Print recipe for automation science packs
2. Analyze current inventory
3. Craft iron gear wheels (we need 8)
4. Craft automation science packs (we need 8)
5. Verify the crafting process
"""

"""
Step 1: Print recipe for automation science packs
"""
recipe = get_prototype_recipe(Prototype.AutomationSciencePack)
print("Automation Science Pack Recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Analyze current inventory
"""
current_inventory = inspect_inventory()
print("Current inventory:")
for item, quantity in current_inventory.items():
    print(f"{item}: {quantity}")

"""
Step 3: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=8)
print("Crafted 8 Iron Gear Wheels")

"""
Step 4: Craft automation science packs
"""
craft_item(Prototype.AutomationSciencePack, quantity=8)
print("Crafted 8 Automation Science Packs")

"""
Step 5: Verify the crafting process
"""
final_inventory = inspect_inventory()
automation_science_packs = final_inventory.get(Prototype.AutomationSciencePack, 0)
print(f"Final count of Automation Science Packs: {automation_science_packs}")

assert automation_science_packs == 8, f"Failed to craft 8 Automation Science Packs. Current count: {automation_science_packs}"
print("Successfully crafted 8 Automation Science Packs!")
'''

FULL_PROGRAM2 = '''
"""
Step 4: Extract steel plates
- Extract the steel plates from the second furnace
- Verify that we have at least 10 steel plates in our inventory
"""
# Extract steel plates from the second furnace
second_furnace = get_entity(Prototype.StoneFurnace, Position(x=-8.0, y=0.0))
move_to(second_furnace.position)

# Attempt to extract steel plates multiple times to ensure all are gathered
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.SteelPlate, second_furnace.position, quantity=50)
    steel_plates_in_inventory = inspect_inventory().get(Prototype.SteelPlate, 0)
    if steel_plates_in_inventory >= 10:
        break
    sleep(5)  # Wait a bit more if needed

print(f"Extracted steel plates. Current inventory count: {steel_plates_in_inventory}")

# Verify that we have at least 10 steel plates
assert steel_plates_in_inventory >= 10, f"Failed to extract required number of steel plates. Only {steel_plates_in_inventory} found in inventory."
print("Successfully extracted required number of steel plates")
print(f"Final steel plate count in inventory: {steel_plates_in_inventory}")
print("Steel plate extraction and verification completed successfully.")
'''

FULL_PROGRAM3 = """
# Craft 10 burner mining drills
recipe_drill = get_prototype_recipe(Prototype.BurnerMiningDrill)
for ingredient in recipe_drill.ingredients:
    required = ingredient.count * 10
    available = inspect_inventory()[ingredient.name]
    if available < required:
        craft_item(ingredient.name, quantity=required - available)
craft_item(Prototype.BurnerMiningDrill, quantity=10)

# Craft 10 stone furnaces
recipe_furnace = get_prototype_recipe(Prototype.StoneFurnace)
for ingredient in recipe_furnace.ingredients:
    required = ingredient.count * 10
    available = inspect_inventory()[ingredient.name]
    if available < required:
        craft_item(ingredient.name, quantity=required - available)
craft_item(Prototype.StoneFurnace, quantity=10)

# Craft 10 burner inserters
recipe_inserter = get_prototype_recipe(Prototype.BurnerInserter)
for ingredient in recipe_inserter.ingredients:
    required = ingredient.count * 10
    available = inspect_inventory()[ingredient.name]
    if available < required:
        craft_item(ingredient.name, quantity=required - available)
craft_item(Prototype.BurnerInserter, quantity=10)

# Craft 30 iron chests
recipe_chest = get_prototype_recipe(Prototype.IronChest)
for ingredient in recipe_chest.ingredients:
    required = ingredient.count * 30
    available = inspect_inventory()[ingredient.name]
    if available < required:
        craft_item(ingredient.name, quantity=required - available)
craft_item(Prototype.IronChest, quantity=30)

# Verify inventory
inventory = inspect_inventory()
print(f"Inventory: {inventory}")
"""

FULL_PROGRAM4 = """
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

FULL_PROGRAM5 = '''
"""
Error: Cannot craft stone, need to harvest it first.

1. Find an iron ore patch.
2. Find a coal patch.
3. Find a stone patch.
4. Harvest Stone.
5. Craft a stone furnace.
6. Move to the iron ore patch
7. Harvest iron ore and coal.
8. Craft iron plates.
9. Craft iron gear wheels.
10. Craft a burner mining drill.
11. Place a burner mining drill on the iron ore.
12. Place a stone furnace near the drill.
13. Place a burner inserter to move ore from drill to furnace.
14. Place a burner mining drill on the coal patch.
15. Place a burner inserter to move coal from coal drill to iron drill and furnace.
16. Fuel the coal drill
"""
# 1. Find an iron ore patch.
iron_ore_position = nearest(Resource.IronOre)
assert iron_ore_position, "Failed to find iron ore patch"
# 2. Find a coal patch.
coal_position = nearest(Resource.Coal)
assert coal_position, "Failed to find coal patch"
# 3. Find a stone patch.
stone_position = nearest(Resource.Stone)
assert stone_position, "Failed to find stone patch"
# 4. Harvest Stone.
move_to(stone_position)
stone_harvested = 0
while stone_harvested < 10:
    stone_harvested += harvest_resource(stone_position, 5)
# 5. Craft a stone furnace.
recipe = get_prototype_recipe(Prototype.StoneFurnace)
for ingredient in recipe.ingredients:
    if inspect_inventory().get(prototype_by_name[ingredient.name], 0) < ingredient.count:
        craft_item(prototype_by_name[ingredient.name], ingredient.count)
craft_item(Prototype.StoneFurnace)
# 6. Move to the iron ore patch
move_to(iron_ore_position)
# 7. Harvest iron ore and coal.
iron_ore_harvested = 0
while iron_ore_harvested < 10:
    iron_ore_harvested += harvest_resource(iron_ore_position, 5)
move_to(coal_position)
coal_harvested = 0
while coal_harvested < 10:
    coal_harvested += harvest_resource(coal_position, 5)
# 8. Craft iron plates.
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.IronOre, stone_furnace, quantity=10)
insert_item(Prototype.Coal, stone_furnace, quantity=10)
sleep(5)
extract_item(Prototype.IronPlate, stone_furnace, quantity=10)
pickup_entity(stone_furnace)
# 9. Craft iron gear wheels.
recipe = get_prototype_recipe(Prototype.IronGearWheel)
for ingredient in recipe.ingredients:
    if inspect_inventory().get(prototype_by_name[ingredient.name], 0) < ingredient.count:
        craft_item(prototype_by_name[ingredient.name], ingredient.count)
craft_item(Prototype.IronGearWheel)
# 10. Craft a burner mining drill.
recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
for ingredient in recipe.ingredients:
    if inspect_inventory().get(prototype_by_name[ingredient.name], 0) < ingredient.count:
        craft_item(prototype_by_name[ingredient.name], ingredient.count)
craft_item(Prototype.BurnerMiningDrill)
# 11. Place a burner mining drill on the iron ore.
iron_drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
# 12. Place a stone furnace near the drill.
stone_furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=iron_drill.position, direction=Direction.RIGHT)
# 13. Place a burner inserter to move ore from drill to furnace.
inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=stone_furnace.position, direction=Direction.LEFT)
# 14. Place a burner mining drill on the coal patch.
coal_drill = place_entity(Prototype.BurnerMiningDrill, position=coal_position)
# 15. Place a burner inserter to move coal from coal drill to iron drill and furnace.
coal_inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=coal_drill.position, direction=Direction.DOWN)
# 16. Fuel the coal drill
insert_item(Prototype.Coal, coal_drill, 10)
move_to(Position(x=0,y=0))
'''


class TestProgramChunkSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = ChunkedMCTS(None, None, None, "", None, initial_state=None)

    def test_single_chunk(self):
        code = '''
"""First task"""
x = 1
y = 2
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)
        self.assertTrue("First task" in chunks[0].code)
        self.assertTrue("x = 1\ny = 2" in chunks[0].code.strip())

    def test_comment(self):
        code = '''
"""First task"""
# This is a comment
x = 1
y = 2
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)
        self.assertTrue("First task" in chunks[0].code)
        self.assertTrue("x = 1\ny = 2" in chunks[0].code.strip())
        self.assertTrue("# This is a comment" in chunks[0].code.strip())

    def test_comment_with_gap(self):
        code = '''
"""First task"""
# This is a comment

x = 1
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)
        self.assertTrue("First task" in chunks[0].code)
        self.assertTrue("x = 1" in chunks[0].code.strip())
        self.assertTrue("# This is a comment" in chunks[0].code.strip())

    def test_multiple_chunks(self):
        code = '''
"""First task"""
x = 1

"""Second task"""
y = 2

"""Third task"""
z = 3
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(3, len(chunks))
        for program, task, value in zip(
            chunks,
            ["First task", "Second task", "Third task"],
            ["x = 1", "y = 2", "z = 3"],
        ):
            self.assertTrue(task in program.code)
            self.assertTrue(value in program.code)

    def test_multiline_code(self):
        code = '''
"""Build structure"""
x = 1
y = 2
z = x + y

"""Place items"""
items = [1, 2, 3]
for item in items:
    place(item)
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(2, len(chunks))
        self.assertTrue("x = 1" in chunks[0].code)
        self.assertTrue("for item in items:" in chunks[1].code)

    def test_multiline_docstring(self):
        code = '''
"""
Build initial structure
With multiple lines
"""
x = 1

"""Place items"""
y = 2
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(2, len(chunks))
        self.assertTrue(
            "Build initial structure\nWith multiple lines" in chunks[0].code
        )

    def test_no_docstring(self):
        code = "x = 1\ny = 2"
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)

    def test_function_definitions(self):
        code = '''
"""Setup functions"""
def func1():
    return 1

def func2():
    x = 1
    return x

"""Use functions"""
result = func1() + func2()
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(2, len(chunks))
        self.assertTrue("def func1():" in chunks[0].code)
        self.assertTrue("def func2():" in chunks[0].code)
        self.assertTrue("result = func1() + func2()" in chunks[1].code)

    def test_empty_chunks(self):
        code = '''
"""Task 1"""

"""Task 2"""
x = 1
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)
        self.assertTrue("Task 2" in chunks[0].code)

    def test_code_with_strings(self):
        code = '''
"""First task"""
x = "This is a string"
y = """This is a multiline
string but not a docstring"""
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)
        self.assertTrue('x = "This is a string"' in chunks[0].code)
        self.assertTrue('y = """This is a multiline' in chunks[0].code)

    def test_full_code(self):
        chunks = self.splitter._split_into_chunks(FULL_PROGRAM3)

        assert len(chunks) == 5

    def test_full_code2(self):
        chunks = self.splitter._split_into_chunks(FULL_PROGRAM4)

        assert len(chunks) == 18

    def test_full_code3(self):
        chunks = self.splitter._split_into_chunks(FULL_PROGRAM5)

        assert len(chunks) == 17

    def test_multiple_chunks_with_one_docstring(self):
        code = '''
"""First task

With a gap
"""
x = 1

y = 2

z = 3
'''
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 1)


if __name__ == "__main__":
    unittest.main()
