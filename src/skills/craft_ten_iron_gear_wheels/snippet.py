
# Check initial inventory
initial_inventory = inspect_inventory()
print(f"Initial inventory: {initial_inventory}")

# Ensure we have enough iron plates
assert initial_inventory.get(Prototype.IronPlate, 0) >= 20, "Not enough iron plates to craft 10 iron gear wheels"

# Craft iron gear wheels
crafted = craft_item(Prototype.IronGearWheel, 10)
print(f"Crafted {crafted} iron gear wheels")

# Verify crafting result
assert crafted == 10, f"Failed to craft 10 iron gear wheels, only crafted {crafted}"

# Check final inventory
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify iron gear wheels in inventory
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 10, f"Expected at least 10 iron gear wheels in inventory, but found {final_inventory.get(Prototype.IronGearWheel, 0)}"

# Verify iron plates were consumed
iron_plates_used = initial_inventory.get(Prototype.IronPlate, 0) - final_inventory.get(Prototype.IronPlate, 0)
assert iron_plates_used == 20, f"Expected to use 20 iron plates, but used {iron_plates_used}"

print("Successfully crafted 10 iron gear wheels")
