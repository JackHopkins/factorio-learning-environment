# Implement a snippet that builds a basic steam power generation setup by placing and configuring an offshore pump, boiler, and steam engine in sequence, with transport belts and inserters to automatically feed coal from a mining drill to the boiler, creating a self-sustaining power production system.

# Find nearest coal patch and water source
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
water_location = nearest(Resource.Water)
assert coal_patch and water_location, "Required resources not found"

# Set up coal mining
drill_position = coal_patch.bounding_box.center
move_to(drill_position)
drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, drill_position)
insert_item(Prototype.Coal, drill, 5)
assert drill, "Failed to place mining drill"

# Place offshore pump at water
move_to(water_location)
pump = place_entity(Prototype.OffshorePump, Direction.UP, water_location)
assert pump, "Failed to place offshore pump"

# Place boiler next to pump
boiler_pos = Position(x=pump.position.x, y=pump.position.y-3)
boiler = place_entity(Prototype.Boiler, Direction.LEFT, boiler_pos)
connect_entities(pump, boiler, Prototype.Pipe)
assert boiler, "Failed to place boiler"

# Place steam engine next to boiler
move_to(boiler_pos)
engine = place_entity_next_to(Prototype.SteamEngine, boiler_pos, Direction.LEFT, spacing=2)
connect_entities(boiler, engine, Prototype.Pipe)
assert engine, "Failed to place steam engine"

# Connect coal supply to boiler
inserter_pos = Position(x=boiler.position.x, y=boiler.position.y - 1)
inserter = place_entity_next_to(Prototype.BurnerInserter, inserter_pos, Direction.RIGHT, spacing=0)
inserter = rotate_entity(inserter, Direction.LEFT)
assert inserter, "Failed to place inserter"

# Place belt from drill to boiler
belts = connect_entities(drill, inserter, Prototype.TransportBelt)
for belt_a, belt_b in zip(belts, belts[1:]):
    connect_entities(belt_a, belt_b, Prototype.TransportBelt)
assert belts, "Failed to place transport belts"

# Verify complete setup
entities = inspect_entities(boiler.position, radius=5)
assert entities.get_entity(Prototype.OffshorePump), "Pump not found"
assert entities.get_entity(Prototype.Boiler), "Boiler not found"
assert entities.get_entity(Prototype.SteamEngine), "Steam engine not found"
assert entities.get_entity(Prototype.BurnerInserter), "Inserter not found"
assert any(e.name == "transport-belt" for e in entities.entities), "Belts not found"

sleep(15)

engine_status = get_entities({Prototype.SteamEngine})[0].status
assert engine_status == EntityStatus.WORKING, "Steam engine not working"
print("Steam power generation setup complete")