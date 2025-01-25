
from factorio_instance import *

"""
Create an automated iron ore mining setup with 2 burner mining drills: 
one feeding into a wooden chest 10 tiles away, and another feeding into a stone furnace 8 tiles away to produce iron plates.
"""

"""
Step 1: Place the burner mining drills on an iron ore patch
"""

# Find the nearest iron ore patch
iron_ore_position = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position.bounding_box.center())
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position.bounding_box.center())
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
Step 2: Place the wooden chest and stone furnace
"""

# Calculate positions for chest and furnace
chest_position = Position(x=drill1.position.x + 10, y=drill1.position.y)
furnace_position = Position(x=drill2.position.x + 8, y=drill2.position.y)

# Place the wooden chest
move_to(chest_position)
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Place the stone furnace
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

# Fuel the furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace"
print("Stone furnace successfully placed and fueled")

"""
Step 3: Set up the burner inserters
"""

# Place and fuel inserter for the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.RIGHT)
chest_inserter = rotate_entity(chest_inserter, Direction.LEFT)
fueled_chest_inserter = insert_item(Prototype.Coal, chest_inserter, quantity=10)
coal_in_chest_inserter = fueled_chest_inserter.fuel.get(Prototype.Coal, 0)
assert coal_in_chest_inserter > 0, "Failed to fuel chest inserter"
print("Chest inserter placed and fueled")

# Place and fuel inserter for the furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.RIGHT)
furnace_inserter = rotate_entity(furnace_inserter, Direction.LEFT)
fueled_furnace_inserter = insert_item(Prototype.Coal, furnace_inserter, quantity=10)
coal_in_furnace_inserter = fueled_furnace_inserter.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace_inserter > 0, "Failed to fuel furnace inserter"
print("Furnace inserter placed and fueled")

"""
Step 4: Connect the drills to the inserters using transport belts
"""

# Connect first drill to chest inserter
chest_belts = connect_entities(fueled_drill1.drop_position, fueled_chest_inserter.pickup_position, Prototype.TransportBelt)
assert chest_belts, "Failed to connect first drill to chest inserter with transport belts"

# Connect second drill to furnace inserter
furnace_belts = connect_entities(fueled_drill2.drop_position, fueled_furnace_inserter.pickup_position, Prototype.TransportBelt)
assert furnace_belts, "Failed to connect second drill to furnace inserter with transport belts"

print("Successfully connected drills to inserters with transport belts")

"""
Step 5: Verify the setup
"""

print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Check wooden chest for iron ore
move_to(chest.position)
updated_chest = get_entity(Prototype.WoodenChest, chest.position)
chest_inventory = inspect_inventory(updated_chest)
iron_ore_count = chest_inventory.get(Prototype.IronOre, 0)
print(f"Iron ore in the wooden chest: {iron_ore_count}")
assert iron_ore_count > 0, "No iron ore found in the wooden chest. Setup verification failed."

# Check furnace for iron plates
move_to(furnace.position)
updated_furnace = get_entity(Prototype.StoneFurnace, furnace.position)
furnace_inventory = inspect_inventory(updated_furnace)
iron_plate_count = furnace_inventory.get(Prototype.IronPlate, 0)
print(f"Iron plates in the furnace: {iron_plate_count}")
assert iron_plate_count > 0, "No iron plates found in the furnace. Setup verification failed."

print("\nSetup verification complete. Automated iron ore mining and smelting system is operational.")
