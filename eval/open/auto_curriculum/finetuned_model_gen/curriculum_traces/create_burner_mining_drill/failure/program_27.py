
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner-mining-drill
- stone-furnace
- iron-gear-wheel
"""
# Get recipes
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print recipes
print("Burner Mining Drill Recipe:", burner_mining_drill_recipe)
print("Stone Furnace Recipe:", stone_furnace_recipe)
print("Iron Gear Wheel Recipe:", iron_gear_wheel_recipe)

"""
Step 1: Gather raw resources
- Mine 36 iron ore
- Mine 12 stone
- Mine 3 coal
"""
resources_to_gather = [
    (Resource.IronOre, 36),
    (Resource.Stone, 12),
    (Resource.Coal, 3)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Verify that we harvested the required amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("All required resources gathered successfully.")

"""
Step 2: Craft and place stone furnaces
- Craft 2 stone furnaces
- Place 2 stone furnaces on the ground
"""
# Craft 2 stone furnaces
stone_furnaces_crafted = craft_item(Prototype.StoneFurnace, quantity=2)
assert stone_furnaces_crafted == 2, f"Failed to craft 2 Stone Furnaces. Only crafted {stone_furnaces_crafted}"

# Place the two Stone Furnaces next to each other
origin = Position(x=0, y=0)
move_to(origin)

furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))

# Verify that the furnaces exist in the game world
furnaces_on_map = get_entities({Prototype.StoneFurnace})
assert len(furnaces_on_map) >= 2, f"Expected at least 2 Stone Furnaces on the map but found {len(furnaces_on_map)}"

print("Successfully placed 2 Stone Furnaces on the map.")

"""
Step 3: Smelt iron plates
- Use 1 furnace to smelt 36 iron ore into iron plates
"""
iron_to_smelt = 36
coal_for_iron = 3

# Insert coal into both furnaces
updated_furnace1 = insert_item(Prototype.Coal, furnace1, 2)
updated_furnace2 = insert_item(Prototype.Coal, furnace2, 1)

# Insert iron ore into the first furnace
iron_per_furnace = iron_to_smelt // 2
updated_furnace1 = insert_item(Prototype.IronOre, updated_furnace1, iron_per_furnace)
updated_furnace2 = insert_item(Prototype.IronOre, updated_furnace2, iron_per_furnace)

# Wait for smelting to complete
smelting_time_per_unit = 0.7  # Slightly longer to ensure complete smelting
total_smelting_time = int(smelting_time_per_unit * iron_to_smelt)
sleep(total_smelting_time)

# Extract iron plates from both furnaces
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace1.position, iron_per_furnace)
    extract_item(Prototype.IronPlate, updated_furnace2.position, iron_per_furnace)
    
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    if current_iron_plate_count >= 36:
        break
    sleep(10)

assert inspect_inventory()[Prototype.IronPlate] >= 36, "Failed to obtain 36 Iron Plates"
print(f"Successfully obtained {inspect_inventory()[Prototype.IronPlate]} Iron Plates")

"""
Step 4: Craft iron gear wheels
- Craft 6 iron gear wheels (4 for the burner-mining-drill, 2 extra)
"""
# Craft 6 iron gear wheels
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, quantity=6)
assert iron_gear_wheels_crafted == 6, f"Failed to craft 6 Iron Gear Wheels. Only crafted {iron_gear_wheels_crafted}"

# Verify that we have 6 Iron Gear Wheels in the inventory
current_inventory = inspect_inventory()
assert current_inventory[Prototype.IronGearWheel] >= 6, f"Insufficient Iron Gear Wheels. Expected: 6, Actual: {current_inventory[Prototype.IronGearWheel]}"

print(f"Successfully crafted 6 Iron Gear Wheels. Current inventory: {current_inventory}")

"""
Step 5: Craft burner-mining-drill
- Craft 1 burner-mining-drill
"""
# Craft 1 burner-mining-drill
burner_mining_drills_crafted = craft_item(Prototype.BurnerMiningDrill, quantity=1)
assert burner_mining_drills_crafted == 1, f"Failed to craft 1 Burner Mining Drill. Only crafted {burner_mining_drills_crafted}"

# Verify that we have at least 1 Burner Mining Drill in the inventory
current_inventory = inspect_inventory()
assert current_inventory[Prototype.BurnerMiningDrill] >= 1, f"Insufficient Burner Mining Drills. Expected at least 1, Actual: {current_inventory[Prototype.BurnerMiningDrill]}"

print(f"Successfully crafted 1 Burner Mining Drill. Current inventory: {current_inventory}")

print("All steps completed successfully.")
