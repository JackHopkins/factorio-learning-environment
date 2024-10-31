from factorio_instance import *

"""
Main Objective: We require one OffshorePump. The final success should be checked by looking if a OffshorePump is in inventory
"""



"""
Step 1: Print recipes. We need to craft an OffshorePump. We must print the recipes for OffshorePump and its components:
- OffshorePump
- ElectronicCircuit
- IronGearWheel
- Pipe
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for OffshorePump
offshore_pump_recipe = get_prototype_recipe(Prototype.OffshorePump)
print("Recipe for OffshorePump:")
print(offshore_pump_recipe)
print()

# Get and print the recipe for ElectronicCircuit
electronic_circuit_recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
print("Recipe for ElectronicCircuit:")
print(electronic_circuit_recipe)
print()

# Get and print the recipe for IronGearWheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Recipe for IronGearWheel:")
print(iron_gear_wheel_recipe)
print()

# Get and print the recipe for Pipe
pipe_recipe = get_prototype_recipe(Prototype.Pipe)
print("Recipe for Pipe:")
print(pipe_recipe)
print()

print("All required recipes have been printed.")


"""
Step 2: Gather and process resources. We need to gather and process the necessary resources:
- Use the stone from the chest to craft a StoneFurnace
- Mine iron ore (we need at least 5 iron plates)
- Take the copper ore from the chest
- Mine coal for fuel
- Smelt iron ore and copper ore into plates using the StoneFurnace
"""
# Inventory at the start of step {}
#Step Execution

# 1. Extract stone and copper ore from the chest
chest = get_entities({Prototype.WoodenChest})[0]
move_to(chest.position)
extract_item(Prototype.Stone, chest.position, 10)
extract_item(Prototype.CopperOre, chest.position, 7)

# Assert that we have extracted the items
inventory = inspect_inventory()
assert inventory[Prototype.Stone] == 10, f"Failed to extract stone. Expected 10, but got {inventory[Prototype.Stone]}"
assert inventory[Prototype.CopperOre] == 7, f"Failed to extract copper ore. Expected 7, but got {inventory[Prototype.CopperOre]}"

# 2. Craft the stone furnace
craft_item(Prototype.StoneFurnace, 1)
inventory = inspect_inventory()
assert inventory[Prototype.StoneFurnace] == 1, f"Failed to craft stone furnace. Expected 1, but got {inventory[Prototype.StoneFurnace]}"

# 3. Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, 10)  # We need at least 5 plates, so mine a bit extra
inventory = inspect_inventory()
assert inventory[Prototype.IronOre] >= 10, f"Failed to mine enough iron ore. Expected at least 10, but got {inventory[Prototype.IronOre]}"

# 4. Mine coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, 5)  # Mine some extra for safety
inventory = inspect_inventory()
assert inventory[Prototype.Coal] >= 5, f"Failed to mine enough coal. Expected at least 5, but got {inventory[Prototype.Coal]}"

# 5. Place the stone furnace
furnace_position = Position(x=iron_ore_position.x + 2, y=iron_ore_position.y)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# 6. Smelt iron ore and copper ore
furnace = insert_item(Prototype.Coal, furnace, 5)
furnace = insert_item(Prototype.IronOre, furnace, 10)

# Wait for iron smelting
sleep(10)  # Assuming it takes about 10 seconds to smelt 10 iron ore

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, 10)
inventory = inspect_inventory()
assert inventory[Prototype.IronPlate] >= 5, f"Failed to smelt enough iron plates. Expected at least 5, but got {inventory[Prototype.IronPlate]}"

# Smelt copper ore
furnace = insert_item(Prototype.CopperOre, furnace, 7)

# Wait for copper smelting
sleep(7)  # Assuming it takes about 7 seconds to smelt 7 copper ore

# Extract copper plates
extract_item(Prototype.CopperPlate, furnace.position, 7)
inventory = inspect_inventory()
assert inventory[Prototype.CopperPlate] >= 7, f"Failed to smelt enough copper plates. Expected at least 7, but got {inventory[Prototype.CopperPlate]}"

print(f"Final inventory after gathering and processing resources: {inspect_inventory()}")


"""
Step 3: Craft intermediate components. We need to craft the following:
- 2 ElectronicCircuits
- 1 IronGearWheel
- 1 Pipe
"""
# Inventory at the start of step {'stone': 5, 'iron-plate': 10, 'copper-plate': 7}
#Step Execution

# Craft intermediate components

# 1. Craft IronGearWheel
print("Crafting IronGearWheel...")
craft_item(Prototype.IronGearWheel, 1)
inventory = inspect_inventory()
assert inventory[Prototype.IronGearWheel] >= 1, f"Failed to craft IronGearWheel. Expected at least 1, but got {inventory[Prototype.IronGearWheel]}"
print(f"Successfully crafted 1 IronGearWheel. Current inventory: {inventory}")

# 2. Craft Pipe
print("Crafting Pipe...")
craft_item(Prototype.Pipe, 1)
inventory = inspect_inventory()
assert inventory[Prototype.Pipe] >= 1, f"Failed to craft Pipe. Expected at least 1, but got {inventory[Prototype.Pipe]}"
print(f"Successfully crafted 1 Pipe. Current inventory: {inventory}")

# 3. Craft Copper Cables for ElectronicCircuits
print("Crafting Copper Cables...")
craft_item(Prototype.CopperCable, 6)  # We need 6 copper cables for 2 ElectronicCircuits
inventory = inspect_inventory()
assert inventory[Prototype.CopperCable] >= 6, f"Failed to craft enough Copper Cables. Expected at least 6, but got {inventory[Prototype.CopperCable]}"
print(f"Successfully crafted 6 Copper Cables. Current inventory: {inventory}")

# 4. Craft ElectronicCircuits
print("Crafting ElectronicCircuits...")
craft_item(Prototype.ElectronicCircuit, 2)
inventory = inspect_inventory()
assert inventory[Prototype.ElectronicCircuit] >= 2, f"Failed to craft enough ElectronicCircuits. Expected at least 2, but got {inventory[Prototype.ElectronicCircuit]}"
print(f"Successfully crafted 2 ElectronicCircuits. Current inventory: {inventory}")

# Final verification
required_items = {
    Prototype.IronGearWheel: 1,
    Prototype.Pipe: 1,
    Prototype.ElectronicCircuit: 2
}

for item, count in required_items.items():
    assert inventory[item] >= count, f"Missing required item: {item}. Expected at least {count}, but got {inventory[item]}"

print("All intermediate components have been successfully crafted.")
print(f"Final inventory after crafting intermediate components: {inventory}")


"""
Step 4: Craft OffshorePump. Use the crafted components to create the OffshorePump.
"""
# Inventory at the start of step {'pipe': 1, 'stone': 5, 'iron-plate': 5, 'copper-plate': 4, 'iron-gear-wheel': 1, 'electronic-circuit': 2}
#Step Execution

# Step 4: Craft OffshorePump

# First, let's verify that we have all the necessary components
inventory = inspect_inventory()
print(f"Current inventory before crafting OffshorePump: {inventory}")

required_components = {
    Prototype.IronGearWheel: 1,
    Prototype.ElectronicCircuit: 2,
    Prototype.Pipe: 1
}

for component, required_count in required_components.items():
    assert inventory[component] >= required_count, f"Not enough {component}. Required: {required_count}, Available: {inventory[component]}"

print("All required components are available. Proceeding to craft OffshorePump.")

# Craft the OffshorePump
craft_item(Prototype.OffshorePump, 1)

# Verify that the OffshorePump has been crafted
updated_inventory = inspect_inventory()
assert updated_inventory[Prototype.OffshorePump] >= 1, f"Failed to craft OffshorePump. Expected at least 1, but got {updated_inventory[Prototype.OffshorePump]}"

print(f"Successfully crafted 1 OffshorePump.")
print(f"Updated inventory after crafting OffshorePump: {updated_inventory}")

# Verify that the components were consumed
for component, required_count in required_components.items():
    assert updated_inventory[component] == inventory[component] - required_count, f"Unexpected count for {component}. Expected: {inventory[component] - required_count}, Actual: {updated_inventory[component]}"

print("All components were correctly consumed in the crafting process.")


"""
Step 5: Verify success. Check the inventory to confirm that an OffshorePump is present.
##
"""
# Inventory at the start of step {'offshore-pump': 1, 'stone': 5, 'iron-plate': 5, 'copper-plate': 4}
#Step Execution

# Verify success by checking the inventory for an OffshorePump

# Get the current inventory
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")

# Check if there's at least one OffshorePump in the inventory
offshore_pump_count = inventory.get(Prototype.OffshorePump, 0)

# Assert that we have at least one OffshorePump
assert offshore_pump_count >= 1, f"Failed to craft OffshorePump. Expected at least 1, but got {offshore_pump_count}"

# If the assertion passes, print a success message
print(f"Success! {offshore_pump_count} OffshorePump(s) found in the inventory.")

# Final success message
print("Main objective completed: We have successfully crafted an OffshorePump!")
