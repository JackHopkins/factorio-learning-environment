# Craft 25 science pack 1 (red science packs) and feed them into a lab

# First, ensure we have enough materials
iron_ore_needed = 25 * 2  # 2 iron plates per science pack (1 for gear, 1 for pack)
copper_ore_needed = 25 * 1  # 1 copper plate per science pack

# Harvest resources
iron_ore_position = nearest(Resource.IronOre)
copper_ore_position = nearest(Resource.CopperOre)

iron_harvested = harvest_resource(iron_ore_position, iron_ore_needed)
copper_harvested = harvest_resource(copper_ore_position, copper_ore_needed)

assert iron_harvested >= iron_ore_needed, f"Not enough iron ore harvested. Got {iron_harvested}, needed {iron_ore_needed}"
assert copper_harvested >= copper_ore_needed, f"Not enough copper ore harvested. Got {copper_harvested}, needed {copper_ore_needed}"

# Craft iron and copper plates
iron_plates_crafted = craft_item(Prototype.IronPlate, iron_harvested)
copper_plates_crafted = craft_item(Prototype.CopperPlate, copper_harvested)

assert iron_plates_crafted >= iron_ore_needed, f"Failed to craft enough iron plates. Crafted {iron_plates_crafted}, needed {iron_ore_needed}"
assert copper_plates_crafted >= copper_ore_needed, f"Failed to craft enough copper plates. Crafted {copper_plates_crafted}, needed {copper_ore_needed}"

# Craft gears (1 gear = 2 iron plates)
gears_crafted = craft_item(Prototype.IronGearWheel, 25)
assert gears_crafted == 25, f"Failed to craft 25 iron gear wheels. Only crafted {gears_crafted}"

# Craft science packs
science_packs_crafted = craft_item(Prototype.AutomationSciencePack, 25)
assert science_packs_crafted == 25, f"Failed to craft 25 science packs. Only crafted {science_packs_crafted}"

# Craft and place a lab
lab_crafted = craft_item(Prototype.Lab, 1)
assert lab_crafted == 1, "Failed to craft a lab"

lab = place_entity(Prototype.Lab, Direction.UP, Position(x=0, y=0))
assert lab is not None, "Failed to place lab"

# Move to the lab
move_to(lab.position)

# Insert science packs into the lab
inserted = insert_item(Prototype.AutomationSciencePack, lab, 25)
assert inserted is not None, "Failed to insert science packs into lab"

# Verify that the lab has received the science packs
lab_inventory = inspect_inventory(lab)
assert lab_inventory.get(Prototype.AutomationSciencePack) == 25, f"Lab does not contain 25 science packs. It contains {lab_inventory.get(Prototype.AutomationSciencePack)}"

print("Successfully crafted 25 science pack 1 and fed them into a lab")
