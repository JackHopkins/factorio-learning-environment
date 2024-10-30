from factorio_instance import *

"""
Main Objective: We need to place and power a electric mining drill at a coal patch. Powering works by connecting thedrill with the steam engine with power poles. The final setup should be checked by looking if the drill has power in it by checking the status of the drill
"""



"""
Step 1: Place electric mining drill. We need to carry out the following substeps:
- Move to the nearest coal patch
- Place the electric mining drill on the coal patch
"""
# Inventory at the start of step {'small-electric-pole': 20, 'pipe': 10, 'electric-mining-drill': 1}
#Step Execution

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
print(f"Nearest coal patch found at: {coal_position}")

# Move to the coal patch
move_to(coal_position)
print(f"Moved to coal patch at: {coal_position}")

# Place the electric mining drill on the coal patch
drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, coal_position)
print(f"Placed electric mining drill at: {drill.position}")

# Verify that the drill was placed successfully
entities_at_coal = get_entities({Prototype.ElectricMiningDrill}, coal_position, radius=1)
assert len(entities_at_coal) > 0, "Failed to place electric mining drill on coal patch"

# Check the inventory to ensure we used one electric mining drill
inventory = inspect_inventory()
assert inventory[Prototype.ElectricMiningDrill] == 0, "Electric mining drill was not consumed from inventory"

print("Successfully placed electric mining drill on coal patch")
print(f"Current inventory: {inventory}")


"""
Step 2: Connect electric mining drill to power. We need to connect the electric mining drill to the steam engine using small electric poles. We need to carry out the following substeps:
- Place a small electric pole next to the steam engine
- Place small electric poles in a line from the steam engine towards the electric mining drill
- Place a small electric pole next to the electric mining drill
"""
# Placeholder 2

"""
Step 3: Verify power connection. We need to check if the electric mining drill is powered. We need to carry out the following substeps:
- Wait for 5 seconds to allow the power to stabilize
- Check the status of the electric mining drill to ensure it's powered and working
##
"""
# Placeholder 3