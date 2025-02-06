
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for:
- Burner Mining Drill
- Stone Furnace
- Transport Belt
- Underground Belt
- Iron Gear Wheel
- Iron Plate

Printing recipes is important as we need to know the exact requirements for crafting these items.
"""
# Print recipes
print("Recipes:")
print("Burner Mining Drill: 3 iron gear wheels, 3 iron plates, 1 stone furnace")
print("Stone Furnace: 5 stone")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (crafts 2)")
print("Underground Belt: 5 iron gear wheels, 10 iron plates (crafts 2)")
print("Iron Gear Wheel: 2 iron plates")
print("Iron Plate: 1 iron ore (smelting)")

"""
Step 2: Gather resources. We need to gather the following resources:
- 25 iron ore
- 12 stone
- 2 coal

We need to gather more resources than we actually need for the final crafting process.
This is because we need to craft intermediate items and smelt iron plates, which requires additional resources.
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity, radius=10)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft initial items. We need to craft:
- 2 stone furnaces
- 25 iron plates

We need 2 stone furnaces: one for the burner-mining-drill recipe and one for smelting iron plates.
We need 25 iron plates: 3 for the burner-mining-drill recipe, 10 for the transport-belts, and 10 for the underground-belt.
"""

# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")

# Move to a suitable position to place the furnace for smelting
move_to(Position(x=0, y=0))

# Place the furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Add coal to fuel the furnace
insert_item(Prototype.Coal, furnace, quantity=2)

# Add iron ore to the furnace to start smelting
insert_item(Prototype.IronOre, furnace, quantity=25)

# Wait for smelting to complete
sleep(25)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=25)

# Verify we have enough iron plates
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 25, f"Failed to obtain required number of Iron Plates. Expected at least 25 but got {iron_plates}"

print("Successfully crafted initial items!")

"""
Step 4: Craft intermediate items. We need to craft:
- 4 iron gear wheels

We need 4 iron gear wheels: 3 for the burner-mining-drill recipe and 1 for the transport-belt recipe.
"""

# Craft 4 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 iron gear wheels")

# Verify we have enough iron gear wheels
iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 4, f"Failed to obtain required number of Iron Gear Wheels. Expected at least 4 but got {iron_gear_wheels}"

print("Successfully crafted intermediate items!")

"""
Step 5: Craft final items. We need to craft:
- 1 burner-mining-drill

We have all the necessary intermediate items, so we can craft the final item.
"""

# Craft 1 burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner-mining-drill")

# Verify we have the burner-mining-drill
burner_mining_drill = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drill >= 1, f"Failed to obtain required number of Burner Mining Drills. Expected at least 1 but got {burner_mining_drill}"

print("Successfully crafted final items!")

"""
Step 6: Craft extra items. We need to craft:
- 14 transport belts
- 4 underground belts

These extra items are not part of the main objective, but we need them for setup.
"""

# Craft 14 transport belts
craft_item(Prototype.TransportBelt, quantity=14)
print("Crafted 14 transport belts")

# Verify we have enough transport belts
transport_belts = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts >= 14, f"Failed to obtain required number of Transport Belts. Expected at least 14 but got {transport_belts}"

# Craft 4 underground belts
craft_item(Prototype.UndergroundBelt, quantity=4)
print("Crafted 4 underground belts")

# Verify we have enough underground belts
underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 4, f"Failed to obtain required number of Underground Belts. Expected at least 4 but got {underground_belts}"

print("Successfully crafted extra items!")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Burner Mining Drill: {final_inventory.get(Prototype.BurnerMiningDrill, 0)}")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")

# Assert that we have crafted the burner-mining-drill
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Burner Mining Drill crafting failed"

print("Successfully crafted all required items!")

