
# Check initial inventory
initial_inventory = inspect_inventory()
print("Initial inventory:", initial_inventory)

# Craft iron gear wheels
iron_plates_needed = 40
assert initial_inventory.get(Prototype.IronPlate) >= iron_plates_needed, f"Not enough iron plates. Need {iron_plates_needed}, have {initial_inventory.get(Prototype.IronPlate)}"

gear_wheels_crafted = craft_item(Prototype.IronGearWheel, 20)
assert gear_wheels_crafted == 20, f"Failed to craft 20 iron gear wheels. Only crafted {gear_wheels_crafted}"

# Check inventory after crafting gear wheels
inventory_after_gears = inspect_inventory()
print("Inventory after crafting gear wheels:", inventory_after_gears)

assert inventory_after_gears.get(Prototype.IronGearWheel) >= 20, f"Not enough iron gear wheels. Have {inventory_after_gears.get(Prototype.IronGearWheel)}, need 20"
assert inventory_after_gears.get(Prototype.CopperPlate) >= 20, f"Not enough copper plates. Have {inventory_after_gears.get(Prototype.CopperPlate)}, need 20"

# Craft automation science packs
science_packs_crafted = craft_item(Prototype.AutomationSciencePack, 20)
assert science_packs_crafted == 20, f"Failed to craft 20 automation science packs. Only crafted {science_packs_crafted}"

# Check final inventory
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

assert final_inventory.get(Prototype.AutomationSciencePack) >= 20, f"Objective not met. Have {final_inventory.get(Prototype.AutomationSciencePack)} automation science packs, need 20"

print("Successfully crafted 20 automation science packs!")
