

from factorio_instance import *

"""
Planning:
We need to set up an automated steel plate production line. 
This requires a burner mining drill for iron ore, a burner mining drill for coal, 
a stone furnace, and transport belts to connect everything.
We have most of the components in our inventory and on the map.
We need to place the drills, connect them to the furnace, and set up the furnace for steel production.
Finally, we need to check if the setup is working correctly.
"""

"""
Step 1: Place the burner mining drills
- We need to place one burner mining drill on an iron ore patch
- We need to place one burner mining drill on a coal patch
"""
# Find the nearest iron ore patch
iron_ore_position = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
print(f"Nearest iron ore patch found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position.bounding_box.center)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the burner mining drill on the iron ore patch
iron_drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position.bounding_box.center)
print(f"Placed burner mining drill for iron ore at: {iron_drill.position}")

# Find the nearest coal patch
coal_position = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
print(f"Nearest coal patch found at: {coal_position}")

# Move to the coal patch
move_to(coal_position.bounding_box.center)
print(f"Moved to coal patch at: {coal_position}")

# Place the burner mining drill on the coal patch
coal_drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=coal_position.bounding_box.center)
print(f"Placed burner mining drill for coal at: {coal_drill.position}")

"""
Step 2: Set up the furnace
- We need to connect the iron ore drill to a stone furnace
- We need to connect the coal drill to the furnace as fuel
"""
# Find the stone furnace on the map
furnace = get_entities({Prototype.StoneFurnace})[0]

# Move to the furnace position
move_to(furnace.position)

# Place an inserter next to the furnace to feed it coal
coal_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.RIGHT)
coal_inserter = rotate_entity(coal_inserter, Direction.LEFT)
print(f"Placed and rotated inserter next to furnace at: {coal_inserter.position}")

# Connect the coal drill to the furnace inserter
coal_belt = connect_entities(coal_drill.drop_position, coal_inserter.pickup_position, Prototype.TransportBelt)
assert coal_belt, "Failed to connect coal drill to furnace inserter with transport belt"
print("Connected coal drill to furnace inserter with transport belt")

# Connect the iron ore drill to the furnace
iron_belt = connect_entities(iron_drill.drop_position, furnace.position, Prototype.TransportBelt)
assert iron_belt, "Failed to connect iron ore drill to furnace with transport belt"
print("Connected iron ore drill to furnace with transport belt")

"""
Step 3: Fuel the drills and furnace
- We need to add coal to both burner mining drills and the furnace
"""
# Harvest some coal first
coal_to_harvest = 20  # Arbitrary amount to ensure we have enough
coal_position = nearest(Resource.Coal)
harvested_coal = harvest_resource(coal_position, coal_to_harvest)
print(f"Harvested {harvested_coal} coal")

# Fuel the iron ore drill
iron_drill = insert_item(Prototype.Coal, iron_drill, quantity=10)
print("Inserted coal into iron ore drill")

# Fuel the coal drill
coal_drill = insert_item(Prototype.Coal, coal_drill, quantity=10)
print("Inserted coal into coal drill")

# Fuel the furnace inserter
coal_inserter = insert_item(Prototype.Coal, coal_inserter, quantity=10)
print("Inserted coal into furnace inserter")

"""
Step 4: Set up the furnace for steel production
- We need to extract iron plates and insert them back for steel smelting
"""
# Place an inserter to take iron plates out of the furnace
output_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.DOWN)
output_inserter = rotate_entity(output_inserter, Direction.UP)
print(f"Placed and rotated output inserter at: {output_inserter.position}")

# Place another inserter to put iron plates back into the furnace
input_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.UP)
print(f"Placed input inserter at: {input_inserter.position}")

# Connect the output of the first inserter to the input of the second inserter
recycle_belt = connect_entities(output_inserter.drop_position, input_inserter.pickup_position, Prototype.TransportBelt)
assert recycle_belt, "Failed to connect output inserter to input inserter with transport belt"
print("Connected output inserter to input inserter with transport belt")

"""
Step 5: Verify the setup
- We need to check if the drills and furnace are working correctly
"""
# Wait for the system to operate for a while
sleep(30)

# Check the furnace inventory for steel plates
furnace_inventory = inspect_inventory(furnace)
steel_plates = furnace_inventory.get(Prototype.SteelPlate, 0)
print(f"Steel plates in the furnace: {steel_plates}")

# Check the chest inventory for steel plates
chest = get_entities({Prototype.WoodenChest})[0]  # Assuming there's one chest on the map
chest_inventory = inspect_inventory(chest)
chest_steel_plates = chest_inventory.get(Prototype.SteelPlate, 0)
print(f"Steel plates in the chest: {chest_steel_plates}")

assert steel_plates > 0 or chest_steel_plates > 0, "No steel plates found in the furnace or chest"
print("Steel plate production is working correctly")

