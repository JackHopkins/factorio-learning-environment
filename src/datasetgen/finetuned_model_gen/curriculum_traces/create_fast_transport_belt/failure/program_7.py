

from factorio_instance import *

"""
Objective: Create a fast-transport-belt from scratch

Steps:
1. Craft 2 stone-furnaces
2. Craft 1 burner-mining-drill
3. Gather iron ore
4. Set up mining and smelting operation
5. Craft iron plates
6. Craft iron gear wheels
7. Craft transport belts
8. Craft fast-transport-belt
"""

"""
Step 1: Craft 2 stone-furnaces
- We need to mine stone and craft furnaces
"""
# Move to the nearest stone patch
stone_position = nearest(Resource.Stone)
move_to(stone_position)

# Mine 12 stone (5 for each furnace, 2 extra for safety)
harvested_stone = harvest_resource(stone_position, quantity=12)
print(f"Harvested {harvested_stone} stone")
assert harvested_stone >= 12, f"Failed to harvest enough stone, got {harvested_stone}"

# Craft 2 stone-furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Verify we have the stone-furnaces
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")
assert inventory.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft 2 stone-furnaces"

"""
Step 2: Craft 1 burner-mining-drill
- We need to mine more stone for the drill's furnace
- We need to mine iron ore for plates and gears
"""
# Mine additional stone for the drill's furnace
harvested_stone = harvest_resource(stone_position, quantity=5)
print(f"Harvested additional {harvested_stone} stone")
assert harvested_stone >= 5, f"Failed to harvest enough additional stone, got {harvested_stone}"

# Move to the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Mine iron ore for plates and gears (need at least 9 iron ore for 3 plates for gears)
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=9)
print(f"Harvested {harvested_iron_ore} iron ore")
assert harvested_iron_ore >= 9, f"Failed to harvest enough iron ore, got {harvested_iron_ore}"

# Craft a third stone-furnace for the drill
craft_item(Prototype.StoneFurnace, quantity=1)

# Craft 2 iron gear wheels (need 4 iron plates)
craft_item(Prototype.IronGearWheel, quantity=2)

# Craft 1 burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Verify we have the burner-mining-drill
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")
assert inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft 1 burner-mining-drill"

"""
Step 3: Gather iron ore
- We need to mine more iron ore
"""
# Move to the nearest iron ore patch
move_to(iron_ore_position)

# Mine iron ore (need at least 31 iron ore for all steps)
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=31)
print(f"Harvested {harvested_iron_ore} iron ore")
assert harvested_iron_ore >= 31, f"Failed to harvest enough iron ore, got {harvested_iron_ore}"

# Verify we have enough iron ore
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")
assert inventory.get(Prototype.IronOre, 0) >= 31, "Insufficient iron ore for the next steps"

"""
Step 4: Set up mining and smelting operation
- Place the burner-mining-drill and stone-furnaces
- Fuel them with coal
"""
# Move near the iron ore patch
move_to(iron_ore_position)

# Place the burner-mining-drill
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed burner-mining-drill at {drill.position}")

# Move near the drill to place furnaces
move_to(drill.position)

# Place the first stone-furnace next to the drill
furnace1 = place_entity_next_to(Prototype.StoneFurnace, drill.position, direction=Direction.RIGHT)
print(f"Placed first stone-furnace at {furnace1.position}")

# Place the second stone-furnace for iron plates
furnace2 = place_entity_next_to(Prototype.StoneFurnace, furnace1.position, direction=Direction.RIGHT)
print(f"Placed second stone-furnace at {furnace2.position}")

# Move to the nearest coal patch
coal_position = nearest(Resource.Coal)
move_to(coal_position)

# Mine coal for fuel (get at least 5 for each entity)
harvested_coal = harvest_resource(coal_position, quantity=15)
print(f"Harvested {harvested_coal} coal")
assert harvested_coal >= 15, f"Failed to harvest enough coal, got {harvested_coal}"

# Insert coal into the drill
updated_drill = insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted coal into burner-mining-drill")

# Insert coal into the first furnace
updated_furnace1 = insert_item(Prototype.Coal, furnace1, quantity=5)
print("Inserted coal into first stone-furnace")

# Insert coal into the second furnace
updated_furnace2 = insert_item(Prototype.Coal, furnace2, quantity=5)
print("Inserted coal into second stone-furnace")

"""
Step 5: Craft iron plates
- Use the smelting operation to create iron plates
"""
# Wait for the drill to mine enough iron ore
sleep(10)  # Wait for 10 seconds

# Extract iron ore from the drill
drill_inventory = inspect_inventory(updated_drill)
iron_ore_in_drill = drill_inventory.get(Prototype.IronOre, 0)
print(f"Extracting {iron_ore_in_drill} iron ore from the drill")
extract_item(Prototype.IronOre, updated_drill.position, quantity=iron_ore_in_drill)

# Insert iron ore into the furnaces
insert_item(Prototype.IronOre, updated_furnace1, quantity=iron_ore_in_drill//2)
insert_item(Prototype.IronOre, updated_furnace2, quantity=iron_ore_in_drill//2)

# Wait for the smelting process
sleep(15)  # Wait for 15 seconds

# Extract iron plates from the furnaces
for _ in range(3):
    extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=iron_ore_in_drill//2)
    extract_item(Prototype.IronPlate, updated_furnace2.position, quantity=iron_ore_in_drill//2)
    sleep(5)

# Verify we have enough iron plates
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
print(f"Current inventory: {inventory}")
assert iron_plates >= 31, f"Failed to obtain enough iron plates, got {iron_plates}"

"""
Step 6: Craft iron gear wheels
- Use iron plates to craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=7)

# Verify we have the iron gear wheels
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
print(f"Current inventory: {inventory}")
assert iron_gear_wheels >= 7, f"Failed to craft enough iron gear wheels, got {iron_gear_wheels}"

"""
Step 7: Craft transport belts
- Use iron gear wheels and plates to craft transport belts
"""
craft_item(Prototype.TransportBelt, quantity=1)

# Verify we have the transport belts
inventory = inspect_inventory()
transport_belts = inventory.get(Prototype.TransportBelt, 0)
print(f"Current inventory: {inventory}")
assert transport_belts >= 1, f"Failed to craft enough transport belts, got {transport_belts}"

"""
Step 8: Craft fast-transport-belt
- Use transport belts to craft fast-transport-belt
"""
craft_item(Prototype.FastTransportBelt, quantity=1)

# Verify we have the fast-transport-belt
inventory = inspect_inventory()
fast_transport_belts = inventory.get(Prototype.FastTransportBelt, 0)
print(f"Current inventory: {inventory}")
assert fast_transport_belts >= 1, f"Failed to craft fast-transport-belt, got {fast_transport_belts}"

print("Successfully crafted a fast-transport-belt!")

