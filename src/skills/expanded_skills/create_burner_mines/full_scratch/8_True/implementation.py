
from factorio_instance import *

"""
Design an automated copper ore extraction setup using 2 burner mining drills: 
one outputting to an iron chest 15 tiles away, and another feeding a stone furnace 11 tiles away to produce copper plates.
"""

# Step 1: Find copper ore patch and place burner mining drills

# Find the nearest copper ore patch
copper_ore_position = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position.bounding_box.center)
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position.bounding_box.center)
print(f"Placed first burner mining drill at: {drill1.position}")

# Place the second burner mining drill next to the first one
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=drill1.position, spacing=1)
print(f"Placed second burner mining drill at: {drill2.position}")

# Fuel both drills
for drill in [drill1, drill2]:
    fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
    coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
    assert coal_in_drill > 0, f"Failed to fuel drill at {drill.position}"
    print(f"Burner mining drill at {drill.position} successfully fueled")

# Step 2: Place iron chest and stone furnace

# Calculate positions for chest and furnace
chest_position = Position(x=drill1.position.x + 15, y=drill1.position.y)
furnace_position = Position(x=drill2.position.x + 11, y=drill2.position.y)

# Place iron chest
move_to(chest_position)
chest = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest_position)
print(f"Placed iron chest at: {chest.position}")

# Place stone furnace
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

# Fuel the furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace"
print("Stone furnace successfully fueled")

# Step 3: Set up burner inserters

# Place and fuel inserter for the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.LEFT)
chest_inserter = rotate_entity(chest_inserter, Direction.RIGHT)
chest_inserter_fueled = insert_item(Prototype.Coal, chest_inserter, quantity=10)
assert chest_inserter_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel chest inserter"
print(f"Placed and fueled chest inserter at: {chest_inserter.position}")

# Place and fuel inserter for the furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.LEFT)
furnace_inserter = rotate_entity(furnace_inserter, Direction.RIGHT)
furnace_inserter_fueled = insert_item(Prototype.Coal, furnace_inserter, quantity=10)
assert furnace_inserter_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel furnace inserter"
print(f"Placed and fueled furnace inserter at: {furnace_inserter.position}")

# Step 4: Connect drills to inserters with transport belts

print("Connecting drills to inserters with transport belts...")
chest_belts = connect_entities(drill1.drop_position, chest_inserter.pickup_position, Prototype.TransportBelt)
assert chest_belts, "Failed to connect first drill to chest inserter with transport belts"

furnace_belts = connect_entities(drill2.drop_position, furnace_inserter.pickup_position, Prototype.TransportBelt)
assert furnace_belts, "Failed to connect second drill to furnace inserter with transport belts"

print("Successfully connected drills to inserters with transport belts")

# Step 5: Verify the setup

print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Check iron chest for copper ore
move_to(chest.position)
chest = get_entity(Prototype.IronChest, chest.position)
chest_inventory = inspect_inventory(chest)
copper_ore_count = chest_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the iron chest: {copper_ore_count}")
assert copper_ore_count > 0, "No copper ore found in the iron chest. Setup verification failed."

# Check furnace for copper plates
move_to(furnace.position)
furnace = get_entity(Prototype.StoneFurnace, furnace.position)
furnace_inventory = inspect_inventory(furnace)
copper_plate_count = furnace_inventory.get(Prototype.CopperPlate, 0)
print(f"Copper plates in the furnace: {copper_plate_count}")
assert copper_plate_count > 0, "No copper plates found in the furnace. Setup verification failed."

print("\nSetup verification complete. The automated copper ore extraction system is working correctly.")
