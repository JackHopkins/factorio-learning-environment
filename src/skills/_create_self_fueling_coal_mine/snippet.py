
# Find the nearest coal patch
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
assert coal_patch, "No coal patch found nearby"
print(f"Coal patch found at: {coal_patch.bounding_box.center}")

# Place electric mining drill
miner = place_entity(Prototype.ElectricMiningDrill, position=coal_patch.bounding_box.center)
assert miner, "Failed to place electric mining drill"
print(f"Miner placed at: {miner.position}")

# Place boiler near water
water_patch = get_resource_patch(Resource.Water, nearest(Resource.Water))
assert water_patch, "No water source found nearby"
boiler = place_entity(Prototype.Boiler, position=water_patch.bounding_box.center + Position(x=2, y=0))
assert boiler, "Failed to place boiler"
print(f"Boiler placed at: {boiler.position}")

# Place steam engine
steam_engine = place_entity_next_to(Prototype.SteamEngine, reference_position=boiler.position, direction=Direction.RIGHT)
assert steam_engine, "Failed to place steam engine"
print(f"Steam engine placed at: {steam_engine.position}")

# Connect boiler to steam engine with pipe
pipes = connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
assert pipes, "Failed to connect boiler to steam engine with pipes"

# Place transport belt from miner to boiler
belts = connect_entities(miner, boiler, connection_type=Prototype.TransportBelt)
assert belts, "Failed to create transport belt line from miner to boiler"

# Place inserter to feed coal into boiler
inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=boiler.position, direction=Direction.UP)
assert inserter, "Failed to place inserter"
print(f"Inserter placed at: {inserter.position}")

# Place electric pole to power the system
pole = place_entity(Prototype.SmallElectricPole, position=miner.position + Position(x=2, y=2))
assert pole, "Failed to place electric pole"
print(f"Electric pole placed at: {pole.position}")

# Wait for the system to start producing
sleep(10)

# Verify that the system is self-fueling
inspection = inspect_entities(position=miner.position, radius=20)
miner_info = inspection.get_entity(Prototype.ElectricMiningDrill)
assert miner_info and miner_info.status == EntityStatus.WORKING, "Miner is not working"

boiler_info = inspection.get_entity(Prototype.Boiler)
assert boiler_info and boiler_info.status == EntityStatus.WORKING, "Boiler is not working"

steam_engine_info = inspection.get_entity(Prototype.SteamEngine)
assert steam_engine_info and steam_engine_info.status == EntityStatus.WORKING, "Steam engine is not working"

# Check if there's coal on the belt
belt_with_coal = next((e for e in inspection.entities if e.name == "transport-belt" and e.contents.get("coal", 0) > 0), None)
assert belt_with_coal, "No coal found on transport belts"

print("Self-fueling coal mining system successfully created and operational!")
