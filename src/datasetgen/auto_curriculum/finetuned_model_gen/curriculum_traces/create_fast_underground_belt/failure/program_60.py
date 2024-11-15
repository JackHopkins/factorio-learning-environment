

from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- fast-underground-belt
- iron-gear-wheel
- underground-belt

"""
# Get the recipes for the required items
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipes
print("fast-underground-belt recipe:")
print(fast_underground_belt_recipe)
print("\niron-gear-wheel recipe:")
print(iron_gear_wheel_recipe)
print("\nunderground-belt recipe:")
print(underground_belt_recipe)


"""
Step 2: Gather raw resources. We need to gather the following resources:
- Iron ore (at least 80)
- Coal (at least 20 for smelting)
- Stone (at least 5 for crafting a stone furnace)
"""

# Define required quantities
required_iron_ore = 80
required_coal = 20
required_stone = 5

# Helper function to gather resources
def gather_resource(resource_type, required_quantity):
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Verify that we gathered enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    print(f"Gathered {actual_quantity} of {resource_type}")
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

# Gather Iron Ore
gather_resource(Resource.IronOre, required_iron_ore)

# Gather Coal
gather_resource(Resource.Coal, required_coal)

# Gather Stone
gather_resource(Resource.Stone, required_stone)

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert final quantities
assert final_inventory.get(Resource.IronOre, 0) >= required_iron_ore, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= required_coal, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= required_stone, "Not enough Stone"

print("Successfully gathered all required resources!")


"""
Step 3: Craft and set up smelting infrastructure. We need to craft and set up the following:
- 1 Stone Furnace
- Place the Stone Furnace
- Add coal to the Stone Furnace as fuel
- Smelt iron plates (at least 80)

"""
# Craft 1 Stone Furnace
print("Crafting Stone Furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
print("Stone Furnace crafted successfully.")

# Place the Stone Furnace
move_to(Position(x=0, y=0))  # Move to origin for placing
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print("Stone Furnace placed successfully.")

# Add coal to the Stone Furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")

fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print("Inserted coal into the Stone Furnace.")

# Verify that coal was successfully inserted
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel Stone Furnace"
print(f"Stone Furnace fueled with {coal_in_furnace} units of coal.")

# Smelt Iron Plates (at least 80)
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

# Insert all available Iron Ore into the Furnace
updated_furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=iron_ore_in_inventory)
print("Inserted Iron Ore into the Stone Furnace.")

# Wait for smelting process to complete
smelting_time_per_unit = 0.7  # Estimated time per unit
total_smelting_time = smelting_time_per_unit * min(80, iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract Iron Plates from Furnace
max_attempts_to_extract = 10
for _ in range(max_attempts_to_extract):
    # Attempt to extract all possible units at once
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=80)
    
    # Check how many are now in inventory
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    
    # If we've reached our target or exceeded it, break out of loop
    if iron_plates_in_inventory >= 80:
        break
    
    sleep(10)  # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_in_inventory}")
assert iron_plates_in_inventory >= 80, f"Failed to smelt enough Iron Plates; Expected: >=80, Actual: {iron_plates_in_inventory}"

print("Successfully crafted and set up smelting infrastructure.")


"""
Step 4: Craft intermediate components. We need to craft the following intermediate components:
- 40 Iron Gear Wheels (requires 80 iron plates)

"""
# Craft 40 Iron Gear Wheels
print("Crafting 40 Iron Gear Wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels.")

# Verify that we have crafted enough
gear_wheels_in_inventory = inspect_inventory()[Prototype.IronGearWheel]
assert gear_wheels_in_inventory >= 40, f"Failed to craft enough Iron Gear Wheels; Expected: >=40, Actual: {gear_wheels_in_inventory}"

print("Successfully crafted all intermediate components.")


"""
Step 5: Craft underground belts. We need to craft the following:
- 2 Underground Belts (requires 80 iron plates and 40 iron gear wheels)

"""
# Print current inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Assert that we have enough Iron Plates and Iron Gear Wheels
assert current_inventory[Prototype.IronPlate] >= 80, f"Not enough Iron Plates; Expected: >=80, Actual: {current_inventory[Prototype.IronPlate]}"
assert current_inventory[Prototype.IronGearWheel] >= 40, f"Not enough Iron Gear Wheels; Expected: >=40, Actual: {current_inventory[Prototype.IronGearWheel]}"

# Craft 2 Underground Belts
print("Crafting 2 Underground Belts...")
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belts.")

# Verify that we have crafted enough
underground_belts_in_inventory = inspect_inventory()[Prototype.UndergroundBelt]
assert underground_belts_in_inventory >= 2, f"Failed to craft enough Underground Belts; Expected: >=2, Actual: {underground_belts_in_inventory}"

print("Successfully crafted 2 Underground Belts.")


"""
Step 6: Craft fast-underground-belt. We need to craft the following:
- 1 Fast Underground Belt (requires 80 iron plates and 40 iron gear wheels)

"""
# Print current inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Assert that we have enough materials
assert current_inventory[Prototype.IronPlate] >= 80, f"Not enough Iron Plates; Expected: >=80, Actual: {current_inventory[Prototype.IronPlate]}"
assert current_inventory[Prototype.IronGearWheel] >= 40, f"Not enough Iron Gear Wheels; Expected: >=40, Actual: {current_inventory[Prototype.IronGearWheel]}"
assert current_inventory[Prototype.UndergroundBelt] >= 2, f"Not enough Underground Belts; Expected: >=2, Actual: {current_inventory[Prototype.UndergroundBelt]}"

# Craft 1 Fast Underground Belt
print("Crafting 1 Fast Underground Belt...")
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} Fast Underground Belt.")

# Verify that we have crafted one
fast_underground_belts_in_inventory = inspect_inventory()[Prototype.FastUndergroundBelt]
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft Fast Underground Belt; Expected: >=1, Actual: {fast_underground_belts_in_inventory}"

print("Successfully crafted 1 Fast Underground Belt.")


"""
Step 7: Verify the craft. We need to verify that we have crafted the fast-underground-belt by checking our inventory.
"""
# Check final inventory for Fast Underground Belt
final_inventory = inspect_inventory()
fast_underground_belts_in_inventory = final_inventory[Prototype.FastUndergroundBelt]

print(f"Final Inventory: {final_inventory}")
print(f"Fast Underground Belts in Inventory: {fast_underground_belts_in_inventory}")

# Assert that we have at least one Fast Underground Belt
assert fast_underground_belts_in_inventory >= 1, f"Expected at least 1 Fast Underground Belt; Found: {fast_underground_belts_in_inventory}"

print("Successfully verified the presence of a crafted Fast Underground Belt.")


