
# Check initial inventory
initial_inventory = inspect_inventory()
initial_copper_plates = initial_inventory.get(Prototype.CopperPlate, 0)
initial_copper_cables = initial_inventory.get(Prototype.CopperCable, 0)

print(f"Initial copper plates: {initial_copper_plates}")
print(f"Initial copper cables: {initial_copper_cables}")

# Ensure we have enough copper plates (10 needed for 20 cables)
assert initial_copper_plates >= 10, f"Not enough copper plates. Need at least 10, but only have {initial_copper_plates}."

# Craft 20 copper cables
craft_success = craft_item(Prototype.CopperCable, 20)
assert craft_success, "Failed to craft copper cables."

# Check final inventory
final_inventory = inspect_inventory()
final_copper_plates = final_inventory.get(Prototype.CopperPlate, 0)
final_copper_cables = final_inventory.get(Prototype.CopperCable, 0)

print(f"Final copper plates: {final_copper_plates}")
print(f"Final copper cables: {final_copper_cables}")

# Verify that 20 copper cables were crafted
cables_crafted = final_copper_cables - initial_copper_cables
assert cables_crafted == 20, f"Expected to craft 20 copper cables, but crafted {cables_crafted}."

# Verify that 10 copper plates were consumed
plates_consumed = initial_copper_plates - final_copper_plates
assert plates_consumed == 10, f"Expected to consume 10 copper plates, but consumed {plates_consumed}."

print("Successfully crafted 20 copper cables!")
