

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner mining drill
- stone furnace
- iron gear wheel
- transport belt
- burner inserter
- firearm magazine
"""
# Print recipes for the required items
print("Recipes:")
print("Burner Mining Drill: 3 iron gear wheels, 1 stone furnace")
print("Stone Furnace: 5 stone")
print("Iron Gear Wheel: 2 iron plates")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (makes 2)")
print("Burner Inserter: 1 iron gear wheel, 1 iron plate")
print("Firearm Magazine: 4 iron plates")


"""
Step 2: Craft and place stone furnace. We need to:
- Gather 5 stone
- Craft 1 stone furnace
- Place the stone furnace at position (2, 2)
"""
from instance import *

"""
Craft and place a stone furnace
:param game: Factorio instance
:return: None
"""
# Step 1: Gather stone for the stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Step 2: Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted a stone furnace")

# Step 3: Place the stone furnace at position (2, 2)
placement_position = Position(x=2, y=2)
move_to(placement_position)
furnace = place_entity(Prototype.StoneFurnace, position=placement_position)
print(f"Placed stone furnace at {furnace.position}")


"""
Step 3: Smelt iron plates. We need to:
- Gather 26 iron ore
- Smelt 26 iron plates (we need extra for crafting mistakes and future use)
"""
# Step 1: Gather iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=26)
print("Gathered 26 iron ore")

# Step 2: Gather coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)
print("Gathered 10 coal")

# Step 3: Move to the stone furnace
furnace_position = Position(x=2, y=2)
move_to(furnace_position)

# Step 4: Insert coal into the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted 5 coal into the furnace")

# Step 5: Insert iron ore into the furnace for smelting
insert_item(Prototype.IronOre, furnace, quantity=26)
print("Inserted 26 iron ore into the furnace")

# Step 6: Wait for smelting to complete
sleep(30)

# Step 7: Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=26)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 26:
        break
    sleep(5)

iron_plates = inventory.get(Prototype.IronPlate, 0)
print(f"Extracted {iron_plates} iron plates")
assert iron_plates >= 26, f"Failed to obtain required number of iron plates. Current count: {iron_plates}"


"""
Step 4: Craft components. We need to craft:
- 6 iron gear wheels (requires 12 iron plates)
- 2 stone furnaces (requires 10 stone)
"""
# Step 1: Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=6)
print("Crafted 6 iron gear wheels")

# Step 2: Gather stone for stone furnaces
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=10)
print("Gathered 10 stone")

# Step 3: Craft stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")


"""
Step 5: Craft burner mining drill. We need to craft:
- 1 burner mining drill (requires 3 iron gear wheels and 1 stone furnace)
"""
# Step 1: Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")


"""
Step 6: Verify crafting. We need to check if we have crafted all the required items:
- burner mining drill: 1
- stone furnace: 1
- iron gear wheel: 6
- transport belt: 4
- burner inserter: 1
- firearm magazine: 1
"""
# Step 1: Check inventory for crafted items
inventory = inspect_inventory()

# Step 2: Verify quantities of crafted items
assert inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft required number of burner mining drills"
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft required number of stone furnaces"
assert inventory.get(Prototype.IronGearWheel, 0) >= 6, "Failed to craft required number of iron gear wheels"
assert inventory.get(Prototype.TransportBelt, 0) >= 4, "Failed to craft required number of transport belts"
assert inventory.get(Prototype.BurnerInserter, 0) >= 1, "Failed to craft required number of burner inserters"
assert inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Failed to craft required number of firearm magazines"

print("Successfully crafted all required items")


"""
Step 7: Set up mining operation. We need to:
- Place the burner mining drill near an iron ore patch
- Fuel the burner mining drill with coal
- Connect the drill to the stone furnace using transport belts
- Place and configure a burner inserter to move iron ore from the belt to the furnace
"""
# Step 1: Place burner mining drill
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed burner mining drill at {drill.position}")

# Step 2: Fuel the burner mining drill
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    fueled_drill = insert_item(Prototype.Coal, drill, quantity=5)
    print("Fueled burner mining drill with coal")
else:
    print("No coal available to fuel the burner mining drill")

# Step 3: Connect drill to furnace with transport belts
furnace = get_entity(Prototype.StoneFurnace, Position(x=2, y=2))
belts = connect_entities(fueled_drill.drop_position, furnace.position, Prototype.TransportBelt)
assert len(belts) > 0, "Failed to connect drill to furnace with transport belts"
print("Connected drill to furnace with transport belts")

# Step 4: Place and configure burner inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.LEFT)
assert inserter is not None, "Failed to place burner inserter"
inserter = rotate_entity(inserter, Direction.RIGHT)
print("Placed and configured burner inserter")

# Step 5: Verify setup
inspection = inspect_entities(drill.position, radius=10)
furnaces = [e for e in inspection.entities if e.name == Prototype.StoneFurnace.value[0]]
assert len(furnaces) > 0, "No stone furnace found in the setup"
assert any(e.name == Prototype.BurnerMiningDrill.value[0] for e in inspection.entities), "No burner mining drill found in the setup"
assert any(e.name == Prototype.BurnerInserter.value[0] for e in inspection.entities), "No burner inserter found in the setup"
print("Mining operation setup successfully")

"""
Step 8: Check if mining setup is working. We need to:
- Wait for 1 minute
- Check if iron ore is being mined and transported to the furnace
"""
# Step 1: Wait for 1 minute
print("Waiting for 1 minute to allow mining operation to start...")
sleep(60)

# Step 2: Move near the furnace to inspect its contents
move_to(furnace.position)

# Step 3: Check the furnace's inventory for iron ore
furnace_inventory = inspect_inventory(furnace)
iron_ore_count = furnace_inventory.get(Prototype.IronOre, 0)
print(f"Iron ore in the furnace: {iron_ore_count}")
assert iron_ore_count > 0, "No iron ore found in the furnace. Mining setup is not working correctly."

# Step 4: Check if the furnace is smelting iron plates
furnace_status = get_entity(Prototype.StoneFurnace, furnace.position).status
if furnace_status == EntityStatus.WORKING:
    print("Furnace is actively smelting iron plates.")
else:
    print("Furnace is not actively smelting. Current status:", furnace_status)

# Step 5: Verify if iron plates are being produced
iron_plate_count = furnace_inventory.get(Prototype.IronPlate, 0)
print(f"Iron plates in the furnace: {iron_plate_count}")
if iron_plate_count > 0:
    print("Iron plates are being produced.")
else:
    print("No iron plates found. Check if there's enough iron ore and fuel.")

print("Mining setup verification complete.")
