

from factorio_instance import *

"""
Step 1: Gather resources
- Mine iron ore (at least 10)
- Mine coal (at least 5)
- Mine stone (at least 5 for furnace)
"""
# Define required resources
required_resources = [
    (Resource.IronOre, 20),
    (Resource.Coal, 10),
    (Resource.Stone, 10),
]

# Gather resources
for resource_type, required_quantity in required_resources:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print(f"Final inventory after gathering resources: {inspect_inventory()}")


"""
Step 2: Set up smelting
- Craft a stone furnace
- Place the stone furnace
- Add coal to the furnace as fuel
- Smelt iron ore into iron plates (at least 20)
"""
# Craft and place stone furnace
craft_item(Prototype.StoneFurnace)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Add coal to furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 5, f"Expected at least 5 coal in inventory, but found {coal_in_inventory}"
insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the furnace")

# Smelt iron ore
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 10, f"Expected at least 10 iron ore in inventory, but found {iron_ore_in_inventory}"
insert_item(Prototype.IronOre, furnace, quantity=10)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to smelt enough iron plates. Expected at least 10, but found {iron_plates}"
print(f"Smelted {iron_plates} iron plates")

# Repeat smelting process for additional iron plates
insert_item(Prototype.Coal, furnace, quantity=5)
insert_item(Prototype.IronOre, furnace, quantity=10)
sleep(10)
extract_item(Prototype.IronPlate, furnace.position, quantity=10)
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 20, f"Failed to smelt enough iron plates. Expected at least 20, but found {iron_plates}"
print(f"Total iron plates after smelting: {iron_plates}")


"""
Step 3: Craft intermediate products
- Craft 2 iron gear wheels (requires 4 iron plates)
- Craft 2 underground belts (requires 2 iron gear wheels and 2 transport belts)
  - Craft 2 transport belts (requires 2 iron gear wheels and 2 iron plates)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=4)
print(f"Crafted 4 Iron Gear Wheels. Current inventory: {inspect_inventory()}")

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=2)
print(f"Crafted 2 Transport Belts. Current inventory: {inspect_inventory()}")

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted 2 Underground Belts. Current inventory: {inspect_inventory()}")


"""
Step 4: Craft fast-underground-belt
- Craft 1 fast-underground-belt (requires 2 underground-belts and 1 iron gear wheel)
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted 1 Fast Underground Belt. Current inventory: {inspect_inventory()}")

# Verify that we have crafted the fast-underground-belt
fast_underground_belts = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to craft fast-underground-belt. Expected at least 1, but found {fast_underground_belts}"

print("Successfully crafted fast-underground-belt!")

