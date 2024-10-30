from factorio_instance import *

"""
Main Objective: We require one GunTurret. The final success should be checked by looking if a GunTurret is in inventory
"""



"""
Step 1: Gather resources. We need to gather the following resources:
- Mine the iron ore and copper ore from the chest
- Mine additional iron ore (at least 31 more)
- Mine additional copper ore (at least 3 more)
- Mine coal for fuel (at least 10)
- Mine stone for furnaces (at least 10)
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Extract resources from the wooden chest
chest = get_entities({Prototype.WoodenChest})[0]
move_to(chest.position)

# Extract iron ore from chest
iron_ore_in_chest = chest.inventory.get(Prototype.IronOre, 0)
extract_item(Prototype.IronOre, chest.position, iron_ore_in_chest)
print(f"Extracted {iron_ore_in_chest} iron ore from chest")

# Extract copper ore from chest
copper_ore_in_chest = chest.inventory.get(Prototype.CopperOre, 0)
extract_item(Prototype.CopperOre, chest.position, copper_ore_in_chest)
print(f"Extracted {copper_ore_in_chest} copper ore from chest")

print(f"Current inventory after extracting from chest: {inspect_inventory()}")

# Step 2: Mine additional resources
resources_to_mine = [
    (Resource.IronOre, 31 + max(0, 31 - iron_ore_in_chest)),
    (Resource.CopperOre, 3 + max(0, 3 - copper_ore_in_chest)),
    (Resource.Coal, 10),
    (Resource.Stone, 10)
]

for resource, amount in resources_to_mine:
    resource_position = nearest(resource)
    move_to(resource_position)
    
    # Harvest a bit more than needed to account for inefficiencies
    harvest_amount = int(amount * 1.2)
    harvested = harvest_resource(resource_position, harvest_amount)
    
    print(f"Mined {harvested} {resource}")
    
    # Check if we have enough resources
    current_amount = inspect_inventory()[resource]
    print(f"Current amount of {resource}: {current_amount}")
    
    if current_amount < amount:
        print(f"Warning: Not enough {resource}. Trying to mine more.")
        additional_harvest = harvest_resource(resource_position, amount - current_amount)
        print(f"Additionally mined {additional_harvest} {resource}")
    
    print(f"Current inventory: {inspect_inventory()}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have gathered enough resources
assert final_inventory[Prototype.IronOre] >= 40, f"Not enough iron ore. Expected at least 40, but got {final_inventory[Prototype.IronOre]}"
assert final_inventory[Prototype.CopperOre] >= 10, f"Not enough copper ore. Expected at least 10, but got {final_inventory[Prototype.CopperOre]}"
assert final_inventory[Prototype.Coal] >= 10, f"Not enough coal. Expected at least 10, but got {final_inventory[Prototype.Coal]}"
assert final_inventory[Prototype.Stone] >= 10, f"Not enough stone. Expected at least 10, but got {final_inventory[Prototype.Stone]}"

print("Successfully gathered all required resources!")


"""
Step 2: Craft and set up smelting. We need to craft furnaces and set up a smelting operation:
- Craft 2 stone furnaces using the stone we gathered
- Place down the furnaces and fuel them with coal
- Start smelting iron ore in one furnace and copper ore in the other
"""
# Inventory at the start of step {'coal': 12, 'stone': 12, 'iron-ore': 72, 'copper-ore': 10}
#Step Execution

# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, 2)
assert inspect_inventory()[Prototype.StoneFurnace] >= 2, "Failed to craft 2 stone furnaces"

# Place down the furnaces
furnace_positions = [
    Position(x=0, y=2),
    Position(x=0, y=-2)
]

furnaces = []
for pos in furnace_positions:
    move_to(pos)
    furnace = place_entity(Prototype.StoneFurnace, position=pos)
    furnaces.append(furnace)
    print(f"Placed a stone furnace at {pos}")

# Fuel the furnaces with coal
coal_per_furnace = 5
for furnace in furnaces:
    insert_item(Prototype.Coal, furnace, coal_per_furnace)
    print(f"Inserted {coal_per_furnace} coal into furnace at {furnace.position}")

# Start smelting iron ore in one furnace and copper ore in the other
iron_ore_to_smelt = min(50, inspect_inventory()[Prototype.IronOre])
copper_ore_to_smelt = min(50, inspect_inventory()[Prototype.CopperOre])

insert_item(Prototype.IronOre, furnaces[0], iron_ore_to_smelt)
print(f"Inserted {iron_ore_to_smelt} iron ore into furnace at {furnaces[0].position}")

insert_item(Prototype.CopperOre, furnaces[1], copper_ore_to_smelt)
print(f"Inserted {copper_ore_to_smelt} copper ore into furnace at {furnaces[1].position}")

# Wait for smelting to start
sleep(5)

# Check if smelting has started
for furnace in furnaces:
    furnace_status = get_entity(Prototype.StoneFurnace, furnace.position).status
    assert furnace_status == EntityStatus.WORKING, f"Furnace at {furnace.position} is not working. Status: {furnace_status}"

print("Successfully set up smelting operation with two furnaces")


"""
Step 3: Craft intermediate components. While smelting is ongoing, craft the necessary intermediate components:
- Craft 10 iron gear wheels (requires 20 iron plates)
"""
# Placeholder 3

"""
Step 4: Craft GunTurret. Once we have all the necessary components, craft the GunTurret:
- Ensure we have 10 copper plates, 10 iron gear wheels, and 20 iron plates
- Craft 1 GunTurret using these components
"""
# Placeholder 4

"""
Step 5: Verify success. Check the inventory to confirm that we have crafted a GunTurret:
- Inspect the inventory to see if there is 1 GunTurret present

##
"""
# Placeholder 5