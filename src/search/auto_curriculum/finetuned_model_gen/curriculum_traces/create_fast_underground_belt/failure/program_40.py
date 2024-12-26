

"""
1. Craft a stone furnace
2. Place and fuel the furnace
3. Smelt iron plates
4. Craft iron gear wheels
5. Craft underground belt
6. Craft fast underground belt
"""

# Step 1: Craft a stone furnace
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=6)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have the furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

# Step 2: Place and fuel the furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Insert coal into furnace
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, 5)

# Verify coal was inserted
coal_in_furnace = furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace"

# Step 3: Smelt iron plates
# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=49)

# Insert iron ore and smelt in batches
for _ in range(5):
    insert_item(Prototype.IronOre, furnace, 10)
    sleep(5)
    extract_item(Prototype.IronPlate, furnace.position, 10)

# Final extraction to ensure all plates are collected
extract_item(Prototype.IronPlate, furnace.position, 5)

# Verify we have enough iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 49, f"Insufficient iron plates: {inventory.get(Prototype.IronPlate)}"

# Step 4: Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 40)

# Verify we have iron gear wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 40, "Failed to craft iron gear wheels"

# Step 5: Craft underground belt
craft_item(Prototype.UndergroundBelt, 2)

# Verify we have underground belts
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 2, "Failed to craft underground belts"

# Step 6: Craft fast underground belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify we have fast underground belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast underground belt"

# Final verification
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Did not achieve goal of crafting fast underground belt"

