# Constants
PLACEMENT_RADIUS = 10

# Helper function to place entity within radius
def place_entity_nearby(prototype, direction, reference_position):
    for dx in range(-PLACEMENT_RADIUS, PLACEMENT_RADIUS + 1):
        for dy in range(-PLACEMENT_RADIUS, PLACEMENT_RADIUS + 1):
            pos = Position(x=reference_position.x + dx, y=reference_position.y + dy)
            entity = place_entity(prototype, direction, pos)
            if entity:
                return entity
    return None

# 1. Set up raw material production
player_pos = Position(x=0, y=0)
iron_miner = place_entity_nearby(Prototype.BurnerMiningDrill, Direction.UP, nearest(Resource.IronOre))
assert iron_miner, "Failed to place iron ore miner"

coal_miner = place_entity_nearby(Prototype.BurnerMiningDrill, Direction.UP, nearest(Resource.Coal))
assert coal_miner, "Failed to place coal miner"

copper_miner = place_entity_nearby(Prototype.BurnerMiningDrill, Direction.UP, nearest(Resource.CopperOre))
assert copper_miner, "Failed to place copper ore miner"

# 2. Establish smelting operations
iron_furnace = place_entity_nearby(Prototype.StoneFurnace, Direction.UP, iron_miner.position)
assert iron_furnace, "Failed to place iron smelting furnace"

copper_furnace = place_entity_nearby(Prototype.StoneFurnace, Direction.UP, copper_miner.position)
assert copper_furnace, "Failed to place copper smelting furnace"

# Connect miners to furnaces
connect_entities(iron_miner, iron_furnace, Prototype.TransportBelt)
connect_entities(copper_miner, copper_furnace, Prototype.TransportBelt)
connect_entities(coal_miner, iron_furnace, Prototype.TransportBelt)
connect_entities(coal_miner, copper_furnace, Prototype.TransportBelt)

# 3. Create component production lines
gear_assembler = place_entity_nearby(Prototype.AssemblingMachine1, Direction.UP, iron_furnace.position)
assert gear_assembler, "Failed to place gear wheel assembler"
set_entity_recipe(gear_assembler, Prototype.IronGearWheel)

circuit_assembler = place_entity_nearby(Prototype.AssemblingMachine1, Direction.UP, copper_furnace.position)
assert circuit_assembler, "Failed to place electronic circuit assembler"
set_entity_recipe(circuit_assembler, Prototype.ElectronicCircuit)

# Connect smelters to component assemblers
connect_entities(iron_furnace, gear_assembler, Prototype.TransportBelt)
connect_entities(iron_furnace, circuit_assembler, Prototype.TransportBelt)
connect_entities(copper_furnace, circuit_assembler, Prototype.TransportBelt)

# 4. Set up inserter assembly
inserter_assembler = place_entity_nearby(Prototype.AssemblingMachine1, Direction.UP, gear_assembler.position)
assert inserter_assembler, "Failed to place inserter assembler"
set_entity_recipe(inserter_assembler, Prototype.BurnerInserter)

# Connect component assemblers to inserter assembler
connect_entities(gear_assembler, inserter_assembler, Prototype.TransportBelt)
connect_entities(circuit_assembler, inserter_assembler, Prototype.TransportBelt)
connect_entities(iron_furnace, inserter_assembler, Prototype.TransportBelt)

# 5. Create output storage
output_chest = place_entity_nearby(Prototype.IronChest, Direction.UP, inserter_assembler.position)
assert output_chest, "Failed to place output chest"

output_inserter = place_entity_nearby(Prototype.BurnerInserter, Direction.LEFT, output_chest.position)
assert output_inserter, "Failed to place output inserter"

# Connect inserter assembler to output chest
connect_entities(inserter_assembler, output_chest, Prototype.TransportBelt)

# 6. Verify production
sleep(120)  # Wait for production to start

inspection = inspect_inventory(output_chest)
assert inspection.get(Prototype.BurnerInserter, 0) > 0, "No inserters produced"

print("Automated inserter production facility created successfully!")
