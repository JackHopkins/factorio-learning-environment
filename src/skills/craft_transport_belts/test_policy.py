from factorio_instance import *

def test_craft_transport_belts():
    # Check the player's inventory for transport belts
    inventory = inspect_inventory()
    transport_belts = inventory.get(Prototype.TransportBelt, 0)

    # Verify that at least 5 transport belts have been crafted
    if transport_belts >= 5:
        print("Objective completed: Crafted 5 transport belts")
        return True
    else:
        print(f"Objective not completed: Only {transport_belts} transport belts crafted. Need at least 5.")
        return False

    # Additional checks (optional, but can provide more detailed feedback)
    iron_plates = inventory.get(Prototype.IronPlate, 0)
    iron_gears = inventory.get(Prototype.IronGearWheel, 0)

    if iron_plates < 5 or iron_gears < 5:
        print("Hint: Make sure you have enough iron plates and iron gear wheels to craft transport belts.")
        print(f"Current inventory: {iron_plates} iron plates, {iron_gears} iron gear wheels")

    # Check if the player knows how to craft transport belts
    transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
    if not transport_belt_recipe:
        print("Hint: Make sure you have unlocked the recipe for transport belts.")

    return False
