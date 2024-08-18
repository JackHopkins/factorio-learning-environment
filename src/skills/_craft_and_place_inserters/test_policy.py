from factorio_instance import *

# Test the craft_and_place_inserters function
try:
    result = craft_and_place_inserters(5)
    
    # Check if the function returned True
    assert result == True, "Function did not return True"
    
    # Check if 5 inserters were crafted
    inventory = inspect_inventory()
    assert inventory.get(Prototype.BurnerInserter, 0) == 0, "Not all inserters were placed"
    
    # Check if 5 inserters were placed in the world
    entities = inspect_entities(radius=20)
    placed_inserters = [e for e in entities if e['name'] == 'burner-inserter']
    assert len(placed_inserters) == 5, f"Expected 5 inserters, but found {len(placed_inserters)}"
    
    # Check if the inserters are properly spaced
    positions = [e['position'] for e in placed_inserters]
    for i in range(len(positions) - 1):
        distance = ((positions[i]['x'] - positions[i+1]['x'])**2 + (positions[i]['y'] - positions[i+1]['y'])**2)**0.5
        assert distance >= 2, f"Inserters {i} and {i+1} are not properly spaced"
    
    print("All tests passed successfully!")

except AssertionError as e:
    print(f"Test failed: {str(e)}")
except Exception as e:
    print(f"An error occurred during testing: {str(e)}")
