from factorio_instance import *

NAME_TO_ENTITY_MAPPING = {"iron-ore": Prototype.IronOre, 
                          "copper-ore": Prototype.CopperOre, "stone": Prototype.Stone, 
                          "iron-plate": Prototype.IronPlate, "copper-plate": Prototype.CopperPlate, 
                          }

furnace_pos = Position(x = 0, y = -1)
chest_pos = Position(x = 5, y = 8)
move_to(chest_pos)
chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)
move_to(furnace_pos)
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)
move_to(chest_pos)
inventory = inspect_inventory()
for item in inventory:
    if item[0] not in NAME_TO_ENTITY_MAPPING:
        continue
    name = item[0]
    count = item[1]
    updated_chest = insert_item(NAME_TO_ENTITY_MAPPING[name], chest, count)


furnace_pos = Position(x = -4, y = 0)
chest_pos = Position(x = 3, y = -12)
move_to(chest_pos)
chest = place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)
move_to(furnace_pos)
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)