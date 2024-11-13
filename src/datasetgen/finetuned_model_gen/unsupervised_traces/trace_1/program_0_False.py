

from factorio_instance import *

"""
OBJECTIVE: Set up an automated copper ore mining system that mines copper ore and stores it in one of the wooden chests on the map

Planning:
1) Find a copper ore patch
2) Place a burner mining drill on the copper ore patch
3) Place a burner inserter next to the wooden chest to insert items into the chest
4) Connect the burner mining drill to the burner inserter using transport belts
5) Fuel the burner mining drill and burner inserter with coal
6) Verify that copper ore is being mined and stored in the wooden chest

Entities needed:
- Burner Mining Drill (1)
- Burner Inserter (1)
- Transport Belts (at least 5)
- Coal (for fueling the drill and inserter)

We'll need to gather some coal for fuel, but we don't need to craft anything as we have all the necessary components in our inventory.
We'll use one of the wooden chests on the map for storing the mined copper ore.
"""

"""
Step 1: Place the burner mining drill on a copper ore patch
- Find a copper ore patch
- Move to the copper ore patch
- Place the burner mining drill
"""
# Find the nearest copper ore patch
copper_ore_position = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position.bounding_box.center)
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the burner mining drill on the copper ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=copper_ore_position.bounding_box.center)
print(f"Placed burner mining drill at: {drill.position}")

"""
Step 2: Set up the chest and inserter
- Find the wooden chest on the map
- Move to the chest
- Place a burner inserter next to the chest
- Rotate the inserter to insert items into the chest
"""
# Find the wooden chest on the map
chest_position = Position(x=-2.5, y=-13.5)  # From the mining_setup information
chest = get_entity(Prototype.WoodenChest, position=chest_position)
print(f"Found wooden chest at: {chest.position}")

# Move to the chest
move_to(chest_position)
print(f"Moved to wooden chest at: {chest_position}")

# Place the burner inserter next to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest_position, direction=Direction.RIGHT)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter to insert items into the chest
inserter = rotate_entity(inserter, Direction.LEFT)
print(f"Rotated burner inserter to insert items into the chest")

"""
Step 3: Connect the drill to the inserter
- Use transport belts to connect the drill's output to the inserter's input
"""
# Connect the drill's output to the inserter's input using transport belts
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to inserter with transport belts"
print("Successfully connected drill to inserter with transport belts")

"""
Step 4: Fuel the drill and inserter
- Mine some coal (at least 10 pieces)
- Insert 5 coal into the burner mining drill
- Insert 5 coal into the burner inserter
"""
# Find the nearest coal patch
coal_position = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
print(f"Nearest coal found at: {coal_position}")

# Move to the coal patch
move_to(coal_position.bounding_box.center)
print(f"Moved to coal patch at: {coal_position}")

# Mine 10 coal
coal_mined = harvest_resource(coal_position.bounding_box.center, quantity=10)
print(f"Mined {coal_mined} coal")

# Check if we mined enough coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
assert coal_in_inventory >= 10, f"Failed to mine enough coal. Expected 10, got {coal_in_inventory}"

# Fuel the burner mining drill
fueled_drill = insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted 5 coal into the burner mining drill")

# Fuel the burner inserter
fueled_inserter = insert_item(Prototype.Coal, inserter, quantity=5)
print("Inserted 5 coal into the burner inserter")

# Verify that both entities have been fueled
assert fueled_drill.fuel.get(Prototype.Coal, 0) > 0, "Burner mining drill is not fueled"
assert fueled_inserter.fuel.get(Prototype.Coal, 0) > 0, "Burner inserter is not fueled"
print("Successfully fueled both the burner mining drill and burner inserter")

"""
Step 5: Verify the setup
- Wait for 30 seconds to allow the system to operate
- Check the contents of the wooden chest for copper ore
"""
# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move back to the chest position to check its contents
move_to(chest_position)

# Check the contents of the wooden chest
chest = get_entity(Prototype.WoodenChest, position=chest_position)
chest_inventory = inspect_inventory(chest)
copper_ore_count = chest_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the wooden chest: {copper_ore_count}")

# Verify that copper ore is present in the wooden chest
assert copper_ore_count > 0, "No copper ore found in the wooden chest. Setup verification failed."
print("Setup verification complete. Automated copper ore mining system is working correctly.")

