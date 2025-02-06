

from instance import *


"""
Step 1: Print recipes
"""
# Get and print recipe for burner mining drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill Recipe: {burner_mining_drill_recipe}")

# Print each ingredient separately
print("Burner Mining Drill Ingredients:")
for ingredient in burner_mining_drill_recipe.ingredients:
    print(f"{ingredient.count}x {ingredient.name}")

# Get and print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Print each ingredient separately
print("Stone Furnace Ingredients:")
for ingredient in stone_furnace_recipe.ingredients:
    print(f"{ingredient.count}x {ingredient.name}")

"""
Step 1: Gather raw resources
- Mine iron ore (at least 20)
- Mine stone (at least 10)
- Mine coal (at least 20)
"""
resources_to_gather = [
    (Resource.IronOre, 20),
    (Resource.Stone, 10),
    (Resource.Coal, 20)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

"""
Step 2: Crafting
- Craft 1 StoneFurnace
- Craft 1 BurnerMiningDrill
"""
# Craft StoneFurnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 StoneFurnace")

# Craft BurnerMiningDrill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 BurnerMiningDrill")

# Verify crafting
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft StoneFurnace"
assert inventory_after_crafting.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft BurnerMiningDrill"
print("Successfully crafted all required items")

"""
Step 3: Set up mining and smelting
1. Place the BurnerMiningDrill on an iron ore patch
2. Place the StoneFurnace next to the drill
3. Fuel both the drill and the furnace with coal
"""
# Place BurnerMiningDrill
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print("Placed BurnerMiningDrill")

# Place StoneFurnace next to the drill
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.RIGHT)
print("Placed StoneFurnace")

# Fuel both entities
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 20, f"Not enough coal in inventory. Required: 20, Found: {coal_in_inventory}"

drill = insert_item(Prototype.Coal, drill, quantity=10)
furnace = insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into BurnerMiningDrill and StoneFurnace")

"""
Step 4: Begin production
1. Wait for the drill to mine iron ore (about 30 seconds for 10 ore)
2. Move iron ore from the drill to the furnace
3. Wait for the furnace to smelt the iron ore into plates
"""
# Wait for mining
print("Waiting for iron ore to be mined...")
sleep(30)
print("30 seconds have passed. Checking for mined iron ore.")

# Move iron ore to furnace
max_attempts = 5
for _ in range(max_attempts):
    # Extract iron ore from drill
    extract_item(Prototype.IronOre, drill.position, quantity=10)
    
    # Insert iron ore into furnace
    furnace = insert_item(Prototype.IronOre, furnace, quantity=10)
    
    # Check if there are enough iron plates
    furnace_inventory = inspect_inventory(furnace)
    iron_plate_count = furnace_inventory.get(Prototype.IronPlate, 0)
    if iron_plate_count >= 10:
        break
    
    sleep(10)

# Final check for iron plates
furnace_inventory = inspect_inventory(furnace)
iron_plate_count = furnace_inventory.get(Prototype.IronPlate, 0)
assert iron_plate_count >= 10, f"Failed to produce enough Iron Plates. Expected at least 10, but found {iron_plate_count}"
print(f"Successfully produced {iron_plate_count} Iron Plates")

print("Initial iron plate production setup complete!")

