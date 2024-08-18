from factorio_instance import *

# Set up initial inventory
initial_inventory = {Prototype.CopperPlate: 15}  # More than enough copper plates

# Mock the inspect_inventory function
def mock_inspect_inventory():
    return initial_inventory

# Mock the craft_item function
def mock_craft_item(prototype, quantity):
    if prototype == Prototype.CopperCable and quantity <= 30:  # 15 plates can make 30 wire
        initial_inventory[Prototype.CopperPlate] -= quantity // 2
        initial_inventory[Prototype.CopperCable] = initial_inventory.get(Prototype.CopperCable, 0) + quantity
        return True
    return False

# Replace the actual functions with our mocks
inspect_inventory = mock_inspect_inventory
craft_item = mock_craft_item

# Test the function
result = craft_copper_wire_from_plates(20)

# Verify the result
assert result == True, "Function should return True for successful crafting"

# Check the final inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.CopperCable, 0) == 20, "Should have crafted exactly 20 copper wire"
assert final_inventory.get(Prototype.CopperPlate, 0) == 5, "Should have used 10 copper plates"

print("All tests passed successfully!")

# Test with insufficient copper plates
initial_inventory = {Prototype.CopperPlate: 5}  # Not enough copper plates
result = craft_copper_wire_from_plates(20)

assert result == False, "Function should return False when there are not enough copper plates"

print("Insufficient resources test passed successfully!")
