from factorio_instance import *

def craft_copper_wire_from_plates(quantity: int = 20) -> bool:
    # Check if we have enough copper plates in the inventory
    inventory = inspect_inventory()
    copper_plates = inventory.get(Prototype.CopperPlate, 0)
    required_plates = quantity // 2  # Each copper wire requires 0.5 copper plates

    if copper_plates < required_plates:
        print(f"Not enough copper plates. Have {copper_plates}, need {required_plates}")
        return False

    # Craft the copper wire
    crafted = craft_item(Prototype.CopperCable, quantity)

    if not crafted:
        print(f"Failed to craft {quantity} copper wire")
        return False

    # Verify the crafting result
    updated_inventory = inspect_inventory()
    crafted_wire = updated_inventory.get(Prototype.CopperCable, 0)

    if crafted_wire < quantity:
        print(f"Crafting incomplete. Only crafted {crafted_wire} out of {quantity} copper wire")
        return False

    print(f"Successfully crafted {quantity} copper wire")
    return True
