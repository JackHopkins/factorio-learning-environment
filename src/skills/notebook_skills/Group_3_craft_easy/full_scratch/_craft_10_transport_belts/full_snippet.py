from factorio_instance import *

"""
Main Objective: We need to craft 7 transport belts. The final success should be checked by looking if the  transport belts are in inventory
"""



"""
Step 1: Print recipes. We need to craft transport belts. We must print the recipe for transport belts:
TransportBelt - Crafting 2 transport belts requires 1 iron gear wheel, 1 iron plate. In total all ingredients require atleast 3 iron plates
"""
# Inventory at the start of step {}
#Step Execution

transport_belts_produced = next((prod.count for prod in transport_belt_recipe.products if prod.name == "transport-belt"), 0)


"""
Step 2: Gather resources. We need to gather the following resources:
- Iron ore (at least 12 to make 4 iron plates)
- Coal (for fueling the stone furnace)
- Stone (to craft a stone furnace)
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 7),
    (Resource.Coal, 15),
    (Resource.IronOre, 15)
]

# Loop through each resource and gather it
for resource, amount in resources_to_gather:
    # Find the nearest location of the resource
    resource_position = nearest(resource)
    print(f"Found {resource} at position {resource_position}")

    # Move to the resource location
    move_to(resource_position)
    print(f"Moved to {resource} at {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Verify that we have gathered enough
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")

    if actual_amount < amount:
        print(f"Warning: Only gathered {actual_amount} {resource}, needed {amount}")
    else:
        print(f"Successfully gathered {actual_amount} {resource}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Verify we have all the resources we need
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough stone gathered"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough coal gathered"
assert final_inventory.get(Resource.IronOre, 0) >= 12, "Not enough iron ore gathered"

print("Successfully gathered all required resources!")


"""
Step 3: Craft and set up smelting. We need to create a basic smelting setup:
- Craft a stone furnace using 5 stone
- Place the stone furnace and fuel it with coal
- Smelt the iron ore into iron plates (we need at least 12 iron plates)
"""
# Inventory at the start of step {'coal': 15, 'stone': 7, 'iron-ore': 15}
#Step Execution

# Craft a stone furnace
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, 1)
print("Stone furnace crafted.")

# Find a suitable location to place the furnace (near the iron ore patch)
furnace_position = nearest(Resource.IronOre)
print(f"Chosen position for furnace: {furnace_position}")

# Move to the chosen position
move_to(furnace_position)
print(f"Moved to position {furnace_position}")

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.NORTH, position=furnace_position)
print(f"Stone furnace placed at {furnace.position}")

# Fuel the furnace with coal
print("Fueling the furnace with coal...")
insert_item(Prototype.Coal, furnace, 5)
print("Furnace fueled with coal.")

# Insert iron ore into the furnace
iron_ore_count = inspect_inventory()[Prototype.IronOre]
print(f"Inserting {iron_ore_count} iron ore into the furnace...")
insert_item(Prototype.IronOre, furnace, iron_ore_count)
print("Iron ore inserted into the furnace.")

# Wait for smelting to complete (3.2 seconds per iron plate)
smelting_time = iron_ore_count * 3.2
print(f"Waiting for {smelting_time} seconds for smelting to complete...")
sleep(smelting_time)

# Extract iron plates from the furnace
print("Extracting iron plates from the furnace...")
extract_item(Prototype.IronPlate, furnace.position, iron_ore_count)

# Verify that we have at least 12 iron plates
inventory = inspect_inventory()
iron_plates_count = inventory[Prototype.IronPlate]
print(f"Current iron plates in inventory: {iron_plates_count}")

assert iron_plates_count >= 12, f"Not enough iron plates. Expected at least 12, but got {iron_plates_count}"
print("Successfully smelted at least 12 iron plates!")

print(f"Final inventory after smelting: {inspect_inventory()}")


"""
Step 4: Craft iron gear wheels. We need to craft iron gear wheels for the transport belts:
- Craft 4 iron gear wheels (each requires 2 iron plates, so 8 iron plates total)
"""
# Inventory at the start of step {'coal': 10, 'stone': 2, 'iron-plate': 15}
#Step Execution

# Get the recipe for iron gear wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Recipe for Iron Gear Wheel: {iron_gear_wheel_recipe}")

# Check the current inventory
initial_inventory = inspect_inventory()
print(f"Initial inventory: {initial_inventory}")

# Calculate the number of iron plates needed
iron_plates_needed = 4 * 2  # 4 gear wheels, 2 plates each
print(f"Iron plates needed: {iron_plates_needed}")

# Ensure we have enough iron plates
assert initial_inventory[Prototype.IronPlate] >= iron_plates_needed, f"Not enough iron plates. Need {iron_plates_needed}, but only have {initial_inventory[Prototype.IronPlate]}"

# Craft 4 iron gear wheels
print("Crafting 4 iron gear wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, 4)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Check the final inventory
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify that we have crafted 4 iron gear wheels
assert final_inventory[Prototype.IronGearWheel] >= 4, f"Failed to craft 4 iron gear wheels. Only have {final_inventory[Prototype.IronGearWheel]}"

# Calculate remaining iron plates
remaining_iron_plates = final_inventory[Prototype.IronPlate]
expected_remaining_iron_plates = initial_inventory[Prototype.IronPlate] - iron_plates_needed
assert remaining_iron_plates == expected_remaining_iron_plates, f"Unexpected number of remaining iron plates. Expected {expected_remaining_iron_plates}, but have {remaining_iron_plates}"

print("Successfully crafted 4 iron gear wheels!")


"""
Step 5: Craft transport belts. We will now craft the transport belts:
- Craft 7 transport belts using 4 iron gear wheels and 4 iron plates
- Check the inventory to confirm that 7 transport belts have been crafted successfully

##
"""
# Placeholder 5