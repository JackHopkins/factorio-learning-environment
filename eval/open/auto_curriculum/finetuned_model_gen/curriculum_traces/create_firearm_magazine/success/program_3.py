

from instance import *

"""
Step 1: Craft a stone furnace
- Gather stone
- Craft stone furnace
"""
# Gather stone for crafting the stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=9)

# Verify we have enough stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 9, f"Insufficient stone, expected at least 9 but got {inventory.get(Prototype.Stone)}"

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify we have crafted the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 2: Set up and fuel the furnace
- Place the furnace
- Gather coal
- Fuel the furnace
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Gather coal for fueling the furnace
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=6)

# Verify we have enough coal
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 6, f"Insufficient coal, expected at least 6 but got {inventory.get(Prototype.Coal)}"

# Move back to the furnace and fuel it
move_to(furnace.position)
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=6)
assert updated_furnace.fuel.get(Prototype.Coal) >= 6, "Failed to fuel furnace"

"""
Step 3: Smelt iron plates
- Mine iron ore
- Smelt iron ore into plates
"""
# Mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=12)

# Verify we have enough iron ore
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 12, f"Insufficient iron ore, expected at least 12 but got {inventory.get(Prototype.IronOre)}"

# Move back to the furnace and insert iron ore
move_to(furnace.position)
insert_item(Prototype.IronOre, updated_furnace, quantity=12)

# Wait for smelting to complete
sleep(15)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=12)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate) >= 9:
        break
    sleep(5)

# Verify we have enough iron plates
assert inventory.get(Prototype.IronPlate) >= 9, f"Failed to obtain sufficient iron plates, expected at least 9 but got {inventory.get(Prototype.IronPlate)}"

"""
Step 4: Craft firearm-magazine
"""
# Craft firearm-magazine
craft_item(Prototype.FirearmMagazine, quantity=1)

# Verify we have crafted the firearm-magazine
inventory = inspect_inventory()
assert inventory.get(Prototype.FirearmMagazine) >= 1, "Failed to craft firearm-magazine"

