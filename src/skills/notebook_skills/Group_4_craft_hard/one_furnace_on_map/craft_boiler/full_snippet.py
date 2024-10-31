from factorio_instance import *

"""
Main Objective: We require one Boiler. The final success should be checked by looking if a Boiler is in inventory
"""



"""
Step 1: Gather resources
- Mine iron ore (at least 4 for the pipes)
- Mine coal (for smelting and fueling the furnace)
OUTPUT CHECK: Verify that we have at least 4 iron ore and some coal in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define required quantities
iron_ore_needed = 4
coal_needed = 5

# Gather Iron Ore
print("Locating nearest Iron Ore patch...")
iron_ore_position = nearest(Resource.IronOre)
print(f"Moving to Iron Ore position: {iron_ore_position}")
move_to(iron_ore_position)

print(f"Harvesting {iron_ore_needed} Iron Ore...")
harvest_resource(iron_ore_position, quantity=iron_ore_needed)

# Verify Iron Ore collection
current_inventory = inspect_inventory()
collected_iron_ore = current_inventory.get('iron-ore', 0)
assert collected_iron_ore >= iron_ore_needed, f"Failed to collect enough Iron Ore! Collected: {collected_iron_ore}"
print(f"Collected {collected_iron_ore} Iron Ore.")

# Gather Coal
print("Locating nearest Coal patch...")
coal_position = nearest(Resource.Coal)
print(f"Moving to Coal position: {coal_position}")
move_to(coal_position)

print(f"Harvesting {coal_needed} Coal...")
harvest_resource(coal_position, quantity=coal_needed)

# Verify Coal collection
current_inventory = inspect_inventory()
collected_coal = current_inventory.get('coal', 0)
assert collected_coal > 0, "Failed to collect any Coal!"
print(f"Collected {collected_coal} Coal.")

final_inventory = inspect_inventory()
print(f"Final Inventory after gathering resources: {final_inventory}")

# Ensure both resources are available in sufficient quantities
assert final_inventory['iron-ore'] >= iron_ore_needed, "Not enough Iron Ore in inventory."
assert final_inventory['coal'] > 0, "No Coal found in inventory."

print("Successfully gathered required resources.")


"""
Step 2: Prepare the furnace for smelting
- Move to the existing stone furnace on the map
- Add coal to the furnace for fuel
"""
# Inventory at the start of step {'coal': 5, 'iron-ore': 4}
#Step Execution

# Get the stone furnace entity from the map
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = stone_furnaces[0]
print(f"Located Stone Furnace at position: {stone_furnace.position}")

# Move to the stone furnace's position
move_to(stone_furnace.position)
print("Moved to Stone Furnace.")

# Check current inventory for available coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")

# Insert coal into the stone furnace for fuel
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} Coal into Stone Furnace.")


"""
Step 3: Smelt iron plates
- Add iron ore to the furnace
- Wait for the smelting process to complete
OUTPUT CHECK: Verify that we have at least 4 iron plates in the inventory
"""
# Inventory at the start of step {'iron-ore': 4}
#Step Execution

# Get current number of iron ores in inventory
iron_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore available in inventory: {iron_in_inventory}")

# Insert all available Iron Ore into Stone Furnace
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_in_inventory)
print(f"Inserted {iron_in_inventory} Iron Ore into Stone Furnace.")

# Calculate expected number of Iron Plates after smelting
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plates = initial_iron_plates + iron_in_inventory

# Wait for smelting process; assuming each piece takes about 0.7 seconds
smelting_time_per_piece = 0.7
total_smelting_time = smelting_time_per_piece * iron_in_inventory
print(f"Waiting {total_smelting_time} seconds for smelting...")
sleep(total_smelting_time)

# Attempt to extract Iron Plates until we have enough or max attempts reached
max_attempts = 5
for attempt in range(max_attempts):
    print(f"Attempt {attempt+1}: Trying to extract Iron Plates...")
    # Try extracting more than needed just in case some were missed initially 
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_in_inventory)
    
    # Verify extracted amount by checking current inventory state 
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    print(f"Current number of Iron Plates in Inventory: {current_iron_plates}")
    
    if current_iron_plates >= expected_iron_plates:
        print("Successfully extracted required number of Iron Plates.")
        break
    
    sleep(10)  # Allow additional time before retrying extraction

# Final verification that we have enough Iron Plates 
final_count_of_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_count_of_iron_plates >= expected_iron_plates, f"Failed! Expected at least {expected_iron_plates}, but got {final_count_of_iron_plates}"

print(f"Smelting complete. Total Iron Plates in inventory: {final_count_of_iron_plates}")


"""
Step 4: Craft pipes
- Craft 4 pipes using the iron plates
OUTPUT CHECK: Verify that we have 4 pipes in the inventory
"""
# Inventory at the start of step {'iron-plate': 4}
#Step Execution

# Check how many iron plates are currently in the inventory
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Crafting 4 pipes from available Iron Plates
pipes_to_craft = 4
crafted_pipes = craft_item(Prototype.Pipe, quantity=pipes_to_craft)
print(f"Crafted {crafted_pipes} Pipes.")

# Verify that we have crafted exactly 4 pipes
current_pipes_in_inventory = inspect_inventory().get(Prototype.Pipe, 0)
assert current_pipes_in_inventory >= pipes_to_craft, f"Failed to craft enough Pipes! Expected at least {pipes_to_craft}, but got {current_pipes_in_inventory}"

print("Successfully crafted required number of Pipes.")


"""
Step 5: Craft the Boiler
- Craft 1 Boiler using the 4 pipes and the stone furnace from the map
OUTPUT CHECK: Verify that we have 1 Boiler in the inventory

##
"""
# Inventory at the start of step {'pipe': 4}
#Step Execution

# Get the stone furnace entity from the map
stone_furnaces = get_entities({Prototype.StoneFurnace})
assert len(stone_furnaces) > 0, "No stone furnace found on the map"
stone_furnace = stone_furnaces[0]
print(f"Located Stone Furnace at position: {stone_furnace.position}")

# Move to the stone furnace's position
move_to(stone_furnace.position)
print("Moved to Stone Furnace.")

# Pick up the stone furnace
pickup_success = pickup_entity(stone_furnace)
assert pickup_success, "Failed to pick up the stone furnace"
print("Successfully picked up the stone furnace")

# Check current inventory
current_inventory = inspect_inventory()
pipes_in_inventory = current_inventory.get(Prototype.Pipe, 0)
stone_furnace_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)

print(f"Current Inventory: Pipes: {pipes_in_inventory}, Stone Furnace: {stone_furnace_in_inventory}")

# Ensure we have enough pipes and a stone furnace to craft a boiler
assert pipes_in_inventory >= 4, f"Not enough Pipes to craft a Boiler! Required: 4, but got {pipes_in_inventory}"
assert stone_furnace_in_inventory >= 1, f"No Stone Furnace in inventory to craft a Boiler!"

# Craft the Boiler
boiler_crafted = craft_item(Prototype.Boiler, quantity=1)
print(f"Crafted {boiler_crafted} Boiler.")

# Verify that we have crafted exactly 1 boiler
current_boilers_in_inventory = inspect_inventory().get(Prototype.Boiler, 0)
assert current_boilers_in_inventory >= 1, f"Failed to craft a Boiler! Expected at least 1, but got {current_boilers_in_inventory}"

print("Successfully crafted the required number of Boilers.")
