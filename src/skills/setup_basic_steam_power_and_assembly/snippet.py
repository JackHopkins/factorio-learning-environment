
# Place offshore pump near water
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, Position(x=0, y=0))
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place boiler next to offshore pump
boiler = place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.RIGHT)
assert boiler, "Failed to place boiler"
print(f"Boiler placed at {boiler.position}")

# Connect offshore pump to boiler with pipes
pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes, "Failed to connect offshore pump to boiler"
print(f"Pipes placed between offshore pump and boiler")

# Place steam engine next to boiler
steam_engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.RIGHT)
assert steam_engine, "Failed to place steam engine"
print(f"Steam engine placed at {steam_engine.position}")

# Connect boiler to steam engine with pipes
pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
assert pipes, "Failed to connect boiler to steam engine"
print(f"Pipes placed between boiler and steam engine")

# Place power pole next to steam engine
power_pole = place_entity_next_to(Prototype.SmallElectricPole, steam_engine.position, Direction.UP)
assert power_pole, "Failed to place power pole"
print(f"Power pole placed at {power_pole.position}")

# Place assembling machine within reach of power network
assembling_machine = place_entity_next_to(Prototype.AssemblingMachine1, power_pole.position, Direction.UP, spacing=2)
assert assembling_machine, "Failed to place assembling machine"
print(f"Assembling machine placed at {assembling_machine.position}")

# Connect assembling machine to power network
connection_pole = place_entity_next_to(Prototype.SmallElectricPole, assembling_machine.position, Direction.DOWN)
assert connection_pole, "Failed to place connection power pole"
print(f"Connection power pole placed at {connection_pole.position}")

# Verify setup
inspection = inspect_entities(offshore_pump.position, radius=20)
entity_names = [entity.name for entity in inspection.entities]

required_entities = [
    "offshore-pump",
    "boiler",
    "steam-engine",
    "assembling-machine-1",
    "small-electric-pole",
    "pipe"
]

for entity in required_entities:
    assert entity in entity_names, f"Missing required entity: {entity}"

print("Steam power setup successfully created and connected to assembling machine")
