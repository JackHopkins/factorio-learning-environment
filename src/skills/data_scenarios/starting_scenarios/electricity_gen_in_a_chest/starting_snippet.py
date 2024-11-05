chest_pos = Position(x=10, y=11)
move_to(chest_pos)

# place a chest down
chest = place_entity(Prototype.WoodenChest, Direction.DOWN, position = chest_pos)
assert chest, "Failed to place chest"

# insert the boiler and offshore pump into the chest
insert_item(Prototype.Boiler, chest)
insert_item(Prototype.OffshorePump, chest)