

from factorio_instance import *

"""
Step 1: Gather resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 100),
    (Resource.Coal, 50),
    (Resource.Stone, 10)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    if resource_type == Resource.IronOre:
        print(f"Found nearest iron ore patch at: {resource_position}")
        
    # Move to the resource position
    move_to(resource_position)
    
    if resource_type == Resource.IronOre:
        print(f"Moved to iron ore patch at: {resource_position}")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    if resource_type == Resource.IronOre:
        print(f"Harvested {harvested} iron ore")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    if actual_quantity < required_quantity:
        raise Exception(f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}")
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify that we have all required resources
assert final_inventory.get(Resource.IronOre) >= 100, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal) >= 50, "Not enough Coal"
assert final_inventory.get(Resource.Stone) >= 10, "Not enough Stone"

print("Successfully gathered all required resources!")


"""
Step 2: Craft and place necessary entities
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Craft burner mining drill (requires iron gear wheel and stone furnace)
craft_item(Prototype.IronGearWheel, 3)
craft_item(Prototype.StoneFurnace, 1)
craft_item(Prototype.BurnerMiningDrill, 1)

# Place stone furnace
origin = Position(x=0, y=0)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Place burner mining drill
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed Burner Mining Drill at {drill.position}")

# Craft and place assembling machine 1 (requires iron gear wheel and electronic circuit)
craft_item(Prototype.IronGearWheel, 3)
craft_item(Prototype.ElectronicCircuit, 3)
craft_item(Prototype.AssemblingMachine1, 1)
move_to(Position(x=2, y=2))
assembler = place_entity(Prototype.AssemblingMachine1, position=Position(x=2, y=2))
print(f"Placed Assembling Machine at {assembler.position}")

# Initialize burner mining drill
# Insert coal into burner mining drill
coal_quantity = 5  # You can adjust this value as needed
insert_item(Prototype.Coal, drill, coal_quantity)
print(f"Inserted {coal_quantity} coal into Burner Mining Drill")

# Check if the drill has coal
drill_coal = drill.fuel.get(Prototype.Coal, 0)
assert drill_coal > 0, "Failed to insert coal into Burner Mining Drill"
print("Burner Mining Drill successfully fueled")


"""
Step 3: Set up automated iron plate production
"""
# Move to the furnace position
move_to(furnace.position)

# Insert coal into the stone furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, 5)
print("Inserted coal into the stone furnace")

# Connect drill to furnace with transport belts
belts = connect_entities(drill.drop_position, fueled_furnace.position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to furnace with transport belts"

# Add inserters to move iron ore from the belt into the furnace
left_inserter = place_entity_next_to(Prototype.BurnerInserter, fueled_furnace.position, direction=Direction.LEFT)
right_inserter = place_entity_next_to(Prototype.BurnerInserter, fueled_furnace.position, direction=Direction.RIGHT)

# Rotate right inserter to face the furnace
right_inserter = rotate_entity(right_inserter, Direction.LEFT)

# Fuel both inserters
fueled_left_inserter = insert_item(Prototype.Coal, left_inserter, 2)
fueled_right_inserter = insert_item(Prototype.Coal, right_inserter, 2)

# Check if both inserters have coal
left_inserter_coal = fueled_left_inserter.fuel.get(Prototype.Coal, 0)
right_inserter_coal = fueled_right_inserter.fuel.get(Prototype.Coal, 0)
assert left_inserter_coal > 0 and right_inserter_coal > 0, "Failed to fuel inserters"

print("Successfully set up automated iron plate production")


"""
Step 4: Craft underground belts and iron gear wheels
"""
# Craft iron gear wheels (20 for fast-underground-belt)
craft_item(Prototype.IronGearWheel, 20)
print("Crafted 20 Iron Gear Wheels")

# Craft underground belts (2 for fast-underground-belt)
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 Underground Belts")

# Verify that we have crafted the required items
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 20, "Failed to craft enough Iron Gear Wheels"
assert inventory.get(Prototype.UndergroundBelt, 0) >= 2, "Failed to craft enough Underground Belts"

print("Successfully crafted required components for fast-underground-belt")


"""
Step 5: Craft fast-underground-belt
"""
# Craft fast-underground-belt (requires 2 underground belts and 20 iron gear wheels)
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 Fast Underground Belt")

# Verify that we have crafted the fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft Fast Underground Belt"

print("Successfully crafted Fast Underground Belt!")

