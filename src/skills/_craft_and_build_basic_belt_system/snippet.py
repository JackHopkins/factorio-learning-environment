# Craft 30 transport belts
crafted_belts = craft_item(Prototype.TransportBelt, 30)
assert crafted_belts == 30, f"Failed to craft 30 transport belts, only crafted {crafted_belts}"

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
assert iron_ore_position, "No iron ore patch found nearby"

# Move closer to the iron ore patch
move_to(iron_ore_position)

# Harvest some iron ore and coal
harvest_resource(iron_ore_position, quantity=50)

coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=20)

# Move back to iron ore position
move_to(iron_ore_position)

# Place a burner mining drill on the iron ore patch
miner = place_entity(Prototype.BurnerMiningDrill, direction=Direction.DOWN, position=iron_ore_position)
assert miner, "Failed to place burner mining drill"

# Place a stone furnace next to the miner
furnace_position = Position(x=miner.position.x, y=miner.position.y + 3)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
assert furnace, "Failed to place stone furnace"

# Connect miner to furnace with transport belts
belt_path = connect_entities(miner, furnace, connection_type=Prototype.TransportBelt)
assert len(belt_path) > 0, "Failed to connect miner to furnace with transport belts"

# Insert fuel into the miner and furnace
insert_item(Prototype.Coal, miner, quantity=5)
insert_item(Prototype.Coal, furnace, quantity=5)

# Wait for some iron ore to be mined
sleep(30)

# Insert iron ore into the furnace to start production
furnace_inventory = inspect_inventory(furnace)
iron_ore_count = furnace_inventory.get(Prototype.IronOre, 0)
if iron_ore_count == 0:
    player_inventory = inspect_inventory()
    iron_ore_to_insert = min(player_inventory.get(Prototype.IronOre, 0), 10)
    if iron_ore_to_insert > 0:
        insert_item(Prototype.IronOre, furnace, quantity=iron_ore_to_insert)

# Wait for some iron plates to be produced
sleep(60)

# Check if iron plates are being produced
furnace_inventory = inspect_inventory(furnace)
iron_plates = furnace_inventory.get(Prototype.IronPlate, 0)
assert iron_plates > 0, f"No iron plates produced after 60 seconds, current count: {iron_plates}"

# Extend the transport belt line
belt_end = Position(x=furnace.position.x + 5, y=furnace.position.y)
additional_belts = connect_entities(furnace.position, belt_end, connection_type=Prototype.TransportBelt)
assert len(additional_belts) > 0, "Failed to extend transport belt line"

# Verify the complete system
total_belts = len(belt_path) + len(additional_belts)
assert total_belts >= 10, f"Not enough transport belts placed. Current: {total_belts}"

print(f"Successfully created a simple ore transportation system with {total_belts} belts. Iron plates produced: {iron_plates}")
