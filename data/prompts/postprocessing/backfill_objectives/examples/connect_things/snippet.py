# Find stone patch and move there
stone_patch = get_resource_patch(Resource.Stone, nearest(Resource.Stone))
assert stone_patch is not None, "No stone patch found"
move_to(stone_patch.bounding_box.center())

# Place mining drill oriented towards where furnace will go
drill = place_entity(
    Prototype.BurnerMiningDrill, Direction.RIGHT, stone_patch.bounding_box.center()
)
assert drill is not None, "Failed to place burner mining drill"

# Place furnace to receive stone
furnace = place_entity_next_to(
    Prototype.StoneFurnace, drill.position, direction=Direction.RIGHT, spacing=1
)

assert furnace is not None, "Failed to place stone furnace"
# Place inserter between drill and furnace
inserter = place_entity_next_to(
    Prototype.BurnerInserter, drill.position, direction=Direction.RIGHT
)
assert inserter is not None, "Failed to place burner inserter"

# Fuel the drill and inserter with coal
insert_item(Prototype.Coal, drill, 5)
insert_item(Prototype.Coal, inserter, 5)
insert_item(Prototype.Coal, furnace, 5)

# Verify the setup
inspection = inspect_entities(drill.position, radius=5)
drill_exists = any(
    e.name == Prototype.BurnerMiningDrill.value[0] for e in inspection.entities
)
furnace_exists = any(
    e.name == Prototype.StoneFurnace.value[0] for e in inspection.entities
)
inserter_exists = any(
    e.name == Prototype.BurnerInserter.value[0] for e in inspection.entities
)

assert drill_exists, "Mining drill not found in setup"
assert furnace_exists, "Furnace not found in setup"
assert inserter_exists, "Inserter not found in setup"
