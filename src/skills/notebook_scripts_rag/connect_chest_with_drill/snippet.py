# Previously chest was placed with chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)
# Drill was placed with miner = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, copper_patch.bounding_box.center)
    
# Move to chest's position
move_to(chest.position)

# Place a inserter next to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT)
# rotate the inserter to face the chest, as by default it takes from the chest
inserter = rotate_entity(inserter, Direction.RIGHT)
assert inserter, "Failed to place inserter"

# Fuel the inserter
fuel_inserter = insert_item(Prototype.Coal, inserter, quantity=5)

# Connect the drill to the inserter with transport belts
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
