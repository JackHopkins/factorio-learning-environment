from factorio_instance import *

def place_five_transport_belts(start_position: Position, direction: Direction) -> bool:
    # Craft 5 transport belts if not already in inventory
    inventory = inspect_inventory()
    belts_needed = 5 - inventory.get(Prototype.TransportBelt, 0)
    
    if belts_needed > 0:
        if not craft_item(Prototype.TransportBelt, belts_needed):
            print("Failed to craft transport belts")
            return False

    # Place 5 transport belts in a line
    current_position = start_position
    for _ in range(5):
        belt = place_entity(Prototype.TransportBelt, direction, current_position)
        if not belt:
            print(f"Failed to place transport belt at {current_position}")
            return False
        
        # Move to the next position based on the direction
        if direction == Direction.UP:
            current_position = Position(current_position.x, current_position.y - 1)
        elif direction == Direction.RIGHT:
            current_position = Position(current_position.x + 1, current_position.y)
        elif direction == Direction.DOWN:
            current_position = Position(current_position.x, current_position.y + 1)
        elif direction == Direction.LEFT:
            current_position = Position(current_position.x - 1, current_position.y)

    print("Successfully placed 5 transport belts")
    return True
