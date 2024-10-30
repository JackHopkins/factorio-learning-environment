from factorio_instance import *

"""
Main Objective: We need 10 copper cables. The final success should be checked by looking if 10 copper cables are in inventory
"""



"""
Step 1: Gather raw resources
- Move to the nearest coal patch and mine at least 10 coal
- Move to the nearest copper ore patch and mine at least 10 copper ore
OUTPUT CHECK: Verify that we have at least 10 coal and 10 copper ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Gather raw resources

# Function to mine a resource
def mine_resource(resource: Resource, amount: int):
    resource_position = nearest(resource)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, amount)
    current_amount = inspect_inventory()[resource]
    assert current_amount >= amount, f"Failed to mine enough {resource}. Expected {amount}, but got {current_amount}"
    print(f"Mined {harvested} {resource}")

# Mine coal
mine_resource(Resource.Coal, 10)

# Mine copper ore
mine_resource(Resource.CopperOre, 10)

# Verify final inventory
inventory = inspect_inventory()
assert inventory[Resource.Coal] >= 10, f"Not enough coal. Expected at least 10, but got {inventory[Resource.Coal]}"
assert inventory[Resource.CopperOre] >= 10, f"Not enough copper ore. Expected at least 10, but got {inventory[Resource.CopperOre]}"

print(f"Current inventory: {inventory}")


"""
Step 2: Fuel and use the existing furnace
- Move to the stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
- Add copper ore to the furnace for smelting
OUTPUT CHECK: Verify that the furnace is operational (has fuel and ingredients)
"""
# Inventory at the start of step {'coal': 10, 'copper-ore': 10}
#Step Execution

# Move to the stone furnace location
furnace_position = Position(x=-12.0, y=-12.0)
move_to(furnace_position)

# Get the stone furnace entity from its known position
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

if not stone_furnace:
    raise Exception("Stone Furnace not found at expected position.")

print(f"Located Stone Furnace at {stone_furnace.position}")

# Add coal as fuel into the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
stone_furnace = insert_item(Prototype.Coal, stone_furnace, coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into the furnace")

# Add copper ore into the furnace for smelting
copper_ore_in_inventory = inspect_inventory()[Prototype.CopperOre]
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} units of copper ore into the furnace")

# Wait a bit for the furnace to update its status
sleep(1)

# Verify that the furnace is operational (has fuel and ingredients)
max_attempts = 5
for attempt in range(max_attempts):
    # Get the updated furnace entity
    stone_furnaces = get_entities({Prototype.StoneFurnace})
    stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)
    
    if stone_furnace is None:
        raise Exception("Stone Furnace not found after inserting items.")
    
    # Check if the furnace has fuel and ingredients
    has_fuel = stone_furnace.fuel.get(Prototype.Coal, 0) > 0
    has_ingredients = stone_furnace.furnace_source.get(Prototype.CopperOre, 0) > 0
    
    if has_fuel and has_ingredients:
        print("Furnace is now operational with both fuel and ingredients.")
        break
    else:
        if attempt < max_attempts - 1:
            print(f"Furnace not ready yet. Retrying in 1 second... (Attempt {attempt + 1}/{max_attempts})")
            sleep(1)
        else:
            raise Exception("Failed to verify furnace operation after multiple attempts.")

# Final assertion
assert has_fuel and has_ingredients, "Furnace is not operational. Missing fuel or ingredients."


"""
Step 3: Collect smelted copper plates
- Wait for the furnace to smelt the copper ore into copper plates
- Collect the copper plates from the furnace
OUTPUT CHECK: Verify that we have at least 5 copper plates in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Wait time per unit of ore smelted (0.7 seconds per unit)
copper_ore_in_furnace = stone_furnace.furnace_source.get(Prototype.CopperOre, 0)
smelting_time = copper_ore_in_furnace * 0.7

print(f"Waiting {smelting_time} seconds for smelting...")
sleep(smelting_time)

# Attempt to extract all available copper plates
max_attempts = 5
for attempt in range(max_attempts):
    # Extract as many copper plates as possible
    extracted_copper_plates = extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_in_furnace)
    
    # Check current inventory for number of copper plates
    current_copper_plates = inspect_inventory()[Prototype.CopperPlate]
    
    print(f"Attempt {attempt + 1}: Extracted {extracted_copper_plates} copper plates.")
    print(f"Current inventory has {current_copper_plates} copper plates.")

    if current_copper_plates >= 5:
        break
    
    if attempt < max_attempts - 1:
        print("Not enough copper plates yet, waiting a bit longer...")
        sleep(10) # Wait some more time before trying again

# Final check on inventory
assert current_copper_plates >= 5, f"Failed to collect enough copper plates. Expected at least 5 but got {current_copper_plates}"

print("Successfully collected at least 5 copper plates.")


"""
Step 4: Craft copper cables
- Use the crafting menu to craft copper cables (2 copper cables per 1 copper plate)
- Craft until we have at least 10 copper cables
OUTPUT CHECK: Verify that we have at least 10 copper cables in the inventory

##
"""
# Placeholder 4