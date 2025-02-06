Use the API to write a Python script to achieve the objective given. Here is an example

EXAMPLE INPUT
Create the script to craft 5 copper plates with inventory "{{}}". Here is the plan to achieve the objective
SUMMARY
In general to craft copper plates, we need to craft a furnace, mine copper ore and smelt copper ore in the furnace. We need 1 copper ore for one copper plate. As we have no materials in inventory, we need to craft everything from scratch

STEPS
To smelt copper plates the plan is as follows
1) As the copper plate requires stone furnace to smelt, first we need to mine 5 stone and 
2) Craft stone furnace
3) Mine coal for stone furnace
4) Move to copper ore
5) Place down stone furnace
6) Mine copper ore
7) Place coal and copper ore to stone furnace
8) Smelt copper ore for copper plates


EXAMPLE OUTPUT

```python
from instance import *

# 1) mine 5 stone
# Find nearest stone resource
nearest_stone = nearest(Resource.Stone)
# Move to the stone resource
move_to(nearest_stone)
# Harvest stone
harvest_resource(nearest_stone, quantity=5)
# test that the stone was harvested
stone_in_inventory = inspect_inventory()[Resource.Stone]
assert stone_in_inventory >= 5, f"Inventory has less than 5 stone, it has {{stone_in_inventory}}"

# 2) Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
# test that the stone furnace was crafted
furnace_in_inventory = inspect_inventory()[Prototype.StoneFurnace]
assert furnace_in_inventory >= 1, f"Inventory has less than 1 stone furnace, it has {{furnace_in_inventory}}"

# 3) Mine coal for stone furnace
nearest_coal = nearest(Resource.Coal)
move_to(nearest_coal)
harvest_resource(nearest_coal, quantity=10)
# test that the coal was harvested
coal_in_inventory = inspect_inventory()[Resource.Coal]
assert coal_in_inventory >= 5, f"Inventory has less than 5 coal, it has {{coal_in_inventory}}"

# 4) Move to copper ore
nearest_copper = nearest(Resource.CopperOre)
move_to(nearest_copper)
# 5) Place down stone furnace
stone_furnace = place_entity_next_to(Prototype.StoneFurnace,
                                     reference_position=nearest_copper,
                                     direction=UP,
                                     spacing=1)
# 6) Mine copper ore
harvest_resource(nearest_copper, quantity=5)
# test that the copper ore was harvested
copper_in_inventory = inspect_inventory()[Resource.CopperOre]
assert copper_in_inventory >= 5, f"Inventory has less than 5 copper ore, it has {{copper_in_inventory}}"

# 7) Place coal and copper ore to stone furnace
insert_item(Prototype.Coal, stone_furnace, 10)
insert_item(Prototype.CopperOre, stone_furnace, 5)
# 8) Smelt copper ore for copper plates
# wait for smelting and test that the copper plates were smelted
# smelting may take longer  thus we need to check the inventory after a while
# if inventory has less than we put in, we need to sleep again and longer
number_of_copper_plates = inspect_inventory()[Prototype.CopperPlate]
max_sleep = 3
# if the copper plates are not there, wait for a while
if number_of_copper_plates < 5:
    sleep(20)
    # extract the copper plates again
    extract_item(Prototype.CopperPlate, stone_furnace, 5)
    # check if you have extracted all copper plates
    number_of_copper_plates = inspect_inventory()[Prototype.CopperPlate]
    if number_of_copper_plates >= 5:
        break
    max_sleep -= 1
    # if have slept for too long, break the loop
    if max_sleep == 0:
        break
# make final test whether we have 5 copper plates
number_of_copper_plates = inspect_inventory()[Prototype.CopperPlate]
assert number_of_copper_plates >= 5, f"Inventory has less than 5 copper plates, it has {{number_of_copper_plates}}" 

```

USER INPUT
Create the script to '{objective}' with inventory {inventory}. Here is the plan to achieve the objective:
{steps}