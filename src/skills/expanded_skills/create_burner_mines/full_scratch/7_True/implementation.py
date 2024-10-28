
from factorio_instance import *

"""
Establish an automated coal mining system with 2 burner mining drills: 
one sending coal to a wooden chest 6 tiles away, and another supplying a boiler 9 tiles away.
"""

"""
Step 1: Place the burner mining drills on a coal patch
"""

# Find the nearest coal patch
coal_position = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
print(f"Nearest coal patch found at: {coal_position}")

# Move to the coal patch
move_to(coal_position.bounding_box.center)
print(f"Moved to coal patch at: {coal_position}")

# Place the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=coal_position.bounding_box.center)
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

"""
Step 2: Place the wooden chest and the boiler
"""

# Calculate positions for chest and boiler
chest_position = Position(x=drill1.position.x + 6, y=drill1.position.y)
boiler_position = Position(x=drill2.position.x + 9, y=drill2.position.y)

# Place the wooden chest
move_to(chest_position)
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Place the boiler
move_to(boiler_position)
boiler = place_entity(Prototype.Boiler, direction=Direction.UP, position=boiler_position)
print(f"Placed boiler at: {boiler.position}")

"""
Step 3: Set up the burner inserters
"""

# Place and set up inserter for the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.LEFT)
chest_inserter = rotate_entity(chest_inserter, Direction.RIGHT)
print(f"Placed and rotated chest inserter at: {chest_inserter.position}")

# Place and set up inserter for the boiler
boiler_inserter = place_entity_next_to(Prototype.BurnerInserter, boiler.position, direction=Direction.LEFT)
boiler_inserter = rotate_entity(boiler_inserter, Direction.RIGHT)
print(f"Placed and rotated boiler inserter at: {boiler_inserter.position}")

# Fuel both inserters
for inserter in [chest_inserter, boiler_inserter]:
    fueled_inserter = insert_item(Prototype.Coal, inserter, quantity=10)
    coal_in_inserter = fueled_inserter.fuel.get(Prototype.Coal, 0)
    assert coal_in_inserter > 0, f"Failed to fuel inserter at {inserter.position}"
    print(f"Burner inserter at {inserter.position} successfully fueled")

"""
Step 4: Connect the drills to the inserters using transport belts
"""

# Connect first drill to chest inserter
first_belts = connect_entities(drill1.drop_position, chest_inserter.pickup_position, Prototype.TransportBelt)
assert first_belts, "Failed to connect first drill to chest inserter with transport belts"
print("Successfully connected first drill to chest inserter with transport belts")

# Connect second drill to boiler inserter
second_belts = connect_entities(drill2.drop_position, boiler_inserter.pickup_position, Prototype.TransportBelt)
assert second_belts, "Failed to connect second drill to boiler inserter with transport belts"
print("Successfully connected second drill to boiler inserter with transport belts")

"""
Step 5: Verify the setup
"""

# Wait for the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Check the wooden chest
move_to(chest.position)
chest = get_entity(Prototype.WoodenChest, chest.position)
chest_inventory = inspect_inventory(chest)
coal_in_chest = chest_inventory.get(Prototype.Coal, 0)
print(f"Coal in the wooden chest: {coal_in_chest}")
assert coal_in_chest > 0, "No coal found in the wooden chest. Setup verification failed."
print("Coal found in the wooden chest")

# Check the boiler
move_to(boiler.position)
boiler = get_entity(Prototype.Boiler, boiler.position)
boiler_inventory = inspect_inventory(boiler)
coal_in_boiler = boiler_inventory.get(Prototype.Coal, 0)
print(f"Coal in the boiler: {coal_in_boiler}")
assert coal_in_boiler > 0, "No coal found in the boiler. Setup verification failed."
print("Coal found in the boiler")

print("\nSetup verification complete. Automated coal mining system established successfully.")
