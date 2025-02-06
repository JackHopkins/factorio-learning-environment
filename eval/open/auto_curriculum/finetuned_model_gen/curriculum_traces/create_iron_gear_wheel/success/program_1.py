

from instance import *

"""
Step 1: Print recipes
"""
# Get recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get recipe for iron plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print(f"Iron Plate Recipe: {iron_plate_recipe}")

# Get recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get recipe for firearm magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print(f"Firearm Magazine Recipe: {firearm_magazine_recipe}")

"""
Step 2: Gather raw resources
"""
# Define required resources
resources_to_gather = [
    (Resource.IronOre, 16),
    (Resource.Coal, 2),
    (Resource.Stone, 6)  # Need 5 for furnace, 1 extra
]

# Gather each resource
for resource_type, required_quantity in resources_to_gather:
    print(f"Gathering {required_quantity} of {resource_type}...")
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} of {resource_type}")

print(f"Final inventory after gathering: {inspect_inventory()}")

"""
Step 3: Craft stone furnace
"""
print("Crafting stone furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"
print("Successfully crafted stone furnace")

"""
Step 4: Set up smelting operation
"""
# Place the furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert coal into the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
    print(f"Inserted {coal_in_inventory} coal into the furnace")
else:
    print("No coal available in inventory!")

# Insert iron ore into the furnace for smelting
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
    print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")
else:
    print("No iron ore available in inventory!")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 seconds per ore
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(5)

print(f"Extracted iron plates; Current inventory: {inspect_inventory()}")

"""
Step 5: Craft iron gear wheel
"""
print("Crafting iron gear wheel...")
craft_item(Prototype.IronGearWheel, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 1, "Failed to craft iron gear wheel"
print("Successfully crafted iron gear wheel")

"""
Step 6: Craft firearm magazine
"""
print("Crafting firearm magazine...")
craft_item(Prototype.FirearmMagazine, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Failed to craft firearm magazine"
print("Successfully crafted firearm magazine")

"""
Final inventory check
"""
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify final inventory
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 1, "Iron gear wheel not found in final inventory"
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Firearm magazine not found in final inventory"
print("Successfully completed the objective of creating iron gear wheel and firearm magazine!")

