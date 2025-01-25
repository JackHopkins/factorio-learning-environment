# Create an automated coal transportation system from a mining drill to 3 stone furnaces

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
assert coal_position, "No coal found nearby"

# Move to the coal position
move_to(coal_position)

# Get the coal patch details
coal_patch = get_resource_patch(Resource.Coal, coal_position, radius=10)
assert coal_patch, "No coal patch found within radius"

# Place the mining drill
miner = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, coal_patch.bounding_box.center())
assert miner, "Failed to place burner mining drill"

# Place stone furnaces
furnaces = []
for i in range(3):
    furnace_pos = Position(x=miner.position.x + 2*i, y=miner.position.y + 3)
    furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)
    assert furnace, f"Failed to place stone furnace at {furnace_pos}"
    furnaces.append(furnace)

# Connect mining drill to furnaces with transport belts
belt_start = Position(x=miner.position.x, y=miner.position.y + 1)
belt_end = Position(x=furnaces[-1].position.x + 1, y=furnaces[-1].position.y)
belts = connect_entities(belt_start, belt_end, Prototype.TransportBelt)
assert belts, "Failed to place transport belts"

# Insert coal into the mining drill
insert_item(Prototype.Coal, miner, quantity=5)

# Verify the setup
inspection = inspect_entities(miner.position, radius=10)
assert any(e.name == "burner-mining-drill" for e in inspection.entities), "Mining drill not found"
assert len([e for e in inspection.entities if e.name == "stone-furnace"]) == 3, "Not all stone furnaces found"
assert any(e.name == "transport-belt" for e in inspection.entities), "Transport belts not found"

print("Automated coal transportation system created successfully!")
