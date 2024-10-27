# Find iron ore patch and move there
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)

# Place burner mining drill on iron patch
drill = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, iron_pos)
assert drill is not None, "Failed to place burner mining drill"
insert_item(Prototype.Coal, drill, 5)

# Place initial belt at drill output
belt = place_entity(Prototype.TransportBelt, Direction.RIGHT, drill.drop_position)
assert belt is not None, "Failed to place transport belt"

# Place furnace with spacing for inserter
furnace = place_entity_next_to(Prototype.StoneFurnace, belt.position, Direction.UP, spacing=1)
assert furnace is not None, "Failed to place stone furnace"
insert_item(Prototype.Coal, furnace, 5)

# Place input inserter between belt and furnace
insert1 = place_entity_next_to(Prototype.BurnerInserter, furnace.position, Direction.DOWN, spacing=0)
insert1 = rotate_entity(insert1, Direction.UP)
assert insert1 is not None, "Failed to place input inserter"
assert insert1.direction == Direction.UP
insert_item(Prototype.Coal, insert1, 5)

# Place chest for output
chest = place_entity_next_to(Prototype.IronChest, furnace.position, Direction.RIGHT, spacing=1)
assert chest is not None, "Failed to place iron chest"

# Place output inserter between furnace and chest
insert2 = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT, spacing=0)
insert2 = rotate_entity(insert2, Direction.RIGHT)
assert insert2 is not None, "Failed to place output inserter"
assert insert2.direction == Direction.RIGHT
insert_item(Prototype.Coal, insert2, 5)

# Verify setup
inspection = inspect_entities(drill.position, radius=10)
assert len([e for e in inspection.entities if e.name == "burner-mining-drill"]) == 1
assert len([e for e in inspection.entities if e.name == "stone-furnace"]) == 1
assert len([e for e in inspection.entities if e.name == "burner-inserter"]) == 2
assert len([e for e in inspection.entities if e.name == "iron-chest"]) == 1
assert len([e for e in inspection.entities if e.name == "transport-belt"]) >= 1

# Verify inserter connections
input_inserter = get_entity(Prototype.BurnerInserter, insert1.position)
assert input_inserter.pickup_position is not None
assert get_entity(Prototype.TransportBelt, input_inserter.pickup_position) is not None
assert get_entity(Prototype.StoneFurnace, input_inserter.drop_position) is not None

output_inserter = get_entity(Prototype.BurnerInserter, insert2.position)
assert output_inserter.pickup_position is not None
assert get_entity(Prototype.StoneFurnace, output_inserter.pickup_position) is not None
assert get_entity(Prototype.IronChest, output_inserter.drop_position) is not None