
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft:
- fast-transport-belt
- transport-belt
- iron-gear-wheel
- stone-furnace
"""
# Define the recipes for the items we need to craft
recipes = {
    "fast-transport-belt": get_prototype_recipe(Prototype.FastTransportBelt),
    "transport-belt": get_prototype_recipe(Prototype.TransportBelt),
    "iron-gear-wheel": get_prototype_recipe(Prototype.IronGearWheel),
    "stone-furnace": get_prototype_recipe(Prototype.StoneFurnace)
}

# Print the recipes
print("Recipes:")
for item, recipe in recipes.items():
    print(f"\n{item}:")
    print(f"Ingredients: {recipe.ingredients}")
    print(f"Products: {recipe.products}")
    print(f"Energy: {recipe.energy}")
    print(f"Category: {recipe.category}")
    print(f"Enabled: {recipe.enabled}")

"""
Step 2: Gather resources. We need to gather the following resources:
- stone (at least 12 for 2 stone furnaces)
- coal (at least 2 for fueling the furnaces)
- iron ore (at least 31 for iron plates)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.Coal, 2),
    (Resource.IronOre, 31)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the required quantity of this resource
    harvested_quantity = harvest_resource(resource_position, required_quantity)
    
    # Print out what we did
    print(f"Harvested {harvested_quantity} of {resource_type}")
    
    # Check inventory to ensure we have what we need
    current_inventory = inspect_inventory()
    assert current_inventory[resource_type] >= required_quantity, f"Failed to gather enough {resource_type}"

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have at least the required quantities of each resource
assert final_inventory[Resource.Stone] >= 12, "Not enough Stone"
assert final_inventory[Resource.Coal] >= 2, "Not enough Coal"
assert final_inventory[Resource.IronOre] >= 31, "Not enough Iron Ore"

print("Successfully gathered all necessary resources!")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""

# Craft the stone furnaces using gathered stone
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Verify that we have the stone furnaces in our inventory
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting[Prototype.StoneFurnace] >= 2, "Failed to craft required number of Stone Furnaces"
print("Successfully crafted and verified presence of Stone Furnaces!")

"""
Step 4: Set up smelting operation. We need to set up a smelting operation to produce iron plates:
- Place a stone furnace
- Fuel it with coal
- Smelt iron ore into iron plates (at least 18 initially for the first few crafts)
"""

# Place the first stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace.")

# Insert iron ore into the furnace for smelting
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=18)
print("Inserted iron ore into the stone furnace.")

# Sleep for a while to allow smelting to occur
sleep(10)

# Extract iron plates from the furnace
extracted_plates = extract_item(Prototype.IronPlate, updated_furnace.position, quantity=18)
print(f"Extracted {extracted_plates} iron plates from the stone furnace.")

# Verify that we have the iron plates in our inventory
inventory_after_extraction = inspect_inventory()
assert inventory_after_extraction[Prototype.IronPlate] >= 18, "Failed to obtain required number of Iron Plates"

print("Successfully set up smelting operation and obtained initial batch of Iron Plates!")

"""
Step 5: Craft intermediate items. We need to craft the following intermediate items:
- 3 iron gear wheels (1 for the fast-transport-belt, 2 for the transport belt)
"""
# Print the recipe for Iron Gear Wheel
recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {recipe}")

# Craft Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=3)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Verify that we have the Iron Gear Wheels in our inventory
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting[Prototype.IronGearWheel] >= 3, "Failed to craft required number of Iron Gear Wheels"

print("Successfully crafted and verified presence of Iron Gear Wheels!")

"""
Step 6: Craft transport belt. We need to craft 1 transport belt.
"""
# Print the recipe for Transport Belt
recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Transport Belt Recipe: {recipe}")

# Craft Transport Belt
crafted_transport_belt = craft_item(Prototype.TransportBelt, quantity=1)
print(f"Crafted {crafted_transport_belt} Transport Belt")

# Verify that we have the Transport Belt in our inventory
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting[Prototype.TransportBelt] >= 1, "Failed to craft required number of Transport Belts"

print("Successfully crafted and verified presence of Transport Belts!")

"""
Step 7: Craft fast-transport-belt. We need to craft 1 fast-transport-belt using the iron gear wheel and transport belt.
"""
# Print the recipe for Fast Transport Belt
recipe = get_prototype_recipe(Prototype.FastTransportBelt)
print(f"Fast Transport Belt Recipe: {recipe}")

# Craft Fast Transport Belt
crafted_fast_transport_belt = craft_item(Prototype.FastTransportBelt, quantity=1)
print(f"Crafted {crafted_fast_transport_belt} Fast Transport Belt")

# Verify that we have the Fast Transport Belt in our inventory
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting[Prototype.FastTransportBelt] >= 1, "Failed to craft required number of Fast Transport Belts"

print("Successfully crafted and verified presence of Fast Transport Belts!")

"""
Step 8: Verify success. Check the inventory to ensure we have at least 1 fast-transport-belt.
"""

# Check the current inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Verify that we have at least one Fast Transport Belt
assert current_inventory[Prototype.FastTransportBelt] >= 1, "Failed to craft required number of Fast Transport Belts"
print("Successfully verified presence of Fast Transport Belts in inventory!")

# Print success message
print("Successfully completed all steps to craft Fast Transport Belt!")

