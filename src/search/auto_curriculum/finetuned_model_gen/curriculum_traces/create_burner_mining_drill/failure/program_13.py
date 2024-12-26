
from factorio_instance import *


"""
Step 1: Gather raw resources
- Mine at least 3 iron ore
- Mine at least 5 stone
- Mine at least 2 coal for fuel
"""
# Find and move to the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
# Mine 3 iron ore
iron_ore_mined = harvest_resource(iron_ore_position, quantity=3)
# Verify we mined enough
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronOre, 0) >= 3, "Failed to mine enough iron ore"

# Find and move to the nearest stone patch
stone_position = nearest(Resource.Stone)
move_to(stone_position)
# Mine 5 stone
stone_mined = harvest_resource(stone_position, quantity=5)
# Verify we mined enough
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone, 0) >= 5, "Failed to mine enough stone"

# Find and move to the nearest coal patch
coal_position = nearest(Resource.Coal)
move_to(coal_position)
# Mine 2 coal
coal_mined = harvest_resource(coal_position, quantity=2)
# Verify we mined enough
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Coal, 0) >= 2, "Failed to mine enough coal"

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after mining:", final_inventory)
assert final_inventory.get(Prototype.IronOre, 0) >= 3, "Insufficient iron ore"
assert final_inventory.get(Prototype.Stone, 0) >= 5, "Insufficient stone"
assert final_inventory.get(Prototype.Coal, 0) >= 2, "Insufficient coal"

print("Successfully gathered all required resources")

"""
Step 2: Craft stone furnace
- Use 5 stone to craft 1 stone furnace
"""
# Verify we have enough stone
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone, 0) >= 5, "Not enough stone to craft furnace"

# Craft stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, "Failed to craft stone furnace"

# Verify stone furnace is in inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Stone furnace not found in inventory"
print("Successfully crafted stone furnace")

"""
Step 3: Smelt iron plates
- Place the stone furnace
- Add coal as fuel
- Smelt 3 iron ore into 3 iron plates
"""
# Place the furnace at current position
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))
assert furnace is not None, "Failed to place stone furnace"

# Add coal to the furnace as fuel
updated_fuel_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
assert updated_fuel_furnace.fuel.get(Prototype.Coal, 0) >= 1, "Failed to fuel furnace"

# Add iron ore to the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_ore_furnace = insert_item(Prototype.IronOre, updated_fuel_furnace, quantity=iron_ore_in_inventory)
assert updated_ore_furnace.furnace_source.get(Prototype.IronOre, 0) >= 1, "Failed to insert iron ore"

# Wait for smelting
sleep(5)

# Extract iron plates
iron_plates_in_inventory_before = inspect_inventory().get(Prototype.IronPlate, 0)
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_ore_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory_after = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory_after >= iron_plates_in_inventory_before + 3:
        break
    sleep(1)

# Verify we have enough iron plates
assert iron_plates_in_inventory_after >= iron_plates_in_inventory_before + 3, "Failed to obtain enough iron plates"
print(f"Successfully obtained {iron_plates_in_inventory_after} iron plates")

"""
Step 4: Craft iron gear wheel
- Use 2 iron plates to craft 1 iron gear wheel
"""
# Verify we have enough iron plates
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronPlate, 0) >= 3, "Not enough iron plates to craft iron gear wheel"

# Craft iron gear wheel
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)
assert crafted_gear_wheels == 1, "Failed to craft iron gear wheel"

# Verify iron gear wheel is in inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 1, "Iron gear wheel not found in inventory"
print("Successfully crafted iron gear wheel")

"""
Step 5: Craft burner mining drill
- Use 1 iron gear wheel, 3 iron plates, and 1 stone furnace to craft 1 burner mining drill
"""
# Verify we have all required materials
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 1, "Missing iron gear wheel"
assert current_inventory.get(Prototype.IronPlate, 0) >= 3, "Missing iron plates"
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Missing stone furnace"

# Craft burner mining drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
assert crafted_drills == 1, "Failed to craft burner mining drill"

# Verify burner mining drill is in inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Burner mining drill not found in inventory"
print("Successfully crafted burner mining drill")

"""
Step 6: Verify that the burner mining drill is in the inventory
"""
# Final inventory check
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Burner mining drill not found in final inventory"
print("Burner mining drill successfully created and verified in inventory")
