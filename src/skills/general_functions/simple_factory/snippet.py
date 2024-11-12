from factorio_instance import *

chest_pos = Position(x=11.5, y=-10.5)
move_to(chest_pos)
place_entity(Prototype.WoodenChest,position= chest_pos)

"""
Step 1: Place a burner mining drill on an iron ore patch
- Find the nearest iron ore patch
- Move to the iron ore patch
- Place the burner mining drill
- Add coal to the drill
"""

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position)
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to the drill
fueled_drill = insert_item(Prototype.Coal, drill, quantity=5)
coal_inserted = fueled_drill.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the burner mining drill")

# Verify that the drill is fueled
assert fueled_drill.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel drill"

"""
Step 2: Set up the wooden chest and inserter
- Locate the wooden chest on the map
- Move to the chest
- Place a burner inserter next to the chest
- Rotate the inserter to insert items into the chest
- Add coal to the inserter
"""

# Find the wooden chest on the map
chest_pos = Position(x=11.5, y=-10.5)  # From the mining setup description
chest = get_entity(Prototype.WoodenChest, chest_pos)
print(f"Wooden chest found at: {chest.position}")

# Move to the chest
move_to(chest.position)
print(f"Moved to wooden chest at: {chest.position}")

# Place a burner inserter next to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.RIGHT)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter to face the chest
inserter = rotate_entity(inserter, Direction.LEFT)
print(f"Rotated inserter to face the chest")

# Add coal to the inserter
fueled_inserter = insert_item(Prototype.Coal, inserter, quantity=5)
coal_inserted = fueled_inserter.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the burner inserter")

# Verify that the inserter is fueled
assert fueled_inserter.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

"""
Step 3: Connect the drill to the inserter
- Use transport belts to connect the drill\'s drop position to the inserter\'s pickup position
"""

print("Connecting drill to inserter with transport belts...")
belts = connect_entities(fueled_drill.drop_position, fueled_inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to inserter with transport belts"
print("Successfully connected drill to inserter")

"""
Step 4: Verify the setup
- Wait for 30 seconds
- Check the contents of the wooden chest for iron ore
"""

print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move to the chest again (in case we moved during setup)
move_to(chest.position)

# Check the contents of the wooden chest for iron ore
chest = get_entity(Prototype.WoodenChest, chest.position)
chest_inventory = inspect_inventory(chest)
iron_ore_count = chest_inventory.get(Prototype.IronOre, 0)
print(f"Iron ore in the wooden chest: {iron_ore_count}")

# Verify that iron ore is present in the chest
assert iron_ore_count > 0, "No iron ore found in the wooden chest. Setup verification failed."
print("Setup verification complete. Iron ore mining operation is working correctly.")