from factorio_instance import *
def test_create_assembly_machine_for_iron_gears():
    # Check if an assembly machine exists and is configured correctly
    assembly_machine = get_entity(Prototype.AssemblingMachine1, nearest(Prototype.AssemblingMachine1))
    if not assembly_machine:
        return False
    
    # Verify the recipe is set to iron gears
    if not get_prototype_recipe(assembly_machine) == get_prototype_recipe(Prototype.IronGearWheel):
        return False
    
    # Check if there's a chest nearby to collect the output
    nearby_entities = inspect_entities(assembly_machine.position, radius=3)
    output_chest = next((e for e in nearby_entities if e['name'] == 'iron-chest'), None)
    if not output_chest:
        return False
    
    # Verify the chest contains at least 50 iron gears
    chest_inventory = inspect_inventory(get_entity(Prototype.IronChest, Position(output_chest['position']['x'], output_chest['position']['y'])))
    iron_gears_count = sum(item.count for item in chest_inventory.items if item.name == 'iron-gear-wheel')
    
    if iron_gears_count < 50:
        return False
    
    # Check if there's a power connection
    if not assembly_machine.is_powered():
        return False
    
    # Check if there's an input inserter for iron plates
    input_inserter = next((e for e in nearby_entities if e['name'] == 'burner-inserter' or e['name'] == 'inserter'), None)
    if not input_inserter:
        return False
    
    # Check if there's an output inserter for iron gears
    output_inserter = next((e for e in nearby_entities if e['name'] == 'burner-inserter' or e['name'] == 'inserter' and e['position'] != input_inserter['position']), None)
    if not output_inserter:
        return False
    
    return True
