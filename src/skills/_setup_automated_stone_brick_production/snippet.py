# Function to ensure an entity is fueled
def ensure_fueled(entity, fuel_amount=5):
    for _ in range(3):  # Try up to 3 times
        insert_item(Prototype.Coal, entity, fuel_amount)
        inventory = inspect_inventory(entity)
        if inventory.get(Prototype.Coal) > 0:
            return True
    return False

# Find nearest stone deposit
stone_deposit = nearest(Resource.Stone)
assert stone_deposit, "No stone deposit found nearby"

# Move to the stone deposit
move_to(stone_deposit)

# Ensure we have enough coal
coal_needed = 60
while inspect_inventory().get(Prototype.Coal, 0) < coal_needed:
    coal_position = nearest(Resource.Coal)
    move_to(coal_position)
    harvest_resource(coal_position, coal_needed - inspect_inventory().get(Prototype.Coal, 0))

# Move back to stone deposit
move_to(stone_deposit)

# Place burner mining drills
drill1 = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, stone_deposit)
assert drill1, "Failed to place first burner mining drill"
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, drill1.position, Direction.DOWN, spacing=1)
assert drill2, "Failed to place second burner mining drill"

# Fuel the burner mining drills
for drill in [drill1, drill2]:
    assert ensure_fueled(drill), f"Failed to fuel {drill.name}"

# Place stone furnaces
furnace1 = place_entity_next_to(Prototype.StoneFurnace, drill1.position, Direction.RIGHT, spacing=2)
assert furnace1, "Failed to place first stone furnace"
furnace2 = place_entity_next_to(Prototype.StoneFurnace, furnace1.position, Direction.DOWN, spacing=1)
assert furnace2, "Failed to place second stone furnace"

# Connect drills to furnaces with inserters
inserter1 = place_entity_next_to(Prototype.BurnerInserter, drill1.position, Direction.RIGHT, spacing=1)
assert inserter1, "Failed to place first inserter"
inserter2 = place_entity_next_to(Prototype.BurnerInserter, drill2.position, Direction.RIGHT, spacing=1)
assert inserter2, "Failed to place second inserter"

# Fuel the stone furnaces and inserters
for entity in [furnace1, furnace2, inserter1, inserter2]:
    assert ensure_fueled(entity), f"Failed to fuel {entity.name}"

# Place output chest
output_chest = place_entity_next_to(Prototype.WoodenChest, furnace1.position, Direction.RIGHT, spacing=2)
assert output_chest, "Failed to place output chest"

# Connect furnaces to output chest with inserters
output_inserter1 = place_entity_next_to(Prototype.BurnerInserter, furnace1.position, Direction.RIGHT, spacing=1)
assert output_inserter1, "Failed to place first output inserter"
output_inserter2 = place_entity_next_to(Prototype.BurnerInserter, furnace2.position, Direction.RIGHT, spacing=1)
assert output_inserter2, "Failed to place second output inserter"

# Fuel output inserters
for inserter in [output_inserter1, output_inserter2]:
    assert ensure_fueled(inserter), f"Failed to fuel {inserter.name}"

# Wait for production to start
sleep(120)  # Increased wait time to allow for production

# Check if stone bricks are being produced
chest_inventory = inspect_inventory(output_chest)
assert chest_inventory.get(Prototype.StoneBrick, 0) > 0, "No stone bricks produced after 120 seconds"

print("Automated stone brick production line set up successfully!")
print(f"Stone bricks in output chest: {chest_inventory.get(Prototype.StoneBrick, 0)}")
