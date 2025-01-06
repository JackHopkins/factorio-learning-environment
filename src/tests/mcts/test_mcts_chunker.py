import unittest
import ast
from dataclasses import dataclass
from typing import List, Optional

from search.mcts.chunked_mcts import ChunkedMCTS


@dataclass
class ProgramChunk:
    docstring: str
    code: str
    state: Optional['GameState'] = None
    reward: float = 0.0

FULL_PROGRAM = \
'''
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

FULL_PROGRAM2= \
'''
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
        self.assertTrue( "x = 1\ny = 2" in chunks[0].code.strip())

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
        self.assertEqual(len(chunks), 3)
        for program, task, value in zip(chunks, ["First task", "Second task", "Third task"], ["x = 1", "y = 2", "z = 3"]):
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
        self.assertEqual(len(chunks), 2)
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
        self.assertEqual(len(chunks), 2)
        self.assertTrue("Build initial structure\nWith multiple lines" in chunks[0].code)

    def test_no_docstring(self):
        code = "x = 1\ny = 2"
        chunks = self.splitter._split_into_chunks(code)
        self.assertEqual(len(chunks), 0)

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
        self.assertEqual(len(chunks), 2)
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
        self.assertEqual(len(chunks), 2)
        self.assertTrue("Task 2" in chunks[1].code)

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
        chunks = self.splitter._split_into_chunks(FULL_PROGRAM2)

        pass

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
            self.assertEqual(len(chunks), 3)


if __name__ == '__main__':
    unittest.main()