from factorio_instance import *

"""
Main Objective: We need to place and power a electric mining drill at a iron patch. Powering works by connecting thedrill with the steam engine with power poles. The final setup should be checked by looking if the drill has power in it by checking the status of the drill
"""



"""
Step 1: Place electric mining drill. We need to find the nearest iron patch and place the electric mining drill on it.
"""
# Inventory at the start of step {'small-electric-pole': 20, 'pipe': 10, 'electric-mining-drill': 1}
#Step Execution

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore patch found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the electric mining drill
drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, iron_ore_position)
print(f"Placed electric mining drill at: {drill.position}")

# Verify that the drill has been placed correctly
entities = get_entities({Prototype.ElectricMiningDrill}, drill.position, radius=1)
assert len(entities) > 0, "Failed to place electric mining drill"
placed_drill = entities[0]
print(f"Electric mining drill successfully placed at {placed_drill.position}")

# Check the inventory to make sure we used one drill
inventory = inspect_inventory()
assert inventory[Prototype.ElectricMiningDrill] == 0, "Failed to use the electric mining drill from inventory"
print("Electric mining drill successfully used from inventory")

# Print the final status
print(f"Electric mining drill placed successfully. Current position: {placed_drill.position}")


"""
Step 2: Connect power to the drill. We need to connect the electric mining drill to the steam engine using small electric poles. This involves the following substeps:
- Place small electric poles starting from the steam engine towards the electric mining drill
- Continue placing poles until we reach the drill, ensuring each pole is within range of the previous one
"""
# Placeholder 2

"""
Step 3: Verify power connection. We need to check if the electric mining drill is powered. This involves:
- Wait for a few seconds to allow the power to stabilize
- Check the status of the electric mining drill to ensure it's powered and working

##
"""
# Placeholder 3