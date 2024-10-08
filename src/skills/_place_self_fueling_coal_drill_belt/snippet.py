
# Find the nearest coal patch
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
assert coal_patch is not None, "No coal patch found nearby"
assert coal_patch.size >= 25, f"Coal patch too small: {coal_patch.size} tiles (need at least 25)"

# Place 5 burner mining drills in a line
drills = []
for i in range(5):
    drill_position = Position(x=coal_patch.bounding_box.left_top.x + i * 3, y=coal_patch.bounding_box.center.y)
    drill = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, drill_position)
    assert drill is not None, f"Failed to place burner mining drill at {drill_position}"
    drills.append(drill)

print(f"Placed {len(drills)} burner mining drills")

# Place transport belt parallel to the drills
belt_start = Position(x=drills[0].position.x - 1, y=drills[0].position.y + 2)
belt_end = Position(x=drills[-1].position.x + 4, y=drills[0].position.y + 2)
belt_entities = connect_entities(belt_start, belt_end, Prototype.TransportBelt)
assert len(belt_entities) > 0, "Failed to place transport belt"

print(f"Placed {len(belt_entities)} transport belt segments")

# Place inserters for each drill
for drill in drills:
    # Output inserter
    output_inserter = place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=drill.position.x + 1, y=drill.position.y + 1))
    assert output_inserter is not None, f"Failed to place output inserter for drill at {drill.position}"
    
    # Input inserter
    input_inserter = place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=drill.position.x - 1, y=drill.position.y + 1))
    assert input_inserter is not None, f"Failed to place input inserter for drill at {drill.position}"

print("Placed all inserters")

# Complete the belt loop
loop_end = connect_entities(belt_entities[-1].position, belt_entities[0].position, Prototype.TransportBelt)
assert len(loop_end) > 0, "Failed to complete the belt loop"

print("Completed the belt loop")

# Verify the setup
inspection = inspect_entities(coal_patch.bounding_box.center, radius=15)
assert len([e for e in inspection.entities if e.name == Prototype.BurnerMiningDrill.value[0]]) == 5, "Not all burner mining drills were placed"
assert len([e for e in inspection.entities if e.name == Prototype.BurnerInserter.value[0]]) == 10, "Not all inserters were placed"
assert len([e for e in inspection.entities if e.name == Prototype.TransportBelt.value[0]]) >= 15, "Not enough transport belt segments were placed"

print("All components verified")

# Kickstart the system by placing coal on the belt
coal_placed = insert_item(Prototype.Coal, belt_entities[0], quantity=5)
assert coal_placed is not None, "Failed to place coal on the belt"

print("System kickstarted with coal")
print("Self-fueling belt of 5 burner mining drills successfully set up")
