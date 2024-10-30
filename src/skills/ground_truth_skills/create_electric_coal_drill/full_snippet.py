from factorio_instance import *


###SEP
"""
Step 1: Place electric mining drill. We need to carry out the following substeps:
- Move to the nearest coal patch
- Place the electric mining drill on the coal patch
"""
# Inventory at the start of step {'small-electric-pole': 20, 'pipe': 10, 'electric-mining-drill': 1}
#Step Execution

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
print(f"Nearest coal patch found at: {coal_position}")

# Move to the coal patch
move_to(coal_position)
print(f"Moved to coal patch at: {coal_position}")

# Place the electric mining drill on the coal patch
drill = place_entity(Prototype.ElectricMiningDrill, Direction.UP, coal_position)
print(f"Placed electric mining drill at: {drill.position}")

# Check the inventory to ensure we used one electric mining drill
inventory = inspect_inventory()
assert inventory[Prototype.ElectricMiningDrill] == 0, "Electric mining drill was not consumed from inventory"

print("Successfully placed electric mining drill on coal patch")
print(f"Current inventory: {inventory}")

###SEP
"""
Step 2: Connect electric mining drill to power. We need to connect the electric mining drill to the steam engine using small electric poles. We need to carry out the following substeps:
- Connect the electric mining drill to the steam engine using small electric poles
"""

# get the steam engine entity, first get all entities
entities = get_entities({Prototype.SteamEngine})
# get all steam engines by looking at the prototype
steam_engines = [x for x in entities if x.prototype is Prototype.SteamEngine]
# get the first one as we only have one
steam_engine = steam_engines[0]

connection = connect_entities(steam_engine, drill, Prototype.SmallElectricPole)
assert connection, "Failed to connect electric mining drill to power"
print("Electric mining drill connected to power")
###SEP
"""
Step 3: Verify power connection. We need to check if the electric mining drill is powered. We need to carry out the following substeps:
- Wait for 5 seconds to allow the power to stabilize
- Check the status of the electric mining drill to ensure it's powered and working
##
"""
# sleep for a few seconds to allow power to stabilize
sleep(5)

# update the drill entity to get the powered one
drill = get_entity(Prototype.ElectricMiningDrill, drill.position)
# Check the status of the electric mining drill
drill_status = drill.status
assert drill_status != EntityStatus.NO_POWER, "Electric mining drill is not powered"
print("Electric mining drill is powered and working")
