
from factorio_instance import *

"""
Construct an automated iron ore mining facility with 2 burner mining drills: 
one supplying an iron chest 13 tiles away, and another feeding a stone furnace 14 tiles away to create iron gears.
"""

# Step 1: Place the burner mining drills
iron_ore_position = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
print(f"Nearest iron ore found at: {iron_ore_position}")

move_to(iron_ore_position.bounding_box.center())
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place first drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position.bounding_box.center())
print(f"Placed first burner mining drill at: {drill1.position}")

# Fuel first drill
fueled_drill1 = insert_item(Prototype.Coal, drill1, quantity=20)
coal_in_drill1 = fueled_drill1.fuel.get(Prototype.Coal, 0)
assert coal_in_drill1 > 0, "Failed to fuel first drill"

# Place second drill
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=fueled_drill1.position, spacing=1)
print(f"Placed second burner mining drill at: {drill2.position}")

# Fuel second drill
fueled_drill2 = insert_item(Prototype.Coal, drill2, quantity=20)
coal_in_drill2 = fueled_drill2.fuel.get(Prototype.Coal, 0)
assert coal_in_drill2 > 0, "Failed to fuel second drill"

print("Both burner mining drills successfully placed and fueled")

# Step 2: Place the iron chest and stone furnace
chest_position = Position(x=drill1.position.x + 13, y=drill1.position.y)
move_to(chest_position)
chest = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest_position)
print(f"Placed iron chest at: {chest.position}")

furnace_position = Position(x=drill2.position.x + 14, y=drill2.position.y)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

# Fuel the furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace"

# Step 3: Set up the burner inserters
# For the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.LEFT)
chest_inserter = rotate_entity(chest_inserter, Direction.RIGHT)
chest_inserter_fueled = insert_item(Prototype.Coal, chest_inserter, quantity=10)
coal_in_chest_inserter = chest_inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_chest_inserter > 0, "Failed to fuel chest inserter"

# For the furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.LEFT)
furnace_inserter = rotate_entity(furnace_inserter, Direction.RIGHT)
furnace_inserter_fueled = insert_item(Prototype.Coal, furnace_inserter, quantity=10)
coal_in_furnace_inserter = furnace_inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace_inserter > 0, "Failed to fuel furnace inserter"

print("Burner inserters placed and fueled")

# Step 4: Connect the drills to the inserters with transport belts
chest_belts = connect_entities(drill1.drop_position, chest_inserter.pickup_position, Prototype.TransportBelt)
assert chest_belts, "Failed to connect first drill to chest inserter with transport belts"

furnace_belts = connect_entities(drill2.drop_position, furnace_inserter.pickup_position, Prototype.TransportBelt)
assert furnace_belts, "Failed to connect second drill to furnace inserter with transport belts"

print("Successfully connected drills to inserters with transport belts")

# Step 5: Set up assembling machine for iron gears
assembler = place_entity_next_to(Prototype.AssemblingMachine1, furnace.position, direction=Direction.RIGHT, spacing=1)
print(f"Placed assembling machine at: {assembler.position}")

# Set the recipe for iron gears
set_recipe(assembler, Recipe.IronGearWheel)

# Add inserter to move iron plates from furnace to assembler
furnace_to_assembler_inserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, direction=Direction.LEFT)
furnace_to_assembler_inserter = rotate_entity(furnace_to_assembler_inserter, Direction.LEFT)
furnace_to_assembler_inserter_fueled = insert_item(Prototype.Coal, furnace_to_assembler_inserter, quantity=10)
coal_in_furnace_to_assembler_inserter = furnace_to_assembler_inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace_to_assembler_inserter > 0, "Failed to fuel furnace to assembler inserter"

print("Assembling machine set up and connected to furnace")

# Step 6: Verify the setup
print("Waiting for 60 seconds to allow the system to operate...")
sleep(60)
print("60 seconds have passed. Checking the setup now.")

# Check iron chest
move_to(chest.position)
chest = get_entity(Prototype.IronChest, chest.position)
chest_inventory = inspect_inventory(chest)
iron_ore_count = chest_inventory.get(Prototype.IronOre, 0)
print(f"Iron ore in the iron chest: {iron_ore_count}")
assert iron_ore_count > 0, "No iron ore found in the iron chest. Setup verification failed."

# Check furnace
furnace = get_entity(Prototype.StoneFurnace, furnace.position)
furnace_inventory = inspect_inventory(furnace)
iron_plate_count = furnace_inventory.get(Prototype.IronPlate, 0)
print(f"Iron plates in the furnace: {iron_plate_count}")
assert iron_plate_count > 0, "No iron plates found in the furnace. Setup verification failed."

# Check assembling machine
assembler = get_entity(Prototype.AssemblingMachine1, assembler.position)
assembler_inventory = inspect_inventory(assembler)
iron_gear_count = assembler_inventory.get(Prototype.IronGearWheel, 0)
print(f"Iron gears in the assembling machine: {iron_gear_count}")
assert iron_gear_count > 0, "No iron gears found in the assembling machine. Setup verification failed."

print("\nSetup verification complete. Automated iron ore mining facility is operational.")
