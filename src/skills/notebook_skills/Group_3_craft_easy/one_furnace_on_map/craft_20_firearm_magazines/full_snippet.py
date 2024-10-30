from factorio_instance import *

"""
Main Objective: We need 20 firearm magazines. The final success should be checked by looking if 20 firearm magazines are in inventory
"""



"""
Step 1: Mine resources
- Move to the nearest coal patch and mine at least 20 coal (for fueling the furnace)
- Move to the nearest iron ore patch and mine at least 80 iron ore
OUTPUT CHECK: Verify that we have at least 20 coal and 80 iron ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define resources required with their respective quantities
resources_to_mine = [(Resource.Coal, 20), (Resource.IronOre, 80)]

# Loop through each resource type and quantity
for resource_type, required_amount in resources_to_mine:
    # Find the nearest position of the current resource type
    resource_position = nearest(resource_type)
    
    # Move to the location where this resource is available
    print(f"Moving to {resource_type} patch located at {resource_position}")
    move_to(resource_position)
    
    # Mine or harvest the specified amount of this resource
    print(f"Harvesting {required_amount} units of {resource_type}")
    harvested_amount = harvest_resource(resource_position, required_amount)

    # Check if we've successfully gathered enough resources into our inventory
    current_inventory_count = inspect_inventory().get(resource_type)
    
    assert current_inventory_count >= required_amount, f"Failed to gather enough {resource_type}. Expected at least {required_amount}, but got {current_inventory_count}"
    
    print(f"Successfully harvested {harvested_amount} units of {resource_type}. Current Inventory: {inspect_inventory()}")

# Final check on inventory after mining operations are complete
final_inventory_state = inspect_inventory()
assert final_inventory_state.get(Resource.Coal) >= 20, "Final check failed: Not enough Coal."
assert final_inventory_state.get(Resource.IronOre) >= 80, "Final check failed: Not enough Iron Ore."

print("Successfully completed mining step with sufficient resources gathered.")


"""
Step 2: Prepare and use the furnace
- Move to the existing stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
- Add iron ore to the furnace for smelting
- Wait for the smelting process to complete (80 iron ore should produce 80 iron plates)
OUTPUT CHECK: Verify that we have 80 iron plates in the inventory
"""
# Inventory at the start of step {'coal': 20, 'iron-ore': 80}
#Step Execution

# Move near the stone furnace
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving to stone furnace located at {furnace_position}")
move_to(furnace_position)

# Get current inventory counts
coal_in_inventory = inspect_inventory()[Prototype.Coal]
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Coal in inventory before insertion: {coal_in_inventory}")
print(f"Iron ore in inventory before insertion: {iron_ore_in_inventory}")

# Retrieve the stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = stone_furnaces[0]

# Insert coal into the furnace as fuel
stone_furnace = insert_item(Prototype.Coal, stone_furnace, coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into the furnace")

# Insert iron ore into the furnace for smelting
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of iron ore into the furnace")

# Wait for smelting process completion; each unit takes approximately 0.7 seconds
smelting_time_per_unit = 0.7
total_smelting_time = iron_ore_in_inventory * smelting_time_per_unit
sleep(total_smelting_time)
print("Waiting completed; checking results...")

# Extracting resulting iron plates from the furnace after waiting period
max_attempts_for_extraction = 5

for _ in range(max_attempts_for_extraction):
    extract_item(Prototype.IronPlate, stone_furnace.position, iron_ore_in_inventory)
    # Check how many plates are now available in your own inventory:
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    
    if current_iron_plate_count >= 80:
        break
    
    sleep(10) # Allow some additional time if not all items were extracted initially

final_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
assert final_iron_plate_count >= 80, f"Failed verification step! Expected at least 80 Iron Plates but found only {final_iron_plate_count}"

print("Successfully prepared and used stove; obtained sufficient number of Iron Plates.")


"""
Step 3: Craft firearm magazines
- Use the crafting menu to create 20 firearm magazines (each requiring 4 iron plates)
OUTPUT CHECK: Verify that we have 20 firearm magazines in the inventory

##
"""
# Inventory at the start of step {'iron-plate': 80}
#Step Execution

# Crafting 20 firearm magazines using available iron plates
print("Starting crafting process for 20 firearm magazines.")

# Craft all required firearm magazines
crafted_magazines = craft_item(Prototype.FirearmMagazine, 20)
print(f"Attempted to craft {crafted_magazines} firearm magazines.")

# Inspect inventory after crafting
inventory_after_crafting = inspect_inventory()
firearm_magazine_count = inventory_after_crafting.get(Prototype.FirearmMagazine)

# Verify if we have crafted enough firearms
assert firearm_magazine_count >= 20, f"Failed verification step! Expected at least 20 Firearm Magazines but found only {firearm_magazine_count}"

print(f"Successfully crafted {firearm_magazine_count} Firearm Magazines.")
print("Final Inventory:", inventory_after_crafting)
