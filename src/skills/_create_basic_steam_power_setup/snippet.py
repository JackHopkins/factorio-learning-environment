
# Find nearest water source
water_position = nearest(Resource.Water)
assert water_position, "No water source found nearby"

# Place offshore pump
offshore_pump = place_entity(Prototype.OffshorePump, Direction.RIGHT, water_position)
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place boiler
boiler_position = Position(x=offshore_pump.position.x + 2, y=offshore_pump.position.y)
boiler = place_entity(Prototype.Boiler, Direction.RIGHT, boiler_position)
assert boiler, "Failed to place boiler"
print(f"Boiler placed at {boiler.position}")

# Connect offshore pump to boiler with pipes
pipes_to_boiler = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes_to_boiler, "Failed to connect offshore pump to boiler with pipes"
print(f"Pipes connected from offshore pump to boiler: {len(pipes_to_boiler)} pipes placed")

# Place steam engine
steam_engine_position = Position(x=boiler.position.x + 2, y=boiler.position.y)
steam_engine = place_entity(Prototype.SteamEngine, Direction.RIGHT, steam_engine_position)
assert steam_engine, "Failed to place steam engine"
print(f"Steam engine placed at {steam_engine.position}")

# Connect boiler to steam engine with pipes
pipes_to_engine = connect_entities(boiler, steam_engine, Prototype.Pipe)
assert pipes_to_engine, "Failed to connect boiler to steam engine with pipes"
print(f"Pipes connected from boiler to steam engine: {len(pipes_to_engine)} pipes placed")

# Verify connections
inspection_results = inspect_entities(offshore_pump.position, radius=10)
entities = inspection_results.entities

assert any(e.name == "offshore-pump" for e in entities), "Offshore pump not found in inspection results"
assert any(e.name == "boiler" for e in entities), "Boiler not found in inspection results"
assert any(e.name == "steam-engine" for e in entities), "Steam engine not found in inspection results"
assert len([e for e in entities if e.name == "pipe"]) >= 2, "Not enough pipes found in inspection results"

print("Offshore pump, boiler, and steam engine successfully placed and connected with pipes")
