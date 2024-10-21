
# Check initial inventory
initial_inventory = inspect_inventory()
initial_copper_cable = initial_inventory.get(Prototype.CopperCable, 0)
print(f"Initial copper cable: {initial_copper_cable}")

# Craft copper cable
crafted = craft_item(Prototype.CopperCable, 20)
print(f"Crafted copper cable: {crafted}")

# Check if crafting was successful
assert crafted == 20, f"Failed to craft 20 copper cable. Only crafted {crafted}."

# Verify final inventory
final_inventory = inspect_inventory()
final_copper_cable = final_inventory.get(Prototype.CopperCable, 0)
print(f"Final copper cable: {final_copper_cable}")

# Assert that we have at least 20 more copper cable than we started with
assert final_copper_cable >= initial_copper_cable + 20, f"Expected at least {initial_copper_cable + 20} copper cable, but only have {final_copper_cable}"

print("Successfully crafted 20 copper cable!")
