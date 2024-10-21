# Place a stone furnace
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
assert furnace, "Failed to place stone furnace"

# Insert iron plates into the furnace
iron_plates_inserted = insert_item(Prototype.IronPlate, furnace, quantity=5)
assert iron_plates_inserted, "Failed to insert iron plates into furnace"

# Insert coal as fuel
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=2)
assert coal_inserted, "Failed to insert coal into furnace"

# Wait for the steel to be produced
sleep(10)

# Check if steel plate is in the furnace output
furnace_inventory = inspect_inventory(furnace)
steel_plates = furnace_inventory.get(Prototype.SteelPlate, 0)
assert steel_plates > 0, "No steel plates produced"

print(f"Successfully produced {steel_plates} steel plates")
