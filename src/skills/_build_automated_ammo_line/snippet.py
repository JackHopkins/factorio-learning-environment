# Start by finding the nearest water source
water_position = nearest(Resource.Water)

# Move closer to the water source, ensuring we're within placement range
move_to(Position(x=water_position.x + 3, y=water_position.y))

# Craft necessary components
craft_item(Prototype.OffshorePump, 1)
craft_item(Prototype.Boiler, 1)
craft_item(Prototype.SteamEngine, 1)
craft_item(Prototype.SmallElectricPole, 1)
craft_item(Prototype.AssemblingMachine1, 2)
craft_item(Prototype.BurnerInserter, 2)
craft_item(Prototype.WoodenChest, 1)
craft_item(Prototype.TransportBelt, 10)

# Place the steam power unit components
offshore_pump = place_entity(Prototype.OffshorePump, Direction.RIGHT, Position(x=water_position.x, y=water_position.y))
assert offshore_pump, "Failed to place offshore pump"

boiler = place_entity(Prototype.Boiler, Direction.RIGHT, Position(x=offshore_pump.position.x + 1, y=offshore_pump.position.y))
assert boiler, "Failed to place boiler"

steam_engine = place_entity(Prototype.SteamEngine, Direction.RIGHT, Position(x=boiler.position.x + 1, y=boiler.position.y))
assert steam_engine, "Failed to place steam engine"

# Connect the offshore pump to the boiler, and the boiler to the steam engine
connect_entities(offshore_pump, boiler, Prototype.Pipe)
connect_entities(boiler, steam_engine, Prototype.Pipe)

# Place a small electric pole to distribute power
electric_pole = place_entity(Prototype.SmallElectricPole, Direction.UP, Position(x=steam_engine.position.x, y=steam_engine.position.y - 2))
assert electric_pole, "Failed to place small electric pole"

# Place assembling machines for iron gear wheels and firearm magazines
gear_assembler = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=electric_pole.position.x + 2, y=electric_pole.position.y))
assert gear_assembler, "Failed to place gear assembling machine"

magazine_assembler = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=gear_assembler.position.x + 3, y=gear_assembler.position.y))
assert magazine_assembler, "Failed to place magazine assembling machine"

# Set recipes for assembling machines
set_entity_recipe(gear_assembler, Prototype.IronGearWheel)
set_entity_recipe(magazine_assembler, Prototype.FirearmMagazine)

# Place inserters to move items between assemblers
inserter1 = place_entity(Prototype.BurnerInserter, Direction.RIGHT, Position(x=gear_assembler.position.x + 1.5, y=gear_assembler.position.y))
assert inserter1, "Failed to place inserter between assemblers"

# Place a chest for output
output_chest = place_entity(Prototype.WoodenChest, Direction.UP, Position(x=magazine_assembler.position.x + 2, y=magazine_assembler.position.y))
assert output_chest, "Failed to place output chest"

inserter2 = place_entity(Prototype.BurnerInserter, Direction.LEFT, Position(x=output_chest.position.x - 0.5, y=output_chest.position.y))
assert inserter2, "Failed to place inserter for output"

# Place transport belts to feed iron plates to both assemblers
start_x = min(gear_assembler.position.x, magazine_assembler.position.x) - 1
for i in range(7):
    belt = place_entity(Prototype.TransportBelt, Direction.UP, Position(x=start_x, y=gear_assembler.position.y - i))
    assert belt, f"Failed to place transport belt at y={gear_assembler.position.y - i}"

# Verify that all components are in place
inspection = inspect_entities(Position(x=steam_engine.position.x, y=steam_engine.position.y), radius=15)
assert len(inspection.entities) >= 10, "Not all components were placed successfully"

print("Automated firearm magazine production line has been set up successfully.")
