from factorio_instance import *

# Mock the necessary functions and classes
class Prototype:
    CopperPlate = "copper-plate"
    CopperCable = "copper-cable"

def inspect_inventory():
    return {"copper-plate": 10}

def craft_item(prototype, quantity):
    return True

# Test the craft_copper_cables function
def test_craft_copper_cables():
    # Set up the initial inventory
    global inventory
    inventory = {"copper-plate": 10}

    # Call the function to craft 20 copper cables
    result = craft_copper_cables(20)

    # Check if the function returned True (successful crafting)
    assert result == True, "Failed to craft copper cables"

    # Verify the inventory after crafting
    final_inventory = inspect_inventory()
    assert final_inventory.get(Prototype.CopperPlate, 0) == 0, "Incorrect number of copper plates remaining"
    assert final_inventory.get(Prototype.CopperCable, 0) == 20, "Incorrect number of copper cables crafted"

    print("Test passed: Successfully crafted 20 copper cables")

# Run the test
test_craft_copper_cables()

# Test with insufficient copper plates
def test_craft_copper_cables_insufficient_plates():
    # Set up the initial inventory with insufficient copper plates
    global inventory
    inventory = {"copper-plate": 5}

    # Call the function to craft 20 copper cables
    result = craft_copper_cables(20)

    # Check if the function returned False (failed crafting due to insufficient materials)
    assert result == False, "Function should return False when there are insufficient copper plates"

    # Verify the inventory remains unchanged
    final_inventory = inspect_inventory()
    assert final_inventory.get(Prototype.CopperPlate, 0) == 5, "Copper plates should not be consumed on failure"
    assert final_inventory.get(Prototype.CopperCable, 0) == 0, "No copper cables should be crafted on failure"

    print("Test passed: Correctly handled insufficient copper plates")

# Run the second test
test_craft_copper_cables_insufficient_plates()
