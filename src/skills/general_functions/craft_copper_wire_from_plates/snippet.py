
# Check initial inventory
initial_inventory = inspect_inventory()
initial_copper_plates = initial_inventory.get(Prototype.CopperPlate, 0)
initial_copper_wire = initial_inventory.get(Prototype.CopperCable, 0)

print(f"Initial copper plates: {initial_copper_plates}")
print(f"Initial copper wire: {initial_copper_wire}")

# Assert we have enough copper plates to craft 5 copper wire
assert initial_copper_plates >= 3, f"Not enough copper plates. Need at least 3, but have {initial_copper_plates}."

# Craft 5 copper wire
craft_success = craft_item(Prototype.CopperCable, 5)
assert craft_success, "Failed to craft copper wire."

# Check final inventory
final_inventory = inspect_inventory()
final_copper_plates = final_inventory.get(Prototype.CopperPlate, 0)
final_copper_wire = final_inventory.get(Prototype.CopperCable, 0)

print(f"Final copper plates: {final_copper_plates}")
print(f"Final copper wire: {final_copper_wire}")

# Assert that we crafted exactly 5 copper wire
assert final_copper_wire == initial_copper_wire + 5, f"Expected to have {initial_copper_wire + 5} copper wire, but have {final_copper_wire}."

# Assert that we used the correct number of copper plates
expected_plates_used = 3  # 3 plates are needed to craft 5 wire
assert final_copper_plates == initial_copper_plates - expected_plates_used, f"Expected to use {expected_plates_used} copper plates, but used {initial_copper_plates - final_copper_plates}."

print("Successfully crafted 5 copper wire!")
