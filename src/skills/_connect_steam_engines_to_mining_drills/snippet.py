# Start by moving to the nearest water source
water_position = nearest(Resource.Water)
move_to(water_position)

# Craft necessary items if not in inventory
items_to_craft = [
    (Prototype.OffshorePump, 1),
    (Prototype.Boiler, 1),
    (Prototype.SteamEngine, 3),
    (Prototype.SmallElectricPole, 10),
    (Prototype.ElectricMiningDrill, 2)
]

# First, craft iron plates if needed
if inspect_inventory().get(Prototype.IronPlate.value[0], 0) < 50:
    iron_ore_position = nearest(Resource.IronOre)
    move_to(iron_ore_position)
    harvest_resource(iron_ore_position, 50)
    craft_item(Prototype.IronPlate, 50)

# Now craft the other items
for item, quantity in items_to_craft:
    current_quantity = inspect_inventory().get(item.value[0], 0)
    if current_quantity < quantity:
        craft_item(item, quantity - current_quantity)

# Move back to water
move_to(water_position)

# Place offshore pump
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, water_position)
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place boiler next to the offshore pump
boiler = place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.RIGHT)
assert boiler, "Failed to place boiler"
print(f"Boiler placed at {boiler.position}")

# Connect offshore pump to boiler
pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes, "Failed to connect offshore pump to boiler"

# Place 3 steam engines
steam_engines = []
prev_entity = boiler
for i in range(3):
    engine = place_entity_next_to(Prototype.SteamEngine, prev_entity.position, Direction.RIGHT, spacing=1)
    assert engine, f"Failed to place steam engine {i+1}"
    steam_engines.append(engine)
    print(f"Steam engine {i+1} placed at {engine.position}")
    pipes = connect_entities(prev_entity, engine, Prototype.Pipe)
    assert pipes, f"Failed to connect {prev_entity.name} to steam engine at {engine.position}"
    prev_entity = engine

# Place electric poles to connect steam engines
prev_pole = None
for engine in steam_engines:
    pole = place_entity_next_to(Prototype.SmallElectricPole, engine.position, Direction.UP)
    assert pole, f"Failed to place electric pole for steam engine at {engine.position}"
    if prev_pole:
        connect_entities(prev_pole, pole, Prototype.SmallElectricPole)
    prev_pole = pole

# Find iron ore and move there
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Place 2 electric mining drills
mining_drills = []
for i in range(2):
    drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, iron_ore_position)
    assert drill, f"Failed to place electric mining drill {i+1}"
    mining_drills.append(drill)
    print(f"Electric mining drill {i+1} placed at {drill.position}")

    # Place electric pole near the drill
    pole = place_entity_next_to(Prototype.SmallElectricPole, drill.position, Direction.UP)
    assert pole, f"Failed to place electric pole for mining drill at {drill.position}"
    connect_entities(prev_pole, pole, Prototype.SmallElectricPole)
    prev_pole = pole

    # Find next iron ore patch
    iron_ore_position = nearest(Resource.IronOre)
    move_to(iron_ore_position)

# Verify the setup
inspection = inspect_entities(radius=30)
assert len([e for e in inspection.entities if e.name == Prototype.SteamEngine.value[0]]) == 3, "Expected 3 steam engines"
assert len([e for e in inspection.entities if e.name == Prototype.ElectricMiningDrill.value[0]]) == 2, "Expected 2 electric mining drills"
assert len([e for e in inspection.entities if e.name == Prototype.SmallElectricPole.value[0]]) >= 5, "Expected at least 5 small electric poles