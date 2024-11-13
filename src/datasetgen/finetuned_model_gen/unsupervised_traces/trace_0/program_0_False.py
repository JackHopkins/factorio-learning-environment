

from factorio_instance import *


"""
Step 1: Place a burner mining drill on an iron ore patch
"""
# Find nearest iron ore patch
iron_position = nearest(Resource.IronOre)
assert iron_position, "No iron ore patch found"

# Move to iron ore patch
move_to(iron_position)

# Place burner mining drill on iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)
assert drill, f"Failed to place burner mining drill at {iron_position}"
print(f"Placed burner mining drill at {drill.position}")

"""
Step 2: Fuel the burner mining drill
"""
# Find nearest coal patch
coal_position = nearest(Resource.Coal)
assert coal_position, "No coal patch found"

# Move to coal patch
move_to(coal_position)

# Mine coal for fuel
coal_mined = harvest_resource(coal_position, quantity=10)
assert coal_mined >= 10, f"Failed to mine enough coal; only got {coal_mined}"
print(f"Mined {coal_mined} coal")

# Move back to drill position
move_to(drill.position)

# Insert coal into the burner mining drill
fueled_drill = insert_item(Prototype.Coal, drill, quantity=10)
assert fueled_drill.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel burner mining drill"
print("Successfully fueled burner mining drill")

"""
Step 3: Connect the drill to a stone furnace
"""
# Find the stone furnace at position (10.0, -16.0)
furnace_pos = Position(x=10.0, y=-16.0)
furnace = get_entity(Prototype.StoneFurnace, position=furnace_pos)
assert furnace, "No stone furnace found at specified location"
print(f"Found stone furnace at {furnace.position}")

# Move to the furnace position
move_to(furnace.position)

# Fuel the stone furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=10)
assert fueled_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel stone furnace"
print("Successfully fueled stone furnace")

# Place an inserter next to the furnace
inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.LEFT)
assert inserter, "Failed to place inserter"
print(f"Placed inserter at {inserter.position}")

# Rotate the inserter to insert items into the furnace
inserter = rotate_entity(inserter, Direction.RIGHT)
assert inserter.direction == Direction.RIGHT, "Failed to rotate inserter"
print("Successfully rotated inserter")

# Fuel the inserter
fueled_inserter = insert_item(Prototype.Coal, inserter, quantity=5)
assert fueled_inserter.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"
print("Successfully fueled inserter")

# Connect the drill's drop position to the inserter's pickup position with transport belts
belts = connect_entities(fueled_drill.drop_position, fueled_inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to furnace with transport belts"
print("Successfully connected drill to furnace with transport belts")

"""
Step 4: Verify the setup
"""
# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Check the contents of the furnace for iron plates
furnace_inventory = inspect_inventory(fueled_furnace)
iron_plates = furnace_inventory.get(Prototype.IronPlate, 0)
assert iron_plates > 0, "No iron plates found in the furnace. Setup verification failed."
print(f"Setup verification complete. Found {iron_plates} iron plates in the furnace.")

