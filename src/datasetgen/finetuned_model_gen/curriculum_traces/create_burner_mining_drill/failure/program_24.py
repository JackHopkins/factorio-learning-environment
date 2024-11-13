

from factorio_instance import *

"""
Step 1: Print recipes. We need to print recipes for burner mining drill, transport belt and underground belt. As there is nothing in inventory, we need to craft everything from scratch
"""
# Get the recipes for the required items
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipes
print("Burner Mining Drill Recipe:")
print(f"Ingredients: {burner_mining_drill_recipe.ingredients}")

print("\nTransport Belt Recipe:")
print(f"Ingredients: {transport_belt_recipe.ingredients}")

print("\nUnderground Belt Recipe:")
print(f"Ingredients: {underground_belt_recipe.ingredients}")

"""
Step 2: Craft 2 burner mining drills. We need to craft 2 burner mining drills from scratch
"""
# Get the recipe for burner mining drill
recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

# Print the recipe details
print("Burner Mining Drill Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Calculate required resources
iron_gear_wheels_needed = 10  # 5 per drill
iron_plates_needed = 10  # 5 per drill
stone_furnaces_needed = 2  # 1 per drill
stone_needed = 10  # 5 per furnace
coal_needed = 10  # For smelting and fueling

# Define resource gathering function
def gather_resources():
    resources_to_gather = [
        (Resource.IronOre, iron_plates_needed * 2),  # Double for iron gear wheels
        (Resource.Stone, stone_needed),
        (Resource.Coal, coal_needed)
    ]
    
    for resource_type, required_quantity in resources_to_gather:
        resource_position = nearest(resource_type)
        move_to(resource_position)
        harvested = harvest_resource(resource_position, required_quantity)
        current_inventory = inspect_inventory()
        actual_quantity = current_inventory.get(resource_type, 0)
        assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
        print(f"Successfully gathered {actual_quantity} {resource_type}")

# Gather resources
gather_resources()

# Craft stone furnaces
craft_item(Prototype.StoneFurnace, quantity=stone_furnaces_needed)

# Set up smelting operation
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.Coal, stone_furnace, quantity=5)
insert_item(Prototype.IronOre, stone_furnace, quantity=iron_plates_needed * 2)

# Wait for smelting
sleep(5)

# Extract iron plates
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_plates_needed * 2)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_needed)

# Craft burner mining drills
crafted = craft_item(Prototype.BurnerMiningDrill, quantity=2)
print(f"Crafted {crafted} burner mining drills")

# Verify crafting success
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 2, "Failed to craft required number of burner mining drills"
print("Successfully crafted 2 burner mining drills")

"""
Step 3: Craft 14 transport belts. We need to craft 14 transport belts from scratch
"""
# Calculate required resources
iron_gear_wheels_needed = 14  # 1 per transport belt
iron_plates_needed = 14  # 1 per transport belt
total_iron_needed = iron_gear_wheels_needed * 2 + iron_plates_needed  # Each gear wheel requires 2 iron plates
coal_needed = 10  # For smelting

# Gather resources
gather_resources()

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place stone furnace and begin smelting
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.Coal, stone_furnace, quantity=5)
insert_item(Prototype.IronOre, stone_furnace, quantity=total_iron_needed)

# Wait for smelting
sleep(5)

# Extract iron plates
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=total_iron_needed)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_needed)

# Craft transport belts
crafted = craft_item(Prototype.TransportBelt, quantity=14)
print(f"Crafted {crafted} transport belts")

# Verify crafting success
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.TransportBelt, 0) >= 14, "Failed to craft required number of transport belts"
print("Successfully crafted 14 transport belts")

"""
Step 4: Craft 4 underground belts. We need to craft 4 underground belts from scratch
"""
# Calculate required resources
iron_gear_wheels_needed = 10  # 5 per underground belt
iron_plates_needed = 2  # 1 per transport belt
total_iron_needed = iron_gear_wheels_needed * 2 + iron_plates_needed 
coal_needed = 10  # For smelting

# Gather resources
gather_resources()

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place stone furnace and begin smelting
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.Coal, stone_furnace, quantity=5)
insert_item(Prototype.IronOre, stone_furnace, quantity=total_iron_needed)

# Wait for smelting
sleep(5)

# Extract iron plates
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=total_iron_needed)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_needed)

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=2)

# Craft underground belts
crafted = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {crafted} underground belts")

# Verify crafting success
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 4, "Failed to craft required number of underground belts"
print("Successfully crafted 4 underground belts")

"""
Step 5: Craft 2 stone furnaces. We need to craft 2 stone furnaces from scratch
"""
# Calculate required resources
stone_needed = 10  # 5 per furnace

# Gather stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stone = harvest_resource(stone_position, quantity=stone_needed)

# Verify stone collection
current_inventory = inspect_inventory()
actual_stone = current_inventory.get(Prototype.Stone, 0)
assert actual_stone >= stone_needed, f"Failed to gather enough stone. Required: {stone_needed}, Actual: {actual_stone}"
print(f"Successfully gathered {actual_stone} stone")

# Craft stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify crafting success
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft required number of stone furnaces"
print("Successfully crafted 2 stone furnaces")

"""
Step 6: Craft 25 iron plates. We need to smelt 25 iron plates from iron ore
"""
# Calculate required resources
iron_ore_needed = 25
coal_needed = 10  # For smelting

# Gather resources
for resource_type, required_quantity in [(Resource.IronOre, iron_ore_needed), (Resource.Coal, coal_needed)]:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Craft and place stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Begin smelting process
insert_item(Prototype.Coal, furnace, quantity=5)
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_needed)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=25)

# Verify iron plate production
final_inventory = inspect_inventory()
actual_iron_plates = final_inventory.get(Prototype.IronPlate, 0)
assert actual_iron_plates >= 25, f"Failed to produce required number of iron plates. Expected: 25, Actual: {actual_iron_plates}"
print(f"Successfully produced {actual_iron_plates} iron plates")

"""
Step 7: Craft 4 iron gear wheels. We need to craft 4 iron gear wheels from iron plates
"""
# Calculate required resources
iron_plates_needed = 8  # 2 per gear wheel

# Verify we have enough iron plates
current_inventory = inspect_inventory()
actual_iron_plates = current_inventory.get(Prototype.IronPlate, 0)
assert actual_iron_plates >= iron_plates_needed, f"Not enough iron plates. Required: {iron_plates_needed}, Actual: {actual_iron_plates}"
print(f"Using {iron_plates_needed} iron plates to craft gear wheels")

# Craft iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=4)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Verify crafting success
final_inventory = inspect_inventory()
actual_gear_wheels = final_inventory.get(Prototype.IronGearWheel, 0)
assert actual_gear_wheels >= 4, f"Failed to craft required number of iron gear wheels. Expected: 4, Actual: {actual_gear_wheels}"
print(f"Successfully crafted {actual_gear_wheels} iron gear wheels")

"""
Step 8: Craft 2 stone furnaces. We need to craft 2 stone furnaces from scratch
"""
# Calculate required resources
stone_needed = 10  # 5 per furnace

# Gather stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stone = harvest_resource(stone_position, quantity=stone_needed)

# Verify stone collection
current_inventory = inspect_inventory()
actual_stone = current_inventory.get(Prototype.Stone, 0)
assert actual_stone >= stone_needed, f"Failed to gather enough stone. Required: {stone_needed}, Actual: {actual_stone}"
print(f"Successfully gathered {actual_stone} stone")

# Craft stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify crafting success
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft required number of stone furnaces"
print("Successfully crafted 2 stone furnaces")

"""
Step 9: Craft 1 burner mining drill. We need to craft 1 burner mining drill using the resources gathered
"""
# Craft burner mining drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drills} burner mining drill")

# Verify crafting success
final_inventory = inspect_inventory()
actual_drills = final_inventory.get(Prototype.BurnerMiningDrill, 0)
assert actual_drills >= 1, f"Failed to craft required number of burner mining drills. Expected: 1, Actual: {actual_drills}"
print(f"Successfully crafted {actual_drills} burner mining drill")

