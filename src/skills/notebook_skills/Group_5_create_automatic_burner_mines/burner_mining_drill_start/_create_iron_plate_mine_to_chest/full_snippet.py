from factorio_instance import *

"""
Main Objective: We need create an automated iron plate burner mine that mines iron ore to a fueled furnace placed at the drill's drop position that will smelt plates and send them to a chest placed further away. First place down the drill, then place the furnace with a inserter next to it, then a chest with a rotated inserter next to it and then connect the pickup pos of chest inserter with the drop pos of furnace inserter. The final setup should be checked by looking if the chest has any iron plates in it
"""



"""
Step 1: Place the burner mining drill. We need to:
- Move to an iron ore patch
- Place the burner mining drill on the iron ore patch
- Fuel the burner mining drill with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Found iron ore patch at {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at {iron_ore_position}")

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position)
print(f"Placed burner mining drill at {drill.position}")

# Insert coal into the burner mining drill to fuel it
insert_item(Prototype.Coal, drill, quantity=1)
print("Inserted coal into burner mining drill")

# Verify that the drill is placed correctly
entities = get_entities({Prototype.BurnerMiningDrill}, position=iron_ore_position, radius=1)
assert len(entities) > 0, "Failed to place burner mining drill"
placed_drill = entities[0]
print(f"Verified drill placement at {placed_drill.position}")

# Verify that the drill is on an iron ore patch
iron_ore_patch = get_resource_patch(Resource.IronOre, placed_drill.position)
assert iron_ore_patch is not None, "Drill is not placed on an iron ore patch"
print(f"Verified drill is on iron ore patch of size {iron_ore_patch.size}")

print("Successfully placed and fueled burner mining drill on iron ore patch")


"""
Step 2: Set up the furnace and its inserter. We need to:
- Place a stone furnace at the drill's drop position
- Fuel the stone furnace with coal
- Place a burner inserter next to the furnace
- Fuel the burner inserter with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 9}
#Step Execution

# Get the existing burner mining drill
drill = get_entities({Prototype.BurnerMiningDrill})[0]
print(f"Found existing burner mining drill at {drill.position}")

# Move closer to the drill's drop position
move_to(drill.drop_position)
print(f"Moved to {drill.drop_position}")

# Check for existing furnaces
existing_furnaces = get_entities({Prototype.StoneFurnace}, position=drill.drop_position, radius=2)

if existing_furnaces:
    furnace = existing_furnaces[0]
    print(f"Found existing stone furnace at {furnace.position}")
else:
    # Place the stone furnace next to the drill's drop position
    furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.drop_position, direction=Direction.DOWN)
    print(f"Placed stone furnace at {furnace.position}")

# Fuel the stone furnace with coal
insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted coal into stone furnace")

# Check for existing inserters
existing_inserters = get_entities({Prototype.BurnerInserter}, position=furnace.position, radius=2)

if existing_inserters:
    inserter = existing_inserters[0]
    print(f"Found existing burner inserter at {inserter.position}")
else:
    # Place a burner inserter next to the furnace
    inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.LEFT)
    print(f"Placed burner inserter at {inserter.position}")

    # Rotate the inserter to face the furnace
    inserter = rotate_entity(inserter, Direction.RIGHT)
    print(f"Rotated burner inserter to face the furnace")

# Fuel the burner inserter with coal
insert_item(Prototype.Coal, inserter, quantity=1)
print("Inserted coal into burner inserter")

# Verify the furnace placement
furnaces = get_entities({Prototype.StoneFurnace}, position=drill.drop_position, radius=2)
assert len(furnaces) >= 1, f"Failed to find or place furnace. Found {len(furnaces)} furnaces."

# Verify the inserter placement
inserters = get_entities({Prototype.BurnerInserter}, position=furnace.position, radius=2)
assert len(inserters) >= 1, f"Failed to find or place inserter. Found {len(inserters)} inserters."

print("Successfully set up the furnace and its inserter")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")


"""
Step 3: Set up the chest and its inserter. We need to:
- Place the wooden chest further away from the furnace
- Place a burner inserter next to the chest
- Rotate the chest inserter to put items into the chest
- Fuel the chest inserter with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 7}
#Step Execution

# Get the existing furnace
furnace = get_entities({Prototype.StoneFurnace})[0]
print(f"Found existing stone furnace at {furnace.position}")

# Calculate the position for the wooden chest (7 tiles away from the furnace)
chest_pos = Position(x=furnace.position.x, y=furnace.position.y + 7)
print(f"Calculated chest position at {chest_pos}")

# Move to the calculated chest position
move_to(chest_pos)
print(f"Moved to {chest_pos}")

# Check for existing chests
existing_chests = get_entities({Prototype.WoodenChest}, position=chest_pos, radius=1)

if existing_chests:
    chest = existing_chests[0]
    print(f"Found existing wooden chest at {chest.position}")
else:
    # Place the wooden chest
    chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)
    print(f"Placed wooden chest at {chest.position}")

# Check for existing inserters near the chest
existing_inserters = get_entities({Prototype.BurnerInserter}, position=chest.position, radius=2)

if existing_inserters:
    inserter_chest = existing_inserters[0]
    print(f"Found existing burner inserter for chest at {inserter_chest.position}")
else:
    # Place a burner inserter next to the chest
    inserter_chest = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT)
    print(f"Placed burner inserter for chest at {inserter_chest.position}")

# Rotate the chest inserter to face the chest (LEFT direction to insert into the chest)
rotate_entity(inserter_chest, Direction.LEFT)
print(f"Rotated chest inserter to face the chest")

# Fetch the updated inserter information
inserter_chest = get_entities({Prototype.BurnerInserter}, position=inserter_chest.position, radius=1)[0]
print(f"Updated chest inserter direction: {inserter_chest.direction}")

# Fuel the chest inserter with coal
insert_item(Prototype.Coal, inserter_chest, quantity=1)
print("Inserted coal into chest inserter")

# Verify the chest placement
chests = get_entities({Prototype.WoodenChest}, position=chest_pos, radius=1)
assert len(chests) >= 1, f"Failed to find or place wooden chest. Found {len(chests)} chests."

# Verify the chest inserter placement
chest_inserters = get_entities({Prototype.BurnerInserter}, position=chest.position, radius=2)
assert len(chest_inserters) >= 1, f"Failed to find or place chest inserter. Found {len(chest_inserters)} inserters."

print("Successfully set up the chest and its inserter")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")


"""
Step 4: Connect the furnace to the chest. We need to:
- Connect the pickup position of the chest inserter with the drop position of the furnace inserter using transport belts
"""
# Placeholder 4

"""
Step 5: Check the setup. We need to:
- Wait for 30 seconds to allow the system to operate
- Check if the wooden chest contains any iron plates
##
"""
# Placeholder 5