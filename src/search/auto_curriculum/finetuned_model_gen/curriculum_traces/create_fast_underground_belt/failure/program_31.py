
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the main objective items and intermediate items.
"""
# Print recipe for fast-underground-belt
print("Recipe for fast-underground-belt:")
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(fast_underground_belt_recipe)

# Print recipe for iron-gear-wheel
print("Recipe for iron-gear-wheel:")
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(iron_gear_wheel_recipe)

# Print recipe for underground-belt
print("Recipe for underground-belt:")
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(underground_belt_recipe)

# Print recipe for stone-furnace (for smelting)
print("Recipe for stone-furnace:")
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(stone_furnace_recipe)

"""
Step 2: Gather raw resources. We need to mine iron ore, coal, and stone.
- Iron ore: At least 4 for the iron gear wheels
- Coal: At least 2 for fuel
- Stone: At least 5 for crafting a stone furnace
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 4),
    (Resource.Coal, 2),
    (Resource.Stone, 5)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")
    
    # Verify that we have harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources.")
print(f"Final inventory: {inspect_inventory()}")

# Final assertion to check if we have all required resources
final_inventory = inspect_inventory()
assert final_inventory.get(Resource.IronOre, 0) >= 4, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("All required resources successfully gathered and verified.")

"""
Step 3: Craft and set up the stone furnace.
- Craft 1 stone furnace
- Place the stone furnace
"""
# Craft 1 stone furnace
print("Crafting 1 stone furnace...")
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)
assert crafted_furnaces == 1, f"Failed to craft stone furnace. Expected to craft 1, but crafted {crafted_furnaces}"
print("Successfully crafted 1 stone furnace.")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

"""
Step 4: Smelt iron plates.
- Use the stone furnace to smelt iron ore into iron plates
"""
# Insert coal as fuel into the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal in inventory before insertion: {coal_in_inventory}")
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print("Inserted coal into the stone furnace.")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore in inventory before insertion: {iron_ore_in_inventory}")
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print("Inserted iron ore into the stone furnace.")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory
print(f"Waiting {smelting_time} seconds for smelting to complete.")
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    if iron_plates_in_inventory >= 4:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted iron plates; current inventory count: {iron_plates_in_inventory}")

# Verify that we have at least 4 iron plates
assert iron_plates_in_inventory >= 4, f"Failed to obtain required number of iron plates. Expected at least 4 but got {iron_plates_in_inventory}"

# Check final inventory state
final_inventory_state = inspect_inventory()
print(f"Final inventory state after smelting: {final_inventory_state}")
assert final_inventory_state[Prototype.IronPlate] >= 4, "Not enough Iron Plates"
print("Successfully completed smelting process and obtained required number of Iron Plates.")

"""
Step 5: Craft intermediate items.
- Craft 40 iron gear wheels
- Craft 2 underground-belts
"""
# Craft iron gear wheels
print("Crafting 40 iron gear wheels...")
crafted_iron_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_iron_gear_wheels} iron gear wheels.")
print(f"Inventory after crafting iron gear wheels: {inspect_inventory()}")

# Craft underground-belts
print("Crafting 2 underground-belts...")
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} underground-belts.")
print(f"Inventory after crafting underground-belts: {inspect_inventory()}")

# Verify that we have crafted the correct number of each item
current_inventory = inspect_inventory()
assert current_inventory[Prototype.IronGearWheel] >= 40, f"Failed to craft required number of iron gear wheels. Expected: 40, Actual: {current_inventory[Prototype.IronGearWheel]}"
assert current_inventory[Prototype.UndergroundBelt] >= 2, f"Failed to craft required number of underground-belts. Expected: 2, Actual: {current_inventory[Prototype.UndergroundBelt]}"

print("Successfully crafted all intermediate items.")

"""
Step 6: Craft the fast-underground-belt.
- Craft 1 fast-underground-belt using the crafted iron gear wheels and underground-belt
"""
# Craft 1 fast-underground-belt
print("Crafting 1 fast-underground-belt...")
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} fast-underground-belt.")
print(f"Inventory after crafting fast-underground-belt: {inspect_inventory()}")

# Verify that we have crafted the correct number of fast-underground-belts
current_inventory = inspect_inventory()
assert current_inventory[Prototype.FastUndergroundBelt] >= 1, f"Failed to craft required number of fast-underground-belts. Expected: 1, Actual: {current_inventory[Prototype.FastUndergroundBelt]}"

print("Successfully crafted a fast-underground-belt.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting fast-underground-belt: {final_inventory}")

# Check if we have at least 1 fast-underground-belt
assert final_inventory[Prototype.FastUndergroundBelt] >= 1, "Failed to craft required number of fast-underground-belts"
print("Successfully completed all steps and crafted a fast-underground-belt.")

