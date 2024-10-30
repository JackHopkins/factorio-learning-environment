# Check if we have enough copper plates in the inventory
inventory = inspect_inventory()
copper_plates = inventory.get(Prototype.CopperPlate, 0)
    
# Calculate the number of copper plates needed (2 cables per plate)
plates_needed = quantity // 2 + (1 if quantity % 2 != 0 else 0)
    
if copper_plates < plates_needed:
    print(f"Not enough copper plates. Have {copper_plates}, need {plates_needed}")
    return False
    
# Craft the copper cables
cables_crafted = 0
while cables_crafted < quantity:
    craft_success = craft_item(Prototype.CopperCable, 2)
    if not craft_success:
        print(f"Failed to craft copper cables. Crafted {cables_crafted} out of {quantity}")
        raise RuntimeError(f"Failed to craft copper cables. Crafted {cables_crafted} out of {quantity}")
    cables_crafted += 2
    
print(f"Successfully crafted {cables_crafted} copper cables")