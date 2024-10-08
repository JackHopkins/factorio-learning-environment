
# Find the nearest coal patch
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
assert coal_patch is not None, "No coal patch found nearby"

# Place burner mining drill on the coal patch
drill_position = coal_patch.bounding_box.center
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.DOWN, position=drill_position)
assert drill is not None, "Failed to place burner mining drill"
print(f"Placed burner mining drill at {drill.position}")

# Place burner inserter next to the drill
inserter_position = Position(x=drill.position.x + 1, y=drill.position.y)
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.LEFT, position=inserter_position)
assert inserter is not None, "Failed to place burner inserter"
print(f"Placed burner inserter at {inserter.position}")

# Place transport belt in front of the drill
belt_position = Position(x=drill.position.x, y=drill.position.y + 1)
belt = place_entity(Prototype.TransportBelt, direction=Direction.RIGHT, position=belt_position)
assert belt is not None, "Failed to place transport belt"
print(f"Placed transport belt at {belt.position}")

# Place chest at the end of the belt
chest_position = Position(x=belt.position.x + 1, y=belt.position.y)
chest = place_entity(Prototype.WoodenChest, position=chest_position)
assert chest is not None, "Failed to place wooden chest"
print(f"Placed wooden chest at {chest.position}")

# Wait for the system to start working
sleep(10)

# Verify that coal is being mined and transported
drill_inventory = inspect_inventory(drill)
assert drill_inventory.get(Prototype.Coal) > 0, "Drill is not mining coal"

inserter_inventory = inspect_inventory(inserter)
assert inserter_inventory.get(Prototype.Coal) > 0, "Inserter is not picking up coal"

chest_inventory = inspect_inventory(chest)
assert chest_inventory.get(Prototype.Coal) > 0, "Coal is not being transported to the chest"

print("Self-fueling coal mining system created successfully!")
