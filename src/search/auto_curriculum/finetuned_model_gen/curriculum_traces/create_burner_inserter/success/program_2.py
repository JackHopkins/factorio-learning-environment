

from factorio_instance import *

"""
Craft a burner-inserter from scratch.

Planning:
We need to craft a burner-inserter, which requires:
- 1 iron gear wheel
- 1 iron plate

In total, we need at least 3 iron plates.

We'll need to:
- Mine iron ore
- Smelt iron ore into iron plates
- Craft iron gear wheel
- Craft burner-inserter

For mining and smelting, we'll need:
- Stone furnace (requires 5 stone)
- Coal for fuel (at least 2, 1 for the furnace, 1 for the inserter)

Steps:
1. Print recipes
2. Gather resources
3. Craft and place furnace
4. Smelt iron plates
5. Craft iron gear wheel
6. Craft burner-inserter
"""

# Step 1: Print recipes
print("Recipes:")
print("Burner Inserter: 1 iron gear wheel, 1 iron plate")
print("Iron Gear Wheel: 2 iron plates")

# Step 2: Gather resources
resources_to_gather = [
    (Resource.IronOre, 6),  # 3 iron plates + 1 extra for safety
    (Resource.Stone, 5),    # for furnace
    (Resource.Coal, 2)      # 1 for furnace, 1 for inserter
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Step 3: Craft and place furnace
craft_item(Prototype.StoneFurnace, 1)
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

# Step 4: Smelt iron plates
insert_item(Prototype.Coal, furnace, 1)
insert_item(Prototype.IronOre, furnace, 6)
sleep(5)
extract_item(Prototype.IronPlate, furnace.position, 6)

# Step 5: Craft iron gear wheel
craft_item(Prototype.IronGearWheel, 1)

# Step 6: Craft burner-inserter
craft_item(Prototype.BurnerInserter, 1)

# Verify we have the burner-inserter
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerInserter, 0) >= 1, "Failed to craft burner-inserter"
print("Successfully crafted burner-inserter")

