# Find resources and water
iron_ore_position = nearest(Resource.IronOre)
copper_ore_position = nearest(Resource.CopperOre)
coal_position = nearest(Resource.Coal)
water_position = nearest(Resource.Water)

# Move closer to water
move_to(water_position)

# Harvest resources
resources_to_harvest = [
    (Resource.IronOre, iron_ore_position),
    (Resource.CopperOre, copper_ore_position),
    (Resource.Coal, coal_position)
]

for resource, position in resources_to_harvest:
    harvested = harvest_resource(position, 30)
    assert harvested >= 20, f"Failed to harvest enough {resource.name}. Only harvested {harvested}"

# Craft items
crafting_list = [
    (Prototype.IronPlate, 30),
    (Prototype.CopperPlate, 30),
    (Prototype.IronGearWheel, 10),
    (Prototype.CopperCable, 30),
    (Prototype.ElectronicCircuit, 10),
    (Prototype.OffshorePump, 1),
    (Prototype.Boiler, 1),
    (Prototype.SteamEngine, 1),
    (Prototype.Radar, 1)
]

for item, quantity in crafting_list:
    crafted = craft_item(item, quantity)
    assert crafted == quantity, f"Failed to craft {item.value[0]}. Only crafted {crafted}"

# Set up power generation
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, water_position)
assert offshore_pump, "Failed to place offshore pump"

boiler = place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.RIGHT, spacing=1)
assert boiler, "Failed to place boiler"

steam_engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.RIGHT, spacing=1)
assert steam_engine, "Failed to place steam engine"

# Connect water pump to boiler to steam engine
assert connect_entities(offshore_pump, boiler, Prototype.Pipe), "Failed to connect offshore pump to boiler"
assert connect_entities(boiler, steam_engine, Prototype.Pipe), "Failed to connect boiler to steam engine"

# Place radar next to steam engine
radar = place_entity_next_to(Prototype.Radar, steam_engine.position, Direction.UP, spacing=1)
assert radar, "Failed to place radar"

# Connect steam engine to radar using copper cable
assert connect_entities(steam_engine, radar, Prototype.CopperCable), "Failed to connect steam engine to radar"

# Insert coal into boiler
assert insert_item(Prototype.Coal, boiler, 5), "Failed to insert coal into boiler"

# Verify radar operation
sleep(5)  # Wait for power to stabilize and radar to start

inspection_results = inspect_entities(radar.position, radius=5)
radar_entity = inspection_results.get_entity(Prototype.Radar)
assert radar_entity, "Radar not found in inspection results"
assert radar_entity.status == EntityStatus.WORKING, f"Radar is not working. Status: {radar_entity.status}"

print("Radar successfully built and powered. It should now be revealing the surrounding area.")
