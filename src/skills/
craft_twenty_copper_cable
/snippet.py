
# Inspect inventory to check how many copper plates we currently have
inventory = inspect_inventory()
print("Current Inventory:", inventory)

# Constants for crafting
required_copper_plates = 20

# Check if we have enough copper plates in the inventory
available_copper_plates = inventory.get('copper-plate', 0)
assert available_copper_plates >= required_copper_plates, (
    f"Not enough copper plates. Required: {required_copper_plates}, Available: {available_copper_plates}"
)

# Craft 20 copper cables
craft_successful = craft_item(Prototype.CopperCable, quantity=20)
assert craft_successful, "Crafting of Copper Cable failed."

# Verify that 20 copper cables were crafted by checking the new state of the inventory
new_inventory = inspect_inventory()
crafted_cable_count = new_inventory.get('copper-cable', 0) - inventory.get('copper-cable', 0)
assert crafted_cable_count == required_copper_plates, (
    f"Copper cable crafting count mismatch. Expected: {required_copper_plates}, Crafted: {crafted_cable_count}"
)

print("Crafted Copper Cables:", crafted_cable_count)
