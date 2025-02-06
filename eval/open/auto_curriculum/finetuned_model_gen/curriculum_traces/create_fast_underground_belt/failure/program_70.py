
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt, transport-belt, iron-gear-wheel, and stone-furnace
"""
# Get the recipes for the required items
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Print the recipes
print("Fast Underground Belt Recipe:")
print(fast_underground_belt_recipe)
print("\nTransport Belt Recipe:")
print(transport_belt_recipe)
print("\nIron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)
print("\nStone Furnace Recipe:")
print(stone_furnace_recipe)

"""
Step 2: Craft stone-furnace. We need to gather stone and craft a stone-furnace. This is necessary because we need to smelt iron plates for the transport-belt.
"""
# Define the amount of stone needed for the stone-furnace
stone_needed = 5

# Find the nearest stone resource
stone_position = nearest(Resource.Stone)

# Move to the stone resource
move_to(stone_position)

# Harvest the stone
harvested_stone = harvest_resource(stone_position, quantity=stone_needed)

# Verify that we have enough stone
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone) >= stone_needed, f"Failed to harvest enough stone; expected {stone_needed}, got {current_inventory.get(Prototype.Stone)}"

# Craft the stone-furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)

# Verify that we have crafted the stone-furnace
assert crafted_furnaces == 1, f"Failed to craft stone-furnace; expected 1, got {crafted_furnaces}"

# Final inventory check
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.StoneFurnace) >= 1, f"Final inventory check failed; expected at least 1 stone-furnace, got {final_inventory.get(Prototype.StoneFurnace)}"

print("Successfully crafted a stone-furnace")

"""
Step 3: Gather resources. We need to mine iron ore and coal. We need at least 3 iron ore for the iron plates and 1 coal for fuel.
"""
# Define the amount of resources needed
iron_ore_needed = 3
coal_needed = 1

# Find and move to the nearest iron ore deposit
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Mine the iron ore
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=iron_ore_needed)

# Verify that we have enough iron ore
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronOre) >= iron_ore_needed, f"Failed to harvest enough iron ore; expected {iron_ore_needed}, got {current_inventory.get(Prototype.IronOre)}"

# Find and move to the nearest coal deposit
coal_position = nearest(Resource.Coal)
move_to(coal_position)

# Mine the coal
harvested_coal = harvest_resource(coal_position, quantity=coal_needed)

# Verify that we have enough coal
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Coal) >= coal_needed, f"Failed to harvest enough coal; expected {coal_needed}, got {current_inventory.get(Prototype.Coal)}"

# Final inventory check
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.IronOre) >= iron_ore_needed, f"Final inventory check failed; expected at least {iron_ore_needed} iron ore, got {final_inventory.get(Prototype.IronOre)}"
assert final_inventory.get(Prototype.Coal) >= coal_needed, f"Final inventory check failed; expected at least {coal_needed} coal, got {final_inventory.get(Prototype.Coal)}"

print(f"Successfully gathered resources. Iron Ore: {final_inventory.get(Prototype.IronOre)}, Coal: {final_inventory.get(Prototype.Coal)}")

"""
Step 4: Set up smelting. We need to place the stone-furnace, fuel it with coal, and smelt the iron ore into iron plates.
"""
# Place the stone-furnace at the current position
current_position = inspect_entities().player_position
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))

# Insert coal into the stone-furnace as fuel
updated_stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=1)

# Insert iron ore into the stone-furnace
updated_stone_furnace = insert_item(Prototype.IronOre, updated_stone_furnace, quantity=3)

# Wait for the smelting process to complete
sleep(3)

# Extract the iron plates
extract_item(Prototype.IronPlate, updated_stone_furnace.position, quantity=3)

# Verify that we have the iron plates
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronPlate) >= 3, f"Failed to obtain required iron plates; expected at least 3, got {current_inventory.get(Prototype.IronPlate)}"

print("Successfully set up smelting and obtained iron plates")

"""
Step 5: Craft intermediate items. We need to craft iron gear wheels. We need 2 iron plates for 1 iron gear wheel.
"""
# Craft iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)

# Verify that we have crafted the iron gear wheel
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel) >= 1, f"Failed to craft required iron gear wheel; expected at least 1, got {current_inventory.get(Prototype.IronGearWheel)}"

print("Successfully crafted intermediate items")

"""
Step 6: Craft transport-belt. We need to craft 2 transport-belts. Each transport-belt requires 1 iron gear wheel and 1 iron plate.
"""
# Craft transport-belt
crafted_transport_belt = craft_item(Prototype.TransportBelt, quantity=2)

# Verify that we have crafted the transport-belt
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.TransportBelt) >= 2, f"Failed to craft required transport-belts; expected at least 2, got {current_inventory.get(Prototype.TransportBelt)}"

print("Successfully crafted transport-belts")

"""
Step 7: Craft fast-underground-belt. We need to use the crafted transport-belt and iron gear wheels to craft the fast-underground-belt.
"""
# Craft fast-underground-belt
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we have crafted the fast-underground-belt
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.FastUndergroundBelt) >= 1, f"Failed to craft required fast-underground-belt; expected at least 1, got {current_inventory.get(Prototype.FastUndergroundBelt)}"

print("Successfully crafted fast-underground-belt")

# Final inventory check
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Fast Underground Belt: {final_inventory.get(Prototype.FastUndergroundBelt)}")

print("Objective completed successfully")

