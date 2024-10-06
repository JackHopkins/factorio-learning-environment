
# Find the nearest wood resource
wood_position = nearest(Resource.Wood)
print(f"Nearest wood position: {wood_position}")

# Move to the wood position
move_to(wood_position)
print("Moved to wood position")

# Initialize wood count
wood_count = 0

# Harvest wood until we have at least 20
while wood_count < 20:
    harvested = harvest_resource(wood_position, quantity=5)
    wood_count += harvested
    print(f"Harvested {harvested} wood, total: {wood_count}")

    # If we didn't harvest any wood, move to the next nearest wood resource
    if harvested == 0:
        wood_position = nearest(Resource.Wood)
        print(f"Moving to next wood position: {wood_position}")
        move_to(wood_position)

# Check inventory to confirm wood count
inventory = inspect_inventory()
actual_wood_count = inventory.get("wood", 0)
print(f"Wood in inventory: {actual_wood_count}")

# Assert that we have at least 20 wood
assert actual_wood_count >= 20, f"Failed to gather 20 wood. Current wood count: {actual_wood_count}"

print("Successfully gathered at least 20 wood!")
