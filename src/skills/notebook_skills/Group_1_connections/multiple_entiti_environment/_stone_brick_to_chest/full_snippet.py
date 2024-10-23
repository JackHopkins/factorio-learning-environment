from factorio_instance import *

"""
Main Objective: We need to set up stone brick transport from a furnace to a chest. The final setup should be checked by looking if the chest where we sent bricks to has stone bricks
"""



"""
Step 1: Place inserters. We need to place two burner inserters: one at the furnace and one at the chest.
- Move to the stone furnace at (5.0, 0.0) and place a burner inserter next to it
- Move to the wooden chest at (0.5, 0.5) and place a burner inserter next to it
- Rotate the inserter at the chest to put items into the chest
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5}
#Step Execution

from factorio_instance import *

# Move to the stone furnace at (5.0, 0.0)
furnace_position = Position(x=5.0, y=0.0)
move_to(furnace_position)

# Place a burner inserter next to the furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace_position, Direction.RIGHT)
print(f"Placed furnace inserter at {furnace_inserter.position}")

# Move to the wooden chest at (0.5, 0.5)
chest_position = Position(x=0.5, y=0.5)
move_to(chest_position)

# Place a burner inserter next to the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest_position, Direction.LEFT)
print(f"Placed chest inserter at {chest_inserter.position}")

# Rotate the inserter at the chest to face the chest
chest_inserter = rotate_entity(chest_inserter, Direction.RIGHT)
print(f"Rotated chest inserter to face {chest_inserter.direction}")

# Verify the inserters are placed correctly
furnace_inserters = get_entities({Prototype.BurnerInserter}, furnace_inserter.position, radius=1)
chest_inserters = get_entities({Prototype.BurnerInserter}, chest_inserter.position, radius=1)

assert len(furnace_inserters) > 0, "Furnace inserter not found"
assert len(chest_inserters) > 0, "Chest inserter not found"

furnace_inserter = furnace_inserters[0]
chest_inserter = chest_inserters[0]

assert furnace_inserter.position.is_close(furnace_position, 1.5), f"Furnace inserter not in expected position. Expected near {furnace_position}, but got {furnace_inserter.position}"
assert chest_inserter.position.is_close(chest_position, 1.5), f"Chest inserter not in expected position. Expected near {chest_position}, but got {chest_inserter.position}"
assert chest_inserter.direction.value == Direction.RIGHT.value, f"Chest inserter is not facing the right direction. Expected {Direction.RIGHT}, but got {chest_inserter.direction}"

print("Successfully placed and configured both inserters")


"""
Step 2: Connect with transport belts. We need to connect the furnace inserter to the chest inserter using transport belts.
- Start at the furnace inserter's drop position
- Place transport belts to connect the furnace inserter's drop position to the chest inserter's pickup position
"""
# Placeholder 2

"""
Step 3: Fuel the inserters. We need to ensure the burner inserters have fuel to operate.
- Move to each inserter and add coal from the chest at (5.5, -4.5) that contains 100 coal
"""
# Placeholder 3

"""
Step 4: Verify the setup. We need to check if the transport system is working correctly.
- Wait for 30 seconds to allow time for stone bricks to be produced and transported
- Check the inventory of the wooden chest at (0.5, 0.5) for stone bricks
##
"""
# Placeholder 4