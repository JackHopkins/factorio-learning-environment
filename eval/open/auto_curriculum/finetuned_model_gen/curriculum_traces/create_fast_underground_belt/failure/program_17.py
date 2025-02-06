

from instance import *

"""
Step 1: Crafting the required entities
"""
# Define the entities we need to craft
entities_to_craft = [
    Prototype.TransportBelt,
    Prototype.AssemblingMachine1,
    Prototype.Inserter,
    Prototype.SmallElectricPole,
    Prototype.Boiler,
    Prototype.SteamEngine
]

# Print the recipes for the entities we need to craft
for entity in entities_to_craft:
    recipe = get_prototype_recipe(entity)
    print(f"Recipe for {entity}: {recipe}")

# Gather raw resources
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=10)

iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=30)

coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)

# Craft initial stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place furnace and smelt iron
move_to(Position(x=0, y=0))
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.Coal, furnace, 5)
insert_item(Prototype.IronOre, furnace, 20)

sleep(10)

# Extract iron plates and craft necessary components
extract_item(Prototype.IronPlate, furnace.position, 20)
craft_item(Prototype.IronGearWheel, 10)
craft_item(Prototype.IronStick, 2)
craft_item(Prototype.CopperCable, 6)
craft_item(Prototype.ElectronicCircuit, 3)
craft_item(Prototype.Pipe, 2)

# Craft the required entities
for entity in entities_to_craft:
    craft_item(entity, 1)

print("Crafted all necessary entities")

"""
Step 2: Setting up power generation
"""
# Place and fuel boiler
boiler = place_entity(Prototype.Boiler, position=Position(x=2, y=0))
insert_item(Prototype.Coal, boiler, 10)

# Place steam engine and connect to boiler
steam_engine = place_entity(Prototype.SteamEngine, position=Position(x=5, y=0))
connect_entities(boiler, steam_engine, Prototype.Pipe)

# Place power poles
pole1 = place_entity(Prototype.SmallElectricPole, position=Position(x=7, y=0))
pole2 = place_entity(Prototype.SmallElectricPole, position=Position(x=10, y=0))

# Connect power poles
connect_entities(pole1, pole2, Prototype.SmallElectricPole)

print("Power generation setup complete")

"""
Step 3: Setting up production line
"""
# Place and connect assembling machines
assembling_machine_1 = place_entity(Prototype.AssemblingMachine1, position=Position(x=13, y=0))
assembling_machine_2 = place_entity(Prototype.AssemblingMachine1, position=Position(x=16, y=0))
assembling_machine_3 = place_entity(Prototype.AssemblingMachine1, position=Position(x=19, y=0))

# Connect assembling machines to power
connect_entities(pole2, assembling_machine_1, Prototype.SmallElectricPole)
connect_entities(pole2, assembling_machine_2, Prototype.SmallElectricPole)
connect_entities(pole2, assembling_machine_3, Prototype.SmallElectricPole)

# Set recipes
set_entity_recipe(assembling_machine_1, Prototype.IronGearWheel)
set_entity_recipe(assembling_machine_2, Prototype.UndergroundBelt)
set_entity_recipe(assembling_machine_3, Prototype.FastUndergroundBelt)

# Place and configure inserters
inserter_1 = place_entity(Prototype.Inserter, position=Position(x=13, y=2))
rotate_entity(inserter_1, Direction.UP)
insert_item(Prototype.IronPlate, inserter_1, 5)

inserter_2 = place_entity(Prototype.Inserter, position=Position(x=16, y=2))
rotate_entity(inserter_2, Direction.UP)
insert_item(Prototype.IronGearWheel, inserter_2, 5)

inserter_3 = place_entity(Prototype.Inserter, position=Position(x=19, y=2))
rotate_entity(inserter_3, Direction.UP)
insert_item(Prototype.UndergroundBelt, inserter_3, 2)

# Connect inserters to power
connect_entities(assembling_machine_1, inserter_1, Prototype.SmallElectricPole)
connect_entities(assembling_machine_2, inserter_2, Prototype.SmallElectricPole)
connect_entities(assembling_machine_3, inserter_3, Prototype.SmallElectricPole)

"""
Step 4: Crafting and verifying fast-underground-belt
"""
# Craft and verify fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted fast-underground-belt")

# Verify
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")

