from factorio_instance import *
def create_assembly_machine_for_iron_gears():
    # Step 1: Craft an assembly machine
    if not craft_item(Prototype.AssemblingMachine1):
        raise Exception("Failed to craft assembly machine")

    # Step 2: Place the assembly machine
    assembly_machine = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=0, y=0))
    if not assembly_machine:
        raise Exception("Failed to place assembly machine")

    # Step 3: Set the recipe for iron gears
    if not set_entity_recipe(assembly_machine, Prototype.IronGearWheel):
        raise Exception("Failed to set recipe for iron gears")

    # Step 4: Place an iron chest for output
    output_chest = place_entity_next_to(Prototype.IronChest, assembly_machine.position, Direction.DOWN)
    if not output_chest:
        raise Exception("Failed to place output chest")

    # Step 5: Place inserters for input and output
    input_inserter = place_entity_next_to(Prototype.BurnerInserter, assembly_machine.position, Direction.UP)
    if not input_inserter:
        raise Exception("Failed to place input inserter")

    output_inserter = place_entity_next_to(Prototype.BurnerInserter, assembly_machine.position, Direction.DOWN)
    if not output_inserter:
        raise Exception("Failed to place output inserter")

    # Step 6: Rotate output inserter to face the chest
    if not rotate_entity(output_inserter, Direction.DOWN):
        raise Exception("Failed to rotate output inserter")

    # Step 7: Place a transport belt for input
    input_belt = place_entity_next_to(Prototype.TransportBelt, input_inserter.position, Direction.UP)
    if not input_belt:
        raise Exception("Failed to place input belt")

    # Step 8: Monitor production until we have 50 iron gears
    gears_produced = 0
    while gears_produced < 50:
        # Insert iron plates into the assembly machine
        insert_item(Prototype.IronPlate, assembly_machine, 10)

        # Wait for production
        sleep(10)

        # Check the output chest
        chest_inventory = inspect_inventory(output_chest)
        if Prototype.IronGearWheel.value[0] in chest_inventory:
            gears_produced += chest_inventory[Prototype.IronGearWheel.value[0]]

        print(f"Iron gears produced: {gears_produced}")

    print("Successfully produced 50 iron gears!")
