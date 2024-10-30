
from factorio_instance import *

"""
Design a copper ore extraction system with two burner mining drills, each feeding into separate iron chests placed at a considerable distance.
"""

# Step 1: Find and move to a copper ore patch
copper_ore_position = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
print(f"Nearest copper ore found at: {copper_ore_position}")
move_to(copper_ore_position.bounding_box.center)

# Step 2: Place and fuel the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position.bounding_box.center)
fueled_drill1 = insert_item(Prototype.Coal, drill1, quantity=20)
coal_in_drill1 = fueled_drill1.fuel.get(Prototype.Coal, 0)
assert coal_in_drill1 > 0, "Failed to fuel first drill"
print("First burner mining drill placed and fueled")

# Step 3: Place and fuel the second burner mining drill
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=fueled_drill1.position, spacing=1)
fueled_drill2 = insert_item(Prototype.Coal, drill2, quantity=20)
coal_in_drill2 = fueled_drill2.fuel.get(Prototype.Coal, 0)
assert coal_in_drill2 > 0, "Failed to fuel second drill"
print("Second burner mining drill placed and fueled")

# Step 4: Place the first iron chest at a distance
chest1_position = Position(x=fueled_drill1.position.x + 10, y=fueled_drill1.position.y)
move_to(chest1_position)
chest1 = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest1_position)
print(f"First iron chest placed at: {chest1.position}")

# Step 5: Place the second iron chest at a distance
chest2_position = Position(x=fueled_drill2.position.x + 10, y=fueled_drill2.position.y + 5)
move_to(chest2_position)
chest2 = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest2_position)
print(f"Second iron chest placed at: {chest2.position}")

# Step 6: Set up burner inserters for each chest
# For chest1
move_to(chest1_position)
inserter1 = place_entity_next_to(Prototype.BurnerInserter, chest1_position, direction=Direction.RIGHT)
inserter1 = rotate_entity(inserter1, Direction.LEFT)
inserter1_fueled = insert_item(Prototype.Coal, inserter1, quantity=10)
coal_in_inserter1 = inserter1_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter1 > 0, "Failed to fuel first inserter"

# For chest2
move_to(chest2_position)
inserter2 = place_entity_next_to(Prototype.BurnerInserter, chest2_position, direction=Direction.RIGHT)
inserter2 = rotate_entity(inserter2, Direction.LEFT)
inserter2_fueled = insert_item(Prototype.Coal, inserter2, quantity=10)
coal_in_inserter2 = inserter2_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter2 > 0, "Failed to fuel second inserter"

print("Burner inserters placed and fueled")

# Step 7: Connect drills to chests with transport belts
belts1 = connect_entities(fueled_drill1.drop_position, inserter1.pickup_position, Prototype.TransportBelt)
assert belts1, "Failed to connect first drill to first chest inserter with transport belts"

belts2 = connect_entities(fueled_drill2.drop_position, inserter2.pickup_position, Prototype.TransportBelt)
assert belts2, "Failed to connect second drill to second chest inserter with transport belts"

print("Drills connected to chests with transport belts")

# Step 8: Verify the setup
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)

# Check first chest
move_to(chest1.position)
chest1 = get_entity(Prototype.IronChest, chest1.position)
chest1_inventory = inspect_inventory(chest1)
copper_ore_count1 = chest1_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the first iron chest: {copper_ore_count1}")

# Check second chest
move_to(chest2.position)
chest2 = get_entity(Prototype.IronChest, chest2.position)
chest2_inventory = inspect_inventory(chest2)
copper_ore_count2 = chest2_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the second iron chest: {copper_ore_count2}")

assert copper_ore_count1 > 0 and copper_ore_count2 > 0, "No copper ore found in one or both chests. Setup verification failed."
print("Setup verification complete. Both chests contain copper ore.")
