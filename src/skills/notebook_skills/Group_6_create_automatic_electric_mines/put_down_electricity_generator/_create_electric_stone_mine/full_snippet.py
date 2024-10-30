from factorio_instance import *

"""
Main Objective: We need to place and power a electric mining drill at a stone patch. Powering works by connecting thedrill with the steam engine with power poles.The final setup should be checked by looking if the drill has power in it by checking the status of the drill
"""



"""
Step 1: Place electric mining drill. We need to find a stone patch and place the electric mining drill on it.
"""
# Inventory at the start of step {'small-electric-pole': 20, 'pipe': 10, 'electric-mining-drill': 1}
#Step Execution

# Find the nearest stone patch
stone_patch_position = nearest(Resource.Stone)
print(f"Nearest stone patch found at: {stone_patch_position}")

# Move to the stone patch location
move_to(stone_patch_position)
print(f"Moved to stone patch at: {stone_patch_position}")

# Place the electric mining drill on the stone patch
drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, stone_patch_position)
print(f"Placed electric mining drill at: {drill.position}")

# Verify that the electric mining drill has been placed correctly
entities_around_drill = get_entities({Prototype.ElectricMiningDrill}, drill.position, radius=1)
assert len(entities_around_drill) == 1, f"Expected 1 electric mining drill, but found {len(entities_around_drill)}"
placed_drill = entities_around_drill[0]
assert placed_drill.name == "electric-mining-drill", f"Expected electric-mining-drill, but found {placed_drill.name}"
assert placed_drill.position.is_close(stone_patch_position), f"Drill not placed on stone patch. Drill at {placed_drill.position}, stone at {stone_patch_position}"

print("Electric mining drill successfully placed on stone patch")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 2: Connect power to the drill. We need to create a power line from the steam engine to the electric mining drill using small electric poles. This involves the following substeps:
- Place the first small electric pole near the steam engine
- Place additional small electric poles to create a power line towards the electric mining drill
- Place the final small electric pole next to the electric mining drill
"""
# Placeholder 2

"""
Step 3: Verify power connection. We need to check if the electric mining drill is powered by examining its status.
- Wait for a few seconds to allow the power to stabilize
- Check the status of the electric mining drill to confirm it has power

##
"""
# Placeholder 3