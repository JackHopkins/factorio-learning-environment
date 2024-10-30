from factorio_instance import *

"""
Step 1: Print recipes. We need to print out the recipe for an OffshorePump which includes electronic circuits, iron gear wheels, and a pipe.
"""

# Get and print the recipe for an OffshorePump
offshore_pump_recipe = get_prototype_recipe(Prototype.OffshorePump)
print(f"Offshore Pump Recipe: {offshore_pump_recipe}")

# Get and print the recipe for Electronic Circuits
electronic_circuit_recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
print(f"Electronic Circuit Recipe: {electronic_circuit_recipe}")

# Get and print the recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get and print the recipe for Pipe
pipe_recipe = get_prototype_recipe(Prototype.Pipe)
print(f"Pipe Recipe: {pipe_recipe}")

# Log success message after printing all recipes
print("Successfully printed all required recipes.")


"""
Step 2: Gather resources. We need to gather enough copper ore and iron ore to produce at least 3 copper plates and 5 iron plates. Additionally, gather coal for fuel in the furnace.
OUTPUT CHECK: Verify that we have gathered sufficient raw materials (copper ore and iron ore) along with coal in our inventory.
"""

# Define the resources required with a slight buffer
resources_needed = [
    ("copper-ore", 5),   # Copper ore needed
    ("iron-ore", 8),     # Iron ore needed
    ("coal", 5)          # Coal needed
]

# Loop through each resource type and its required quantity
for resource_name, quantity in resources_needed:
    print(f"Gathering {quantity} of {resource_name}")  # Use direct string names
    
    # Find nearest position of the resource on map by converting name back into Resource enum if necessary 
    resource_position = nearest(getattr(Resource, ''.join([word.capitalize() for word in resource_name.split('-')])))
    
    # Move player near to the resource position before harvesting
    move_to(resource_position)
    
    # Harvest specified quantity of this resource from its position
    harvested_quantity = harvest_resource(resource_position, quantity)
    
    print(f"Harvested {harvested_quantity} units of {resource_name}")  # Use direct string names

# Verify if all resources are gathered correctly by checking inventory state

inventory_state = inspect_inventory()

copper_ore_count = inventory_state["copper-ore"]
iron_ore_count = inventory_state["iron-ore"]
coal_count = inventory_state["coal"]

print(f"Inventory after gathering: Copper Ore={copper_ore_count}, Iron Ore={iron_ore_count}, Coal={coal_count}")

# Assert checks to ensure correct amounts were gathered

assert copper_ore_count >= resources_needed[0][1], f"Expected at least {resources_needed[0][1]} Copper Ores but found {copper_ore_count}"
assert iron_ore_count >= resources_needed[1][1], f"Expected at least {resources_needed[1][1]} Iron Ores but found {iron_ore_count}"
assert coal_count >= resources_needed[2][1], f"Expected at least {resources_needed[2][1]} Coals but found {coal_count}"

print("Successfully gathered all required raw materials.")


"""
Step 3: Craft and place a furnace. Since there are no stone furnaces on the map or in our inventory, we must craft one using stone collected from mining.
OUTPUT CHECK: Ensure that a stone furnace is crafted and placed successfully on the ground.
"""

# PLANNING STAGE:
# 1. Gather at least 5 stones as that's typically needed for crafting a single Stone Furnace.
# 2. Craft one Stone Furnace using gathered stones.
# 3. Place this newly crafted Stone Furnace on an appropriate location near resources or coal patch.

# Step 1: Gather Stones
stone_needed = 5
print(f"Step 1: Gathering {stone_needed} units of stone.")
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stones = harvest_resource(stone_position, quantity=stone_needed)

inventory_after_stone_gathering = inspect_inventory()
current_stone_count = inventory_after_stone_gathering.get("stone", 0)
assert current_stone_count >= stone_needed, f"Failed to gather enough stones! Expected at least {stone_needed}, but got {current_stone_count}"
print(f"Successfully gathered {harvested_stones} units of stone.")

# Step 2: Craft Stone Furnace
print("Step 2: Crafting one Stone Furnace.")
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)

inventory_after_crafting_furnace = inspect_inventory()
furnace_count_in_inventory = inventory_after_crafting_furnace.get(Prototype.StoneFurnace.value[0], 0)
assert furnace_count_in_inventory >= crafted_furnaces, "Failed to craft a Stone Furnace!"
print("Successfully crafted one Stone Furnace.")

# Step 3: Place the Crafted Stone Furnace
print("Step 3: Placing the crafted Stone Furnace.")
placement_position_near_coal_patch = nearest(Resource.Coal) # Assuming placing near coal for easy fueling later
move_to(placement_position_near_coal_patch)
placed_furnace_entity = place_entity(Prototype.StoneFurnace, position=placement_position_near_coal_patch)

inspection_results_post_placement = inspect_entities(position=placed_furnace_entity.position)
furnished_entities_on_ground = [entity for entity in inspection_results_post_placement.entities if entity.name == Prototype.StoneFurnace.value[0]]
assert len(furnished_entities_on_ground) > 0, "Stone Furnace was not placed successfully!"
print("Successfully placed one Stone Furnace on the ground.")

print("All tasks related to crafting and placing a Stone Furnace are completed successfully!")


"""
Step 4: Smelt ores into plates. Use the stone furnace to smelt copper ore into copper plates and iron ore into iron plates by fueling it with coal.
OUTPUT CHECK: Confirm that we have at least 3 copper plates and 5 iron plates in our inventory after smelting.
"""

# Step 1: Locate the Stone Furnace
print("Step 1: Locating Stone Furnace.")
furnace_position = nearest(Prototype.StoneFurnace)
stone_furnace = get_entity(Prototype.StoneFurnace, position=furnace_position)

# Step 2: Fueling the Stone Furnace with Coal
coal_quantity = inspect_inventory()["coal"]
print(f"Step 2: Inserting {coal_quantity} coal into Stone Furnace.")
insert_item(Prototype.Coal, stone_furnace, quantity=coal_quantity)

# Step 3: Smelting Iron Ore
iron_ore_quantity = inspect_inventory()["iron-ore"]
print(f"Step 3: Inserting {iron_ore_quantity} Iron Ore into Stone Furnace.")
insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_quantity)

# Wait for smelting process (0.7 seconds per item as an estimate)
sleep_time_for_iron = iron_ore_quantity * 0.7
print(f"Waiting {sleep_time_for_iron} seconds for Iron Plates to be ready.")
sleep(sleep_time_for_iron)

# Extract Iron Plates from Furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_quantity)
    current_inventory = inspect_inventory()
    if current_inventory["iron-plate"] >= min(5, iron_ore_quantity):
        break
    sleep(10) # Wait more if not enough plates are ready

assert current_inventory["iron-plate"] >= min(5, iron_ore_quantity), "Failed to smelt required number of Iron Plates!"
print(f"Successfully extracted {current_inventory['iron-plate']} Iron Plates.")

# Step 4: Smelting Copper Ore
copper_ore_quantity = inspect_inventory()["copper-ore"]
print(f"Step 4: Inserting {copper_ore_quantity} Copper Ore into Stone Furnace.")
insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_quantity)

# Wait for smelting process (0.7 seconds per item as an estimate)
sleep_time_for_copper = copper_ore_quantity * 0.7
print(f"Waiting {sleep_time_for_copper} seconds for Copper Plates to be ready.")
sleep(sleep_time_for_copper)

# Extract Copper Plates from Furnace
for _ in range(max_attempts):
    extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_quantity)
    final_inventory = inspect_inventory()
    if final_inventory["copper-plate"] >= min(3,copper_ore_quantity):
        break
    sleep(10) # Wait more if not enough plates are ready

assert final_inventory["copper-plate"] >= min(3,copper_ore_quantity), "Failed to smelt required number of Copper Plates!"
print(f"Successfully extracted {final_inventory['copper-plate']} Copper Plates.")

# Final Output Check - Confirm successful completion of objective 
assert final_inventory["copper-plate"] >= 3 and final_inventory["iron-plate"] >= 5,\
    f"Objective not met! Expected at least [Copper Plate=3] & [Iron Plate=5], but got [Copper Plate={final_inventory['copper-plate']}] & [Iron Plate={final_inventory['iron-plate']}]"
    
print("Successfully completed smelting ores into required metal plates!")


"""
Step 5: Craft intermediate components. Using the smelted plates:
- Craft electronic circuits (requires copper cables made from copper plates).
- Craft an iron gear wheel (requires two iron plates).
- Craft a pipe (requires one iron plate).
OUTPUT CHECK: Check if all intermediate components - electronic circuit(s), an iron gear wheel, and a pipe - are present in our inventory.
"""

# Step 1: Craft Copper Cables
copper_cable_quantity = craft_item(Prototype.CopperCable, quantity=6) # Adjusted quantity based on available resources
print(f"Crafted {copper_cable_quantity} Copper Cables.")

# Step 2: Craft Electronic Circuits
electronic_circuit_quantity = craft_item(Prototype.ElectronicCircuit, quantity=2)
print(f"Crafted {electronic_circuit_quantity} Electronic Circuits.")

# Step 3: Craft Iron Gear Wheel
iron_gear_wheel_quantity = craft_item(Prototype.IronGearWheel, quantity=1)
print(f"Crafted {iron_gear_wheel_quantity} Iron Gear Wheel.")

# Step 4: Craft Pipe
pipe_quantity = craft_item(Prototype.Pipe, quantity=1)
print(f"Crafted {pipe_quantity} Pipe.")

# Check Inventory for all components
inventory_after_crafting_components = inspect_inventory()
assert inventory_after_crafting_components.get("electronic-circuit", 0) >= electronic_circuit_quantity,\
    f"Failed to craft required number of Electronic Circuits! Expected at least {electronic_circuit_quantity}, but got {inventory_after_crafting_components.get('electronic-circuit',0)}"
assert inventory_after_crafting_components.get("iron-gear-wheel", 0) >= iron_gear_wheel_quantity,\
    f"Failed to craft required number of Iron Gear Wheels! Expected at least {iron_gear_wheel_quantity}, but got {inventory_after_crafting_components.get('iron-gear-wheel',0)}"
assert inventory_after_crafting_components.get("pipe", 0) >= pipe_quantity,\
    f"Failed to craft required number of Pipes! Expected at least {pipe_quantity}, but got {inventory_after_crafting_components.get('pipe',0)}"

print("Successfully crafted all intermediate components - Electronic Circuit(s), Iron Gear Wheel, and Pipe.")


"""
Step 6: Craft OffshorePump. With all intermediate components ready, proceed to craft one OffshorePump.
OUTPUT CHECK: Verify that an OffshorePump is now available in our inventory as confirmation of success.
"""

# Step: Craft OffshorePump using available intermediate components

print("Crafting one OffshorePump.")

# Craft the OffshorePump
offshore_pump_quantity = craft_item(Prototype.OffshorePump, quantity=1)

# Check if the offshore pump is now in our inventory
inventory_after_crafting_offshore_pump = inspect_inventory()
crafted_offshore_pumps = inventory_after_crafting_offshore_pump.get("offshore-pump", 0)

assert crafted_offshore_pumps >= offshore_pump_quantity,\
    f"Failed to craft an Offshore Pump! Expected at least {offshore_pump_quantity}, but got {crafted_offshore_pumps}"

print(f"Successfully crafted {crafted_offshore_pumps} Offshore Pump(s).")
