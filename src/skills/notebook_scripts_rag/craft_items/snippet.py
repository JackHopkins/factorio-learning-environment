
# first craft a the burner mining drill
craft_item(Prototype.BurnerMiningDrill, 1)
# check the inventory after crafting the drill
drill_count = inspect_inventory()[Prototype.BurnerMiningDrill]
assert drill_count >= 1, f"Failed to craft burner mining drill. Expected 1, but got {drill_count}"
print("Crafted a burner mining drill")

# craft the burner inserter
craft_item(Prototype.BurnerInserter, 1)
# check the inventory after crafting the inserter
inserter_count = inspect_inventory()[Prototype.BurnerInserter]
assert inserter_count >= 1, f"Failed to craft burner inserter. Expected 1, but got {inserter_count}"
print("Crafted a burner inserter")