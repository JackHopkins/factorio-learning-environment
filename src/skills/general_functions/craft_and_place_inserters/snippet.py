
# Step 1: Check if we have enough materials
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 3, "Not enough iron plates. Need at least 3."
assert inventory.get(Prototype.IronGearWheel) >= 3, "Not enough iron gear wheels. Need at least 3."
assert inventory.get(Prototype.ElectronicCircuit) >= 3, "Not enough electronic circuits. Need at least 3."

# Step 2: Craft 3 inserters
for _ in range(3):
    craft_success = craft_item(Prototype.BurnerInserter)
    assert craft_success, f"Failed to craft inserter. Current inventory: {inspect_inventory()}"

# Verify that we have crafted 3 inserters
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerInserter) >= 3, f"Failed to craft 3 inserters. Current inventory: {inventory}"

# Step 3 & 4: Identify locations and place inserters
structures = inspect_entities(radius=20)
chests = [entity for entity in structures.entities if entity.name == Prototype.IronChest.value[0]]
furnaces = [entity for entity in structures.entities if entity.name == Prototype.StoneFurnace.value[0]]

assert len(chests) >= 1 and len(furnaces) >= 1, "Not enough structures to place inserters between. Need at least one chest and one furnace."

for i in range(3):
    chest = chests[i % len(chests)]
    furnace = furnaces[i % len(furnaces)]
    
    # Calculate position between chest and furnace
    mid_position = Position(
        x=(chest.position.x + furnace.position.x) / 2,
        y=(chest.position.y + furnace.position.y) / 2
    )
    
    # Place inserter
    inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, mid_position)
    assert inserter is not None, f"Failed to place inserter {i+1} at position {mid_position}"
    
    # Rotate inserter to face from chest to furnace
    direction = Direction.RIGHT if furnace.position.x > chest.position.x else Direction.LEFT
    rotate_success = rotate_entity(inserter, direction)
    assert rotate_success, f"Failed to rotate inserter {i+1} to face from chest to furnace"

# Step 5: Verify placement
final_structures = inspect_entities(radius=20)
placed_inserters = [entity for entity in final_structures.entities if entity.name == Prototype.BurnerInserter.value[0]]
assert len(placed_inserters) >= 3, f"Failed to place 3 inserters. Only {len(placed_inserters)} found."

print("Successfully crafted and placed 3 inserters between structures.")
