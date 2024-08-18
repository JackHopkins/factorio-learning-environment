from factorio_instance import *

def craft_and_place_inserters(num_inserters: int = 5) -> bool:
    # Step 1: Gather resources
    iron_ore_needed = num_inserters * 4  # 4 iron plates per inserter
    while inspect_inventory().get(Prototype.IronPlate, 0) < iron_ore_needed:
        harvest_resource(nearest(Resource.IronOre), 10)
        furnace = place_entity(Prototype.StoneFurnace, position=nearest(Resource.IronOre))
        insert_item(Prototype.IronOre, furnace, 10)
        sleep(10)  # Wait for smelting
        extract_item(Prototype.IronPlate, furnace.position, 10)

    # Step 2: Craft intermediate components
    while inspect_inventory().get(Prototype.IronGearWheel, 0) < num_inserters:
        craft_item(Prototype.IronGearWheel, 1)
    
    while inspect_inventory().get(Prototype.CopperCable, 0) < num_inserters * 3:
        craft_item(Prototype.CopperCable, 1)
    
    while inspect_inventory().get(Prototype.ElectronicCircuit, 0) < num_inserters:
        craft_item(Prototype.ElectronicCircuit, 1)

    # Step 3: Craft inserters
    for _ in range(num_inserters):
        craft_item(Prototype.BurnerInserter, 1)

    # Step 4 & 5: Place inserters
    placed_inserters = 0
    for _ in range(num_inserters):
        placement_position = place_entity_next_to(Prototype.BurnerInserter, spacing=2).position
        if placement_position:
            placed_inserters += 1
        else:
            print(f"Failed to place inserter {_ + 1}")

    if placed_inserters != num_inserters:
        raise RuntimeError(f"Failed to place all inserters. Placed {placed_inserters} out of {num_inserters}")

    # Step 6: Power the inserters (Burner inserters don't need external power)

    # Step 7: Test the setup
    print("Inserters placed successfully. Please check their functionality manually.")

    return True
