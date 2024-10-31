from factorio_instance import *

"""
Main Objective: We require one ElectricMiningDrill. The final success should be checked by looking if a ElectricMiningDrill is in inventory
"""



"""
Step 1: Gather resources. We need to gather the following resources:
- Mine 23 iron ore
- Mine 5 coal (for fueling the furnace)
- Mine 5 stone (for crafting a stone furnace)
- Collect 19 copper ore from the wooden chest on the map
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Gather resources

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 23),
    (Resource.Coal, 5),
    (Resource.Stone, 5)
]

# Gather each resource
for resource, amount in resources_to_gather:
    resource_position = nearest(resource)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Verify the gathered amount
    inventory = inspect_inventory()
    assert inventory[resource] >= amount, f"Failed to gather enough {resource}. Expected {amount}, got {inventory[resource]}"

# Collect copper ore from the wooden chest
chests = get_entities({Prototype.WoodenChest})
if chests:
    copper_chest = chests[0]
    move_to(copper_chest.position)
    extracted = extract_item(Prototype.CopperOre, copper_chest.position, 19)
    print(f"Extracted {extracted} copper ore from the wooden chest")

    # Verify the extracted amount
    inventory = inspect_inventory()
    assert inventory[Prototype.CopperOre] >= 19, f"Failed to extract enough copper ore. Expected 19, got {inventory[Prototype.CopperOre]}"
else:
    print("No wooden chest found on the map")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory[Prototype.IronOre]}")
print(f"Coal: {final_inventory[Prototype.Coal]}")
print(f"Stone: {final_inventory[Prototype.Stone]}")
print(f"Copper Ore: {final_inventory[Prototype.CopperOre]}")

# Assert that we have gathered all required resources
assert final_inventory[Prototype.IronOre] >= 23, "Not enough Iron Ore gathered"
assert final_inventory[Prototype.Coal] >= 5, "Not enough Coal gathered"
assert final_inventory[Prototype.Stone] >= 5, "Not enough Stone gathered"
assert final_inventory[Prototype.CopperOre] >= 19, "Not enough Copper Ore gathered"

print("Successfully gathered all required resources!")


"""
Step 2: Craft and set up smelting. We need to craft a stone furnace and smelt the ores:
- Craft a stone furnace using 5 stone
- Place the stone furnace and fuel it with coal
- Smelt 5 copper plates and 23 iron plates
"""
# Placeholder 2

"""
Step 3: Craft components. We need to craft the following components:
- Craft 10 iron gear wheels (using 20 iron plates)
- Craft 9 copper cables (using 5 copper plates)
- Craft 3 electronic circuits (using 9 copper cables and 3 iron plates)
"""
# Placeholder 3

"""
Step 4: Craft ElectricMiningDrill. Use the components to craft the final product:
- Craft 1 ElectricMiningDrill using 3 electronic circuits, 5 iron gear wheels, and 10 iron plates
"""
# Placeholder 4

"""
Step 5: Verify success. Check the inventory to confirm that we have crafted an ElectricMiningDrill.
##
"""
# Placeholder 5