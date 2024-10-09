# First, gather available resources
iron_ore_position = nearest(Resource.IronOre)
coal_position = nearest(Resource.Coal)

# Harvest iron ore and coal
iron_ore_harvested = harvest_resource(iron_ore_position, 100)
coal_harvested = harvest_resource(coal_position, 50)

print(f"Harvested {iron_ore_harvested} iron ore and {coal_harvested} coal")

# Craft iron plates
iron_plates = craft_item(Prototype.IronPlate, iron_ore_harvested)
print(f"Crafted {iron_plates} iron plates")

# Calculate how many items we can craft based on available iron plates
max_gears = iron_plates // 2
max_ammo = iron_plates // 4
max_turrets = min(5, iron_plates // 20)  # Cap at 5 turrets

# Craft necessary items
gears_crafted = craft_item(Prototype.IronGearWheel, max_gears)
ammo_crafted = craft_item(Prototype.FirearmMagazine, max_ammo)
turrets_crafted = craft_item(Prototype.GunTurret, max_turrets)

print(f"Crafted {gears_crafted} iron gear wheels, {ammo_crafted} firearm magazines, and {turrets_crafted} gun turrets")

# Choose a defensive location (adjust as needed)
defensive_position = Position(x=10, y=10)

# Place the gun turrets in a line
turrets = []
for i in range(turrets_crafted):
    turret_position = Position(x=defensive_position.x + i*2, y=defensive_position.y)
    turret = place_entity(Prototype.GunTurret, direction=Direction.SOUTH, position=turret_position)
    if turret:
        turrets.append(turret)

print(f"Placed {len(turrets)} gun turrets")

# Supply ammunition to each turret
if turrets:
    ammo_per_turret = min(20, ammo_crafted // len(turrets))
    for turret in turrets:
        inserted_ammo = insert_item(Prototype.FirearmMagazine, turret, ammo_per_turret)
        if inserted_ammo:
            print(f"Inserted {ammo_per_turret} ammunition into turret at {turret.position}")
        else:
            print(f"Failed to insert ammunition into turret at {turret.position}")

# Verify total ammunition used
player_inventory = inspect_inventory()
remaining_ammo = player_inventory.get(Prototype.FirearmMagazine, 0)

print(f"Defensive line of {len(turrets)} gun turrets built and supplied with {ammo_per_turret} ammunition each")
print(f"Remaining ammunition in inventory: {remaining_ammo}")

# Final assertions to check if we met the objective
assert len(turrets) > 0, "Failed to build any gun turrets"
assert len(turrets) <= 5, f"Built too many turrets: {len(turrets)}"
assert remaining_ammo < ammo_crafted, "Failed to supply turrets with ammunition"

# Additional assertion to ensure we built as many turrets as possible
assert len(turrets) == turrets_crafted, f"Expected to place {turrets_crafted} turrets, but placed {len(turrets)}"

print("Objective completed: Built a defensive line of gun turrets and manually supplied them with ammunition")
