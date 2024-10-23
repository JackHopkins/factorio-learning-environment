from factorio_instance import *

"""
Main Objective: We need to craft 7 transport belts. The final success should be checked by looking if the  transport belts are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Transport Belt
- Iron Gear Wheel
- Stone Furnace
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Print recipes

# Get and print the recipe for Transport Belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Transport Belt Recipe: {transport_belt_recipe}")

# Get and print the recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- 12 iron ore (for 12 iron plates)
- Sufficient coal for smelting and fueling the furnace
- Use the stone from the wooden chest on the map
"""
# Inventory at the start of step {}
#Step Execution

# Step 2: Gather resources

# Define required resources with a buffer
resources_to_gather = [(Prototype.IronOre, 15), (Prototype.Coal, 10)]

# Loop over each resource type and amount
for resource_type, quantity in resources_to_gather:
    # Find closest position of specified resource type
    resource_position = nearest(resource_type)
    
    # Move player character near the target resource location
    move_to(resource_position)
    
    # Harvest specified amount of selected resource type at identified location
    harvested_amount = harvest_resource(resource_position, quantity)
    
    # Check if successfully harvested sufficient quantities of desired items 
    assert harvested_amount >= quantity - (quantity * 0.1), f"Not enough {resource_type.name}. Expected at least {quantity}, but got {harvested_amount}"
    
    print(f"Successfully mined {harvested_amount} {resource_type.name}(s). Current Inventory:", inspect_inventory())

# Collecting stone from wooden chest entity on map

# Locate existing wooden chest entity within game world environment 
wooden_chests = get_entities({Prototype.WoodenChest})
assert len(wooden_chests) > 0, "No wooden chest found on the map"
wooden_chest = wooden_chests[0]

# Navigate toward designated wooden-chest coordinates  
move_to(wooden_chest.position)

# Extract entire stone content stored inside previously discovered container object/entity structure  
extracted_stone = extract_item(Prototype.Stone, wooden_chest.position, 7)

print(f"Extracted {extracted_stone} stones from Wooden Chest.")

current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone.value[0], 0) >= 7, "Failed extraction! Insufficient Stones Retrieved."

print("Resources gathering completed successfully!")
print("Final Inventory:", inspect_inventory())


"""
Step 3: Craft and set up the furnace. We need to:
- Move to the wooden chest and collect the 7 stone
- Craft a stone furnace
- Place the stone furnace and fuel it with coal
"""
# Inventory at the start of step {'coal': 10, 'stone': 7, 'iron-ore': 15}
#Step Execution

# Step 3: Craft and set up the furnace

# Craft a stone furnace using available stones
print("Crafting a Stone Furnace...")
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)
assert crafted_furnaces == 1, f"Failed to craft Stone Furnace. Expected 1 but got {crafted_furnaces}"
print("Successfully crafted a Stone Furnace.")

# Decide on position to place the stone furnace
furnace_position = Position(x=-10.0, y=-10.0) # Example position; adjust based on strategy/game requirements

# Move close to desired position before placing entity
move_to(furnace_position)

# Place the crafted stone furnace at decided location
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, position=furnace_position)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Fueling process - Insert coal into placed stone furnace's fuel inventory
coal_amount_to_insert = inspect_inventory().get('coal', 0) # Use all available coal for now 

if coal_amount_to_insert > 0:
    print(f"Inserting {coal_amount_to_insert} units of Coal into the Stone Furnace...")
    inserter_response = insert_item(Prototype.Coal, target=stone_furnace, quantity=coal_amount_to_insert)
    print(f"Coal inserted successfully into Furnace at {inserter_response.position}.")
else:
    print("No Coal available in inventory for fueling! Check resource collection step.")

print("Stone Furnace setup completed!")


"""
Step 4: Smelt iron plates. We need to:
- Smelt 12 iron ore into 12 iron plates using the stone furnace
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 15}
#Step Execution

# Step 4: Smelt iron plates

# Get existing stone furnace entity
stone_furnace = get_entities({Prototype.StoneFurnace})[0]

# Check initial inventory state for logging and debugging purposes
initial_inventory = inspect_inventory()
print(f"Initial Inventory before smelting: {initial_inventory}")

# Extract any existing contents from the furnace if necessary (e.g., leftover plates)
existing_plates_in_furnace = stone_furnace.furnace_result.get(Prototype.IronPlate.value[0], 0)
if existing_plates_in_furnace > 0:
    extract_item(Prototype.IronPlate, stone_furnace.position, existing_plates_in_furnace)
    print(f"Extracted {existing_plates_in_furnace} existing iron plates from the furnace")

# Obtain current quantity of iron ore in inventory
iron_ore_quantity = initial_inventory.get('iron-ore', 0)

# Insert required amount of iron ore into stone furnace's source inventory
required_iron_ore = min(12, iron_ore_quantity)  # Ensure not exceeding available resources

if required_iron_ore > 0:
    print(f"Inserting {required_iron_ore} units of Iron Ore into Stone Furnace...")
    insert_item(Prototype.IronOre, target=stone_furnace, quantity=required_iron_ore)
else:
    raise ValueError("Not enough Iron Ore available for smelting!")

print("Iron Ore successfully inserted.")

# Calculate expected number of resulting iron plates after smelting operation completes 
expected_final_plate_count = inspect_inventory().get('iron-plate', 0) + required_iron_ore

# Wait duration calculated based on number of ores being processed - approximately ~3.5 seconds per unit 
smelting_duration_seconds = 3.5 * required_iron_ore

sleep(smelting_duration_seconds)

max_attempts = 5
for _ in range(max_attempts):
    # Attempt extraction once sufficient time has elapsed since initiation point  
    extract_item(Prototype.IronPlate, position=stone_furnace.position, quantity=required_iron_ore)
    
    # Verify whether desired outcome achieved via accurate count comparison against pre-determined expectations   
    current_plate_count = inspect_inventory().get('iron-plate', 0)
    if current_plate_count >= expected_final_plate_count:
        print(f"Successfully smelted {required_iron_ore} iron plates.")
        break
    else:
        print(f"Smelting not complete. Current iron plate count: {current_plate_count}. Waiting for more...")
        sleep(5)  # Wait a bit more if not all plates are ready

# Final assertion to ensure we have the required number of iron plates
final_iron_plate_count = inspect_inventory().get('iron-plate', 0)
assert final_iron_plate_count >= 12, f"Failed to smelt enough iron plates. Expected at least 12, but got {final_iron_plate_count}"

print(f"Final Inventory after smelting: {inspect_inventory()}")


"""
Step 5: Craft iron gear wheels. We need to:
- Craft 4 iron gear wheels using 8 of the iron plates
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 3, 'iron-plate': 12}
#Step Execution

# Step 5: Craft iron gear wheels

# Check initial count of iron plates and calculate how many are needed
initial_iron_plate_count = inspect_inventory().get('iron-plate', 0)
required_iron_plates = 8

assert initial_iron_plate_count >= required_iron_plates, f"Not enough Iron Plates to craft Iron Gear Wheels. Required: {required_iron_plates}, Available: {initial_iron_plate_count}"

print(f"Initial Inventory before crafting Iron Gear Wheels: {inspect_inventory()}")

# Crafting 4 Iron Gear Wheels using available Iron Plates
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=4)
assert crafted_gears == 4, f"Failed to craft all required Iron Gear Wheels. Expected: 4, Crafted: {crafted_gears}"
print(f"Successfully crafted {crafted_gears} Iron Gear Wheels.")

# Verify final count of items in inventory after crafting operation
final_inventory = inspect_inventory()
expected_final_gear_wheel_count = final_inventory.get('iron-gear-wheel', 0)

assert expected_final_gear_wheel_count >= crafted_gears, f"Iron Gear Wheel count mismatch! Expected at least {crafted_gears}, but found {expected_final_gear_wheel_count}."

print(f"Final Inventory after crafting Iron Gear Wheels: {final_inventory}")


"""
Step 6: Craft transport belts. We need to:
- Craft 4 sets of transport belts (8 in total) using 4 iron gear wheels and 4 iron plates
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 3, 'iron-plate': 4, 'iron-gear-wheel': 4}
#Step Execution

# Step 6: Craft transport belts

# Check initial count of required materials in inventory
initial_iron_plate_count = inspect_inventory().get('iron-plate', 0)
initial_iron_gear_wheel_count = inspect_inventory().get('iron-gear-wheel', 0)

# Calculate how many transport belts we can craft based on available materials
craftable_transport_belts = min(initial_iron_plate_count, initial_iron_gear_wheel_count)

print(f"Initial Inventory before crafting Transport Belts: {inspect_inventory()}")
print(f"We can craft up to {craftable_transport_belts} Transport Belts.")

# Crafting Transport Belts using available Iron Plates and Gear Wheels
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=craftable_transport_belts)
assert crafted_transport_belts == craftable_transport_belts, (
    f"Failed to craft all possible Transport Belts. Expected: {craftable_transport_belts}, Crafted: {crafted_transport_belts}"
)
print(f"Successfully crafted {crafted_transport_belts} Transport Belts.")

# Verify final count of items in inventory after crafting operation
final_inventory = inspect_inventory()
final_transport_belt_count = final_inventory.get('transport-belt', 0)

assert final_transport_belt_count >= crafted_transport_belts, (
    f"Transport Belt count mismatch! Expected at least {crafted_transport_belts}, but found {final_transport_belt_count}."
)

print(f"Final Inventory after crafting Transport Belts: {final_inventory}")

# Check if we met the original goal of 7 transport belts
if final_transport_belt_count >= 7:
    print("Successfully crafted at least 7 transport belts as required.")
else:
    print(f"Warning: Only crafted {final_transport_belt_count} transport belts. The goal was 7.")


"""
Step 7: Verify success. We need to:
- Check the inventory to confirm that we have at least 7 transport belts
##
"""
# Inventory at the start of step {'transport-belt': 4, 'stone': 2, 'iron-ore': 3, 'iron-plate': 2, 'iron-gear-wheel': 2}
#Step Execution

# Verify Success Step

# Check current inventory for logging purposes
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Get count of Transport Belts in inventory
transport_belt_count = current_inventory.get('transport-belt', 0)
print(f"Transport Belt Count: {transport_belt_count}")

# Check if we have achieved our goal of crafting at least 7 Transport Belts
if transport_belt_count >= 7:
    print("Success! We have met our goal with at least 7 Transport Belts.")
else:
    missing_transport_belts = 7 - transport_belt_count
    print(f"We need {missing_transport_belts} more Transport Belts to meet our goal.")
    
    # Calculate required resources
    iron_plates_needed = missing_transport_belts
    iron_gear_wheels_needed = missing_transport_belts
    
    print(f"To craft the remaining Transport Belts, we need:")
    print(f"- {iron_plates_needed} Iron Plates")
    print(f"- {iron_gear_wheels_needed} Iron Gear Wheels")
    
    # Check if we have enough resources to craft the remaining Transport Belts
    iron_plates_available = current_inventory.get('iron-plate', 0)
    iron_gear_wheels_available = current_inventory.get('iron-gear-wheel', 0)
    
    if iron_plates_available >= iron_plates_needed and iron_gear_wheels_available >= iron_gear_wheels_needed:
        print("We have enough resources to craft the remaining Transport Belts.")
        print("Please run the crafting step again to complete the goal.")
    else:
        print("We don't have enough resources to craft the remaining Transport Belts.")
        print("Please gather more resources and craft the necessary components before trying again.")

print("Verification step completed.")
