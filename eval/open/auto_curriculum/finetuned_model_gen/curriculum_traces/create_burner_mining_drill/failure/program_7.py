
from instance import *

"""
Step 1: Gather raw resources
- Mine stone for the stone furnace
- Mine iron ore for iron plates and gear wheels
- Mine coal for smelting
"""
# Move to and mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=6)
print("Mined 6 stone")

# Move to and mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=26)
print("Mined 26 iron ore")

# Move to and mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=2)
print("Mined 2 coal")

# Verify resources in inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 6, "Not enough stone"
assert inventory.get(Prototype.IronOre) >= 26, "Not enough iron ore"
assert inventory.get(Prototype.Coal) >= 2, "Not enough coal"
print(f"Inventory after gathering: {inventory}")

"""
Step 2: Craft and set up stone furnace
- Craft a stone furnace
- Place the furnace
- Add coal to the furnace as fuel
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place furnace near player
player_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_pos[0]+2, y=player_pos[1]))
print(f"Placed furnace at {furnace.position}")

# Add coal to furnace
insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted 2 coal into the furnace")

# Verify coal was inserted successfully
furnace_inventory = inspect_inventory(furnace)
assert furnace_inventory.get(Prototype.Coal) >= 1, "Failed to insert coal into furnace"
print(f"Furnace inventory after fueling: {furnace_inventory}")

"""
Step 3: Smelt iron plates
- Smelt iron ore into iron plates
- We need 26 iron plates
"""
# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, quantity=26)
print("Inserted 26 iron ore into the furnace")

# Wait for smelting to complete
smelt_time_per_ore = 0.7  # approximate time per ore
total_smelt_time = int(smelt_time_per_ore * 26)
sleep(total_smelt_time)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=26)
print("Extracted iron plates")

# Verify we have enough iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 26, f"Need at least 26 iron plates, only have {inventory.get(Prototype.IronPlate)}"
print(f"Inventory after smelting: {inventory}")

"""
Step 4: Craft components and burner mining drill
- Craft 6 iron gear wheels
- Craft 1 burner mining drill (requires 3 iron gear wheels and 1 stone furnace)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=6)
print("Crafted 6 iron gear wheels")

# Craft stone furnace for burner mining drill
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace for burner mining drill")

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")

# Verify we have the burner mining drill
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner mining drill"
print(f"Inventory after crafting components and burner mining drill: {inventory}")

"""
Step 5: Craft additional items
- Craft 1 firearm magazine
- Craft 1 burner inserter
- Craft 4 transport belts
"""
# Craft firearm magazine
craft_item(Prototype.FirearmMagazine, quantity=1)
print("Crafted 1 firearm magazine")

# Craft burner inserter
craft_item(Prototype.BurnerInserter, quantity=1)
print("Crafted 1 burner inserter")

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 transport belts")

# Verify we have crafted all required items
inventory = inspect_inventory()
assert inventory.get(Prototype.FirearmMagazine) >= 1, "Failed to craft firearm magazine"
assert inventory.get(Prototype.BurnerInserter) >= 1, "Failed to craft burner inserter"
assert inventory.get(Prototype.TransportBelt) >= 4, "Failed to craft transport belts"
print(f"Inventory after crafting additional items: {inventory}")

print("Successfully completed all steps and crafted required items!")
