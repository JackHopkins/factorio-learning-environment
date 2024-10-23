# Previously chest was placed with chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)

# wait for 30 seconds
sleep(30)

# moveto chest's position
move_to(chest.position)

# get the iron ore in the chest inventory
iron_ore_count = inspect_entity(chest)[Resource.IronOre]
print(f"Iron ore in chest: {iron_ore_count}")
assert iron_ore_count > 0, f"Expected iron ore in chest, but got {iron_ore_count}"
