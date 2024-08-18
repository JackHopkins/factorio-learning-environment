from factorio_instance import *

# Test setup
initial_coal = 20
initial_iron_plates = 10

# Add initial resources to inventory
for _ in range(initial_coal):
    craft_item(Prototype.Coal)
for _ in range(initial_iron_plates):
    craft_item(Prototype.IronPlate)

# Place a stone furnace for testing
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
if not furnace:
    print("Failed to place stone furnace for testing")
    exit(1)

# Call the function to test
result = craft_and_place_burner_inserters_for_furnaces(3)

if not result:
    print("Function returned False, indicating failure")
    exit(1)

# Verify the results
inserters = []
for i in range(3):
    inserter_position = Position(x=furnace.position.x, y=furnace.position.y - 1 - i)
    inserter = get_entity(Prototype.BurnerInserter, inserter_position)
    if not inserter:
        print(f"Failed to find burner inserter at position {inserter_position}")
        exit(1)
    inserters.append(inserter)

# Check if inserters are placed correctly
if len(inserters) != 3:
    print(f"Expected 3 inserters, but found {len(inserters)}")
    exit(1)

# Check if inserters are fueled
for i, inserter in enumerate(inserters):
    inserter_inventory = inspect_inventory(inserter)
    coal_count = inserter_inventory.get(Prototype.Coal, 0)
    if coal_count != 5:
        print(f"Inserter {i+1} has {coal_count} coal instead of 5")
        exit(1)

# Check if the correct amount of resources were used
final_inventory = inspect_inventory()
final_coal = final_inventory.get(Prototype.Coal, 0)
final_iron_plates = final_inventory.get(Prototype.IronPlate, 0)

expected_coal_used = 15  # 5 for each inserter
expected_iron_plates_used = 6  # 2 for each inserter (1 for the inserter, 1 for the iron gear wheel)

if initial_coal - final_coal != expected_coal_used:
    print(f"Unexpected coal usage. Expected {expected_coal_used}, but used {initial_coal - final_coal}")
    exit(1)

if initial_iron_plates - final_iron_plates != expected_iron_plates_used:
    print(f"Unexpected iron plate usage. Expected {expected_iron_plates_used}, but used {initial_iron_plates - final_iron_plates}")
    exit(1)

print("All tests passed successfully!")
