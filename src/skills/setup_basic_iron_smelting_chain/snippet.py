# Place iron ore patch
iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
assert iron_ore_patch, "No iron ore patch found"
print(f"Iron ore patch found at {iron_ore_patch.bounding_box.center}")

# Place burner mining drill on iron ore patch
move_to(iron_ore_patch.bounding_box.center)
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.RIGHT,
                          position=iron_ore_patch.bounding_box.center)
assert drill, "Failed to place burner mining drill"
print(f"Burner mining drill placed at {drill.position}")

# Fuel the burner mining drill
drill_with_coal = insert_item(Prototype.Coal, drill, quantity=5)
assert drill_with_coal.fuel_inventory.get(Prototype.Coal, 0) > 0, "Failed to fuel burner mining drill"
print(f"Inserted {drill_with_coal.fuel_inventory.get(Prototype.Coal, 0)} coal into burner mining drill")

# Place stone furnace next to drill
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position,
                                    direction=Direction.RIGHT)
assert furnace, "Failed to place stone furnace"
print(f"Stone furnace placed at {furnace.position}")

# Fuel the stone furnace
furnace_with_coal = insert_item(Prototype.Coal, furnace, quantity=5)
assert furnace_with_coal.fuel_inventory.get(Prototype.Coal, 0) > 0, "Failed to fuel stone furnace"
print(f"Inserted {furnace_with_coal.fuel_inventory.get(Prototype.Coal, 0)} coal into stone furnace")

# Place inserter next to furnace
inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position,
                                     direction=Direction.RIGHT)
assert inserter, "Failed to place inserter"
print(f"Inserter placed at {inserter.position}")

# Fuel the inserter
inserter_with_coal = insert_item(Prototype.Coal, inserter, quantity=2)
assert inserter_with_coal.fuel_inventory.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"
print(f"Inserted {inserter_with_coal.fuel_inventory.get(Prototype.Coal, 0)} coal into inserter")

# Place chest next to inserter
chest = place_entity_next_to(Prototype.WoodenChest, reference_position=inserter.position,
                                  direction=Direction.RIGHT)
assert chest, "Failed to place chest"
print(f"Chest placed at {chest.position}")

# Verify setup
sleep(60)  # Wait for the system to produce some iron plates

chest_inventory = inspect_inventory(chest)
iron_plates = chest_inventory.get(Prototype.IronPlate, 0)
assert iron_plates > 0, f"No iron plates produced after 60 seconds. Check fuel levels and connections."
print(f"Success! {iron_plates} iron plates produced and stored in the chest.")
