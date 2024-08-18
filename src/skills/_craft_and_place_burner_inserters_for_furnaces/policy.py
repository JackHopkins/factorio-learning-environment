from factorio_instance import *

def craft_and_place_burner_inserters_for_furnaces(num_inserters: int = 3):
    # Craft burner inserters
    for _ in range(num_inserters):
        # Craft iron gear wheel
        craft_item(Prototype.IronGearWheel)
        
        # Craft burner inserter
        craft_item(Prototype.BurnerInserter)

    # Find the nearest stone furnace
    furnace_position = nearest(Prototype.StoneFurnace)
    
    # Place burner inserters next to furnaces
    for i in range(num_inserters):
        # Calculate position for the next inserter
        inserter_position = Position(x=furnace_position.x, y=furnace_position.y - 1 - i)
        
        # Place the burner inserter
        inserter = place_entity(Prototype.BurnerInserter, Direction.DOWN, inserter_position)
        
        if not inserter:
            print(f"Failed to place burner inserter at {inserter_position}")
            return False

        # Find nearest coal patch
        coal_position = nearest(Resource.Coal)
        
        # Move to coal position
        move_to(coal_position)
        
        # Harvest some coal
        harvest_resource(coal_position, quantity=5)
        
        # Move back to the inserter
        move_to(inserter_position)
        
        # Insert coal into the burner inserter
        insert_item(Prototype.Coal, inserter, quantity=5)

    print(f"Successfully placed and fueled {num_inserters} burner inserters")
    return True
