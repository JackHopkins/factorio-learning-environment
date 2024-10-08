# Create an automated inserter production facility

# Start by placing essential buildings near the player
assembler = place_entity(Prototype.AssemblingMachine1, direction=Direction.UP, position=Position(x=0, y=-3))
assert assembler, "Failed to place assembling machine"

iron_chest_input = place_entity(Prototype.IronChest, direction=Direction.UP, position=Position(x=-2, y=-3))
assert iron_chest_input, "Failed to place input iron chest"

iron_chest_output = place_entity(Prototype.IronChest, direction=Direction.UP, position=Position(x=2, y=-3))
assert iron_chest_output, "Failed to place output iron chest"

# Place inserters to move items
input_inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=Position(x=-1, y=-3))
assert input_inserter, "Failed to place input inserter"

output_inserter = place_entity(Prototype.BurnerInserter, direction=Direction.LEFT, position=Position(x=1, y=-3))
assert output_inserter, "Failed to place output inserter"

# Set the recipe for the assembling machine
recipe_set = set_entity_recipe(assembler, Prototype.BurnerInserter)
assert recipe_set, "Failed to set recipe for assembling machine"

# Craft initial materials
craft_item(Prototype.IronPlate, quantity=10)
craft_item(Prototype.IronGearWheel, quantity=10)

# Insert initial materials into the input chest
player_inventory = inspect_inventory()
iron_plates = min(player_inventory.get(Prototype.IronPlate, 0), 10)
iron_gears = min(player_inventory.get(Prototype.IronGearWheel, 0), 10)

insert_item(Prototype.IronPlate, iron_chest_input, quantity=iron_plates)
insert_item(Prototype.IronGearWheel, iron_chest_input, quantity=iron_gears)

# Place a small electric pole to power the assembling machine
electric_pole = place_entity(Prototype.SmallElectricPole, direction=Direction.UP, position=Position(x=0, y=-5))
assert electric_pole, "Failed to place small electric pole"

# Wait for production to start
sleep(30)

# Verify that burner inserters are being produced
output_inventory = inspect_inventory(iron_chest_output)
assert output_inventory.get(Prototype.BurnerInserter) > 0, "No burner inserters produced"

print("Automated inserter production facility created successfully")
