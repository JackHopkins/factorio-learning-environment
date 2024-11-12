from factorio_instance import *
import random

inventory = inspect_inventory()
chests_in_inventory = inventory.get(Prototype.WoodenChest, 0)
chest_positions = []
for chest in range(chests_in_inventory):
    # get a random x and y position between -15 and 15
    x = random.randint(-15, 15)
    y = random.randint(-15, 15)
    chest_pos = Position(x = x, y = y)
    move_to(chest_pos)
    chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)
    chest_positions.append(chest.position)

furnaces_in_inventory = inventory.get(Prototype.StoneFurnace, 0)
furnace_positions = []
for furnace in range(furnaces_in_inventory):
    # get a random x and y position between -15 and 15
    x = random.randint(-15, 15)
    y = random.randint(-15, 15)
    furnace_pos = Position(x = x, y = y)
    move_to(furnace_pos)
    furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)
    furnace_positions.append(furnace.position)