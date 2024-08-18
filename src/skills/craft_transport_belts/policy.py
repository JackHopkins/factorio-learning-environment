from factorio_instance import *
def craft_transport_belts():
    # Check if we have enough iron plates
    inventory = inspect_inventory()
    iron_plates = inventory.get(Prototype.IronPlate, 0)
    
    if iron_plates < 15:
        print("Not enough iron plates. Mining and smelting more.")
        # Mine and smelt more iron
        while iron_plates < 15:
            harvest_resource(nearest(Resource.IronOre), 5)
            move_to(nearest(Prototype.StoneFurnace))
            insert_item(Prototype.IronOre, get_entity(Prototype.StoneFurnace, nearest(Prototype.StoneFurnace)), 5)
            sleep(10)  # Wait for smelting
            extract_item(Prototype.IronPlate, nearest(Prototype.StoneFurnace), 5)
            inventory = inspect_inventory()
            iron_plates = inventory.get(Prototype.IronPlate, 0)
    
    # Craft iron gear wheels
    print("Crafting iron gear wheels.")
    for _ in range(5):
        craft_item(Prototype.IronGearWheel, 2)
    
    # Craft transport belts
    print("Crafting transport belts.")
    for _ in range(5):
        craft_item(Prototype.TransportBelt, 1)
    
    # Verify completion
    inventory = inspect_inventory()
    transport_belts = inventory.get(Prototype.TransportBelt, 0)
    
    if transport_belts >= 5:
        print("Successfully crafted 5 transport belts!")
    else:
        raise Exception(f"Failed to craft 5 transport belts. Only crafted {transport_belts}.")
