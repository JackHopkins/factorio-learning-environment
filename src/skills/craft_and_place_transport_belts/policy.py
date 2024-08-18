from factorio_instance import *
from factorio_instance import *
def craft_and_place_transport_belts():
    # Craft 5 transport belts
    for _ in range(5):
        # Craft iron gear wheel
        if not craft_item(Prototype.IronGearWheel):
            print("Failed to craft iron gear wheel")
            return False

        # Craft transport belt
        if not craft_item(Prototype.TransportBelt):
            print("Failed to craft transport belt")
            return False

    # Place 5 transport belts in a line
    start_position = Position(x=0, y=0)
    for i in range(5):
        position = Position(x=start_position.x + i, y=start_position.y)
        if not can_place_entity(Prototype.TransportBelt, Direction.RIGHT, position):
            print(f"Cannot place transport belt at position {position}")
            return False
        
        placed_belt = place_entity(Prototype.TransportBelt, Direction.RIGHT, position)
        if not placed_belt:
            print(f"Failed to place transport belt at position {position}")
            return False

    print("Successfully crafted and placed 5 transport belts")
    return True
