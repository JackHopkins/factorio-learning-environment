
from instance import *

"""
Step 1: Print recipes. We need to craft a fast underground belt, which requires 2 underground belts and 40 iron gear wheels.
We have no entities on the map or in our inventory, so we need to craft everything from scratch.
"""
print("Recipes:")
print("Fast Underground Belt: 2 Underground Belts, 40 Iron Gear Wheels")
print("Underground Belt: 5 Iron Gear Wheels, 1 Transport Belt (each)")
print("Transport Belt: 1 Iron Gear Wheel, 1 Iron Plate")
print("Iron Gear Wheel: 2 Iron Plates")

"""
Step 2: Gather resources. We need to gather iron ore and coal for fuel.
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 70),  # 40 for iron gear wheels, 20 for underground belts, 10 for fast-underground-belt
    (Resource.Coal, 30)  # For fueling the furnace and burner mining drill
]

# Loop through each resource type and amount
for resource_type, amount in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_amount = current_inventory.get(resource_type, 0)
    assert actual_amount >= amount, f"Failed to gather enough {resource_type}. Expected: {amount}, Actual: {actual_amount}"
    
    print(f"Successfully gathered {actual_amount} {resource_type}")

# Print out final inventory after gathering resources
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Verify that we have at least the required amounts
assert final_inventory.get(Resource.IronOre, 0) >= 70, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 30, "Not enough Coal"

print("Successfully gathered all required resources.")

"""
Step 3: Craft a stone furnace. We need 5 stone for this.
"""
# Find the nearest stone patch
stone_position = nearest(Resource.Stone)

# Move to the stone patch
move_to(stone_position)

# Harvest 5 stone
harvested_stone = harvest_resource(stone_position, 5)

# Check if we got the required amount of stone
current_inventory = inspect_inventory()
assert current_inventory.get(Resource.Stone, 0) >= 5, f"Failed to gather enough Stone. Expected: 5, Actual: {current_inventory.get(Resource.Stone, 0)}"

print(f"Successfully gathered {current_inventory.get(Resource.Stone, 0)} Stone")

# Craft the stone furnace
crafted = craft_item(Prototype.StoneFurnace, quantity=1)

# Verify that we have crafted a stone furnace
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, f"Failed to craft Stone Furnace. Current Inventory: {current_inventory}"

print("Successfully crafted a Stone Furnace")

# Print out final inventory after crafting
final_inventory = inspect_inventory()
print(f"Final inventory after crafting Stone Furnace: {final_inventory}")

"""
Step 4: Place the stone furnace and smelt iron plates. We need 70 iron plates in total.
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace for fuel
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=30)
print("Inserted coal into the Stone Furnace")

# Insert iron ore into the furnace
iron_ore_inserted = insert_item(Prototype.IronOre, furnace, quantity=70)
print("Inserted Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * 70)
sleep(total_smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=70)
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.IronPlate, 0) >= 70:
        break
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted Iron Plates; Current Inventory Count: {current_inventory.get(Prototype.IronPlate, 0)}")

# Verify that we have enough iron plates
assert current_inventory.get(Prototype.IronPlate, 0) >= 70, f"Failed to obtain required number of Iron Plates. Expected: 70, Actual: {current_inventory.get(Prototype.IronPlate, 0)}"

print("Successfully obtained required number of Iron Plates")

"""
Step 5: Craft a burner mining drill. We need 3 iron gear wheels and 1 stone furnace for this.
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 Iron Gear Wheels")

# Craft a burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

"""
Step 6: Place the burner mining drill and start mining iron ore.
"""
# Find an iron ore patch
iron_ore_position = nearest(Resource.IronOre)

# Move to the iron ore patch
move_to(iron_ore_position)

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.RIGHT, position=iron_ore_position)
print(f"Placed Burner Mining Drill at {drill.position}")

# Fuel the burner mining drill with coal
coal_inserted = insert_item(Prototype.Coal, drill, quantity=15)
print("Inserted coal into the Burner Mining Drill")

# Verify that the drill has coal
coal_in_drill = drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel Burner Mining Drill"

# Wait for the drill to mine some iron ore
sleep(30)

# Check the contents of the drill
drill_inventory = inspect_inventory(drill)
iron_ore_in_drill = drill_inventory.get(Prototype.IronOre, 0)
print(f"Iron Ore in Burner Mining Drill: {iron_ore_in_drill}")

assert iron_ore_in_drill > 0, "Burner Mining Drill is not mining Iron Ore"

"""
Step 7: Craft and place a wooden chest next to the burner mining drill.
"""
# Craft a wooden chest
craft_item(Prototype.WoodenChest, quantity=1)
print("Crafted 1 Wooden Chest")

# Place the wooden chest next to the burner mining drill
chest_position = Position(x=drill.position.x + 2, y=drill.position.y)  # Assuming the drill is facing right
chest = place_entity(Prototype.WoodenChest, position=chest_position)
print(f"Placed Wooden Chest at {chest.position}")

"""
Step 8: Craft and place a burner inserter to transfer iron ore from the drill to the chest.
"""
# Craft a burner inserter
craft_item(Prototype.BurnerInserter, quantity=1)
print("Crafted 1 Burner Inserter")

# Place the burner inserter between the drill and the chest
inserter_position = Position(x=drill.position.x + 1, y=drill.position.y)
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=inserter_position)
print(f"Placed Burner Inserter at {inserter.position}")

# Fuel the burner inserter with coal
coal_inserted = insert_item(Prototype.Coal, inserter, quantity=5)
print("Inserted coal into the Burner Inserter")

"""
Step 9: Wait for the system to produce iron ore. We need 40 iron ore in the chest.
"""
# Wait for the system to produce iron ore
max_wait_time = 180  # Maximum time to wait in seconds
sleep_interval = 30  # Check every 30 seconds

for _ in range(max_wait_time // sleep_interval):
    sleep(sleep_interval)
    chest_inventory = inspect_inventory(chest)
    iron_ore_count = chest_inventory.get(Prototype.IronOre, 0)
    print(f"Iron ore in the chest: {iron_ore_count}")
    if iron_ore_count >= 40:
        print("Sufficient iron ore collected in the chest.")
        break

assert iron_ore_count >= 40, "Failed to collect enough iron ore in the chest"
print("Successfully collected 40 iron ore in the chest.")

# Extract the iron ore from the chest
extracted_ore = extract_item(Prototype.IronOre, chest.position, quantity=40)
print(f"Extracted {extracted_ore} Iron Ore from the Chest")

"""
Step 10: Craft iron gear wheels. We need 40 iron gear wheels.
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 Iron Gear Wheels")

# Verify that we have crafted enough iron gear wheels
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 40, f"Failed to craft required number of Iron Gear Wheels. Expected: 40, Actual: {current_inventory.get(Prototype.IronGearWheel, 0)}"

print("Successfully crafted 40 Iron Gear Wheels")

"""
Step 11: Craft 2 underground-belts. We need 10 iron gear wheels and 2 transport belts for this.
"""
# Print the recipe for underground-belt
recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {recipe}")

# Craft 2 underground-belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 Underground Belts")

# Verify that we have crafted enough underground-belts
current_inventory = inspect_inventory()
underground_belt_count = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 2, f"Failed to craft required number of Underground Belts. Expected: 2, Actual: {underground_belt_count}"

print("Successfully crafted 2 Underground Belts")

"""
Step 12: Craft the fast-underground-belt.
"""
# Print the recipe for fast-underground-belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(f"Fast Underground Belt Recipe: {recipe}")

# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 Fast Underground Belt")

# Verify that we have crafted the fast-underground-belt
current_inventory = inspect_inventory()
fast_underground_belt_count = current_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft required number of Fast Underground Belts. Expected: 1, Actual: {fast_underground_belt_count}"

print("Successfully crafted 1 Fast Underground Belt")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Check if we have crafted a fast-underground-belt
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft a fast-underground-belt"
