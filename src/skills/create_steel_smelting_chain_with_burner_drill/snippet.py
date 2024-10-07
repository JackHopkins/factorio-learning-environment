# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
game.move_to(iron_ore_position)
assert iron_ore_position, "No iron ore patch found"

# Place burner mining drill on iron ore patch
burner_drill = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, iron_ore_position)
assert burner_drill, "Failed to place burner mining drill"
print(f"Burner mining drill placed at {burner_drill.position}")

# Place two stone furnaces near the burner mining drill
furnace1 = place_entity_next_to(Prototype.StoneFurnace, burner_drill.position, Direction.RIGHT, spacing=0)
assert furnace1, "Failed to place first stone furnace"
print(f"First stone furnace placed at {furnace1.position}")

furnace2 = place_entity_next_to(Prototype.StoneFurnace, furnace1.position, Direction.RIGHT, spacing=1)
assert furnace2, "Failed to place second stone furnace"
print(f"Second stone furnace placed at {furnace2.position}")

# Place inserters between entities
inserter1 = place_entity_next_to(Prototype.BurnerInserter, furnace1.position, Direction.RIGHT)
assert inserter1, "Failed to place second inserter"
rotate_entity(inserter1, Direction.RIGHT)
print(f"Second inserter placed at {inserter1.position}")

# Add fuel to entities (assuming coal is in inventory)
insert_item(Prototype.Coal, burner_drill, 5)
insert_item(Prototype.Coal, furnace1, 5)
insert_item(Prototype.Coal, furnace2, 5)
insert_item(Prototype.Coal, inserter1, 1)

# Verify setup
entities = inspect_entities(burner_drill.position, radius=10)
assert any(
    e.name == "burner-mining-drill" for e in entities.entities), "Burner mining drill not found in inspection"
assert sum(
    1 for e in entities.entities if e.name == "stone-furnace") == 2, "Two stone furnaces not found in inspection"
assert sum(1 for e in entities.entities if
           e.name == "burner-inserter") == 1, "A burner inserter not found in inspection"

# Test that the stone furnace has steel after 60 seconds
sleep(60)
furnace_inventory = inspect_inventory(furnace2)
steel = furnace_inventory.get(Prototype.SteelPlate, 0)
assert steel > 0, f"No steel produced after 60 seconds. Check fuel levels and connections."

print("Steel smelting chain setup complete and verified")
