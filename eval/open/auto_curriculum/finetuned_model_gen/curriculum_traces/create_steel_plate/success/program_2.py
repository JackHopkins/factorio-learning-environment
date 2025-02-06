

from instance import *

"""
Step 1: Place stone-furnace from inventory
- Move to the stone-furnace on the map
- Place the stone-furnace from our inventory next to it
"""
# Move to the existing stone-furnace on the map
furnace_on_map = get_entities({Prototype.StoneFurnace})[0]
move_to(furnace_on_map.position)

# Place the stone-furnace from inventory next to the existing one
furnace_inventory = place_entity_next_to(Prototype.StoneFurnace, furnace_on_map.position, direction=Direction.RIGHT, spacing=1)
assert furnace_inventory is not None, "Failed to place stone-furnace from inventory"

"""
Step 2: Insert iron plates and fuel
- Move to the inventory stone-furnace
- Insert 5 iron plates into it
- Insert coal into the stone-furnace to fuel it
"""
# Move to the stone-furnace from inventory
move_to(furnace_inventory.position)

# Insert 5 iron plates into the stone-furnace
insert_item(Prototype.IronPlate, furnace_inventory, quantity=5)
print("Inserted 5 iron plates into the stone-furnace")

# Insert coal into the stone-furnace to fuel it
insert_item(Prototype.Coal, furnace_inventory, quantity=1)
print("Inserted coal into the stone-furnace")

"""
Step 3: Wait for steel plate to be produced
- Wait for the steel plate to be produced (5 iron plates smelt into 1 steel plate)
"""
# Wait for the steel plate to be produced (5 iron plates smelt into 1 steel plate)
sleep(10)  # Wait for 10 seconds to allow smelting

"""
Step 4: Extract steel plate
- Extract the steel plate from the inventory stone-furnace
"""
# Extract the steel plate from the stone-furnace
inventory = inspect_inventory(furnace_inventory)
steel_plates = inventory.get(Prototype.SteelPlate, 0)

if steel_plates > 0:
    extract_item(Prototype.SteelPlate, furnace_inventory.position, quantity=steel_plates)
    print(f"Extracted {steel_plates} steel plates from the stone-furnace")
else:
    print("No steel plates found in the stone-furnace")

"""
Step 5: Verify steel plate production
- Check our inventory to confirm we have the steel plate
"""
# Check our inventory for the steel plate
player_inventory = inspect_inventory()
steel_plates_in_inventory = player_inventory.get(Prototype.SteelPlate, 0)

assert steel_plates_in_inventory >= 1, f"Failed to produce steel plate. Expected at least 1, but found {steel_plates_in_inventory}"
print(f"Successfully produced {steel_plates_in_inventory} steel plate(s)")

