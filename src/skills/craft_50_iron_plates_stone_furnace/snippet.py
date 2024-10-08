
# Place a stone furnace
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
assert furnace is not None, "Failed to place stone furnace"
print(f"Stone furnace placed at {furnace.position}")

# Mine coal and iron ore
coal_position = nearest(Resource.Coal)
iron_ore_position = nearest(Resource.IronOre)

coal_mined = harvest_resource(coal_position, quantity=50)
iron_ore_mined = harvest_resource(iron_ore_position, quantity=50)

assert coal_mined >= 50, f"Not enough coal mined. Only mined {coal_mined}"
assert iron_ore_mined >= 50, f"Not enough iron ore mined. Only mined {iron_ore_mined}"

print(f"Mined {coal_mined} coal and {iron_ore_mined} iron ore")

# Insert coal and iron ore into the furnace
insert_item(Prototype.Coal, furnace, quantity=25)
insert_item(Prototype.IronOre, furnace, quantity=50)

# Wait for smelting to complete (approx. 100 seconds for 50 plates)
sleep(100)

# Check furnace inventory
furnace_inventory = inspect_inventory(furnace)
iron_plates_in_furnace = furnace_inventory.get(Prototype.IronPlate, 0)

# Extract iron plates from the furnace
extract_item(Prototype.IronPlate, furnace.position, quantity=50)

# Check player inventory
player_inventory = inspect_inventory()
iron_plates_crafted = player_inventory.get(Prototype.IronPlate, 0)

assert iron_plates_crafted >= 50, f"Failed to craft 50 iron plates. Only crafted {iron_plates_crafted}"

print(f"Successfully crafted {iron_plates_crafted} iron plates")
