# Find nearest coal patch
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
assert coal_patch, "No coal patch found nearby"

# Place coal burner mining drill
drill_position = coal_patch.bounding_box.center
move_to(drill_position)
drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, drill_position)
assert drill, f"Failed to place burner mining drill at {drill_position}"
print(f"Placed burner mining drill at {drill.position}")

# Place inserter next to the drill
inserter_position = Position(x=drill.position.x, y=drill.position.y + 1)
inserter = place_entity(Prototype.BurnerInserter, Direction.UP, inserter_position)
assert inserter, f"Failed to place inserter at {inserter_position}"
print(f"Placed inserter at {inserter.position}")

# Verify inserter is facing the drill
assert inserter.direction.name == Direction.UP.name, f"Inserter is not facing the drill. Current direction: {inserter.direction}"

# Place transport belt connecting drill to inserter
belt_start = drill.drop_position
belt_end = inserter.pickup_position
belts = connect_entities(belt_start, belt_end, Prototype.TransportBelt)
assert belts, f"Failed to place transport belt from {belt_start} to {belt_end}"
print(f"Placed {len(belts)} transport belt(s) from drill to inserter")

# Verify the setup
entities = inspect_entities(drill.position, radius=5)
assert entities.get_entity(Prototype.BurnerMiningDrill), "Burner mining drill not found in setup"
assert entities.get_entity(Prototype.BurnerInserter), "Inserter not found in setup"
assert any(e.name == "transport-belt" for e in entities.entities), "Transport belts not found in setup"

print("Successfully set up coal mining loop with burner mining drill, inserter, and transport belts")