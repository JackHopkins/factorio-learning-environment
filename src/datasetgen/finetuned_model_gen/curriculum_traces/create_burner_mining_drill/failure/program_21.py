
from factorio_instance import *

"""
Step 1: Print recipes. We need to print out the recipes for the following items:
- transport-belt
- underground-belt
- stone-furnace
- iron-plate
- iron-gear-wheel
- burner-mining-drill
"""
# Print recipes for required items
print("Recipes:")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (crafts 2)")
print("Underground Belt: 10 iron gear wheels, 10 iron plates (crafts 2)")
print("Stone Furnace: 5 stone")
print("Iron Plate: Smelt 1 iron ore")
print("Iron Gear Wheel: 2 iron plates")
print("Burner Mining Drill: 3 iron gear wheels, 3 iron plates, 1 stone furnace")


"""
Step 2: Gather resources.
We need to gather the following resources:
- 12 stone (5 for stone furnace, 7 for underground belt)
- 25 iron ore (for iron plates)
- 2 coal (for fueling the furnace)
"""
# Define required resources
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 25),
    (Resource.Coal, 5)  # Extra for fueling
]

# Gather required resources
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather sufficient {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final inventory check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print(f"Final inventory: {final_inventory}")
print("Successfully gathered all required resources")


"""
Step 3: Craft and place stone furnace.
We need to craft 2 stone furnaces and place one of them for smelting.
"""
# Craft first stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
stone_furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Stone furnace placed at: {stone_furnace.position}")

# Craft second stone furnace for the drill recipe
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted second stone furnace for the drill recipe")

# Verify that we have a stone furnace for the drill recipe
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace for drill recipe"

print("Successfully crafted and placed stone furnace")


"""
Step 4: Smelt iron plates.
We need to smelt 25 iron ore into iron plates. This will require fueling the furnace with coal.
"""
# Move to the stone furnace
move_to(stone_furnace.position)

# Insert coal into the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 2, f"Not enough coal in inventory. Expected at least 2, but found {coal_in_inventory}"
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=2)
print("Inserted coal into the stone furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 25, f"Not enough iron ore in inventory. Expected at least 25, but found {iron_ore_in_inventory}"
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=25)
print("Inserted iron ore into the stone furnace")

# Wait for smelting to complete (assuming smelting time is 0.7 seconds per ore)
smelting_time = 0.7 * 25
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=25)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 25:
        break
    sleep(10)  # Wait a bit more if not all plates are ready
print(f"Extracted {iron_plates_in_inventory} iron plates from the stone furnace")

# Verify that we have smelted the required number of iron plates
assert iron_plates_in_inventory >= 25, f"Failed to smelt required number of iron plates. Expected: 25, Found: {iron_plates_in_inventory}"

print(f"Inventory after smelting: {inspect_inventory()}")
print("Successfully smelted required number of iron plates")


"""
Step 5: Craft iron gear wheels.
We need to craft 4 iron gear wheels (2 for transport belt, 2 for burner mining drill).
"""
# Craft 4 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=4)

# Verify that we have crafted the required number of iron gear wheels
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 4, f"Failed to craft required number of iron gear wheels. Expected: 4, Found: {iron_gear_wheels}"
print(f"Successfully crafted {iron_gear_wheels} iron gear wheels")

print(f"Inventory after crafting iron gear wheels: {inspect_inventory()}")


"""
Step 6: Craft transport belts.
We need to craft 12 transport belts (6 for transport belt, 6 for underground belt).
"""
# Craft 12 transport belts
craft_item(Prototype.TransportBelt, quantity=12)

# Verify that we have crafted the required number of transport belts
inventory = inspect_inventory()
transport_belts = inventory.get(Prototype.TransportBelt, 0)
assert transport_belts >= 12, f"Failed to craft required number of transport belts. Expected: 12, Found: {transport_belts}"
print(f"Successfully crafted {transport_belts} transport belts")

print(f"Inventory after crafting transport belts: {inspect_inventory()}")


"""
Step 7: Craft underground belts.
We need to craft 4 underground belts.
"""
# Craft 4 underground belts
craft_item(Prototype.UndergroundBelt, quantity=4)

# Verify that we have crafted the required number of underground belts
inventory = inspect_inventory()
underground_belts = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 4, f"Failed to craft required number of underground belts. Expected: 4, Found: {underground_belts}"
print(f"Successfully crafted {underground_belts} underground belts")

print(f"Inventory after crafting underground belts: {inspect_inventory()}")


"""
Step 8: Craft burner mining drill.
We need to craft 1 burner mining drill using 3 iron gear wheels, 3 iron plates, and 1 stone furnace.
"""
# Craft 1 burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Verify that we have crafted the burner mining drill
inventory = inspect_inventory()
burner_mining_drills = inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft burner mining drill. Expected: 1, Found: {burner_mining_drills}"
print(f"Successfully crafted {burner_mining_drills} burner mining drill")

print(f"Final inventory: {inspect_inventory()}")
