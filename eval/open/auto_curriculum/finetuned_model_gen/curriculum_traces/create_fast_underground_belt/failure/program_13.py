

from instance import *

"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to craft a fast-underground-belt. To do this, we need to mine iron ore, smelt it into iron plates, and then craft the necessary components. We'll set up a temporary mining and smelting operation to produce the iron plates we need.
"""

"""
Step 1: Print recipes
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe
print("Recipe for fast-underground-belt:")
print(f"Ingredients: {fast_underground_belt_recipe.ingredients}")

# Get the recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipe
print("Recipe for iron gear wheel:")
print(f"Ingredients: {iron_gear_wheel_recipe.ingredients}")

# Get the recipe for underground belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipe
print("Recipe for underground belt:")
print(f"Ingredients: {underground_belt_recipe.ingredients}")

# Get the recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Print the recipe
print("Recipe for transport belt:")
print(f"Ingredients: {transport_belt_recipe.ingredients}")

"""
Step 2: Prepare mining setup
- Craft stone furnace
- Craft burner mining drill
- Craft burner inserters
- Craft wooden chest
- Gather coal for fuel
"""
# Gather stone for furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Gather resources for burner mining drill
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=9)

# Craft iron gear wheels for burner mining drill
craft_item(Prototype.IronGearWheel, quantity=3)

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Craft burner inserters (2 for our setup)
craft_item(Prototype.BurnerInserter, quantity=2)

# Gather wood for chest
wood_position = nearest(Resource.Wood)
move_to(wood_position)
harvest_resource(wood_position, quantity=2)

# Craft wooden chest
craft_item(Prototype.WoodenChest, quantity=1)

# Gather coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=20)

"""
Step 3: Set up iron ore mining and smelting
- Place burner mining drill
- Place stone furnace
- Place burner inserters
- Place wooden chest
- Fuel all entities
"""
# Place burner mining drill
iron_patch = get_resource_patch(Resource.IronOre, iron_position)
move_to(iron_patch.bounding_box.center)
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_patch.bounding_box.center)

# Place stone furnace
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.RIGHT, spacing=1)

# Place burner inserter for furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.RIGHT, spacing=0)
furnace_inserter = rotate_entity(furnace_inserter, direction=Direction.LEFT)

# Place wooden chest
chest = place_entity_next_to(Prototype.WoodenChest, reference_position=furnace_inserter.position, direction=Direction.RIGHT, spacing=0)

# Place burner inserter for chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=chest.position, direction=Direction.RIGHT, spacing=0)
chest_inserter = rotate_entity(chest_inserter, direction=Direction.LEFT)

# Fuel entities
insert_item(Prototype.Coal, drill, quantity=10)
insert_item(Prototype.Coal, furnace, quantity=10)
insert_item(Prototype.Coal, furnace_inserter, quantity=5)
insert_item(Prototype.Coal, chest_inserter, quantity=5)

"""
Step 4: Gather and smelt iron plates
- Wait for iron plates to be produced
- Collect iron plates
"""
# Wait for iron plates to be produced
sleep(30)

# Move to the chest to collect iron plates
move_to(chest.position)

# Collect iron plates
iron_plates_needed = 16
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, chest.position, quantity=iron_plates_needed)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= iron_plates_needed:
        break
    sleep(10)

current_iron_plates = inventory.get(Prototype.IronPlate, 0)
print(f"Collected iron plates: {current_iron_plates}")
assert current_iron_plates >= iron_plates_needed, f"Failed to collect enough iron plates. Needed: {iron_plates_needed}, but got: {current_iron_plates}"

"""
Step 5: Craft fast-underground-belt
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=6)

# Craft transport belt
craft_item(Prototype.TransportBelt, quantity=1)

# Craft underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)

# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

"""
Step 6: Verify the result
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print(f"Successfully crafted fast-underground-belt. Current inventory: {final_inventory}")

