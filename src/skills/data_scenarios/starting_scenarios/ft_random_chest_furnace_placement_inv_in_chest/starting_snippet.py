from factorio_instance import *
import random

NAME_TO_ENTITY_MAPPING_CHEST_1 = {"electronic-circuit": Prototype.ElectronicCircuit, 
                          "burner-mining-drill": Prototype.BurnerMiningDrill, "coal": Prototype.Coal, 
                          "iron-plate": Prototype.IronPlate, "stone": Prototype.Stone, 
                          }

NAME_TO_ENTITY_MAPPING_CHEST_2 = {"iron-ore": Prototype.IronOre, 
                          "copper-ore": Prototype.CopperOre, 
                          "transport-belt": Prototype.TransportBelt, "copper-plate": Prototype.CopperPlate, 
                          }


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


# move to first chest
move_to(chest_positions[0])
for item in inventory:
    if item[0] not in NAME_TO_ENTITY_MAPPING_CHEST_1:
        continue
    name = item[0]
    count = item[1]
    chest = get_entity(Prototype.WoodenChest, chest_positions[0])
    updated_chest = insert_item(NAME_TO_ENTITY_MAPPING_CHEST_1[name], chest, count)

# move to second chest
move_to(chest_positions[1])
for item in inventory:
    if item[0] not in NAME_TO_ENTITY_MAPPING_CHEST_2:
        continue
    name = item[0]
    count = item[1]
    chest = get_entity(Prototype.WoodenChest, chest_positions[1])
    updated_chest = insert_item(NAME_TO_ENTITY_MAPPING_CHEST_2[name], chest, count)

