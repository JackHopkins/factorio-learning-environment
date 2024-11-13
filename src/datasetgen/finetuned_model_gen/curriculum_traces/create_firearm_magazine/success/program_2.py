

from factorio_instance import *

"""
Step 1: Print recipes
"""
# Print the recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

# Print the recipe for firearm-magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print("Firearm Magazine Recipe:")
print(f"Ingredients: {firearm_magazine_recipe.ingredients}")

"""
Step 2: Craft and place stone furnace
"""
# Move to stone position
stone_position = nearest(Resource.Stone)
print(f"Moving to stone position: {stone_position}")
move_to(stone_position)

# Mine stone for furnace
stone_needed = 5
harvested_stone = harvest_resource(stone_position, stone_needed)
print(f"Harvested {harvested_stone} stone")
assert harvested_stone >= stone_needed, f"Failed to harvest enough stone. Needed: {stone_needed}, Got: {harvested_stone}"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 Stone Furnace")

# Check inventory for stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft Stone Furnace"

# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

"""
Step 3: Mine resources and smelt iron plates
"""
# Move to coal position and harvest
coal_position = nearest(Resource.Coal)
print(f"Moving to coal position: {coal_position}")
move_to(coal_position)

coal_needed = 1
harvested_coal = harvest_resource(coal_position, coal_needed)
print(f"Harvested {harvested_coal} coal")
assert harvested_coal >= coal_needed, f"Failed to harvest enough coal. Needed: {coal_needed}, Got: {harvested_coal}"

# Insert coal into furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted coal into Stone Furnace")

# Move to iron ore position and harvest
iron_ore_position = nearest(Resource.IronOre)
print(f"Moving to iron ore position: {iron_ore_position}")
move_to(iron_ore_position)

iron_ore_needed = 12
harvested_iron_ore = harvest_resource(iron_ore_position, iron_ore_needed)
print(f"Harvested {harvested_iron_ore} iron ore")
assert harvested_iron_ore >= iron_ore_needed, f"Failed to harvest enough iron ore. Needed: {iron_ore_needed}, Got: {harvested_iron_ore}"

# Move back to furnace and insert iron ore
move_to(updated_furnace.position)
insert_item(Prototype.IronOre, updated_furnace, quantity=12)
print("Inserted iron ore into Stone Furnace")

# Wait for smelting
sleep(10)

# Extract iron plates
for _ in range(3):  # Attempt multiple times if needed
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=12)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 12:
        break
    sleep(5)

iron_plates = inventory.get(Prototype.IronPlate, 0)
print(f"Extracted iron plates. Current inventory: {iron_plates} iron plates")
assert iron_plates >= 12, f"Failed to obtain enough iron plates. Needed: 12, Got: {iron_plates}"

"""
Step 4: Craft firearm-magazine
"""
print("Crafting firearm-magazine...")
craft_item(Prototype.FirearmMagazine, 1)

# Verify firearm-magazine in inventory
final_inventory = inspect_inventory()
firearm_magazine_count = final_inventory.get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_count >= 1, f"Failed to craft firearm-magazine. Got: {firearm_magazine_count}"

print(f"Successfully crafted firearm-magazine. Total in inventory: {firearm_magazine_count}")

# Final inventory check
print("Final inventory:")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")
print(f"Firearm-Magazine: {final_inventory.get(Prototype.FirearmMagazine, 0)}")

