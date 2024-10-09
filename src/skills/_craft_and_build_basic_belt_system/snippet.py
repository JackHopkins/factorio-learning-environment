# Craft 30 transport belts
initial_belt_count = inspect_inventory().get(Prototype.TransportBelt, 0)
craft_item(Prototype.TransportBelt, 30)
final_belt_count = inspect_inventory().get(Prototype.TransportBelt, 0)
assert final_belt_count - initial_belt_count == 30, f"Failed to craft 30 transport belts. Only crafted {final_belt_count - initial_belt_count}"
print(f"Successfully crafted {final_belt_count - initial_belt_count} transport belts")

# Find nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
assert iron_ore_position, "No iron ore patch found nearby"
print(f"Found iron ore patch at {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at {iron_ore_position}")

# Place a mining drill on the iron ore patch
miner = place_entity(Prototype.ElectricMiningDrill, Direction.DOWN, iron_ore_position)
assert miner, "Failed to place mining drill"
print(f"Placed mining drill at {miner.position}")

# Start placing transport belts from the miner output
belt_start = miner.position + Position(x=0, y=2)  # Assuming miner output is on the bottom
current_position = belt_start
belts_placed = 0

for _ in range(30):
    move_to(current_position)
    belt = place_entity(Prototype.TransportBelt, Direction.DOWN, current_position)
    if not belt:
        print(f"Failed to place belt at {current_position}")
        break

    belts_placed += 1
    current_position = current_position + Position(x=0, y=1)

    # Move every 3 belts to ensure we're within range
    if belts_placed % 3 == 0:
        move_to(current_position)

assert belts_placed == 30, f"Failed to place all 30 transport belts. Only placed {belts_placed}"
print(f"Successfully placed {belts_placed} transport belts")

# Verify the transportation system
total_belts = 0
for i in range(0, 30, 3):
    inspection = inspect_entities(belt_start + Position(x=0, y=i), radius=5)
    belt_line = inspection.get_entities(Prototype.TransportBelt)
    total_belts += len(belt_line)

assert total_belts >= 25, f"Expected at least 25 connected transport belts, but found {total_belts}"
print(f"Verified transport belt line: {total_belts} belts found")

# Check if the system is operational
miner_entity = get_entity(Prototype.ElectricMiningDrill, miner.position)
assert miner_entity, "Failed to get the mining drill entity"
miner_status = miner_entity.status
assert miner_status in [EntityStatus.WORKING, EntityStatus.NORMAL], f"Mining drill is not working. Status: {miner_status}"
print("Mining drill is operational")

# Wait for some time to allow ore to be mined and transported
sleep(20)

# Check multiple belts for iron ore
ore_found = False
for i in range(1, 31):  # Check all 30 belts
    belt_position = belt_start + Position(x=0, y=i-1)
    move_to(belt_position)  # Move to each belt to ensure it's within inspection range
    belt = get_entity(Prototype.TransportBelt, belt_position)
    if belt:
        belt_inventory = inspect_inventory(belt)
        if belt_inventory.get(Prototype.IronOre, 0) > 0:
            print(f"Iron ore found on belt at position {belt_position}")
            ore_found = True
            break

assert ore_found, "No iron ore found on any of the transport belts"

print("Objective completed: 30 transport belts crafted and simple ore transportation system created")
