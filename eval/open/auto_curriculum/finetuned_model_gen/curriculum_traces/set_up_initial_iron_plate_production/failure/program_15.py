

from instance import *

"""
Policy to set up initial iron plate production
"""

"""
Step 1: Print recipes
"""
print("Recipes needed:")
print("Burner Mining Drill: 3 iron gear wheels, 3 iron plates, 1 stone furnace")
print("Stone Furnace: 5 stone")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (crafts 2 belts)")
print("Iron Gear Wheel: 2 iron plates")

"""
Step 2: Gather raw resources
"""
resources_to_gather = [
    (Resource.IronOre, 10),
    (Resource.Stone, 5),
    (Resource.Coal, 5)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

"""
Step 3: Craft stone furnace
"""
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 Stone Furnace")

"""
Step 4: Craft burner mining drill
"""
craft_item(Prototype.IronGearWheel, 3)
craft_item(Prototype.BurnerMiningDrill, 1)
print("Crafted 1 Burner Mining Drill")

"""
Step 5: Craft transport belts
"""
craft_item(Prototype.IronGearWheel, 1)
craft_item(Prototype.TransportBelt, 2)
print("Crafted 2 Transport Belts")

"""
Step 6: Set up mining and smelting area
"""
# Place burner mining drill
iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
move_to(iron_ore_patch.bounding_box.center)
drill = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.center)
assert drill, "Failed to place Burner Mining Drill"
print("Placed Burner Mining Drill")

# Place stone furnace
furnace = place_entity_next_to(Prototype.StoneFurnace, drill.position, direction=Direction.RIGHT, spacing=2)
assert furnace, "Failed to place Stone Furnace"
print("Placed Stone Furnace")

# Connect with transport belts
belts = connect_entities(drill.drop_position, furnace.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to furnace with transport belts"
print("Connected drill to furnace with transport belts")

# Place and rotate inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.RIGHT)
inserter = rotate_entity(inserter, Direction.LEFT)
assert inserter, "Failed to place or rotate inserter"
print("Placed and rotated inserter")

# Fuel entities
insert_item(Prototype.Coal, drill, 2)
insert_item(Prototype.Coal, furnace, 2)
insert_item(Prototype.Coal, inserter, 1)
print("Fueled entities")

"""
Step 7: Start production and verification
"""
move_to(furnace.position)  # Move near the furnace to collect plates
sleep(30)  # Wait for production

# Extract iron plates
for _ in range(5):  # Try multiple times to ensure we get all plates
    extract_item(Prototype.IronPlate, furnace.position, 10)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 10:
        break
    sleep(5)

assert current_iron_plate_count >= 10, f"Failed to produce enough Iron Plates. Expected: 10, Actual: {current_iron_plate_count}"
print(f"Successfully produced {current_iron_plate_count} Iron Plates")

