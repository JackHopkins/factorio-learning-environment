from factorio_instance import *

"""
Main Objective: We need 10 copper cables. The final success should be checked by looking if 10 copper cables are in inventory
"""



"""
Step 1: Gather raw resources
- Mine coal (at least 5 pieces for furnace fuel)
- Mine copper ore (at least 5 pieces, as we need 5 copper plates for 10 copper cables)
OUTPUT CHECK: Verify that we have at least 5 coal and 5 copper ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define required quantities
required_coal = 5
required_copper_ore = 5

# Gather Coal
print("Gathering Coal...")
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvested_coal = harvest_resource(coal_position, required_coal)

# Check if we have harvested enough coal
inventory_after_coal = inspect_inventory()
coal_in_inventory = inventory_after_coal.get(Prototype.Coal, 0)
assert coal_in_inventory >= required_coal, f"Failed to gather enough coal. Expected {required_coal}, but got {coal_in_inventory}"
print(f"Successfully gathered {coal_in_inventory} pieces of coal.")

# Gather Copper Ore
print("Gathering Copper Ore...")
copper_ore_position = nearest(Resource.CopperOre)
move_to(copper_ore_position)
harvested_copper_ore = harvest_resource(copper_ore_position, required_copper_ore)

# Check if we have harvested enough copper ore
inventory_after_copper_ore = inspect_inventory()
copper_ore_in_inventory = inventory_after_copper_ore.get(Prototype.CopperOre, 0)
assert copper_ore_in_inventory >= required_copper_ore, f"Failed to gather enough copper ore. Expected {required_copper_ore}, but got {copper_ore_in_inventory}"
print(f"Successfully gathered {copper_ore_in_inventory} pieces of copper ore.")

final_inventory_check = inspect_inventory()
print(f"Final Inventory: {final_inventory_check}")


"""
Step 2: Fuel the furnace
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace
OUTPUT CHECK: Verify that the furnace status changes from NO_FUEL to IDLE
"""
# Inventory at the start of step {'coal': 5, 'copper-ore': 5}
#Step Execution

# Step 2: Fueling the Furnace

# Define position for existing stone furnace
furnace_position = Position(x=-12.0, y=-12.0)

# Move near to the stone furnace
print(f"Moving to stone furnace at {furnace_position}")
move_to(furnace_position)

# Get current inventory details for logging purposes
inventory_before_fueling = inspect_inventory()
coal_in_inventory = inventory_before_fueling.get(Prototype.Coal, 0)
print(f"Coal available in inventory before fueling: {coal_in_inventory}")

# Retrieve entity information for existing stone-furnace on map
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

if not stone_furnace:
    raise Exception("Stone Furnace not found!")

# Insert all available coal into the Stone Furnace
stone_furnace = insert_item(Prototype.Coal, target=stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} pieces of coal into Stone Furnace.")

# Inspect updated status after fueling process
updated_stone_furnaces = get_entities({Prototype.StoneFurnace})
updated_stone_furnace = next((f for f in updated_stone_furnaces if f.position.is_close(furnace_position)), None)

if not updated_stone_furnace:
    raise Exception("Updated Stone Furnace not found!")

assert updated_stone_furnace.status != EntityStatus.NO_FUEL, "Failed to fuel Stone Furnace; still showing NO_FUEL."

print("Successfully fueled Stone Furnace.")


"""
Step 3: Smelt copper plates
- Add copper ore to the furnace
- Wait for the smelting process to complete (5 copper ore should produce 5 copper plates)
OUTPUT CHECK: Verify that we have at least 5 copper plates in the inventory
"""
# Inventory at the start of step {'copper-ore': 5}
#Step Execution

# Step 3: Smelt Copper Plates

# Move near to the stone furnace
print(f"Moving to stone furnace at {furnace_position}")
move_to(furnace_position)

# Get current inventory details for logging purposes
inventory_before_smelting = inspect_inventory()
copper_ore_in_inventory = inventory_before_smelting.get(Prototype.CopperOre, 0)
print(f"Copper ore available in inventory before smelting: {copper_ore_in_inventory}")

# Retrieve entity information for existing stone-furnace on map
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

if not stone_furnace:
    raise Exception("Stone Furnace not found!")

# Insert all available copper ore into the Stone Furnace
stone_furnace = insert_item(Prototype.CopperOre, target=stone_furnace, quantity=copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} pieces of copper ore into Stone Furnace.")

# Wait for smelting process (approximately 0.7 seconds per piece of copper ore)
sleep(copper_ore_in_inventory * 0.7)

max_attempts = 5
for _ in range(max_attempts):
    # Attempt to extract exactly as many copper plates as there were ores inserted.
    extract_item(Prototype.CopperPlate, stone_furnace.position, copper_ore_in_inventory)
    
    # Check how many copper plates are now in your inventory.
    current_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)
    
    # If you have enough plates (i.e., more or equal than expected), break out of loop.
    if current_copper_plate_count >= copper_ore_in_inventory:
        break
    
    sleep(10)  # Wait a bit more if not all plates are ready yet

print(f"Extracted {current_copper_plate_count} copper plates from the furnace")
print(f"Inventory after extracting: {inspect_inventory()}")

# Verify that we have at least as many copper plates as there were ores inserted.
assert current_copper_plate_count >= copper_ore_in_inventory, (
    f"Failed to produce enough copper plates. Expected at least {copper_ore_in_inventory}, "
    f"but got {current_copper_plate_count}"
)

print("Successfully completed smelting step with required number of Copper Plates.")


"""
Step 4: Craft copper cables
- Craft copper cables using the recipe: 1 copper plate produces 2 copper cables
- Repeat the crafting process 5 times to get 10 copper cables
OUTPUT CHECK: Verify that we have 10 copper cables in the inventory

##
"""
# Inventory at the start of step {'copper-plate': 5}
#Step Execution

# Step 4: Craft Copper Cables

# Define how many crafts we need
required_crafts = 5

print("Starting to craft Copper Cables...")

# Perform the crafting process
for _ in range(required_crafts):
    # Craft a pair of copper cables from one copper plate
    crafted_quantity = craft_item(Prototype.CopperCable, quantity=1)
    print(f"Crafted {crafted_quantity} Copper Cable(s)")

# Check final inventory for verification
final_inventory = inspect_inventory()
copper_cable_count = final_inventory.get(Prototype.CopperCable, 0)

# Verify that we have at least 10 Copper Cables as required
assert copper_cable_count >= 10, f"Failed to craft enough Copper Cables. Expected at least 10, but got {copper_cable_count}"
print("Successfully crafted the required number of Copper Cables.")
