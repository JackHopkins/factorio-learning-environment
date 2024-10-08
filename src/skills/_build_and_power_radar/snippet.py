# Gather necessary resources
harvest_resource(nearest(Resource.IronOre), 20)
harvest_resource(nearest(Resource.CopperOre), 10)
harvest_resource(nearest(Resource.Coal), 10)

# Craft basic materials
craft_item(Prototype.IronPlate, 20)
craft_item(Prototype.CopperPlate, 10)
craft_item(Prototype.IronGearWheel, 10)
craft_item(Prototype.CopperCable, 10)
craft_item(Prototype.ElectronicCircuit, 5)

# Craft main components
craft_item(Prototype.Radar)
craft_item(Prototype.SmallElectricPole, 2)
craft_item(Prototype.SteamEngine)

# Place a small electric pole
pole = place_entity(Prototype.SmallElectricPole, Direction.UP, Position(x=0, y=0))
assert pole, "Failed to place small electric pole"

# Place a radar with more space
radar_pos = place_entity_next_to(Prototype.Radar, pole.position, Direction.RIGHT, spacing=3)
assert radar_pos, "Failed to place radar"

# Place the steam engine
engine_pos = place_entity_next_to(Prototype.SteamEngine, pole.position, Direction.DOWN, spacing=3)
assert engine_pos, "Failed to place steam engine"

# Connect the radar to the pole
radar_connection = connect_entities(pole, radar_pos, Prototype.SmallElectricPole)
assert radar_connection, "Failed to connect radar to pole"

# Connect the steam engine to the pole
engine_connection = connect_entities(engine_pos, pole, Prototype.SmallElectricPole)
assert engine_connection, "Failed to connect steam engine to pole"

# Wait for a moment to allow the radar to start working
sleep(5)

# Verify that the radar is working
inspection = inspect_entities(pole.position, radius=10)
radar_entity = next((e for e in inspection.entities if e.name == "radar"), None)
assert radar_entity and radar_entity.status == EntityStatus.WORKING, "Radar is not working"

print("Radar has been built and powered successfully")
