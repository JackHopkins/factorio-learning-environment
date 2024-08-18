from factorio_instance import *
def craft_and_place_burner_inserters_for_furnace_automation():
    # Step 1: Gather resources
    while inspect_inventory().get(Prototype.IronPlate, 0) < 9 or inspect_inventory().get(Prototype.Coal, 0) < 15:
        iron_ore_pos = nearest(Resource.IronOre)
        coal_pos = nearest(Resource.Coal)
        
        move_to(iron_ore_pos)
        harvest_resource(iron_ore_pos, 10)
        
        move_to(coal_pos)
        harvest_resource(coal_pos, 15)
    
    # Step 2: Smelt iron ore into iron plates
    furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
    insert_item(Prototype.Coal, furnace, 5)
    insert_item(Prototype.IronOre, furnace, 10)
    
    # Wait for smelting to complete
    sleep(10)
    
    # Step 3: Craft burner inserters
    craft_item(Prototype.IronGearWheel, 3)
    craft_item(Prototype.BurnerInserter, 3)
    
    # Step 4 & 5: Set up the automation system
    furnace_positions = [
        Position(x=2, y=0),
        Position(x=4, y=0),
        Position(x=6, y=0)
    ]
    
    inserter_positions = [
        Position(x=2, y=1),
        Position(x=4, y=1),
        Position(x=6, y=1)
    ]
    
    for pos in furnace_positions:
        place_entity(Prototype.StoneFurnace, position=pos)
    
    for pos in inserter_positions:
        inserter = place_entity(Prototype.BurnerInserter, direction=Direction.UP, position=pos)
        insert_item(Prototype.Coal, inserter, 1)
    
    # Place a chest with coal
    coal_chest = place_entity(Prototype.WoodenChest, position=Position(x=4, y=2))
    insert_item(Prototype.Coal, coal_chest, 10)
    
    # Step 6: Test the system
    sleep(30)
    
    # Step 7: Check if the system is working
    for pos in inserter_positions:
        inserter = get_entity(Prototype.BurnerInserter, pos)
        if not inserter or inspect_inventory(inserter).get(Prototype.Coal, 0) == 0:
            raise Exception("Automation system is not working correctly")
    
    print("Successfully set up burner inserter automation for furnaces")
