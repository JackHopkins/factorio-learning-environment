

from instance import *


"""
Policy to craft a fast-underground-belt from scratch

We need to craft the following intermediate items:
- 20 iron gear wheels
- 2 transport belts
- 2 underground belts

We need to gather and smelt the following resources:
- 40 iron plates (for iron gear wheels)
- 4 iron plates (for transport belts)
- 80 iron ore (to smelt into iron plates)
- 40 coal (to fuel the furnace for smelting)
"""

"""
Step 1: Print recipes
"""
# Print recipes for intermediate items
print("Iron Gear Wheel Recipe: 2 iron plates")
print("Transport Belt Recipe: 1 iron gear wheel, 1 iron plate")
print("Underground Belt Recipe: 10 iron gear wheels, 1 transport belt")
print("Fast Underground Belt Recipe: 10 iron gear wheels, 2 underground belts")

"""
Step 2: Gather resources
- Mine 80 iron ore
- Mine 40 coal
"""
# Find nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Mine iron ore
iron_ore_needed = 80
iron_ore_mined = harvest_resource(iron_ore_position, iron_ore_needed)
print(f"Mined {iron_ore_mined} iron ore")

# Verify iron ore quantity
inventory = inspect_inventory()
actual_iron_ore = inventory.get(Prototype.IronOre, 0)
assert actual_iron_ore >= iron_ore_needed, f"Failed to gather enough iron ore. Expected: {iron_ore_needed}, Actual: {actual_iron_ore}"
print(f"Successfully gathered {actual_iron_ore} iron ore")

# Find nearest coal patch
coal_position = nearest(Resource.Coal)
print(f"Nearest coal found at: {coal_position}")

# Move to coal patch
move_to(coal_position)
print(f"Moved to coal patch at: {coal_position}")

# Mine coal
coal_needed = 40
coal_mined = harvest_resource(coal_position, coal_needed)
print(f"Mined {coal_mined} coal")

# Verify coal quantity
inventory = inspect_inventory()
actual_coal = inventory.get(Prototype.Coal, 0)
assert actual_coal >= coal_needed, f"Failed to gather enough coal. Expected: {coal_needed}, Actual: {actual_coal}"
print(f"Successfully gathered {actual_coal} coal")

# Final inventory check
print(f"Final inventory: {inventory}")
assert inventory.get(Prototype.IronOre, 0) >= 80, "Not enough Iron Ore"
assert inventory.get(Prototype.Coal, 0) >= 40, "Not enough Coal"

print("Successfully gathered all required resources!")


"""
Step 3: Smelt iron plates
- Smelt 80 iron ore into 80 iron plates
"""
# We need a furnace for smelting
# Check if we have a stone furnace or need to craft one
inventory = inspect_inventory()
if inventory.get(Prototype.StoneFurnace) < 1:
    # We need 5 stone to craft a stone furnace
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    harvest_resource(stone_position, quantity=5)
    craft_item(Prototype.StoneFurnace, 1)

# Place the furnace at the current position
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))

# Add coal to the furnace
insert_item(Prototype.Coal, furnace, quantity=40)

# Add iron ore to the furnace
insert_item(Prototype.IronOre, furnace, quantity=80)

# Wait for smelting to complete
smelting_time = 80 * 0.7  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=80)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 80:
        break
    sleep(10)

# Verify iron plate quantity
assert inventory.get(Prototype.IronPlate, 0) >= 80, f"Failed to smelt enough iron plates. Expected: 80, Actual: {inventory.get(Prototype.IronPlate, 0)}"
print(f"Successfully smelted {inventory.get(Prototype.IronPlate, 0)} iron plates")

# Clean up: Remove the furnace
pickup_entity(Prototype.StoneFurnace, furnace.position)


"""
Step 4: Craft iron gear wheels
- Craft 40 iron gear wheels
"""
craft_item(Prototype.IronGearWheel, 40)
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 40, f"Failed to craft enough iron gear wheels. Expected: 40, Actual: {inventory.get(Prototype.IronGearWheel, 0)}"
print(f"Successfully crafted {inventory.get(Prototype.IronGearWheel, 0)} iron gear wheels")


"""
Step 5: Craft transport belts
- Craft 4 transport belts
"""
craft_item(Prototype.TransportBelt, 4)
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt, 0) >= 4, f"Failed to craft enough transport belts. Expected: 4, Actual: {inventory.get(Prototype.TransportBelt, 0)}"
print(f"Successfully crafted {inventory.get(Prototype.TransportBelt, 0)} transport belts")


"""
Step 6: Craft underground belts
- Craft 2 underground belts
"""
craft_item(Prototype.UndergroundBelt, 2)
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 2, f"Failed to craft enough underground belts. Expected: 2, Actual: {inventory.get(Prototype.UndergroundBelt, 0)}"
print(f"Successfully crafted {inventory.get(Prototype.UndergroundBelt, 0)} underground belts")


"""
Step 7: Craft fast-underground-belt
- Craft 1 fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, f"Failed to craft fast-underground-belt. Expected: 1, Actual: {inventory.get(Prototype.FastUndergroundBelt, 0)}"
print(f"Successfully crafted {inventory.get(Prototype.FastUndergroundBelt, 0)} fast-underground-belt")


"""
Step 8: Verify crafting
- Check if we have successfully crafted a fast-underground-belt
"""
# Check final inventory
final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft fast-underground-belt. Expected at least 1, but got {fast_underground_belt_count}"
print(f"Final inventory: {final_inventory}")
print(f"Successfully crafted {fast_underground_belt_count} fast-underground-belt(s)")

print("Objective achieved: Successfully crafted fast-underground-belt!")

