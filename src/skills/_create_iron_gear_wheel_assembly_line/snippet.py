# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
assert iron_ore_position, "No iron ore patch found nearby"

# Move to the iron ore patch
move_to(iron_ore_position)

# Place an electric mining drill on the iron ore patch
mining_drill = place_entity(Prototype.ElectricMiningDrill, position=iron_ore_position)
assert mining_drill, "Failed to place electric mining drill"

# Place a stone furnace near the mining drill
furnace = place_entity_next_to(Prototype.StoneFurnace, mining_drill.position, Direction.RIGHT, spacing=1)
assert furnace, "Failed to place stone furnace"

# Place inserters to move ore from drill to furnace and plates from furnace
drill_to_furnace = place_entity_next_to(Prototype.BurnerInserter, mining_drill.position, Direction.RIGHT)
assert drill_to_furnace, "Failed to place inserter between drill and furnace"

furnace_output = place_entity_next_to(Prototype.BurnerInserter, furnace.position, Direction.RIGHT)
assert furnace_output, "Failed to place inserter for furnace output"

# Place assembling machine for iron gear wheel production
assembling_machine = place_entity_next_to(Prototype.AssemblingMachine1, furnace_output.position, Direction.RIGHT, spacing=1)
assert assembling_machine, "Failed to place assembling machine"

# Set recipe for assembling machine
recipe_set = set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
assert recipe_set, "Failed to set iron gear wheel recipe for assembling machine"

# Place inserter to feed iron plates into assembling machine
plate_to_assembler = place_entity_next_to(Prototype.BurnerInserter, furnace.position, Direction.RIGHT, spacing=2)
assert plate_to_assembler, "Failed to place inserter between furnace and assembling machine"

# Place chest for output and inserter to move gear wheels to chest
output_chest = place_entity_next_to(Prototype.WoodenChest, assembling_machine.position, Direction.RIGHT, spacing=1)
assert output_chest, "Failed to place output chest"

assembler_to_chest = place_entity_next_to(Prototype.BurnerInserter, assembling_machine.position, Direction.RIGHT)
assert assembler_to_chest, "Failed to place inserter between assembling machine and chest"

# Connect power
electric_pole = place_entity_next_to(Prototype.SmallElectricPole, mining_drill.position, Direction.UP)
assert electric_pole, "Failed to place electric pole"

# Verify the setup
entities = inspect_entities(radius=20)
assert entities.get_entity(Prototype.ElectricMiningDrill), "Electric mining drill not found in inspection"
assert entities.get_entity(Prototype.StoneFurnace), "Stone furnace not found in inspection"
assert len(entities.get_entities(Prototype.BurnerInserter)) >= 4, "Not enough inserters found in inspection"
assert entities.get_entity(Prototype.AssemblingMachine1), "Assembling machine not found in inspection"
assert entities.get_entity(Prototype.WoodenChest), "Output chest not found in inspection"

print("Iron gear wheel production line set up successfully!")

# Ensure burner inserters and stone furnace have fuel
for entity in entities.get_entities(Prototype.BurnerInserter) + [furnace]:
    insert_item(Prototype.Coal, entity, quantity=5)

# Wait for production to start
sleep(180)

# Check if iron gear wheels are being produced
chest_inventory = inspect_inventory(output_chest)
iron_gear_wheels = chest_inventory.get(Prototype.IronGearWheel, 0)

if iron_gear_wheels > 0:
    print(f"Iron gear wheels in output chest: {iron_gear_wheels}")
    print("Iron gear wheel production line is working correctly!")
else:
    print("No iron gear wheels found in output chest. Troubleshooting:")

    # Check iron ore in mining drill
    mining_drill_inventory = inspect_inventory(mining_drill)
    print(f"Iron ore in mining drill: {mining_drill_inventory.get(Prototype.IronOre, 0)}")

    # Check iron plates in furnace
    furnace_inventory = inspect_inventory(furnace)
    print(f"Iron plates in furnace: {furnace_inventory.get(Prototype.IronPlate, 0)}")

    # Check assembling machine
    assembling_machine_inventory = inspect_inventory(assembling_machine)
    print(f"Iron plates in