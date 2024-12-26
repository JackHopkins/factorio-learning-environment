
from factorio_instance import *

"""
Step 1: Craft a stone furnace
- We need to mine stone and craft a stone furnace
"""
# Check recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace recipe: {stone_furnace_recipe}")

# Find and mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
stone_mined = harvest_resource(stone_position, quantity=5)
print(f"Mined {stone_mined} stone")
assert stone_mined >= 5, f"Failed to mine enough stone. Got {stone_mined}"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Verify stone furnace in inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 2: Mine iron ore
- We need to mine at least 10 iron ore
"""
# Find and mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
iron_ore_mined = harvest_resource(iron_ore_position, quantity=10)
print(f"Mined {iron_ore_mined} iron ore")
assert iron_ore_mined >= 10, f"Failed to mine enough iron ore. Got {iron_ore_mined}"

"""
Step 3: Place and fuel the stone furnace
- We need to place the stone furnace and fuel it with coal
"""
# Place the stone furnace
furnace_position = Position(x=0, y=0)  # Assuming we place it at the origin
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at {furnace.position}")

# Find and mine coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
coal_mined = harvest_resource(coal_position, quantity=5)
print(f"Mined {coal_mined} coal")
assert coal_mined >= 5, f"Failed to mine enough coal. Got {coal_mined}"

# Insert coal into the furnace
move_to(furnace_position)
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the stone furnace")

"""
Step 4: Smelt iron ore into iron plates
- We need to smelt the iron ore into iron plates
"""
# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
print("Inserted iron ore into the stone furnace")

# Wait for smelting to complete (assuming 0.7 seconds per iron plate)
smelting_time = 0.7 * 10
sleep(smelting_time)

# Extract iron plates
# Note: We can extract more than 5 at a time if needed
for _ in range(2):  # Attempt to extract multiple times if needed
    extracted = extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    if extracted:
        print(f"Extracted {extracted} iron plates")
        break
    sleep(5)  # Wait a bit more if not all plates are ready

# Verify iron plates in inventory
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to produce enough iron plates. Got {iron_plates}"
print(f"Successfully produced {iron_plates} iron plates")

print("Iron plate production set up successfully!")
