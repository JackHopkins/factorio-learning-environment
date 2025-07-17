# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Verify we got stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"
