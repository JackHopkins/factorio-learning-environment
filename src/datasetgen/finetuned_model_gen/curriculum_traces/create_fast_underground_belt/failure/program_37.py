

from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the entities we need to craft.
"""
# Print recipes for the required entities
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Burner Mining Drill: 3 iron gear wheels, 3 iron plates, 1 stone furnace (crafted)")
print("Burner Inserter: 1 iron gear wheel, 1 iron plate")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (crafts 2)")
print("Underground Belt: 5 iron gear wheels, 10 iron plates (crafts 2)")
print("Iron Gear Wheel: 2 iron plates")
print("Fast Underground Belt: 1 underground belt, 20 iron gear wheels")

print("Total iron plates needed: 76")

"""
Step 2: Craft stone furnace. We need to craft a stone furnace. There are no stone furnaces on the map or in our inventory, so we need to gather stone and craft one.
"""
# Gather stone for the furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=6)

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify that we have crafted the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft Stone Furnace"

"""
Step 3: Set up iron mining and smelting. We need to set up a burner mining drill to mine iron ore and a stone furnace to smelt it into iron plates. We also need to fuel these entities with coal.
"""
# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Craft the burner mining drill (3 iron gear wheels, 3 iron plates, 1 stone furnace)
craft_item(Prototype.BurnerMiningDrill, 1)

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)

# Find the nearest coal patch and harvest some coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)

# Insert coal into the burner mining drill
insert_item(Prototype.Coal, drill, 5)

# Move back to the iron ore position
move_to(iron_ore_position)

# Place the stone furnace next to the burner mining drill
furnace = place_entity_next_to(Prototype.StoneFurnace, direction=Direction.DOWN, reference_position=iron_ore_position)

# Insert coal into the stone furnace
insert_item(Prototype.Coal, furnace, 5)

# Connect the drill to the furnace using a burner inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, direction=Direction.UP, reference_position=furnace.position)
inserter = rotate_entity(inserter, Direction.DOWN)
insert_item(Prototype.Coal, inserter, 5)

"""
Step 4: Craft transport belts. We need to craft 4 transport belts using 2 iron gear wheels and 2 iron plates.
"""
# Move to the furnace to get iron plates
move_to(furnace.position)

# Extract iron plates from the furnace
extract_item(Prototype.IronPlate, furnace.position, quantity=8)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 2)

# Craft transport belts
craft_item(Prototype.TransportBelt, 4)

# Verify that we have crafted the transport belts
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 4, "Failed to craft Transport Belts"

"""
Step 5: Craft underground belts. We need to craft 2 underground belts using 5 iron gear wheels and 10 iron plates.
"""
# Extract more iron plates from the furnace
extract_item(Prototype.IronPlate, furnace.position, quantity=20)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 5)

# Craft underground belts
craft_item(Prototype.UndergroundBelt, 2)

# Verify that we have crafted the underground belts
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 2, "Failed to craft Underground Belts"

"""
Step 6: Craft fast underground belt. We need to craft 1 fast underground belt using 1 underground belt and 20 iron gear wheels.
"""
# Extract more iron plates from the furnace
extract_item(Prototype.IronPlate, furnace.position, quantity=40)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 20)

# Craft fast underground belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify that we have crafted the fast underground belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft Fast Underground Belt"

print("Successfully crafted Fast Underground Belt!")

