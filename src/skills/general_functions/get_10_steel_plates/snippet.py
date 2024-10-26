# Check current inventory for coal - Dependency Phase
inventory = inspect_inventory()
coal_needed = max(60 - inventory.get(Prototype.Coal, 0), 0)

if coal_needed > 0:
    # Find and mine coal
    coal_pos = nearest(Resource.Coal)
    move_to(coal_pos)
    harvest_resource(coal_pos, quantity=coal_needed)

# Need 5 iron plates per steel plate for dependency
iron_plates_needed = 6 * 5

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=iron_plates_needed)

# Get stone for furnace if needed
inventory = inspect_inventory()
if inventory.get(Prototype.StoneFurnace) == 0:
    stone_pos = nearest(Resource.Stone)
    move_to(stone_pos)
    harvest_resource(stone_pos, quantity=5)
    craft_item(Prototype.StoneFurnace, 1)

# First smelt iron ore into plates
current_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_pos[0] + 2, y=current_pos[1]))

# Smelt iron ore into plates in batches
remaining_ore = iron_plates_needed
while remaining_ore > 0:
    batch_size = min(20, remaining_ore)
    insert_item(Prototype.Coal, furnace, 10)
    insert_item(Prototype.IronOre, furnace, batch_size)
    sleep(15)
    extract_item(Prototype.IronPlate, furnace.position, batch_size)
    remaining_ore -= batch_size

# Now smelt iron plates into steel in batches
remaining_plates = iron_plates_needed
while remaining_plates > 0:
    batch_size = min(20, remaining_plates)
    insert_item(Prototype.Coal, furnace, 10)
    insert_item(Prototype.IronPlate, furnace, batch_size)
    sleep(25)
    extract_item(Prototype.SteelPlate, furnace.position, batch_size // 5)
    remaining_plates -= batch_size

pickup_entity(Prototype.StoneFurnace, furnace.position)

# Verify dependency phase
inventory = inspect_inventory()
assert inventory.get(
    Prototype.SteelPlate) >= 6, f"Failed to obtain required steel plates for dependency, only have {inventory.get(Prototype.SteelPlate)}"

# Main Implementation Phase
inventory = inspect_inventory()
coal_needed = max(40 - inventory.get(Prototype.Coal, 0), 0)

if coal_needed > 0:
    coal_pos = nearest(Resource.Coal)
    move_to(coal_pos)
    harvest_resource(coal_pos, quantity=coal_needed)

# Check current inventory for steel plates
inventory = inspect_inventory()
steel_plates_needed = max(10 - inventory.get(Prototype.SteelPlate, 0), 0)

if steel_plates_needed > 0:
    iron_plates_needed = steel_plates_needed * 5

    iron_pos = nearest(Resource.IronOre)
    move_to(iron_pos)
    harvest_resource(iron_pos, quantity=iron_plates_needed)

    inventory = inspect_inventory()
    if inventory.get(Prototype.StoneFurnace) == 0:
        stone_pos = nearest(Resource.Stone)
        move_to(stone_pos)
        harvest_resource(stone_pos, quantity=5)
        craft_item(Prototype.StoneFurnace, 1)

    current_pos = inspect_entities().player_position
    furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_pos[0] + 2, y=current_pos[1]))

    # Smelt iron ore in batches
    remaining_ore = iron_plates_needed
    while remaining_ore > 0:
        batch_size = min(20, remaining_ore)
        insert_item(Prototype.Coal, furnace, 10)
        insert_item(Prototype.IronOre, furnace, batch_size)
        sleep(15)
        extract_item(Prototype.IronPlate, furnace.position, batch_size)
        remaining_ore -= batch_size

    # Smelt iron plates into steel in batches
    remaining_plates = iron_plates_needed
    while remaining_plates > 0:
        batch_size = min(20, remaining_plates)
        insert_item(Prototype.Coal, furnace, 10)
        insert_item(Prototype.IronPlate, furnace, batch_size)
        sleep(25)
        extract_item(Prototype.SteelPlate, furnace.position, batch_size // 5)
        remaining_plates -= batch_size

    pickup_entity(Prototype.StoneFurnace, furnace.position)

# Final verification
inventory = inspect_inventory()
assert inventory.get(
    Prototype.SteelPlate) >= 10, f"Failed to obtain required steel plates, only have {inventory.get(Prototype.SteelPlate)}"