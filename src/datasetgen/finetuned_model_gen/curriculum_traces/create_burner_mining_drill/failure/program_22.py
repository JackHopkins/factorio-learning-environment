

from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner-mining-drill
- transport-belt
- underground-belt
- stone-furnace
- iron-plate
- iron-gear-wheel
"""

# Get and print recipe for burner-mining-drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Recipe for Burner Mining Drill: {burner_mining_drill_recipe}")

# Get and print recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Recipe for Transport Belt: {transport_belt_recipe}")

# Get and print recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Recipe for Underground Belt: {underground_belt_recipe}")

# Get and print recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Recipe for Stone Furnace: {stone_furnace_recipe}")

# Get and print recipe for iron-plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print(f"Recipe for Iron Plate: {iron_plate_recipe}")

# Get and print recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Recipe for Iron Gear Wheel: {iron_gear_wheel_recipe}")

"""
Step 2: Gather initial resources. We need to gather the following resources:
- stone: 12
- iron-ore: 25
- coal: 2 (for smelting)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 25),
    (Resource.Coal, 2)
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
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering: {final_inventory}")

# Assert that we have at least the required quantities of each resource
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough stone"
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough iron ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough coal"

print("Successfully gathered all required resources.")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""

# Craft 2 stone furnaces
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_stone_furnaces} stone furnaces")

# Check if we crafted the correct amount
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.StoneFurnace, 0)
assert actual_quantity >= 2, f"Failed to craft enough stone furnaces. Required: 2, Actual: {actual_quantity}"
print(f"Successfully crafted {actual_quantity} stone furnaces")

# Print the current inventory
print(f"Current inventory after crafting stone furnaces: {current_inventory}")

"""
Step 4: Set up smelting. We need to:
- Place one stone furnace
- Add coal to the furnace as fuel
- Smelt 25 iron-ore into iron-plates
"""

# Move to a suitable position to place the furnace
move_to(Position(x=0, y=0))

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print("Stone furnace placed.")

# Insert coal into the furnace as fuel
furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the furnace.")

# Insert iron ore into the furnace
iron_ore_quantity = 25
furnace = insert_item(Prototype.IronOre, furnace, quantity=iron_ore_quantity)
print(f"Inserted {iron_ore_quantity} iron ore into the furnace.")

# Smelting process
smelting_time = iron_ore_quantity * 0.7
sleep(smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_quantity)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= iron_ore_quantity:
        break
    sleep(5)  # Wait a bit more if not all plates are ready

print(f"Extracted iron plates. Current inventory: {inspect_inventory()}")

# Verify we have 25 iron plates
assert inspect_inventory().get(Prototype.IronPlate, 0) >= 25, "Failed to smelt enough iron plates!"
print("Successfully smelted 25 iron plates.")

"""
Step 5: Craft iron gear wheels. We need to:
- Craft 10 iron gear wheels (using 20 iron plates)
"""

# Craft 10 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=10)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Check if we crafted the correct amount
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.IronGearWheel, 0)
assert actual_quantity >= 10, f"Failed to craft enough iron gear wheels. Required: 10, Actual: {actual_quantity}"
print(f"Successfully crafted {actual_quantity} iron gear wheels")

# Print the current inventory
print(f"Current inventory after crafting iron gear wheels: {current_inventory}")

"""
Step 6: Craft and place burner mining drill. We need to:
- Craft 1 burner mining drill (using 3 iron gear wheels, 3 iron plates, and 1 stone furnace)
- Place the burner mining drill near an iron ore patch
"""

# Craft 1 burner mining drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drill} burner mining drill")

# Check if we crafted the correct amount
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.BurnerMiningDrill, 0)
assert actual_quantity >= 1, f"Failed to craft enough burner mining drills. Required: 1, Actual: {actual_quantity}"
print(f"Successfully crafted {actual_quantity} burner mining drills")

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore patch found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print("Moved to iron ore patch.")

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed burner mining drill at: {drill.position}")

# Verify that the drill was placed successfully
entities = get_entities({Prototype.BurnerMiningDrill})
placed_drills = [e for e in entities if e.position.is_close(drill.position)]
assert len(placed_drills) == 1, "Failed to place the burner mining drill correctly"
print("Successfully placed burner mining drill.")

# Print the final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after placing burner mining drill: {final_inventory}")

"""
Step 7: Craft transport belts. We need to:
- Craft 14 transport belts (using 14 iron gear wheels and 14 iron plates)
"""

# Craft 14 transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=14)
print(f"Crafted {crafted_transport_belts} transport belts")

# Check if we crafted the correct amount
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.TransportBelt, 0)
assert actual_quantity >= 14, f"Failed to craft enough transport belts. Required: 14, Actual: {actual_quantity}"
print(f"Successfully crafted {actual_quantity} transport belts")

# Print the current inventory
print(f"Current inventory after crafting transport belts: {current_inventory}")

"""
Step 8: Craft underground belts. We need to:
- Craft 4 underground belts (using 4 transport belts and 8 iron plates)
"""

# Craft 4 underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {crafted_underground_belts} underground belts")

# Check if we crafted the correct amount
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.UndergroundBelt, 0)
assert actual_quantity >= 4, f"Failed to craft enough underground belts. Required: 4, Actual: {actual_quantity}"
print(f"Successfully crafted {actual_quantity} underground belts")

# Print the final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after crafting all required items: {final_inventory}")

"""
Final step: Verify that we have crafted all required items successfully.
"""

# Check if we have all required items in the inventory
required_items = {
    Prototype.TransportBelt: 12,
    Prototype.UndergroundBelt: 4,
    Prototype.StoneFurnace: 1,
    Prototype.IronPlate: 25,
    Prototype.IronGearWheel: 4,
    Prototype.BurnerMiningDrill: 1
}

for item, required_quantity in required_items.items():
    actual_quantity = final_inventory.get(item, 0)
    assert actual_quantity >= required_quantity, f"Failed to craft enough {item}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully crafted {actual_quantity} {item}")

print("All required items have been crafted successfully!")

