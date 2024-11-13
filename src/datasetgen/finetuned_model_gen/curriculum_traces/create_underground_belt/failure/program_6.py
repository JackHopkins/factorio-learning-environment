
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for transport-belt and underground-belt
"""
# Print recipe for transport-belt
print("Transport Belt Recipe:")
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Ingredients for Transport Belt: {transport_belt_recipe.ingredients}")

# Print recipe for underground-belt
print("Underground Belt Recipe:")
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Ingredients for Underground Belt: {underground_belt_recipe.ingredients}")

print("Recipes printed successfully")

"""
Step 2: Gather and prepare resources. We need to gather and smelt iron ore and stone
"""
# Define required resources
required_resources = {
    Resource.IronOre: 21,
    Resource.Coal: 2,
    Resource.Stone: 12
}

# Gather resources
for resource_type, quantity in required_resources.items():
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, quantity=quantity)
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type, 0) >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Found: {current_inventory.get(resource_type, 0)}"
    print(f"Successfully gathered {harvested} of {resource_type}")

# Craft stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Place and use furnaces
origin = Position(x=0, y=0)
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))

# Smelt iron plates
insert_item(Prototype.Coal, furnace1, 1)
insert_item(Prototype.IronOre, furnace1, 21)
sleep(10)  # Allow time for smelting
extract_item(Prototype.IronPlate, furnace1.position, 21)

# Verify iron plates
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 21, f"Failed to obtain enough Iron Plates. Required: 21, Found: {iron_plates}"
print(f"Successfully obtained {iron_plates} Iron Plates")

# Verify stone furnaces
stone_furnaces = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 1, f"Failed to craft Stone Furnaces. Required: 1, Found: {stone_furnaces}"
print(f"Successfully crafted {stone_furnaces} Stone Furnaces")

print("Resource gathering and preparation completed successfully")

"""
Step 3: Craft transport-belts. We need to craft at least 4 transport-belts, which requires 4 iron gear wheels and 4 iron plates
"""
# Craft Transport Belts
craft_item(Prototype.TransportBelt, quantity=4)

# Verify Transport Belts in inventory
transport_belts = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts >= 4, f"Failed to craft enough Transport Belts. Required: 4, Found: {transport_belts}"
print(f"Successfully crafted {transport_belts} Transport Belts")

"""
Step 4: Craft underground-belt. Use the crafted transport-belts and remaining iron gear wheels to craft the underground-belt
"""
# Craft Underground Belt
craft_item(Prototype.UndergroundBelt, quantity=1)

# Verify Underground Belt in inventory
underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 1, f"Failed to craft Underground Belt. Required: 1, Found: {underground_belts}"
print(f"Successfully crafted {underground_belts} Underground Belt. Inventory: {inspect_inventory()}")

print("All steps completed successfully. We have crafted an Underground Belt!")
