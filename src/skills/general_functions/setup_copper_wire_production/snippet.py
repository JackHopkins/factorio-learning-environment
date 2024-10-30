# Set up a small copper wire production facility using an assembling machine

# Place an assembling machine
assembling_machine = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=0, y=2))
assert assembling_machine, "Failed to place assembling machine"

# Set the recipe for copper wire
set_recipe_success = set_entity_recipe(assembling_machine, Prototype.CopperCable)
assert set_recipe_success, "Failed to set copper wire recipe"

# Place an iron chest for input (copper plates)
input_chest = place_entity(Prototype.IronChest, Direction.UP, Position(x=-1, y=2))
assert input_chest, "Failed to place input chest"

# Place an iron chest for output (copper wire)
output_chest = place_entity(Prototype.IronChest, Direction.UP, Position(x=1, y=2))
assert output_chest, "Failed to place output chest"

# Connect input chest to assembling machine
input_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, Position(x=-1, y=1))
assert input_inserter, "Failed to place input inserter"

# Connect assembling machine to output chest
output_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, Position(x=1, y=1))
assert output_inserter, "Failed to place output inserter"

# Insert some copper plates into the input chest
insert_item(Prototype.CopperPlate, input_chest, quantity=50)

# Verify the setup
inspection = inspect_entities(Position(x=0, y=0), radius=5)
assert any(e.name == "assembling-machine-1" for e in inspection.entities), "Assembling machine not found"
assert any(e.name == "iron-chest" for e in inspection.entities), "Iron chests not found"
assert any(e.name == "burner-inserter" for e in inspection.entities), "Inserters not found"

print("Copper wire production facility set up successfully")
