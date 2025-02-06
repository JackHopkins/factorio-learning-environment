
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft.
"""
# Print recipe for burner-mining-drill
print("Burner Mining Drill Recipe:")
print("3 iron gear wheels (6 iron plates)")
print("1 stone furnace (5 stone)")

# Print recipe for stone furnace
print("\nStone Furnace Recipe:")
print("5 stone")

# Print recipe for iron gear wheel
print("\nIron Gear Wheel Recipe:")
print("2 iron plates per gear wheel")

"""
Step 2: Gather raw resources. We need to mine iron ore, stone, and coal.
"""
# Define required quantities
required_iron_ore = 8  # 6 for gear wheels, 2 extra for safety
required_stone = 5     # 5 for stone furnace
required_coal = 2      # for smelting fuel

# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, required_iron_ore)
print(f"Mined {required_iron_ore} iron ore")

# Mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, required_stone)
print(f"Mined {required_stone} stone")

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, required_coal)
print(f"Mined {required_coal} coal")

# Verify gathered resources
inventory = inspect_inventory()
assert inventory.get("iron-ore") >= required_iron_ore, f"Failed to gather enough iron ore. Inventory: {inventory}"
assert inventory.get("stone") >= required_stone, f"Failed to gather enough stone. Inventory: {inventory}"
assert inventory.get("coal") >= required_coal, f"Failed to gather enough coal. Inventory: {inventory}"

print("Successfully gathered all required resources")

"""
Step 3: Craft and set up smelting infrastructure. We need to craft a stone furnace and set it up for smelting.
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_quantity = 2
insert_item(Prototype.Coal, furnace, quantity=coal_quantity)
print(f"Inserted {coal_quantity} coal into the furnace")

"""
Step 4: Smelt iron plates. We need to smelt iron ore into iron plates.
"""
# Insert iron ore into the furnace
iron_ore_quantity = 8
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_quantity)
print(f"Inserted {iron_ore_quantity} iron ore into the furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_quantity)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_quantity)
    current_iron_plates = inspect_inventory().get("iron-plate", 0)
    if current_iron_plates >= iron_ore_quantity:
        break
    sleep(5)

print(f"Extracted {current_iron_plates} iron plates from the furnace")
assert current_iron_plates >= 6, f"Failed to smelt enough iron plates. Current inventory: {inspect_inventory()}"

"""
Step 5: Craft intermediate products. We need to craft iron gear wheels.
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 iron gear wheels")

# Verify crafted items
inventory = inspect_inventory()
assert inventory.get("iron-gear-wheel") >= 3, f"Failed to craft enough iron gear wheels. Inventory: {inventory}"

"""
Step 6: Craft burner-mining-drill. We need to craft the final product.
"""
# Craft burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner-mining-drill")

# Verify crafted item
inventory = inspect_inventory()
assert inventory.get("burner-mining-drill") >= 1, f"Failed to craft burner-mining-drill. Inventory: {inventory}"

print("Successfully crafted a burner-mining-drill!")

# Final inventory check
final_inventory = inspect_inventory()
print("\nFinal Inventory:")
print(f"Iron Ore: {final_inventory.get('iron-ore', 0)}")
print(f"Stone: {final_inventory.get('stone', 0)}")
print(f"Coal: {final_inventory.get('coal', 0)}")
print(f"Iron Plates: {final_inventory.get('iron-plate', 0)}")
print(f"Iron Gear Wheels: {final_inventory.get('iron-gear-wheel', 0)}")
print(f"Burner Mining Drill: {final_inventory.get('burner-mining-drill', 0)}")
