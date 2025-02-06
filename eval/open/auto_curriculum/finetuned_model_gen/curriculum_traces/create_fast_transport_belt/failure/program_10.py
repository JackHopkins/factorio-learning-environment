

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the entities we need to craft. 
"""
# Get the recipes for the required entities
recipes_to_print = [
    Prototype.FastTransportBelt,
    Prototype.TransportBelt,
    Prototype.IronGearWheel,
    Prototype.BurnerMiningDrill,
    Prototype.StoneFurnace
]

# Print the recipes
for recipe in recipes_to_print:
    print_recipe(recipe)

"""
Step 1: Gather resources
- Mine stone for furnaces
- Mine iron ore for plates and gear wheels
- Mine coal for fuel
"""
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 31),
    (Resource.Coal, 2)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Expected {required_quantity}, but got {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

assert final_inventory.get(Resource.Stone) >= 12, f"Insufficient Stone. Expected at least 12, but got {final_inventory.get(Resource.Stone)}"
assert final_inventory.get(Resource.IronOre) >= 31, f"Insufficient Iron Ore. Expected at least 31, but got {final_inventory.get(Resource.IronOre)}"
assert final_inventory.get(Resource.Coal) >= 2, f"Insufficient Coal. Expected at least 2, but got {final_inventory.get(Resource.Coal)}"

print("Successfully gathered all required resources")

"""
Step 2: Craft and place initial entities
- Craft 2 stone furnaces (1 for smelting, 1 for burner mining drill)
- Craft 1 burner mining drill
"""
# Craft stone furnaces
print("Crafting 2 Stone Furnaces")
crafted_furnaces = craft_item(Prototype.StoneFurnace, 2)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace) >= 2, f"Failed to craft 2 Stone Furnaces. Only have {current_inventory.get(Prototype.StoneFurnace)}"
print("Successfully crafted 2 Stone Furnaces")

# Craft burner mining drill
print("Crafting 1 Burner Mining Drill")
crafted_burner_mining_drill = craft_item(Prototype.BurnerMiningDrill, 1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.BurnerMiningDrill) >= 1, f"Failed to craft 1 Burner Mining Drill. Only have {current_inventory.get(Prototype.BurnerMiningDrill)}"
print("Successfully crafted 1 Burner Mining Drill")

"""
Step 3: Set up iron plate production
- Place the burner mining drill on an iron ore patch
- Place a stone furnace nearby
- Connect the drill to the furnace using an inserter
"""
# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the burner mining drill on the iron ore patch
burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, iron_ore_position)
print(f"Placed burner mining drill at: {burner_mining_drill.position}")

# Place the stone furnace next to the burner mining drill
furnace_position = Position(x=burner_mining_drill.position.x + 2, y=burner_mining_drill.position.y)
move_to(furnace_position)
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed stone furnace at: {stone_furnace.position}")

# Initialize the burner inserter
print("Crafting Burner Inserter")
crafted_burner_inserter = craft_item(Prototype.BurnerInserter, 1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.BurnerInserter) >= 1, f"Failed to craft Burner Inserter. Only have {current_inventory.get(Prototype.BurnerInserter)}"
print("Successfully crafted Burner Inserter")

# Place the burner inserter between the drill and furnace
print("Placing Burner Inserter")
move_to(Position(
    x=(burner_mining_drill.position.x + stone_furnace.position.x) / 2,
    y=(burner_mining_drill.position.y + stone_furnace.position.y) / 2
))
burner_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, Position(
    x=(burner_mining_drill.position.x + stone_furnace.position.x) / 2,
    y=(burner_mining_drill.position.y + stone_furnace.position.y) / 2
))
print(f"Placed burner inserter at: {burner_inserter.position}")

# Rotate the burner inserter to point towards the furnace
burner_inserter = rotate_entity(burner_inserter, Direction.RIGHT)
print("Rotated burner inserter to face the furnace")

# Connect the drill to the furnace using an inserter
print("Connecting drill to furnace with an inserter")
# Use the connect_entities function to connect the drill's output to the furnace's input
connection = connect_entities(burner_mining_drill.drop_position, burner_inserter.pickup_position, Prototype.TransportBelt)
assert connection, "Failed to connect drill to furnace with an inserter"


"""
Step 4: Fuel the drill and furnace
- Add coal to the burner mining drill
- Add coal to the stone furnace
"""
# Insert coal into the burner mining drill
print("Inserting coal into the burner mining drill")
updated_burner_mining_drill = insert_item(Prototype.Coal, burner_mining_drill, quantity=1)
coal_in_drill = updated_burner_mining_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to insert coal into the burner mining drill"
print("Successfully fueled burner mining drill")

# Insert coal into the stone furnace
print("Inserting coal into the stone furnace")
updated_stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=1)
coal_in_furnace = updated_stone_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to insert coal into the stone furnace"
print("Successfully fueled stone furnace")

"""
Step 5: Produce iron plates
- Wait for the furnace to produce iron plates
- Extract iron plates from the furnace
"""
# Wait for the furnace to smelt iron plates
smelting_time = 5  # seconds
print(f"Waiting for {smelting_time} seconds for iron plates to be smelted")
sleep(smelting_time)

# Extract iron plates from the stone furnace
print("Extracting iron plates from the stone furnace")
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_stone_furnace.position, quantity=5)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count > initial_iron_plate_count:
        break
    sleep(2)
print(f"Extracted iron plates; current inventory count: {current_iron_plate_count}")

# Verify that we have extracted some iron plates
assert current_iron_plate_count > initial_iron_plate_count, "Failed to extract any iron plates"
print("Successfully produced and extracted iron plates")


"""
Step 6: Craft intermediate products
- Craft iron plates into iron gear wheels
"""
# Craft Iron Gear Wheels
print("Crafting Iron Gear Wheels")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=5)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel) >= 5, f"Failed to craft 5 Iron Gear Wheels. Only have {current_inventory.get(Prototype.IronGearWheel)}"
print("Successfully crafted 5 Iron Gear Wheels")


"""
Step 7: Craft transport belt
- Craft a transport belt
"""
# Craft Transport Belt
print("Crafting Transport Belt")
crafted_transport_belt = craft_item(Prototype.TransportBelt, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.TransportBelt) >= 1, f"Failed to craft 1 Transport Belt. Only have {current_inventory.get(Prototype.TransportBelt)}"
print("Successfully crafted 1 Transport Belt")


"""
Step 8: Craft fast-transport-belt
- Use the transport belt and iron gear wheel to craft a fast-transport-belt
"""
# Craft Fast Transport Belt
print("Crafting Fast Transport Belt")
crafted_fast_transport_belt = craft_item(Prototype.FastTransportBelt, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.FastTransportBelt) >= 1, f"Failed to craft 1 Fast Transport Belt. Only have {current_inventory.get(Prototype.FastTransportBelt)}"
print("Successfully crafted 1 Fast Transport Belt")


"""
Final verification
- Check inventory for fast-transport-belt
"""
print("Final Inventory Check")
final_inventory = inspect_inventory()
fast_transport_belt_count = final_inventory.get(Prototype.FastTransportBelt, 0)

assert fast_transport_belt_count >= 1, f"Final verification failed: Expected at least 1 Fast Transport Belt but found {fast_transport_belt_count}"
print(f"Successfully completed the task; final inventory contains {fast_transport_belt_count} Fast Transport Belt(s)")

