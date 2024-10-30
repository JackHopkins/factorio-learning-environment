
from factorio_instance import *

"""
Set up two burner mining drills to extract stone, each connected to its own stone furnace located away from the mining area.
"""

"""
Step 1: Place the burner mining drills on a stone patch
"""

# Find the nearest stone patch
stone_position = get_resource_patch(Resource.Stone, nearest(Resource.Stone))
print(f"Nearest stone patch found at: {stone_position}")

# Move to the stone patch
move_to(stone_position.bounding_box.center)
print(f"Moved to stone patch at: {stone_position}")

# Place the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=stone_position.bounding_box.center)
print(f"Placed first burner mining drill at: {drill1.position}")

# Fuel the first drill
fueled_drill1 = insert_item(Prototype.Coal, drill1, quantity=20)
coal_in_drill1 = fueled_drill1.fuel.get(Prototype.Coal, 0)
assert coal_in_drill1 > 0, "Failed to fuel first drill"
print("First burner mining drill successfully placed and fueled")

# Place the second burner mining drill
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=fueled_drill1.position, spacing=1)
print(f"Placed second burner mining drill at: {drill2.position}")

# Fuel the second drill
fueled_drill2 = insert_item(Prototype.Coal, drill2, quantity=20)
coal_in_drill2 = fueled_drill2.fuel.get(Prototype.Coal, 0)
assert coal_in_drill2 > 0, "Failed to fuel second drill"
print("Second burner mining drill successfully placed and fueled")

"""
Step 2: Place the stone furnaces away from the mining area
"""

# Calculate positions for furnaces (10 tiles to the right of each drill)
furnace1_position = Position(x=fueled_drill1.position.x + 10, y=fueled_drill1.position.y)
furnace2_position = Position(x=fueled_drill2.position.x + 10, y=fueled_drill2.position.y)

# Place the first stone furnace
move_to(furnace1_position)
furnace1 = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace1_position)
print(f"Placed first stone furnace at: {furnace1.position}")

# Place the second stone furnace
move_to(furnace2_position)
furnace2 = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace2_position)
print(f"Placed second stone furnace at: {furnace2.position}")

"""
Step 3: Set up burner inserters for each furnace
"""

# Set up inserter for the first furnace
inserter1 = place_entity_next_to(Prototype.BurnerInserter, furnace1.position, direction=Direction.LEFT)
inserter1 = rotate_entity(inserter1, Direction.RIGHT)
inserter1_fueled = insert_item(Prototype.Coal, inserter1, quantity=10)
assert inserter1_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel first inserter"
print(f"Placed and fueled first burner inserter at: {inserter1.position}")

# Set up inserter for the second furnace
inserter2 = place_entity_next_to(Prototype.BurnerInserter, furnace2.position, direction=Direction.LEFT)
inserter2 = rotate_entity(inserter2, Direction.RIGHT)
inserter2_fueled = insert_item(Prototype.Coal, inserter2, quantity=10)
assert inserter2_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel second inserter"
print(f"Placed and fueled second burner inserter at: {inserter2.position}")

"""
Step 4: Connect the drills to the furnaces using transport belts
"""

# Connect first drill to first furnace
belts1 = connect_entities(fueled_drill1.drop_position, inserter1.pickup_position, Prototype.TransportBelt)
assert belts1, "Failed to connect first drill to first furnace with transport belts"
print("Successfully connected first drill to first furnace")

# Connect second drill to second furnace
belts2 = connect_entities(fueled_drill2.drop_position, inserter2.pickup_position, Prototype.TransportBelt)
assert belts2, "Failed to connect second drill to second furnace with transport belts"
print("Successfully connected second drill to second furnace")

"""
Step 5: Verify the setup
"""

# Wait for the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)

# Check the contents of the first furnace
move_to(furnace1.position)
furnace1 = get_entity(Prototype.StoneFurnace, furnace1.position)
furnace1_inventory = inspect_inventory(furnace1)
stone_count1 = furnace1_inventory.get(Prototype.Stone, 0)
print(f"Stone in the first furnace: {stone_count1}")

# Check the contents of the second furnace
move_to(furnace2.position)
furnace2 = get_entity(Prototype.StoneFurnace, furnace2.position)
furnace2_inventory = inspect_inventory(furnace2)
stone_count2 = furnace2_inventory.get(Prototype.Stone, 0)
print(f"Stone in the second furnace: {stone_count2}")

assert stone_count1 > 0 or stone_count2 > 0, "No stone found in either furnace. Setup verification failed."
print("Setup verification complete. At least one furnace contains stone.")
