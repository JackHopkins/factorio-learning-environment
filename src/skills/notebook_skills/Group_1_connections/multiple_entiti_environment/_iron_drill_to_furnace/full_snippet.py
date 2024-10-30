from factorio_instance import *

"""
Main Objective: We need to set up iron ore transport from a a drill to a furnace. You need to send the correct ore to the furnace smelting that ore. To see which ore a drill is mining, find the resource patch it's closest to.  The final setup should be checked by looking if the furnace where we sent iron to has more iron ore than starting
"""



"""
Step 1: Identify the iron ore mining drill and furnace. We need to:
- Determine which of the two burner mining drills is closest to an iron ore patch
- Confirm that the furnace at position (0.0, 5.0) is the one processing iron ore
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5}
#Step Execution

from factorio_instance import *

# Get all burner mining drills on the map
burner_drills = get_entities({Prototype.BurnerMiningDrill})
print(f"Found {len(burner_drills)} burner mining drills")

# Find the drill that's closest to an iron ore patch
iron_drill = None
shortest_distance = float('inf')

for drill in burner_drills:
    iron_ore_position = nearest(Resource.IronOre)
    distance = ((drill.position.x - iron_ore_position.x)**2 + (drill.position.y - iron_ore_position.y)**2)**0.5
    if distance < shortest_distance:
        shortest_distance = distance
        iron_drill = drill

if iron_drill is None:
    raise Exception("Could not find a drill close to iron ore")

print(f"The drill closest to iron ore is at position {iron_drill.position}")

# Get the furnace at position (0.0, 5.0)
furnaces = get_entities({Prototype.StoneFurnace})
iron_furnace = next((f for f in furnaces if f.position.x == 0.0 and f.position.y == 5.0), None)

if iron_furnace is None:
    raise Exception("Could not find the furnace at position (0.0, 5.0)")

print(f"Found furnace at position {iron_furnace.position}")

# Check if this furnace has iron ore or iron plates
if 'iron-ore' in iron_furnace.furnace_source or 'iron-plate' in iron_furnace.furnace_result:
    print("Confirmed: The furnace at (0.0, 5.0) is set up for processing iron ore")
else:
    print("Note: The furnace at (0.0, 5.0) is currently empty or processing a different ore")
    print("We will use this furnace for iron ore processing")

# Store the identified entities for later use
identified_iron_drill = iron_drill
identified_iron_furnace = iron_furnace

print("Successfully identified the iron ore mining drill and furnace")

# Assert tests
assert identified_iron_drill is not None, "Failed to identify an iron ore mining drill"
assert identified_iron_furnace is not None, "Failed to identify the iron ore furnace"
assert identified_iron_furnace.position.x == 0.0 and identified_iron_furnace.position.y == 5.0, "Identified furnace is not at the expected position (0.0, 5.0)"


"""
Step 2: Fuel the iron ore mining drill. We need to:
- Move to the chest at (5.5, -4.5) to collect coal
- Move to the identified iron ore mining drill
- Add coal to the drill's fuel inventory
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5}
#Step Execution

# Move to the chest containing coal
coal_chest_position = Position(x=5.5, y=-4.5)
move_to(coal_chest_position)
print(f"Moved to coal chest at {coal_chest_position}")

# Extract coal from the chest
coal_chest = get_entity(Prototype.WoodenChest, coal_chest_position)
extract_item(Prototype.Coal, coal_chest.position, quantity=10)
print("Extracted 10 coal from the chest")

# Check if we have coal in our inventory
inventory = inspect_inventory()
coal_count = inventory.get(Prototype.Coal, 0)
print(f"Current coal in inventory: {coal_count}")
assert coal_count >= 10, f"Failed to extract enough coal. Expected at least 10, but got {coal_count}"

# Move to the identified iron ore mining drill
move_to(identified_iron_drill.position)
print(f"Moved to iron ore mining drill at {identified_iron_drill.position}")

# Insert coal into the drill's fuel inventory
insert_item(Prototype.Coal, identified_iron_drill, quantity=5)
print("Inserted 5 coal into the iron ore mining drill")

# Verify that the drill has been fueled
updated_drill = get_entity(Prototype.BurnerMiningDrill, identified_iron_drill.position)
print(f"Updated drill status: {updated_drill.status}")
assert updated_drill.status != EntityStatus.NO_FUEL, "Failed to fuel the iron ore mining drill"

print("Successfully fueled the iron ore mining drill")


"""
Step 3: Set up the transport system. We need to:
- Place transport belts from the drill's drop position towards the iron ore furnace
- Place a burner inserter next to the furnace, rotated to insert items into it
- Connect the last transport belt to the inserter's pickup position
- Fuel the burner inserter with coal
"""
# Placeholder 3

"""
Step 4: Verify the setup. We need to:
- Wait for 30 seconds to allow time for ore transport
- Check if the iron ore furnace has more iron ore than it started with (initially 49)

##
"""
# Placeholder 4