Sure! The objective requires us to create fast-transport-belt.
The final success of the policy will be checked by looking if fast-transport-belt is in inventory
Here's a policy that achieves the objective of creating fast-transport-belt:

"""
from factorio_instance import *

"""
Step 1: Craft a stone furnace. We need 5 stone for one furnace.
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Verify we got the stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have the furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

print("Successfully crafted stone furnace")

"""
Step 2: Print recipes. We need to print the recipes for transport-belt and fast-transport-belt.
"""
print("Recipes:")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Fast Transport Belt: 1 transport belt, 1 iron gear wheel")

"""
Step 3: Craft a burner mining drill. 
- We need 3 iron gear wheels, 3 iron plates, and 1 stone furnace. 
- We need to mine iron ore and smelt it into iron plates.
"""
# Get stone for the additional furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft additional stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have the furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft additional stone furnace"

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)

# Place furnace near player
player_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_pos[0]+2, y=player_pos[1]))

# Insert fuel into furnace
insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore and extract plates
insert_item(Prototype.IronOre, furnace, quantity=10)
sleep(5)
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

# Verify iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 10, "Failed to get enough iron plates"

# Craft gear wheel
craft_item(Prototype.IronGearWheel, 3)

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, 1)

# Verify we have the drill
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner mining drill"

print("Successfully crafted burner mining drill")

"""
Step 4: Set up iron plate production.
- Place the burner mining drill on an iron ore patch.
- Place a stone furnace next to the drill.
- Mine coal for fuel and iron ore for smelting.
"""
# Find and move to iron ore patch
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)

# Place burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_pos)
print(f"Placed burner mining drill at {drill.position}")

# Place furnace next to drill
furnace = place_entity_next_to(Prototype.StoneFurnace, drill.position, direction=Direction.RIGHT)
print(f"Placed stone furnace at {furnace.position}")

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)

# Insert coal into drill and furnace
move_to(drill.position)
insert_item(Prototype.Coal, drill, quantity=10)
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=10)

# Verify setup
inspection = inspect_entities(drill.position, radius=5)
assert inspection.get_entity(Prototype.BurnerMiningDrill), "Failed to place burner mining drill"
assert inspection.get_entity(Prototype.StoneFurnace), "Failed to place stone furnace"

print("Iron plate production setup complete")

"""
Step 5: Craft transport belts.
- We need 1 iron gear wheel and 1 iron plate per transport belt.
- Craft at least 1 transport belt.
"""
# Get initial iron plates
sleep(10)
move_to(furnace.position)
extract_item(Prototype.IronPlate, furnace.position, quantity=5)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 1)

# Craft transport belts
craft_item(Prototype.TransportBelt, 1)

# Verify transport belts
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 1, "Failed to craft transport belts"

print("Successfully crafted transport belts")

"""
Step 6: Craft fast transport belts.
- We need 1 transport belt and 1 iron gear wheel per fast transport belt.
- Craft at least 1 fast transport belt.
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 1)

# Craft fast transport belts
craft_item(Prototype.FastTransportBelt, 1)

# Verify fast transport belts
inventory = inspect_inventory()
assert inventory.get(Prototype.FastTransportBelt) >= 1, "Failed to craft fast transport belts"

print("Successfully crafted fast transport belts")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

assert final_inventory.get(Prototype.FastTransportBelt) >= 1, "Final inventory doesn't contain required fast transport belts"

print("Objective completed successfully")
"""