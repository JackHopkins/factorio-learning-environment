from factorio_instance import *

"""
Main Objective: We need to craft 7 electronic circuits. The final success should be checked by looking if the electronic circuits are in inventory
"""



"""
Step 1: Print recipes and gather initial resources. We need to print out the recipes for electronic circuits and gather initial resources by hand.
- Print recipe for electronic circuit
- Mine iron ore, copper ore, coal, and stone by hand
- Craft a stone furnace
"""
# Inventory at the start of step {}
#Step Execution

from factorio_instance import *

# Print the recipe for electronic circuits
electronic_circuit_recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
print(f"Electronic Circuit Recipe: {electronic_circuit_recipe}")

# Determine required resources and mine them
resources_to_mine = [
    (Resource.IronOre, 35),  # Extra for crafting and smelting
    (Resource.CopperOre, 35),  # Extra for crafting and smelting
    (Resource.Coal, 20),  # For fueling
    (Resource.Stone, 10)  # For stone furnace and extra
]

print("Starting to mine resources:")
for resource, amount in resources_to_mine:
    resource_position = nearest(resource)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, amount)
    print(f"Mined {harvested} {resource}")

    # Verify the mined amount
    inventory = inspect_inventory()
    assert inventory[resource] >= harvested, f"Failed to mine enough {resource}. Expected at least {harvested}, but got {inventory[resource]}"

# Craft a stone furnace
print("Crafting a stone furnace")
crafted = craft_item(Prototype.StoneFurnace, 1)
assert crafted == 1, f"Failed to craft Stone Furnace. Expected 1, but crafted {crafted}"

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources and crafting:")
for item in [Resource.IronOre, Resource.CopperOre, Resource.Coal, Resource.Stone, Prototype.StoneFurnace]:
    amount = final_inventory[item]
    print(f"{item}: {amount}")

# Verify we have all required items
required_items = [Resource.IronOre, Resource.CopperOre, Resource.Coal, Resource.Stone, Prototype.StoneFurnace]
for item in required_items:
    assert final_inventory[item] > 0, f"Missing {item} in inventory"

print("Successfully gathered all required resources and crafted a stone furnace")


"""
Step 2: Set up initial mining and smelting. We need to create a basic setup for mining and smelting.
- Place the stone furnace
- Craft and place a burner mining drill on an iron ore patch
- Fuel the burner mining drill and furnace with coal
- Start smelting iron plates
"""
# Placeholder 2

"""
Step 3: Expand mining and smelting. We need to set up copper mining and smelting.
- Craft another stone furnace and burner mining drill
- Place the new burner mining drill on a copper ore patch
- Place the new stone furnace
- Fuel the new burner mining drill and furnace with coal
- Start smelting copper plates
"""
# Placeholder 3

"""
Step 4: Craft intermediate products. We need to craft copper cables for the electronic circuits.
- Craft copper cables using the copper plates
"""
# Placeholder 4

"""
Step 5: Craft electronic circuits. We need to craft 7 electronic circuits and verify their presence in the inventory.
- Craft 7 electronic circuits using iron plates and copper cables
- Check inventory to confirm the presence of 7 electronic circuits

##
"""
# Placeholder 5