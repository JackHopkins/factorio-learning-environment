# First, gather necessary raw materials
resources_needed = {
    Resource.IronOre: 40,
    Resource.CopperOre: 20,
    Resource.Coal: 20,
    Resource.Stone: 10
}

for resource, amount in resources_needed.items():
    resource_position = nearest(resource)
    if resource_position:
        move_to(resource_position)
        harvested = harvest_resource(resource_position, amount)
        print(f"Harvested {harvested} {resource.name}")

# Craft necessary intermediate items
craft_item(Prototype.IronPlate, 20)
craft_item(Prototype.CopperPlate, 10)
craft_item(Prototype.IronGearWheel, 10)
craft_item(Prototype.CopperCable, 10)
craft_item(Prototype.ElectronicCircuit, 5)

# Now craft the main items
craft_item(Prototype.OffshorePump, 1)
craft_item(Prototype.Boiler, 1)
craft_item(Prototype.SteamEngine, 3)
craft_item(Prototype.ElectricMiningDrill, 2)
craft_item(Prototype.SmallElectricPole, 10)

# Move closer to water
water_position = nearest(Resource.Water)
move_to(water_position)

# Place offshore pump near water
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, water_position)
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place boiler and connect to offshore pump
boiler = place_entity(Prototype.Boiler, Direction.RIGHT, offshore_pump.position + Position(x=1, y=0))
assert boiler, "Failed to place boiler"
print(f"Boiler placed at {boiler.position}")
connect_entities(offshore_pump, boiler, Prototype.Pipe)

# Place 3 steam engines and connect them
steam_engines = []
for i in range(3):
    engine = place_entity(Prototype.SteamEngine, Direction.RIGHT, boiler.position + Position(x=i+1, y=0))
    assert engine, f"Failed to place steam engine {i+1}"
    steam_engines.append(engine)
    if i == 0:
        connect_entities(boiler, engine, Prototype.Pipe)
    else:
        connect_entities(steam_engines[i-1], engine, Prototype.Pipe)
    print(f"Steam engine {i+1} placed at {engine.position}")

# Connect steam engines with electric poles
prev_pole = None
for engine in steam_engines:
    pole = place_entity(Prototype.SmallElectricPole, Direction.UP, engine.position + Position(x=0, y=-1))
    assert pole, f"Failed to place electric pole near steam engine at {engine.position}"
    if prev_pole:
        connect_entities(prev_pole, pole, Prototype.SmallElectricPole)
    prev_pole = pole
    print(f"Electric pole placed at {pole.position}")

# Find nearest ore patch for mining drills
ore_position = nearest(Resource.IronOre)
if not ore_position:
    ore_position = nearest(Resource.CopperOre)
assert ore_position, "No suitable ore patch found"

# Move closer to ore patch
move_to(ore_position)

# Place 2 electric mining drills
drills = []
for i in range(2):
    drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, ore_position + Position(x=i*3, y=0))
    assert drill, f"Failed to place electric mining drill {i+1}"
    drills.append(drill)
    print(f"Electric mining drill {i+1} placed at {drill.position}")

# Connect drills to the electric network
for drill in drills:
    pole = place_entity(Prototype.SmallElectricPole, Direction.UP, drill.position + Position(x=1, y=1))
    assert pole, f"Failed to place electric pole near drill at {drill.position}"
    connect_entities(prev_pole, pole, Prototype.SmallElectricPole)
    prev_pole = pole
    print(f"Electric pole placed at {pole.position}")

# Insert coal into boiler
insert_item(Prototype.Coal, boiler, 5)

# Verify the setup
inspection = inspect_entities(boiler.position, 50)
assert len([e for e in inspection.entities if e.name == "offshore-pump"]) == 1, "Offshore pump not found"
assert len([e for e in inspection.entities if e.name == "boiler"]) == 1, "Boiler not found"
assert len([e for e in inspection.entities if e.name == "steam-engine"]) == 3, "Not all steam engines found"
assert len([e for e in inspection.entities if e.name == "electric-mining-drill"]) == 2, "Not all electric mining drills found"
assert len([e for e in inspection.entities if e.name == "small-electric-pole"]) >= 5, "Not enough electric poles found"

# Check if drills are powered
for i, drill in enumerate(drills):
    drill_status = get_entity(Prototype.ElectricMiningDrill, drill.position).status
    assert drill_status == EntityStatus.WORKING, f"Electric mining drill {i+1} is not working. Status: {drill_status}"
    print(f"Electric mining drill {i+1} is working")

print("Small electric network successfully created with 3 steam engines connected to 2 electric mining drills")
