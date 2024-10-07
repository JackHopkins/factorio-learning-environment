
# Gather resources
harvest_resource(nearest(Resource.IronOre), 20)
harvest_resource(nearest(Resource.CopperOre), 20)

# Set up basic infrastructure
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
assert furnace, "Failed to place stone furnace"

# Create iron and copper plates
insert_item(Prototype.IronOre, furnace, 10)
insert_item(Prototype.CopperOre, furnace, 10)
sleep(10)  # Wait for smelting

iron_plates = extract_item(Prototype.IronPlate, furnace.position, 10)
copper_plates = extract_item(Prototype.CopperPlate, furnace.position, 10)
assert iron_plates and copper_plates, "Failed to create iron or copper plates"

# Craft necessary components
craft_item(Prototype.IronGearWheel, 10)
craft_item(Prototype.CopperCable, 10)

# Build an assembly machine
craft_item(Prototype.AssemblingMachine1, 1)
assembler = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=2, y=0))
assert assembler, "Failed to place assembly machine"

# Set up automated science pack production
recipe_set = set_entity_recipe(assembler, Prototype.ElectronicCircuit)
assert recipe_set, "Failed to set recipe for automated science pack"

# Feed materials into the assembly machine
insert_item(Prototype.IronGearWheel, assembler, 10)
insert_item(Prototype.CopperPlate, assembler, 10)

# Wait for production
sleep(50)  # Wait for 10 science packs to be produced (5 seconds each)

# Collect the science packs
science_packs = extract_item(Prototype.ElectronicCircuit, assembler.position, 10)
assert science_packs, "Failed to extract science packs from assembler"

# Verify the result
inventory = inspect_inventory()
assert inventory.get(Prototype.ElectronicCircuit) >= 10, f"Failed to craft 10 automated science packs. Current count: {inventory.get(Prototype.ElectronicCircuit)}"

print(f"Successfully crafted {inventory.get(Prototype.ElectronicCircuit)} automated science packs")
