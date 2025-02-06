
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft. In this case, we need to print the recipes for:
- Fast-underground-belt
- Underground-belt
- Iron gear wheel (as it's used in both underground-belt and transport-belt)

"""
# Print the recipe for fast-underground-belt
print("Recipe for fast-underground-belt:")
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(fast_underground_belt_recipe)

# Print the recipe for underground-belt
print("\nRecipe for underground-belt:")
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(underground_belt_recipe)

# Print the recipe for iron gear wheel
print("\nRecipe for iron gear wheel:")
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(iron_gear_wheel_recipe)

# Print the recipe for transport belt
print("\nRecipe for transport belt:")
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(transport_belt_recipe)


"""
Step 2: Gather resources. We need to gather the following resources:
- Iron ore (at least 8, as we need 8 iron plates for this recipe)
- Coal (at least 5, as we need to fuel the furnace)
- Stone (at least 5, as we need to craft a stone furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 10),  # We need at least 8 iron ore
    (Resource.Coal, 10),     # We need at least 5 coal
    (Resource.Stone, 5)      # We need exactly 5 stone for the furnace
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    inventory = inspect_inventory()
    actual_quantity = inventory.get(resource_type, 0)
    
    # Print the result
    print(f"Harvested {actual_quantity} of {resource_type[0]}")
    
    # Assert that we have harvested at least the required quantity
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type[0]}"
    
print("Successfully gathered all necessary resources.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have all required resources
assert final_inventory.get(Resource.IronOre, 0) >= 8, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 5, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all necessary resources.")

"""
Step 3: Craft a stone furnace. We need to craft a stone furnace using the 5 stone we gathered.
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnace(s)")

# Check the inventory to confirm we have a stone furnace
current_inventory = inspect_inventory()
furnaces_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)
assert furnaces_in_inventory >= 1, "Failed to craft a stone furnace"

print(f"Current inventory after crafting: {current_inventory}")

"""
Step 4: Place the stone furnace and smelt iron plates. We need to:
- Place the stone furnace
- Fuel it with coal
- Smelt the iron ore into at least 8 iron plates
"""
# Move to a suitable position to place the furnace
move_to(Position(x=0, y=0))

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Insert coal into the furnace as fuel
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=5)
print(f"Inserted {coal_inserted} coal into the furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
iron_ore_inserted = insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_inserted} iron ore into the furnace")

# Wait for smelting to complete (assuming 3.2 seconds per iron plate)
sleep(3.2 * iron_ore_inserted)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_inserted)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    
    if iron_plates_in_inventory >= 8:
        break
    
    sleep(5)

print(f"Extracted {iron_plates_in_inventory} iron plates from the furnace")

# Final assertion to ensure we have enough iron plates
assert iron_plates_in_inventory >= 8, f"Failed to obtain required number of iron plates. Current count: {iron_plates_in_inventory}"

# Print final inventory state
final_inventory_state = inspect_inventory()
print(f"Final inventory state: {final_inventory_state}")

print("Successfully placed furnace and smelted iron plates.")

"""
Step 5: Craft intermediate items. We need to craft the following intermediate items:
- 2 iron gear wheels (for the underground belts)
- 1 transport belt
"""
# Craft 2 iron gear wheels
iron_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=2)
print(f"Crafted {iron_gear_wheels} iron gear wheels")

# Craft 1 transport belt
transport_belts = craft_item(Prototype.TransportBelt, quantity=1)
print(f"Crafted {transport_belts} transport belts")

# Check the inventory to confirm we have crafted the necessary items
current_inventory = inspect_inventory()
print(f"Current inventory after crafting intermediate items: {current_inventory}")

# Assert that we have crafted the necessary number of each item
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 2, "Failed to craft required number of Iron Gear Wheels"
assert current_inventory.get(Prototype.TransportBelt, 0) >= 1, "Failed to craft required number of Transport Belts"

print("Successfully crafted all intermediate items.")

"""
Step 6: Craft underground-belts. We need to craft 2 underground-belts
"""
# Craft 2 underground belts
underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {underground_belts} underground belts")

# Check the inventory to confirm we have crafted the necessary number of underground belts
current_inventory = inspect_inventory()
print(f"Current inventory after crafting underground belts: {current_inventory}")

# Assert that we have crafted the necessary number of underground belts
assert current_inventory.get(Prototype.UndergroundBelt, 0) >= 2, "Failed to craft required number of Underground Belts"

print("Successfully crafted 2 underground belts.")

"""
Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt using the 2 underground-belts
"""
# Craft 1 fast-underground-belt
fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {fast_underground_belts} fast-underground-belt")

# Check the inventory to confirm we have crafted the necessary number of fast-underground-belts
current_inventory = inspect_inventory()
print(f"Current inventory after crafting fast-underground-belt: {current_inventory}")

# Assert that we have crafted the necessary number of fast-underground-belts
assert current_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft required number of Fast Underground Belts"

print("Successfully crafted 1 fast-underground-belt.")

