
from factorio_instance import *

"""
Step 1: Craft a stone furnace
- We need 5 stone to craft a stone furnace
- There are no furnaces on the map or in our inventory
- We need to mine stone
"""
# Find the nearest stone patch
stone_position = nearest(Resource.Stone)
print(f"Nearest stone patch found at: {stone_position}")

# Move to the stone patch
move_to(stone_position)
print(f"Moved to stone patch at: {stone_position}")

# Mine 5 stone
harvested_stone = harvest_resource(stone_position, quantity=5)
print(f"Harvested {harvested_stone} stone")

# Check if we successfully harvested 5 stone
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone) >= 5, f"Failed to gather enough stone. Current inventory: {current_inventory}"

# Craft the stone furnace
crafted = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted} stone furnace(s)")

# Verify that we have a stone furnace in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace) >= 1, f"Failed to craft stone furnace. Current inventory: {current_inventory}"

print("Successfully crafted a stone furnace")

"""
Step 2: Set up iron plate production
- Place the stone furnace
- Mine iron ore
- Insert iron ore and coal into the furnace
- Wait for smelting and extract iron plates
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at: {furnace.position}")

# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=10)
print(f"Harvested {harvested_iron_ore} iron ore")

# Move back to the furnace
move_to(furnace.position)

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, furnace, quantity=10)
print(f"Inserted iron ore into the furnace")

# Insert coal into the furnace for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvested_coal = harvest_resource(coal_position, quantity=5)
move_to(furnace.position)
updated_furnace = insert_item(Prototype.Coal, updated_furnace, quantity=5)
print(f"Inserted coal into the furnace")

# Wait for smelting to complete
sleep(10)
print("Smelting complete")

# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
print("Extracted iron plates")

# Verify that we have produced iron plates
final_inventory = inspect_inventory()
produced_iron_plates = final_inventory.get(Prototype.IronPlate, 0)
assert produced_iron_plates >= 10, f"Failed to produce enough iron plates. Produced: {produced_iron_plates}"

print(f"Successfully produced {produced_iron_plates} iron plates")
