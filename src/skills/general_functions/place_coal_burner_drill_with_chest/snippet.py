
# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
assert coal_position, "No coal resource found nearby"

# Craft burner mining drill and wooden chest if not in inventory
inventory = inspect_inventory()
if inventory.get(Prototype.BurnerMiningDrill) == 0:
    crafted = craft_item(Prototype.BurnerMiningDrill)
    assert crafted == 1, f"Failed to craft Burner Mining Drill. Crafted: {crafted}"

if inventory.get(Prototype.WoodenChest) == 0:
    crafted = craft_item(Prototype.WoodenChest)
    assert crafted == 1, f"Failed to craft Wooden Chest. Crafted: {crafted}"

# Move to the coal position
moved = move_to(coal_position)
assert moved, f"Failed to move to coal position at {coal_position}"

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_position)
assert drill, f"Failed to place Burner Mining Drill at {coal_position}"

# Get the drop position of the mining drill
drop_position = drill.drop_position
print(f"Drill drop position: {drop_position}")

# Place the wooden chest at the drop position
chest = place_entity(Prototype.WoodenChest, Direction.UP, drop_position)
assert chest, f"Failed to place Wooden Chest at {drop_position}"

# Verify that the drill is mining coal
entities = inspect_entities(coal_position, radius=5)
drill_entity = entities.get_entity(Prototype.BurnerMiningDrill)
assert drill_entity, "Burner Mining Drill not found in inspection results"
assert drill_entity.status == EntityStatus.WORKING, f"Burner Mining Drill is not working. Status: {drill_entity.status}"

# Verify that the chest is at the correct position
chest_entity = entities.get_entity(Prototype.WoodenChest)
assert chest_entity, "Wooden Chest not found in inspection results"
assert chest_entity.position.is_close(drop_position), f"Chest position {chest_entity.position} does not match drop position {drop_position}"

print("Successfully placed burner mining drill mining coal with a chest at its drop position")
