# Harvest available resources
iron_ore_harvested = harvest_resource(nearest(Resource.IronOre), 200)
copper_ore_harvested = harvest_resource(nearest(Resource.CopperOre), 100)
coal_harvested = harvest_resource(nearest(Resource.Coal), 50)

# Craft intermediate materials
iron_plates_crafted = craft_item(Prototype.IronPlate, iron_ore_harvested)
copper_plates_crafted = craft_item(Prototype.CopperPlate, copper_ore_harvested)
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, min(iron_plates_crafted // 2, 20))

# Calculate maximum number of gun turrets we can craft
max_turrets = min(5, iron_plates_crafted // 20, copper_plates_crafted // 10, iron_gear_wheels_crafted // 5)

# Craft gun turrets
gun_turrets_crafted = craft_item(Prototype.GunTurret, max_turrets)
assert gun_turrets_crafted > 0, "Failed to craft any gun turrets"

# Craft ammunition
ammo_crafted = craft_item(Prototype.FirearmMagazine, min(copper_plates_crafted, iron_plates_crafted) * 2)
assert ammo_crafted > 0, "Failed to craft any ammunition"

# Place gun turrets in a line
start_position = Position(x=0, y=0)
turrets = []

for i in range(gun_turrets_crafted):
    position = Position(x=start_position.x + i * 3, y=start_position.y)
    turret = place_entity(Prototype.GunTurret, direction=Direction.NORTH, position=position)
    assert turret, f"Failed to place gun turret at position {position}"
    turrets.append(turret)

# Supply ammunition to each turret
ammo_per_turret = min(20, ammo_crafted // len(turrets))
for turret in turrets:
    inserted_ammo = insert_item(Prototype.FirearmMagazine, turret, ammo_per_turret)
    assert inserted_ammo, f"Failed to insert ammunition into turret at {turret.position}"

# Verify that all turrets have ammunition
for turret in turrets:
    inventory = inspect_inventory(turret)
    assert inventory.get(Prototype.FirearmMagazine) > 0, f"Turret at {turret.position} does not have ammunition"

# Final verification
inspection = inspect_entities(start_position, radius=15)
gun_turrets = [entity for entity in inspection.entities if entity.name == Prototype.GunTurret.value[0]]
assert len(gun_turrets) == gun_turrets_crafted, f"Expected {gun_turrets_crafted} gun turrets in the area, but found {len(gun_turrets)}"

print(f"Objective completed successfully: Defensive line of {len(turrets)} gun turrets built and supplied with ammunition")
