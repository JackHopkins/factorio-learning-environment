
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft.
"""
# Print recipes for the required items
print("Recipes:")
for item in [Prototype.BurnerMiningDrill, Prototype.StoneFurnace, Prototype.IronGearWheel, Prototype.TransportBelt, Prototype.UndergroundBelt]:
    recipe = get_prototype_recipe(item)
    print(f"{item.value[0]}: {recipe}")

"""
Step 2: Gather resources. We need to mine the following resources:
- 25 iron ore
- 12 stone
- 2 coal
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource type and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    nearest_patch = nearest(resource_type)

    # Move to the center of this patch
    move_to(nearest_patch)

    # Harvest the requested amount
    harvested = harvest_resource(nearest_patch, required_quantity)

    # Verify that we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    print(f"{resource_type}: {actual_quantity}")
    assert actual_quantity >= required_quantity, f"Not enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces using 10 stone.
"""
# Craft 2 stone furnaces using the available stone
craft_item(Prototype.StoneFurnace, quantity=2)

# Verify that we have 2 stone furnaces in our inventory
current_inventory = inspect_inventory()
stone_furnaces = current_inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 2, f"Failed to craft enough stone furnaces. Expected: 2, Actual: {stone_furnaces}"
print(f"Successfully crafted {stone_furnaces} stone furnaces")

# Check remaining stone in inventory
remaining_stone = current_inventory.get(Prototype.Stone, 0)
print(f"Remaining stone in inventory: {remaining_stone}")
assert remaining_stone >= 2, f"Not enough remaining stone for future steps. Expected at least 2, Actual: {remaining_stone}"

"""
Step 4: Set up smelting. We need to:
a) Place a stone furnace
b) Add coal as fuel
c) Smelt 25 iron ore into iron plates
"""
# Move to a suitable position for placing the furnace
move_to(Position(x=0, y=0))

# Place one stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the stone furnace")

# Wait for the smelting process to complete
smelting_time = 0.7 * iron_ore_in_inventory
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 25:
        break
    sleep(5)  # Allow more time if needed

print(f"Extracted iron plates; Current inventory count: {current_iron_plate_count}")

# Verify that we have at least 25 iron plates
assert current_iron_plate_count >= 25, f"Failed to obtain required number of Iron Plates. Expected: 25, Actual: {current_iron_plate_count}"
print(f"Successfully obtained {current_iron_plate_count} iron plates")

"""
Step 5: Craft iron gear wheels. We need to craft 4 iron gear wheels using 8 iron plates.
"""
# Craft 4 iron gear wheels using 8 iron plates
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 Iron Gear Wheels")

# Verify that we have 4 iron gear wheels in our inventory
current_inventory = inspect_inventory()
iron_gear_wheels = current_inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 4, f"Failed to craft enough Iron Gear Wheels. Expected: 4, Actual: {iron_gear_wheels}"
print(f"Successfully crafted {iron_gear_wheels} Iron Gear Wheels")

# Check remaining iron plates in inventory
remaining_iron_plates = current_inventory.get(Prototype.IronPlate, 0)
print(f"Remaining Iron Plates in inventory: {remaining_iron_plates}")

"""
Step 6: Craft burner-mining-drill. We need to craft 1 burner-mining-drill using:
- 1 stone furnace
- 3 iron gear wheels
- 3 iron plates
"""
# Craft 1 burner-mining-drill using the available materials
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

# Verify that we have 1 burner-mining-drill in our inventory
current_inventory = inspect_inventory()
burner_mining_drills = current_inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft Burner Mining Drill. Expected: 1, Actual: {burner_mining_drills}"
print(f"Successfully crafted {burner_mining_drills} Burner Mining Drill")

"""
Step 7: Craft transport belts. We need to craft 14 transport belts using 7 iron gear wheels and 7 iron plates.
"""
# Craft 14 transport belts using the available materials
craft_item(Prototype.TransportBelt, quantity=14)
print("Crafted 14 Transport Belts")

# Verify that we have 14 transport belts in our inventory
current_inventory = inspect_inventory()
transport_belts = current_inventory.get(Prototype.TransportBelt, 0)
assert transport_belts >= 14, f"Failed to craft Transport Belts. Expected: 14, Actual: {transport_belts}"
print(f"Successfully crafted {transport_belts} Transport Belts")

"""
Step 8: Craft underground belts. We need to craft 4 underground belts using 10 iron gear wheels and 10 transport belts.
"""
# Craft 4 underground belts using the available materials
craft_item(Prototype.UndergroundBelt, quantity=4)
print("Crafted 4 Underground Belts")

# Verify that we have 4 underground belts in our inventory
current_inventory = inspect_inventory()
underground_belts = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 4, f"Failed to craft Underground Belts. Expected: 4, Actual: {underground_belts}"
print(f"Successfully crafted {underground_belts} Underground Belts")

"""
Final verification: Check if we have crafted all the required items.
"""
# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
for item, count in final_inventory.items():
    print(f"{item}: {count}")

# Assert that we have crafted all the required items
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Missing Burner Mining Drill"
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 2, "Missing Stone Furnaces"
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 4, "Missing Iron Gear Wheels"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 14, "Missing Transport Belts"
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 4, "Missing Underground Belts"
assert final_inventory.get(Prototype.IronPlate, 0) >= 25, "Missing Iron Plates"

print("All required items have been successfully crafted!")
