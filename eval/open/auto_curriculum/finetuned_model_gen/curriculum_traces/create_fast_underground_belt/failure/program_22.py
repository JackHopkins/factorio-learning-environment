
from instance import *


"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt, underground-belt and iron-gear-wheel
"""
# Print recipe for fast-underground-belt
print("fast-underground-belt recipe:")
print("4 iron gear wheels, 2 underground belts")

# Print recipe for underground-belt
print("underground-belt recipe:")
print("10 iron gear wheels, 1 transport belt")

# Print recipe for iron-gear-wheel
print("iron-gear-wheel recipe:")
print("2 iron plates")

"""
Step 2: Gather resources. We need to gather iron ore and coal for smelting
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 100),  # We need a lot of iron ore for plates
    (Resource.Coal, 50)       # We need coal for fueling the furnace
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    # Ensure we have harvested at least the required quantity
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 100, "Not enough Iron Ore in final inventory"
assert final_inventory.get(Resource.Coal, 0) >= 50, "Not enough Coal in final inventory"

"""
Step 3: Craft and set up furnace. We need to craft a stone furnace and set it up for smelting
"""
# We need to craft a stone furnace first
# Crafting requires 5 stone, so we need to gather stone first
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stone = harvest_resource(stone_position, quantity=5)
print(f"Harvested {harvested_stone} stone")

# Craft the stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Check if we have the stone furnace in our inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"

# Place the stone furnace near our current position
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0]+2, y=current_position[1]))
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace for fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_in_furnace} coal into the furnace")
assert coal_in_furnace > 0, "Failed to insert coal into the furnace"

"""
Step 4: Smelt iron plates. We need to smelt iron ore into iron plates
"""
# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore available in inventory: {iron_ore_in_inventory}")

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 seconds per iron ore
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    # Attempt to extract all possible iron plates
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check how many iron plates are now in our inventory
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    
    # If we've extracted all expected plates, break out of the loop early
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    
    sleep(10)  # Wait a bit before trying again

print(f"Extracted {current_iron_plate_count} iron plates from the furnace")

# Final assertion to ensure we have enough iron plates
assert current_iron_plate_count >= 80, f"Failed to obtain enough iron plates; expected at least 80 but got {current_iron_plate_count}"

print("Successfully completed smelting process.")

"""
Step 5: Craft iron gear wheels. We need to craft 40 iron gear wheels
"""
# Calculate the number of iron plates needed
required_iron_plates = 80  # 2 plates per gear wheel

# Check if we have enough iron plates
assert inspect_inventory().get(Prototype.IronPlate, 0) >= required_iron_plates, "Not enough iron plates"

# Craft the iron gear wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gears} iron gear wheels")

# Check if we have the iron gear wheels in our inventory
inventory = inspect_inventory()
iron_gear_wheel_count = inventory.get(Prototype.IronGearWheel, 0)
print(f"Iron gear wheels in inventory: {iron_gear_wheel_count}")

# Assert that we have crafted at least the required number of iron gear wheels
assert iron_gear_wheel_count >= 40, f"Failed to craft enough iron gear wheels; expected at least 40 but got {iron_gear_wheel_count}"

print("Successfully crafted enough iron gear wheels.")

"""
Step 6: Craft underground belts. We need to craft 2 underground belts
"""
# Calculate the number of iron gear wheels needed
required_iron_gears = 20  # 10 gears per underground belt

# Check if we have enough iron gear wheels
assert inspect_inventory().get(Prototype.IronGearWheel, 0) >= required_iron_gears, "Not enough iron gear wheels"

# Craft the underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} underground belts")

# Check if we have the underground belts in our inventory
inventory = inspect_inventory()
underground_belt_count = inventory.get(Prototype.UndergroundBelt, 0)
print(f"Underground belts in inventory: {underground_belt_count}")

# Assert that we have crafted at least the required number of underground belts
assert underground_belt_count >= 2, f"Failed to craft enough underground belts; expected at least 2 but got {underground_belt_count}"

print("Successfully crafted enough underground belts.")

"""
Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt
"""
# Calculate the number of iron gear wheels needed
required_iron_gears = 4  # 4 gears per fast-underground-belt
required_underground_belts = 2  # 2 underground belts per fast-underground-belt

# Check if we have enough iron gear wheels and underground belts
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= required_iron_gears, "Not enough iron gear wheels"
assert inventory.get(Prototype.UndergroundBelt, 0) >= required_underground_belts, "Not enough underground belts"

# Craft the fast-underground-belt
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} fast-underground-belt")

# Check if we have the fast-underground-belt in our inventory
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
print(f"Fast-underground-belt in inventory: {fast_underground_belt_count}")

# Assert that we have crafted at least the required number of fast-underground-belts
assert fast_underground_belt_count >= 1, f"Failed to craft enough fast-underground-belts; expected at least 1 but got {fast_underground_belt_count}"

print("Successfully crafted fast-underground-belt.")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Fast Underground Belt: {final_inventory.get(Prototype.FastUndergroundBelt, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Not enough Fast Underground Belt in final inventory"

