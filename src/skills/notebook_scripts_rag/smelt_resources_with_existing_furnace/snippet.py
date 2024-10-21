
# first get the stone furnace entity
# This will give us all the entities of type stone furnace
stone_furnaces = get_entities({Prototype.StoneFurnace})
# We can get the first one as we know there is only one stone furnace
stone_furnace = stone_furnaces[0]

# Extract the existing iron plates from the furnace
iron_plates_in_furnace = stone_furnace.furnace_result.get(Prototype.IronPlate, 0)
extract_item(Prototype.IronPlate, stone_furnace.position, iron_plates_in_furnace)
print(f"Extracted {iron_plates_in_furnace} iron plates from the furnace")

# get the coal and iron ore in the inventory
coal_in_inventory = inspect_inventory()[Prototype.Coal]
iron_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Coal in inventory: {coal_in_inventory}")
print(f"Iron ore in inventory: {iron_in_inventory}")

# add coal and iron to the furnace
# Need to update the furnace var as well after every insert
stone_furnace =insert_item(Prototype.Coal, stone_furnace, coal_in_inventory)
stone_furnace =insert_item(Prototype.IronOre, stone_furnace, iron_in_inventory)
print(f"Inserted {coal_in_inventory} coal and {iron_in_inventory} iron ore into the furnace")
print(f"Inventory after inserting: {inspect_inventory()}")

# Get the initial number of iron plates in the inventory and the expecected number of plates
# This is used to check how many plates we have after smelting
# This is important to know if we have smelted enough plates
initial_iron_plates = inspect_inventory()[Prototype.IronPlate]
expected_iron_plates = initial_iron_plates + iron_in_inventory

# Wait for smelting to complete, 0.7 seconds per iron ore
sleep(iron_in_inventory * 0.7)
max_attempts = 5
for _ in range(max_attempts):
    # IMPORTANT: Always try to extract the exact number of items you need
    # It is OK to extract more than the furnace has
    extract_item(Prototype.IronPlate, stone_furnace.position, iron_in_inventory)
    # IMPORTANT: To check the extraction, you need to check the amount of iron plates in the inventory
    # After every extraction, check how many plates you have in your inventory
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    # If you have enough plates, i.e more or equal than expected
    # break out of the loop
    if iron_plates_in_inventory >= expected_iron_plates:
        break
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted {iron_in_inventory} iron plates from the furnace")
print(f"Inventory after extracting: {inspect_inventory()}")
# Check if we have more than input_iron_ore iron plates
iron_in_inventory = inspect_inventory()[Prototype.IronPlate]
assert iron_in_inventory >= expected_iron_plates, f"Failed to smelt enough iron plates. Expected more than {iron_in_inventory}, but got {iron_in_inventory}"

