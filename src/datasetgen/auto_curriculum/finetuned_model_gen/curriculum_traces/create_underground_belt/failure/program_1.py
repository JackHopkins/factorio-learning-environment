
from factorio_instance import *

"""
Step 1: Print recipes. We need to print recipes for:
- Underground Belt
- Transport Belt
- Iron Gear Wheel
- Stone Furnace
- Iron Plate
"""
# Print recipe for Underground Belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {underground_belt_recipe}")

# Print recipe for Transport Belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Transport Belt Recipe: {transport_belt_recipe}")

# Print recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Print recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Print recipe for Iron Plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print(f"Iron Plate Recipe: {iron_plate_recipe}")

"""
Step 2: Craft and place stone furnaces. We need to:
- Craft 2 stone furnaces (need 10 stone)
- Place both stone furnaces
"""
# Gather stone for crafting furnaces
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=12)  # Gather extra for safety

# Craft two stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Place the first stone furnace
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=2))
print(f"First furnace placed at: {furnace1.position}")

# Place the second stone furnace
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=2))
print(f"Second furnace placed at: {furnace2.position}")

"""
Step 3: Gather resources. We need to:
- Mine 21 iron ore
- Mine 2 coal
"""
# Gather iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=21)

# Gather coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=2)

"""
Step 4: Smelt iron plates. We need to:
- Use both stone furnaces to smelt 21 iron ore into iron plates
"""
# Move back to the furnaces
move_to(furnace1.position)
# Add coal to both furnaces as fuel
insert_item(Prototype.Coal, furnace1, quantity=1)
insert_item(Prototype.Coal, furnace2, quantity=1)

# Insert iron ore into both furnaces
insert_item(Prototype.IronOre, furnace1, quantity=11)
insert_item(Prototype.IronOre, furnace2, quantity=10)

# Wait for smelting to complete
sleep(10)

# Extract iron plates from both furnaces
extract_item(Prototype.IronPlate, furnace1.position, quantity=11)
extract_item(Prototype.IronPlate, furnace2.position, quantity=10)

# Check inventory for iron plates
inventory = inspect_inventory()
print(f"Iron plates in inventory after extraction: {inventory.get(Prototype.IronPlate, 0)}")

"""
Step 5: Craft components. We need to:
- Craft 8 iron gear wheels (requires 16 iron plates)
- Craft 6 transport belts (requires 6 iron gear wheels and 6 iron plates)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=8)
print("Crafted 8 Iron Gear Wheels")

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=6)
print("Crafted 6 Transport Belts")

# Check inventory for crafted items
inventory = inspect_inventory()
print(f"Transport Belts in inventory after crafting: {inventory.get(Prototype.TransportBelt, 0)}")

"""
Step 6: Craft underground belt. We need to:
- Craft 1 underground belt (requires 10 iron plates and 1 transport belt)
"""
# Ensure we have enough iron plates and transport belts
assert inventory.get(Prototype.IronPlate, 0) >= 10, "Not enough Iron Plates"
assert inventory.get(Prototype.TransportBelt, 0) >= 1, "Not enough Transport Belts"

# Craft the underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 Underground Belt")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Assert that we have crafted the underground belt
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 1, "Failed to craft Underground Belt"

print("Successfully crafted Underground Belt!")

