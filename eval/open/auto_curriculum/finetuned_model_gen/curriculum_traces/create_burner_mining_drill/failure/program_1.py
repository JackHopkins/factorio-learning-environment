
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner-mining-drill
- stone-furnace
- firearm-magazine
- transport-belt
- burner-inserter
- iron-gear-wheel
- iron-plate
"""
# Get the recipes
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)

# Print the recipes
print("Burner Mining Drill Recipe:", burner_mining_drill_recipe)
print("Stone Furnace Recipe:", stone_furnace_recipe)
print("Firearm Magazine Recipe:", firearm_magazine_recipe)
print("Transport Belt Recipe:", transport_belt_recipe)
print("Burner Inserter Recipe:", burner_inserter_recipe)
print("Iron Gear Wheel Recipe:", iron_gear_wheel_recipe)
print("Iron Plate Recipe:", iron_plate_recipe)

"""
Step 2: Gather resources. We need to gather the following resources:
- 6 stone (for the stone furnace)
- 26 iron ore (to make 26 iron plates)
- 2 coal (for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 26),
    (Resource.Coal, 2)
]

# Loop over each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} patch at {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Verify that we've gathered enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

print("All resources successfully gathered.")
print("Final inventory:")
print(inspect_inventory())

"""
Step 3: Craft stone furnace. Use the 6 stone to craft 1 stone furnace.
"""
# Craft the stone furnace
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_stone_furnaces} stone furnace(s)")

# Verify that we've crafted a stone furnace
current_inventory = inspect_inventory()
stone_furnaces_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 1, f"Failed to craft stone furnace. Expected at least 1, but found {stone_furnaces_in_inventory}"

print("Successfully crafted a stone furnace.")
print("Current inventory:")
print(inspect_inventory())

"""
Step 4: Smelt iron plates. Place the stone furnace, add coal as fuel, and smelt the 26 iron ore into 26 iron plates.
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print("Inserted iron ore into the stone furnace")

# Wait for the smelting process to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 26:
        break
    sleep(5)  # Allow additional time if needed

print(f"Extracted iron plates; current inventory count: {current_iron_plate_count}")

# Final assertion check to ensure we have enough iron plates
assert current_iron_plate_count >= 26, f"Failed to obtain required number of iron plates. Expected: 26, Found: {current_iron_plate_count}"

print("Successfully smelted iron plates.")
print("Final inventory:")
print(inspect_inventory())

"""
Step 5: Craft intermediate items. We need to craft the following:
- 6 iron gear wheels (requires 12 iron plates)
- 4 transport belts (requires 1 iron gear wheel and 1 iron plate each, so 4 iron gear wheels and 4 iron plates total)
- 1 burner inserter (requires 1 iron gear wheel, 2 iron plates, and 1 transport belt, so 1 iron gear wheel, 2 iron plates, and 1 transport belt total)
- 1 stone furnace (requires 5 stone)
- 1 firearm magazine (requires 4 iron plates)
"""
# Craft iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=6)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Craft transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=4)
print(f"Crafted {crafted_transport_belts} transport belts")

# Craft burner inserter
crafted_burner_inserter = craft_item(Prototype.BurnerInserter, quantity=1)
print(f"Crafted {crafted_burner_inserter} burner inserter")

# Craft stone furnace
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_stone_furnaces} stone furnace")

# Craft firearm magazine
crafted_firearm_magazine = craft_item(Prototype.FirearmMagazine, quantity=1)
print(f"Crafted {crafted_firearm_magazine} firearm magazine")

# Verify that we've crafted all intermediate items
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 6, "Failed to craft enough iron gear wheels"
assert current_inventory.get(Prototype.TransportBelt, 0) >= 4, "Failed to craft enough transport belts"
assert current_inventory.get(Prototype.BurnerInserter, 0) >= 1, "Failed to craft burner inserter"
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"
assert current_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Failed to craft firearm magazine"

print("Successfully crafted all intermediate items.")
print("Current inventory:")
print(inspect_inventory())

"""
Step 6: Craft burner-mining-drill. Use the following items to craft 1 burner-mining-drill:
- 3 iron gear wheels
- 1 stone furnace
- 3 iron plates
"""
# Craft the burner-mining-drill
crafted_burner_mining_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_burner_mining_drills} burner-mining-drill")

# Verify that we've crafted a burner-mining-drill
current_inventory = inspect_inventory()
burner_mining_drills_in_inventory = current_inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills_in_inventory >= 1, f"Failed to craft burner-mining-drill. Expected at least 1, but found {burner_mining_drills_in_inventory}"

print("Successfully crafted a burner-mining-drill.")
print("Final inventory:")
print(inspect_inventory())
