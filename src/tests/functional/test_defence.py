import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'stone-furnace': 1,
                                  'iron-chest': 3,
                                  'burner-inserter': 6,
                                  'coal': 50,
                                  'transport-belt': 50,
                                  'burner-mining-drill': 5}
    instance.reset()
    instance.speed(10)
    yield instance
    instance.reset()
    instance.speed(1)

def test_defence(game):
    # First, gather available resources
    iron_ore_position = game.nearest(Resource.IronOre)
    coal_position = game.nearest(Resource.Coal)

    # Harvest iron ore and coal
    game.move_to(iron_ore_position)
    iron_ore_harvested = 0
    while iron_ore_harvested < 400:
        iron_ore_harvested += game.harvest_resource(iron_ore_position, 50)

    copper_ore_position = game.nearest(Resource.CopperOre)
    game.move_to(copper_ore_position)
    copper_ore_harvested = 0
    while copper_ore_harvested < 200:
        copper_ore_harvested += game.harvest_resource(copper_ore_position, 50)

    coal_harvested = game.harvest_resource(coal_position, 50)

    print(f"Harvested {iron_ore_harvested} iron ore and {coal_harvested} coal")

    # Craft iron plates
    iron_plates = game.craft_item(Prototype.IronPlate, iron_ore_harvested)
    print(f"Crafted {iron_plates} iron plates")

    # Craft copper plates
    copper_plates = game.craft_item(Prototype.CopperPlate, copper_ore_harvested)
    print(f"Crafted {copper_plates} copper plates")

    # Calculate how many items we can craft based on available iron plates
    max_gears = iron_plates // 8
    max_ammo = iron_plates // 8
    max_turrets = min(5, iron_plates // 20)  # Cap at 5 turrets

    # Craft necessary items
    gears_crafted = game.craft_item(Prototype.IronGearWheel, max_gears)
    ammo_crafted = game.craft_item(Prototype.FirearmMagazine, max_ammo)
    turrets_crafted = game.craft_item(Prototype.GunTurret, max_turrets)

    print(
        f"Crafted {gears_crafted} iron gear wheels, {ammo_crafted} firearm magazines, and {turrets_crafted} gun turrets")

    # Choose a defensive location (adjust as needed)
    defensive_position = Position(x=10, y=10)

    # Place the gun turrets in a line
    turrets = []
    for i in range(turrets_crafted):
        turret_position = Position(x=defensive_position.x + i * 2, y=defensive_position.y)
        game.move_to(turret_position)
        turret = game.place_entity(Prototype.GunTurret, direction=Direction.SOUTH, position=turret_position)
        if turret:
            turrets.append(turret)

    print(f"Placed {len(turrets)} gun turrets")

    # Supply ammunition to each turret
    if turrets:
        ammo_per_turret = min(20, ammo_crafted // len(turrets))
        for turret in turrets:
            inserted_ammo = game.insert_item(Prototype.FirearmMagazine, turret, ammo_per_turret)
            if inserted_ammo:
                print(f"Inserted {ammo_per_turret} ammunition into turret at {turret.position}")
            else:
                print(f"Failed to insert ammunition into turret at {turret.position}")

    # Verify total ammunition used
    player_inventory = game.inspect_inventory()
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
