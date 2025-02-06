

from instance import *

"""
Objective: Set up initial iron plate production

Planning:
We need to set up a basic iron plate production line.
There are no entities on the map and our inventory is empty, so we need to craft everything from scratch.
We need to mine iron ore and coal, craft a stone furnace and a burner mining drill, and set up the smelting process.
"""

"""
Step 1: Print recipes
"""
# Get recipes for the needed entities
drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)

# Print the recipes
print("Burner Mining Drill Recipe:")
print(f"Ingredients: {drill_recipe.ingredients}")
print("Stone Furnace Recipe:")
print(f"Ingredients: {furnace_recipe.ingredients}")
print("Burner Inserter Recipe:")
print(f"Ingredients: {inserter_recipe.ingredients}")

"""
Step 2: Gather raw resources
- Mine iron ore (at least 15)
- Mine stone (at least 5 for the furnace)
- Mine coal (at least 5 for fuel)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 15),
    (Resource.Stone, 5),
    (Resource.Coal, 5)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 15, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 5, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft intermediate products
- Craft 1 stone furnace
- Craft 3 iron gear wheels
- Craft 1 pipe
"""

# Craft stone furnace
print("Crafting stone furnace...")
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Craft iron gear wheels
print("Crafting iron gear wheels...")
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=3)
print(f"Crafted {crafted_gears} iron gear wheels")

# Craft pipe
print("Crafting pipe...")
crafted_pipes = craft_item(Prototype.Pipe, quantity=1)
print(f"Crafted {crafted_pipes} pipes")

# Check inventory for crafted items
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"
assert inventory.get(Prototype.IronGearWheel, 0) >= 3, "Failed to craft iron gear wheels"
assert inventory.get(Prototype.Pipe, 0) >= 1, "Failed to craft pipe"

print("Successfully crafted all intermediate products!")

"""
Step 4: Craft final products
- Craft 1 burner mining drill
- Craft 1 burner inserter
"""

# Craft burner mining drill
print("Crafting burner mining drill...")
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drills} burner mining drills")

# Craft burner inserter
print("Crafting burner inserter...")
crafted_inserters = craft_item(Prototype.BurnerInserter, quantity=1)
print(f"Crafted {crafted_inserters} burner inserters")

# Check inventory for crafted items
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft burner mining drill"
assert inventory.get(Prototype.BurnerInserter, 0) >= 1, "Failed to craft burner inserter"

print("Successfully crafted all final products!")

"""
Step 5: Place and set up the mining drill
- Find an iron ore patch
- Place the burner mining drill on the iron ore patch
- Fuel the drill with coal
"""

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore patch found at: {iron_ore_position}")

# Move to the iron ore patch
print("Moving to iron ore patch...")
move_to(iron_ore_position)

# Place the burner mining drill
print("Placing burner mining drill...")
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position, direction=Direction.DOWN)
print(f"Placed burner mining drill at: {drill.position}")

# Fuel the drill with coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    print(f"Inserting {coal_in_inventory} coal into the drill")
    fueled_drill = insert_item(Prototype.Coal, drill, quantity=coal_in_inventory)
    print("Drill successfully fueled")
else:
    print("No coal available in inventory to fuel the drill")

# Verify that the drill is placed correctly and fueled
inspection = inspect_entities(position=drill.position, radius=1)
placed_drill = next((e for e in inspection.entities if e.name == Prototype.BurnerMiningDrill.value[0]), None)
assert placed_drill is not None, "Failed to place burner mining drill"
print("Burner mining drill successfully placed and fueled")

"""
Step 6: Place and set up the furnace
- Place the stone furnace next to the drill's drop position
- Fuel the furnace with coal
- Set up an inserter to move ore from the drill to the furnace
"""

# Calculate the furnace position based on the drill's drop position
furnace_position = drill.drop_position
print(f"Calculated furnace position: {furnace_position}")

# Move to the calculated position
print(f"Moving to position: {furnace_position}")
move_to(furnace_position)

# Place the stone furnace
print("Placing stone furnace...")
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

# Fuel the furnace with coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    print(f"Inserting {coal_in_inventory} coal into the furnace")
    fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
    print("Furnace successfully fueled")
else:
    print("No coal available in inventory to fuel the furnace")

# Verify that the furnace is placed correctly and fueled
inspection = inspect_entities(position=furnace.position, radius=1)
placed_furnace = next((e for e in inspection.entities if e.name == Prototype.StoneFurnace.value[0]), None)
assert placed_furnace is not None, "Failed to place stone furnace"
print("Stone furnace successfully placed and fueled")

# Set up a burner inserter to move ore from the drill to the furnace
print("Placing burner inserter...")
inserter = place_entity_next_to(Prototype.BurnerInserter, direction=Direction.RIGHT, reference_position=drill.position)
inserter = rotate_entity(inserter, direction=Direction.LEFT)

# Fuel the inserter with coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    print(f"Inserting {coal_in_inventory} coal into the inserter")
    inserter = insert_item(Prototype.Coal, inserter, quantity=coal_in_inventory)
    print("Inserter successfully fueled")
else:
    print("No coal available in inventory to fuel the inserter")

# Connect the drill to the inserter and the inserter to the furnace
print("Connecting drill to furnace with inserter...")
connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
connect_entities(inserter.drop_position, furnace.position, Prototype.TransportBelt)

print("Furnace setup complete")

"""
Step 7: Smelt iron plates
- Wait for the furnace to smelt 10 iron plates
- Extract the iron plates from the furnace
"""

# Wait for smelting to complete
smelting_time = 7  # 10 iron ore * 0.7 seconds per ore
print(f"Waiting {smelting_time} seconds for smelting to complete...")
sleep(smelting_time)

# Move close to the furnace to extract the plates
print("Moving closer to the furnace to extract iron plates...")
move_to(furnace.position)

# Extract iron plates
print("Extracting iron plates from the furnace...")
max_attempts = 5
for _ in range(max_attempts):
    # Attempt to extract iron plates
    extract_item(Prototype.IronPlate, furnace, quantity=10)
    # Check current inventory for iron plates
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    # If we have at least 10 iron plates, break out of the loop
    if current_iron_plates >= 10:
        break
    sleep(5)  # Wait a bit more if not all plates are ready

print(f"Extracted iron plates; current inventory count: {current_iron_plates}")

# Assert that we have at least 10 iron plates in our inventory
assert current_iron_plates >= 10, f"Failed to obtain required number of Iron Plates. Expected: 10, Actual: {current_iron_plates}"
print("Successfully obtained required number of Iron Plates!")

# Check final inventory state
final_inventory = inspect_inventory()
print(f"\nFinal Inventory after extracting Iron Plates:\n{final_inventory}")

