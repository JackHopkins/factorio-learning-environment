from factorio_instance import *

"""
Main Objective: We need create an automated copper plate burner mine that mines copper ore to a fueled furnace placed at the drill's drop position that will smelt plates and send them to a chest placed further away. First place down the drill, then place the furnace with a inserter next to it, then a chest with a rotated inserter next to it and then connect the pickup pos of chest inserter with the drop pos of furnace inserter. The final setup should be checked by looking if the chest has any copper plates in it
"""



"""
Step 1: Place the burner mining drill and furnace. We need to:
- Move to a copper ore patch
- Place the burner mining drill on the copper ore
- Place a stone furnace at the drill's drop position
- Fuel both the mining drill and the furnace with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest copper ore patch and move to it
copper_ore_position = nearest(Resource.CopperOre)
move_to(copper_ore_position)
print(f"Moved to copper ore patch at {copper_ore_position}")

# Place the burner mining drill on the copper ore
drill = place_entity(Prototype.BurnerMiningDrill, position=copper_ore_position)
print(f"Placed burner mining drill at {drill.position}")

# Get the drop position of the burner mining drill
drill_drop_position = drill.drop_position
print(f"Drill drop position: {drill_drop_position}")

# Place a stone furnace at the drill's drop position
furnace = place_entity(Prototype.StoneFurnace, position=drill_drop_position)
print(f"Placed stone furnace at {furnace.position}")

# Fuel both the mining drill and the furnace with coal
insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted 5 coal into burner mining drill")

insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted 5 coal into stone furnace")

# Verify that both entities are placed correctly
entities = get_entities({Prototype.BurnerMiningDrill, Prototype.StoneFurnace})
assert len(entities) == 2, f"Expected 2 entities (drill and furnace), but found {len(entities)}"
print("Successfully placed and fueled burner mining drill and stone furnace")

# Print current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")


"""
Step 2: Set up the furnace inserter. We need to:
- Place a burner inserter next to the furnace (no rotation needed as we want it to take from the furnace)
- Fuel the inserter with coal
"""
# Placeholder 2

"""
Step 3: Set up the chest and chest inserter. We need to:
- Place the wooden chest further away from the furnace
- Place a burner inserter next to the chest
- Rotate the chest inserter to put items into the chest
- Fuel the chest inserter with coal
"""
# Placeholder 3

"""
Step 4: Connect the inserters with transport belts. We need to:
- Connect the pickup position of the chest inserter with the drop position of the furnace inserter using transport belts
"""
# Placeholder 4

"""
Step 5: Check the setup. We need to:
- Wait for 30 seconds to allow the system to operate
- Check if the wooden chest contains any copper plates
##
"""
# Placeholder 5