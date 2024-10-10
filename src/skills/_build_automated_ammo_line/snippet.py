# Find the nearest water source and move closer to it
water_position = nearest(Resource.Water)
move_to(water_position)

# Craft necessary items
craft_item(Prototype.OffshorePump, 1)
craft_item(Prototype.Boiler, 1)
craft_item(Prototype.SteamEngine, 1)
craft_item(Prototype.ElectricMiningDrill, 2)
craft_item(Prototype.TransportBelt, 50)
craft_item(Prototype.BurnerInserter, 10)
craft_item(Prototype.StoneFurnace, 2)
craft_item(Prototype.AssemblingMachine1, 1)
craft_item(Prototype.IronChest, 1)
craft_item(Prototype.Pipe, 10)

# Set up power generation
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, water_position)
assert offshore_pump, "Failed to place offshore pump"

boiler = place_entity(Prototype.Boiler, Direction.UP, offshore_pump.position + Position(x=1, y=0))
assert boiler, "Failed to place boiler"

steam_engine = place_entity(Prototype.SteamEngine, Direction.UP, boiler.position + Position(x=3, y=0))
assert steam_engine, "Failed to place steam engine"

# Connect water pump to boiler
pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes, "Failed to connect offshore pump to boiler"

# Connect boiler to steam engine
pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
assert pipes, "Failed to connect boiler to steam engine"

# Set up iron ore mining
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
iron_miner = place_entity(Prototype.ElectricMiningDrill, Direction.DOWN, iron_ore_position)
assert iron_miner, "Failed to place iron miner"

iron_belt = place_entity(Prototype.TransportBelt, Direction.RIGHT, iron_miner.position + Position(x=0, y=2))
assert iron_belt, "Failed to place iron transport belt"

# Set up iron plate production
iron_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, iron_belt.position + Position(x=2, y=-1))
assert iron_furnace, "Failed to place iron furnace"

iron_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, iron_furnace.position + Position(x=-1, y=0))
assert iron_inserter, "Failed to place iron inserter"

iron_output_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, iron_furnace.position + Position(x=1, y=0))
assert iron_output_inserter, "Failed to place iron output inserter"

iron_output_belt = place_entity(Prototype.TransportBelt, Direction.DOWN, iron_furnace.position + Position(x=2, y=0))
assert iron_output_belt, "Failed to place iron output belt"

# Set up copper ore mining and smelting
copper_ore_position = nearest(Resource.CopperOre)
move_to(copper_ore_position)
copper_miner = place_entity(Prototype.ElectricMiningDrill, Direction.DOWN, copper_ore_position)
assert copper_miner, "Failed to place copper miner"

copper_belt = place_entity(Prototype.TransportBelt, Direction.RIGHT, copper_miner.position + Position(x=0, y=2))
assert copper_belt, "Failed to place copper transport belt"

copper_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, copper_belt.position + Position(x=2, y=-1))
assert copper_furnace, "Failed to place copper furnace"

copper_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, copper_furnace.position + Position(x=-1, y=0))
assert copper_inserter, "Failed to place copper inserter"

copper_output_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, copper_furnace.position + Position(x=1, y=0))
assert copper_output_inserter, "Failed to place copper output inserter"

copper_output_belt = place_entity(Prototype.TransportBelt, Direction.DOWN, copper_furnace.position + Position(x=2, y=0))
assert copper_output_belt, "Failed to place copper output belt"

# Set up firearm magazine production
assembler_position = iron_output_belt.position + Position(x=4, y=0)
move_to(assembler_position)
assembler = place_entity(Prototype.AssemblingMachine1, Direction.UP, assembler_position)
assert assembler, "Failed to place assembling machine"

recipe_set = set_entity_recipe(assembler, Prototype.FirearmMagazine)
assert recipe_set, "Failed to set recipe for firearm magazine"

iron_input_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, assembler.position + Position(x=-1, y=1))
assert iron_input_inserter, "Failed to place iron input inserter"

copper_input_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, assembler.position + Position(x=-1, y=-1))
assert copper_input_inserter, "Failed to place copper input inserter"

output_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, assembler.position + Position(x=1, y=0))
assert output_inserter, "Failed to place output inserter"

output_chest = place_entity(Prototype.IronChest, Direction.UP, assembler.position + Position(x=2, y=0))
assert output_chest, "Failed to place output chest"

# Connect iron and copper belts to assembler inputs
iron_assembler_belt = connect_entities(iron_output_belt, iron_input_inserter.position, Prototype.TransportBelt)
assert iron_assembler_belt, "Failed to connect iron belt to assembler"

copper_assembler_belt = connect_entities(copper_output_belt, copper_input_inserter.position, Prototype.TransportBelt)
assert copper_assembler_belt, "Failed to connect copper belt to assembler"

# Verify production line setup
inspection = inspect_entities(assembler.position, radius=20)
assert any(e.name == "assembling-machine-1" for e in inspection.entities), "Assembling machine not found in production line"
assert any(e.name == "iron-chest" for e in inspection.entities), "Output chest not found in production line"
assert any(e.name == "transport-belt" for e in inspection.entities), "Transport belts not found in production line"
assert any(e.name == "burner-inserter" for e in inspection.entities), "Inserters not found in production line"
assert any(e.name == "stone-furnace" for e in inspection.entities), "Furnaces not found in production line"
assert any(e.name == "electric-mining-drill" for e in inspection.entities), "Mining drills not found in production line"
assert any(e.name == "steam-engine" for e in inspection.entities), "Steam engine not found in production line"
assert any(e.name == "boiler" for e in inspection.entities), "Boiler not found in production line"
assert any(e.name == "offshore-pump" for e in inspection.entities), "Offshore pump not found in production line"

print("Automated firearm magazine production line successfully built!")
