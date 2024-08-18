from factorio_instance import *

def test_place_five_transport_belts():
    # Test setup
    start_position = Position(x=0, y=0)
    direction = Direction.RIGHT

    # Call the function
    result = place_five_transport_belts(start_position, direction)

    # Check if the function returned True
    assert result == True, "Function should return True on successful placement"

    # Check if 5 transport belts were placed
    belts = inspect_entities(start_position, radius=5)
    transport_belts = [entity for entity in belts if entity['name'] == Prototype.TransportBelt.value[0]]
    assert len(transport_belts) == 5, f"Expected 5 transport belts, but found {len(transport_belts)}"

    # Check if the belts are placed in a line
    expected_positions = [
        Position(x=0, y=0),
        Position(x=1, y=0),
        Position(x=2, y=0),
        Position(x=3, y=0),
        Position(x=4, y=0)
    ]
    for belt, expected_pos in zip(transport_belts, expected_positions):
        assert belt['position'] == expected_pos, f"Belt at {belt['position']} should be at {expected_pos}"

    # Check if all belts are facing the correct direction
    for belt in transport_belts:
        assert belt['direction'] == direction, f"Belt at {belt['position']} is facing {belt['direction']}, should be facing {direction}"

    # Test item movement (optional, if game mechanics allow)
    test_item = Prototype.IronPlate
    place_entity(test_item, direction, start_position)
    sleep(2)  # Wait for item to move
    end_position = Position(x=4, y=0)
    item_at_end = get_entity(test_item, end_position)
    assert item_at_end is not None, f"Test item should have moved to the end of the belt at {end_position}"

    print("All tests passed successfully!")

# Run the test
test_place_five_transport_belts()
