# Set up an automated stone brick production line using burner mining drills and stone furnaces

# Find nearest stone deposit
stone_deposit = nearest(Resource.Stone)
assert stone_deposit, "No stone deposit found nearby"

# Move closer to the stone deposit
move_to(stone_deposit)

# Place burner mining drill
miner = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, stone_deposit)
assert miner, "Failed to place burner mining drill"

# Calculate furnace position (3 tiles south of miner to ensure space for belt)
furnace_position = Position(x=miner.position.x, y=miner.position.y + 3)

# Place stone furnace
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
assert furnace, "Failed to place stone furnace"

# Connect miner to furnace with transport belt
belt_start = Position(x=miner.position.x, y=miner.position.y + 1)
belt_end = Position(x=furnace.position.x, y=furnace.position.y - 1)

# Place belts individually to avoid conflicts
current_pos = belt_start
while current_pos.y <= belt_end.y:
    belt = place_entity(Prototype.TransportBelt, Direction.DOWN, current_pos)
    assert belt, f"Failed to place transport belt at {current_pos}"
    current_pos = Position(x=current_pos.x, y=current_pos.y + 1)

# Insert coal into miner and furnace
insert_item(Prototype.Coal, miner, 10)
insert_item(Prototype.Coal, furnace, 10)

# Ensure the furnace is a valid crafting machine before setting the recipe
if isinstance(furnace, AssemblingMachine1):
    set_entity_recipe(furnace, Prototype.StoneBrick)
else:
    print("Warning: Unable to set recipe for the furnace")

# Wait for production
print("Waiting for production...")
sleep(120)

# Check if stone bricks are being produced
inventory = inspect_inventory(furnace)
assert inventory.get(Prototype.StoneBrick) > 0, "Stone bricks are not being produced"

print("Automated stone brick production line set up successfully!")
