# Find nearest stone deposit
stone_deposit = nearest(Resource.Stone)
assert stone_deposit, "No stone deposit found nearby"

# Move to the stone deposit
move_to(stone_deposit)

# Place burner mining drills
drill1 = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, stone_deposit)
assert drill1, "Failed to place first burner mining drill"
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, drill1.position, Direction.DOWN, spacing=1)
assert drill2, "Failed to place second burner mining drill"

# Find nearest coal deposit
coal_deposit = nearest(Resource.Coal)
assert coal_deposit, "No coal deposit found nearby"

# Move to the coal deposit
move_to(coal_deposit)

# Place coal mining drill
coal_drill = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, coal_deposit)
assert coal_drill, "Failed to place coal burner mining drill"

# Manually mine some coal
harvested_coal = harvest_resource(coal_deposit, quantity=50)
assert harvested_coal > 0, f"Failed to harvest coal. Harvested: {harvested_coal}"

# Fuel the coal drill first
insert_item(Prototype.Coal, coal_drill, 5)
assert inspect_inventory(coal_drill).get(Prototype.Coal) > 0, "Failed to fuel coal drill"

# Wait for coal production
sleep(60)

# Move back to stone area and fuel stone drills
for drill in [drill1, drill2]:
    move_to(drill.position)
    insert_item(Prototype.Coal, drill, 5)
    assert inspect_inventory(drill).get(Prototype.Coal) > 0, f"Failed to fuel {drill.name}"

# Place stone furnaces closer to drills
furnace1 = place_entity_next_to(Prototype.StoneFurnace, drill1.position, Direction.RIGHT, spacing=1)
assert furnace1, "Failed to place first stone furnace"
furnace2 = place_entity_next_to(Prototype.StoneFurnace, drill2.position, Direction.RIGHT, spacing=1)
assert furnace2, "Failed to place second stone furnace"

# Fuel the stone furnaces
for furnace in [furnace1, furnace2]:
    move_to(furnace.position)
    insert_item(Prototype.Coal, furnace, 5)
    fuel_amount = inspect_inventory(furnace).get(Prototype.Coal, 0)
    assert fuel_amount > 0, f"Failed to fuel {furnace.name}. Current fuel: {fuel_amount}"

# Create transport system
belt1 = connect_entities(drill1, furnace1, Prototype.TransportBelt)
belt2 = connect_entities(drill2, furnace2, Prototype.TransportBelt)
assert belt1 and belt2, "Failed to create transport system"

# Place output chests for stone bricks
chest1 = place_entity_next_to(Prototype.WoodenChest, furnace1.position, Direction.RIGHT, spacing=1)
chest2 = place_entity_next_to(Prototype.WoodenChest, furnace2.position, Direction.RIGHT, spacing=1)
assert chest1 and chest2, "Failed to place output chests"

# Connect furnaces to output chests
output_belt1 = connect_entities(furnace1, chest1, Prototype.TransportBelt)
output_belt2 = connect_entities(furnace2, chest2, Prototype.TransportBelt)
assert output_belt1 and output_belt2, "Failed to create output transport system"

# Move back to coal area
move_to(coal_deposit)

# Create coal distribution system
coal_chest = place_entity_next_to(Prototype.WoodenChest, coal_drill.position, Direction.RIGHT, spacing=1)
assert coal_chest, "Failed to place coal output chest"
coal_belt = connect_entities(coal_drill, coal_chest, Prototype.TransportBelt)
assert coal_belt, "Failed to create coal transport system"

# Connect coal chest to furnaces and drills
for target in [drill1, drill2, furnace1, furnace2]:
    coal_dist_belt = connect_entities(coal_chest, target, Prototype.TransportBelt)
    assert coal_dist_belt, f"Failed to connect coal to {target.name}"

# Wait for production to start
sleep(360)

# Verify production
stone_bricks1 = inspect_inventory(chest1).get(Prototype.StoneBrick, 0)
stone_bricks2 = inspect_inventory(chest2).get(