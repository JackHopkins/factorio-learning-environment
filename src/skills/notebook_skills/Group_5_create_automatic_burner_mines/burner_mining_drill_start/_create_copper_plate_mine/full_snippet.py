from factorio_instance import *

"""
Main Objective: We need create an automated copper plate burner mine that mines copper ore to a fueled furnace placed at the drill's drop position that will smelt plates. First place down the drill and then place a furnace at drill's drop position with fuel. The final setup should be checked by looking if the furnace has any copper PLATES in it
"""



"""
Step 1: Place the burner mining drill. We need to find a copper ore patch and place the burner mining drill on it. This step involves:
- Move to a copper ore patch
- Place the burner mining drill on the copper ore
- Fuel the burner mining drill with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest copper ore patch
copper_ore_position = nearest(Resource.CopperOre)
print(f"Found copper ore at position: {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position)
print(f"Moved to copper ore position: {copper_ore_position}")

# Place the burner mining drill on the copper ore
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position)
print(f"Placed burner mining drill at position: {drill.position}")

# Fuel the burner mining drill with coal
insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted 5 coal into the burner mining drill")

# Verify that the drill is placed correctly
entities = get_entities({Prototype.BurnerMiningDrill}, position=copper_ore_position, radius=1)
assert len(entities) > 0, "Failed to place burner mining drill"
print("Successfully placed burner mining drill")

# Verify that the drill is fueled
drill_inventory = inspect_inventory(drill)
assert drill_inventory[Prototype.Coal] > 0, "Failed to fuel burner mining drill"
print("Successfully fueled burner mining drill")

print("Burner mining drill setup complete")


"""
Step 2: Place and fuel the stone furnace. We need to place a stone furnace at the drill's drop position and fuel it. This step involves:
- Identify the drop position of the burner mining drill
- Place a stone furnace at the identified drop position
- Fuel the stone furnace with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Get the burner mining drill we placed in the previous step
drill = get_entities({Prototype.BurnerMiningDrill})[0]
print(f"Retrieved burner mining drill at position: {drill.position}")

# Identify the drop position of the burner mining drill
drop_position = drill.drop_position
print(f"Identified drop position: {drop_position}")

# Move near the drop position
move_to(Position(x=drop_position.x, y=drop_position.y + 1))
print(f"Moved near the drop position")

# Place the stone furnace at the drop position
furnace = place_entity(Prototype.StoneFurnace, position=drop_position)
print(f"Placed stone furnace at position: {furnace.position}")

# Place a burner inserter next to the furnace
inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.WEST, spacing=0)
print(f"Placed burner inserter at position: {inserter.position}")

# Rotate the inserter to face the furnace
inserter = rotate_entity(inserter, Direction.EAST)
print(f"Rotated inserter to face the furnace")

# Insert coal into the inserter
insert_item(Prototype.Coal, inserter, quantity=5)
print("Inserted 5 coal into the burner inserter")

# Verify that the furnace is placed correctly
entities = get_entities({Prototype.StoneFurnace}, position=drop_position, radius=1)
assert len(entities) > 0, "Failed to place stone furnace"
print("Successfully placed stone furnace")

# Verify that the inserter is placed and has coal
inserter_inventory = inspect_inventory(inserter)
assert inserter_inventory[Prototype.Coal] > 0, "Failed to fuel burner inserter"
print("Successfully fueled burner inserter")

print("Stone furnace and burner inserter setup complete")


"""
Step 3: Verify the setup. We need to check if the automated copper plate production is working correctly. This step involves:
- Wait for 30 seconds to allow time for the mining and smelting process
- Check the contents of the stone furnace for copper plates

##
"""
# Placeholder 3