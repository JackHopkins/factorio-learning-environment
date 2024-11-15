

from factorio_instance import *

"""
Step 1: Print recipes. We need to print recipes for:
- Assembling machine
- Stone furnace
- Transport belt
- Burner mining drill
- Burner inserter
- Wooden chest
"""

# Get and print recipe for assembling machine
assembling_machine_recipe = get_prototype_recipe(Prototype.AssemblingMachine1)
print("Assembling Machine Recipe:")
print(f"Ingredients: {assembling_machine_recipe.ingredients}")

# Get and print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("\nStone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

# Get and print recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print("\nTransport Belt Recipe:")
print(f"Ingredients: {transport_belt_recipe.ingredients}")

# Get and print recipe for burner mining drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print("\nBurner Mining Drill Recipe:")
print(f"Ingredients: {burner_mining_drill_recipe.ingredients}")

# Get and print recipe for burner inserter
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)
print("\nBurner Inserter Recipe:")
print(f"Ingredients: {burner_inserter_recipe.ingredients}")

# Get and print recipe for wooden chest
wooden_chest_recipe = get_prototype_recipe(Prototype.WoodenChest)
print("\nWooden Chest Recipe:")
print(f"Ingredients: {wooden_chest_recipe.ingredients}")


"""
Step 2: Gather initial resources. We need to:
- Mine iron ore (at least 30 for safety)
- Mine coal (at least 20 for safety)
- Mine stone (at least 10 for crafting stone furnace)
- Gather wood (at least 2 for wooden chest)
"""

# Define required resources and quantities
resources_needed = [
    (Resource.IronOre, 30),
    (Resource.Coal, 20),
    (Resource.Stone, 10),
    (Resource.Wood, 2)
]

# Loop through each resource type and quantity
for resource_type, quantity in resources_needed:
    # Find nearest position of this resource type
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest specified quantity of this resource
    harvested = harvest_resource(resource_position, quantity)
    
    # Check if we harvested enough; if not, try again with remaining amount needed
    while inspect_inventory()[resource_type] < quantity:
        remaining = quantity - inspect_inventory()[resource_type]
        harvested += harvest_resource(resource_position, remaining)
    
    # Verify that we have harvested at least the required amount
    assert inspect_inventory()[resource_type] >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Actual: {inspect_inventory()[resource_type]}"
    
    print(f"Successfully gathered {inspect_inventory()[resource_type]} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Assert that we have at least the required amounts for each resource
assert final_inventory[Resource.IronOre] >= 30, "Not enough Iron Ore"
assert final_inventory[Resource.Coal] >= 20, "Not enough Coal"
assert final_inventory[Resource.Stone] >= 10, "Not enough Stone"
assert final_inventory[Resource.Wood] >= 2, "Not enough Wood"

print("Successfully gathered all necessary resources.")


"""
Step 3: Craft and set up basic structures. We need to:
- Craft a stone furnace
- Place the stone furnace at (0, 0)
- Craft and place a burner mining drill on the iron ore patch
- Craft and place a burner inserter between the drill and the furnace
- Craft and place a wooden chest next to the furnace
"""

# Craft a stone furnace
print("Crafting Stone Furnace...")
craft_item(Prototype.StoneFurnace, 1)
print("Successfully crafted Stone Furnace.")

# Place the stone furnace at (0, 0)
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
stone_furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed Stone Furnace at {furnace_position}")

# Find nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest Iron Ore patch found at {iron_ore_position}")

# Move to iron ore patch
move_to(iron_ore_position)

# Craft a burner mining drill
print("Crafting Burner Mining Drill...")
craft_item(Prototype.BurnerMiningDrill, 1)
print("Successfully crafted Burner Mining Drill.")

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed Burner Mining Drill at {drill.position}")

# Craft a burner inserter
print("Crafting Burner Inserter...")
craft_item(Prototype.BurnerInserter, 1)
print("Successfully crafted Burner Inserter.")

# Calculate position for burner inserter (midway between drill and furnace)
inserter_position = Position(
    x=(drill.position.x + stone_furnace.position.x) / 2,
    y=(drill.position.y + stone_furnace.position.y) / 2
)

# Move to inserter position
move_to(inserter_position)

# Place the burner inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, direction=Direction.RIGHT, reference_position=drill.position)
print(f"Placed Burner Inserter at {inserter.position}")

# Craft a wooden chest
print("Crafting Wooden Chest...")
craft_item(Prototype.WoodenChest, 1)
print("Successfully crafted Wooden Chest.")

# Calculate position for wooden chest (next to furnace)
chest_position = Position(
    x=stone_furnace.position.x + 1,
    y=stone_furnace.position.y
)

# Move to chest position
move_to(chest_position)

# Place the wooden chest
chest = place_entity(Prototype.WoodenChest, position=chest_position)
print(f"Placed Wooden Chest at {chest.position}")

print("Successfully completed Step 3: Crafted and set up basic structures.")


"""
Step 4: Smelt iron plates. We need to:
- Fuel the stone furnace with coal
- Insert iron ore into the furnace
- Wait for smelting and extract at least 20 iron plates
"""

# Move to stone furnace position
move_to(stone_furnace.position)

# Insert coal into the stone furnace as fuel
print("Inserting coal into the Stone Furnace...")
updated_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=10)
print("Coal successfully inserted.")

# Check if the furnace has fuel
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to insert coal into the Stone Furnace"
print(f"Stone Furnace now has {coal_in_furnace} units of coal.")

# Insert iron ore into the stone furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Inserting {iron_ore_in_inventory} units of Iron Ore into the Stone Furnace...")
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print("Iron Ore successfully inserted.")

# Wait for smelting to complete
smelting_time_per_unit = 3.2  # Average smelting time per unit
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Attempt to extract iron plates multiple times to ensure we get them all
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    if current_iron_plate_count >= 20:
        break
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

# Final assertion check
assert current_iron_plate_count >= 20, f"Failed to obtain required number of Iron Plates! Expected at least 20 but got {current_iron_plate_count}"
print("Successfully obtained at least 20 Iron Plates.")


"""
Step 5: Craft iron gear wheels. We need to:
- Craft at least 4 iron gear wheels
"""

# Check initial inventory for available iron plates
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Calculate the number of iron gear wheels needed (at least 4)
iron_gears_needed = 4

# Ensure we have enough iron plates to craft the required number of iron gear wheels
assert iron_plates_in_inventory >= iron_gears_needed * 2, f"Not enough Iron Plates to craft required number of Iron Gear Wheels! Available: {iron_plates_in_inventory}, Required: {iron_gears_needed * 2}"

# Crafting Iron Gear Wheels
print(f"Crafting {iron_gears_needed} Iron Gear Wheels...")
crafted_iron_gears = craft_item(Prototype.IronGearWheel, quantity=iron_gears_needed)
print(f"Successfully crafted {crafted_iron_gears} Iron Gear Wheels.")

# Verify that we have crafted at least the required number of iron gear wheels
current_iron_gear_count = inspect_inventory()[Prototype.IronGearWheel]
assert current_iron_gear_count >= iron_gears_needed, f"Failed to craft required number of Iron Gear Wheels! Expected at least {iron_gears_needed} but got {current_iron_gear_count}"

print(f"Inventory after crafting: {inspect_inventory()}")
print("Successfully completed Step 5: Crafted at least 4 Iron Gear Wheels.")


"""
Step 6: Craft underground-belt. We need to:
- Craft 2 iron gear wheels
- Craft 1 underground-belt
"""

# Check initial inventory for available iron plates
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Calculate the number of iron gear wheels needed (2 for underground-belt)
iron_gears_needed = 2

# Ensure we have enough iron plates to craft the required number of iron gear wheels
assert iron_plates_in_inventory >= iron_gears_needed * 2, f"Not enough Iron Plates to craft required number of Iron Gear Wheels! Available: {iron_plates_in_inventory}, Required: {iron_gears_needed * 2}"

# Crafting Iron Gear Wheels
print(f"Crafting {iron_gears_needed} Iron Gear Wheels...")
crafted_iron_gears = craft_item(Prototype.IronGearWheel, quantity=iron_gears_needed)
print(f"Successfully crafted {crafted_iron_gears} Iron Gear Wheels.")

# Verify that we have crafted the required number of iron gear wheels
current_iron_gear_count = inspect_inventory()[Prototype.IronGearWheel]
assert current_iron_gear_count >= iron_gears_needed, f"Failed to craft required number of Iron Gear Wheels! Expected {iron_gears_needed} but got {current_iron_gear_count}"

# Crafting Underground Belt
print("Crafting 1 Underground Belt...")
crafted_underground_belt = craft_item(Prototype.UndergroundBelt, quantity=1)
print(f"Successfully crafted {crafted_underground_belt} Underground Belt.")

# Verify that we have crafted at least 1 underground belt
current_underground_belt_count = inspect_inventory()[Prototype.UndergroundBelt]
assert current_underground_belt_count >= 1, f"Failed to craft required number of Underground Belts! Expected at least 1 but got {current_underground_belt_count}"

print(f"Inventory after crafting: {inspect_inventory()}")
print("Successfully completed Step 6: Crafted 2 Iron Gear Wheels and 1 Underground Belt.")


"""
Step 7: Craft fast-underground-belt. We need to:
- Craft 2 iron gear wheels
- Craft 1 fast-underground-belt
"""

# Check initial inventory for available iron plates
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Calculate the number of iron gear wheels needed (2 for fast-underground-belt)
iron_gears_needed = 2

# Ensure we have enough iron plates to craft the required number of iron gear wheels
assert iron_plates_in_inventory >= iron_gears_needed * 2, f"Not enough Iron Plates to craft required number of Iron Gear Wheels! Available: {iron_plates_in_inventory}, Required: {iron_gears_needed * 2}"

# Crafting Iron Gear Wheels
print(f"Crafting {iron_gears_needed} Iron Gear Wheels...")
crafted_iron_gears = craft_item(Prototype.IronGearWheel, quantity=iron_gears_needed)
print(f"Successfully crafted {crafted_iron_gears} Iron Gear Wheels.")

# Verify that we have crafted the required number of iron gear wheels
current_iron_gear_count = inspect_inventory()[Prototype.IronGearWheel]
assert current_iron_gear_count >= iron_gears_needed, f"Failed to craft required number of Iron Gear Wheels! Expected {iron_gears_needed} but got {current_iron_gear_count}"

# Crafting Fast Underground Belt
print("Crafting 1 Fast Underground Belt...")
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Successfully crafted {crafted_fast_underground_belt} Fast Underground Belt.")

# Verify that we have crafted at least 1 fast underground belt
current_fast_underground_belt_count = inspect_inventory()[Prototype.FastUndergroundBelt]
assert current_fast_underground_belt_count >= 1, f"Failed to craft required number of Fast Underground Belts! Expected at least 1 but got {current_fast_underground_belt_count}"

print(f"Inventory after crafting: {inspect_inventory()}")
print("Successfully completed Step 7: Crafted 2 Iron Gear Wheels and 1 Fast Underground Belt.")


