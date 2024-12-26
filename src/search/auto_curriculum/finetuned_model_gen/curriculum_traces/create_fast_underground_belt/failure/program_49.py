
from factorio_instance import *

"""
Step 1: Print recipes for required items
"""
# Print recipe for fast-underground-belt
print("fast-underground-belt recipe:")
print("Crafting requires 2 underground belts, 40 iron gear wheels")

# Print recipe for underground-belt
print("\nunderground-belt recipe:")
print("Crafting requires 10 iron plates, 4 iron gear wheels")

# Print recipe for iron-gear-wheel
print("\niron-gear-wheel recipe:")
print("Crafting requires 2 iron plates")

"""
Step 2: Calculate required resources
- We need to gather enough iron ore to make at least 90 iron plates (80 for gear wheels, 10 for underground belts)
- We need to gather at least 5 stone to craft a stone furnace
"""
# Calculate total iron plates needed
iron_plates_for_gear_wheels = 2 * 40  # 40 iron gear wheels
iron_plates_for_underground_belts = 10
total_iron_plates_needed = iron_plates_for_gear_wheels + iron_plates_for_underground_belts

print(f"\nTotal iron plates needed: {total_iron_plates_needed}")

"""
Step 3: Gather resources
- Mine iron ore (at least 90)
- Mine stone (at least 5 for furnace)
"""
# Get iron ore
iron_ore_pos = nearest(Resource.IronOre)
move_to(iron_ore_pos)
harvest_resource(iron_ore_pos, quantity=100)

# Get stone
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=10)

# Check inventory
inventory = inspect_inventory()
print(f"Inventory after gathering resources: {inventory}")
assert inventory[Prototype.IronOre] >= 90, "Not enough iron ore"
assert inventory[Prototype.Stone] >= 5, "Not enough stone"

"""
Step 4: Craft stone furnace
- Use 5 stone to craft a stone furnace
"""
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 stone furnace")

"""
Step 5: Set up smelting area
- Place stone furnace
- Insert iron ore into furnace
- Fuel the furnace with coal
"""
# Place furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
move_to(furnace.position)

# Insert iron ore
insert_item(Prototype.IronOre, furnace, total_iron_plates_needed)
print(f"Inserted {total_iron_plates_needed} iron ore into the furnace")

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, 10)
print("Inserted 10 coal into the furnace")

"""
Step 6: Smelt iron plates
"""
# Wait for smelting
sleep(30)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, total_iron_plates_needed)
print(f"Extracted {total_iron_plates_needed} iron plates")

# Verify
inventory = inspect_inventory()
assert inventory[Prototype.IronPlate] >= total_iron_plates_needed, "Not enough iron plates"
print(f"Inventory after smelting: {inventory}")

"""
Step 7: Craft intermediate items
- Craft 40 iron gear wheels (using 80 iron plates)
- Craft 2 underground belts (using 10 iron plates and 4 gear wheels)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 40)
print("Crafted 40 iron gear wheels")

# Craft underground belts
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 underground belts")

# Verify intermediate items
inventory = inspect_inventory()
assert inventory[Prototype.IronGearWheel] >= 40, "Failed to craft enough iron gear wheels"
assert inventory[Prototype.UndergroundBelt] >= 2, "Failed to craft enough underground belts"
print(f"Inventory after crafting intermediate items: {inventory}")

"""
Step 8: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 fast-underground-belt")

# Verify final item
inventory = inspect_inventory()
assert inventory[Prototype.FastUndergroundBelt] >= 1, "Failed to craft fast-underground-belt"
print(f"Final inventory: {inventory}")

print("\nSuccessfully crafted fast-underground-belt!")
