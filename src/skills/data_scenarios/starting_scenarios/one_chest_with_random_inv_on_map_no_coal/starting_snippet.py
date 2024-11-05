from factorio_instance import *

NAME_TO_ENTITY_MAPPING = {"iron-ore": Prototype.IronOre, 
                          "copper-ore": Prototype.CopperOre, "stone": Prototype.Stone, 
                          "iron-plate": Prototype.IronPlate, "copper-plate": Prototype.CopperPlate, 
                          }

furnace_pos = Position(x = -7, y = -7)
move_to(furnace_pos)
stone_furnace = place_entity(Prototype.WoodenChest, Direction.UP, furnace_pos)

inventory = inspect_inventory()
for item in inventory:
    name = item[0]
    count = item[1]
    if name in NAME_TO_ENTITY_MAPPING:
        updated_chest = insert_item(NAME_TO_ENTITY_MAPPING[name], stone_furnace, count)