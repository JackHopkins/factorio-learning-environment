import pytest

from fle.env import DirectionInternal
from fle.env.entities import Furnace, Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "coal": 5,
        "iron-chest": 1,
        "iron-plate": 50,
        "iron-ore": 10,
        "stone-furnace": 1,
        "assembling-machine-1": 1,
        "burner-mining-drill": 1,
        "lab": 1,
        "automation-science-pack": 1,
        "gun-turret": 1,
        "firearm-magazine": 5,
        "boiler": 1,
        "offshore-pump": 1,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_get_offshore_pump(game):
    """
    Test to ensure that the inventory of an offshore pump is correctly updated after mining water
    :param game:
    :return:
    """
    # Check initial inventory
    position = game.nearest(Resource.Water)
    game.move_to(position)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, DirectionInternal.RIGHT, position
    )
    assert offshore_pump is not None, "Failed to place offshore pump"

    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, DirectionInternal.RIGHT, spacing=2
    )
    assert boiler

    pipes = game.connect_entities(boiler, offshore_pump, Prototype.Pipe)
    assert pipes
    game.sleep(1)
    # Load entities from the game
    offshore_pump = game.get_entities({Prototype.OffshorePump})[0]
    assert offshore_pump is not None, "Failed to retrieve offshore pump"
    # Check to see if the offshore pump has water
    assert offshore_pump.fluid_box, "Failed to get water"
    boiler = game.get_entities({Prototype.Boiler})[0]
    assert boiler is not None, "Failed to retrieve boiler"
    # Check to see if the boiler has water
    assert boiler.fluid_box, "Failed to get water"


def test_get_stone_furnace(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    # Check initial inventory
    position = game.nearest(Resource.Stone)
    game.move_to(position)
    # 1. Place a stone furnace
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, DirectionInternal.UP, position
    )
    assert stone_furnace is not None, "Failed to place stone furnace"
    assert stone_furnace.warnings == ["out of fuel", "no ingredients to smelt"], (
        "Failed to place stone furnace"
    )

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(5)
    retrieved_furnace: Furnace = game.get_entity(
        Prototype.StoneFurnace, stone_furnace.position
    )

    assert retrieved_furnace is not None, "Failed to retrieve stone furnace"
    assert retrieved_furnace.furnace_result.get(Prototype.IronPlate, 0) > 0, (
        "Failed to smelt iron plate"
    )
    assert retrieved_furnace.furnace_source.get(Prototype.IronOre, 0) < 5, (
        "Failed to smelt iron ore"
    )
    assert retrieved_furnace.fuel.get(Prototype.Coal, 0) < 5, "Failed to consume coal"


def test_get_mining_drill(game):
    """
    Test to ensure that the inventory of a mining drill is correctly updated after mining iron ore
    :param game:
    :return:
    """
    # Check initial inventory
    position = game.nearest(Resource.IronOre)
    game.move_to(position)
    mining_drill = game.place_entity(
        Prototype.BurnerMiningDrill, DirectionInternal.UP, position
    )
    game.insert_item(Prototype.Coal, mining_drill, 5)
    assert mining_drill is not None, "Failed to place mining drill"

    game.sleep(5)
    retrieved_drill = game.get_entity(
        Prototype.BurnerMiningDrill, mining_drill.position
    )

    assert retrieved_drill is not None, "Failed to retrieve mining drill"
    assert retrieved_drill.fuel.get(Prototype.Coal, 0) < 5, "Failed to burn fuel"


def test_get_iron_chest(game):
    """
    Test to ensure that the inventory of an iron chest is correctly updated after inserting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    iron_chest_count = inventory.get(Prototype.IronChest, 0)
    assert iron_chest_count != 0, "Failed to get iron chest count"

    iron_chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, iron_chest, quantity=5)
    game.insert_item(Prototype.IronPlate, iron_chest, quantity=5)

    retrieved_chest = game.get_entity(Prototype.IronChest, iron_chest.position)

    assert retrieved_chest is not None, "Failed to retrieve iron chest"
    assert retrieved_chest.inventory.get(Prototype.Coal, 0) == 5, (
        "Failed to insert coal"
    )
    assert retrieved_chest.inventory.get(Prototype.IronPlate, 0) == 5, (
        "Failed to insert iron plate"
    )


def test_get_assembling_machine(game):
    """
    Test to ensure that the inventory of an assembling machine is correctly updated after crafting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    assembling_machine_count = inventory.get(Prototype.AssemblingMachine1, 0)
    assert assembling_machine_count != 0, "Failed to get assembling machine count"

    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, assembling_machine, quantity=5)
    game.craft_item(Prototype.IronGearWheel, 5)
    game.insert_item(Prototype.IronGearWheel, assembling_machine, quantity=5)

    retrieved_machine = game.get_entity(
        Prototype.AssemblingMachine1, assembling_machine.position
    )

    assert retrieved_machine is not None, "Failed to retrieve assembling machine"
    assert (
        retrieved_machine.assembling_machine_output.get(Prototype.IronGearWheel, 0) == 5
    ), "Failed to get output inventory"
    assert (
        retrieved_machine.assembling_machine_input.get(Prototype.IronPlate, 0) == 5
    ), "Failed to consume input inventory"


def test_get_lab(game):
    """
    Test to ensure that the inventory of a lab is correctly updated after researching a science pack
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    lab_count = inventory.get(Prototype.Lab, 0)
    assert lab_count != 0, "Failed to get lab count"

    lab = game.place_entity(Prototype.Lab, position=Position(x=0, y=0))
    game.insert_item(Prototype.AutomationSciencePack, lab, quantity=1)
    retrieved_lab = game.get_entity(Prototype.Lab, lab.position)

    assert retrieved_lab is not None, "Failed to retrieve lab"
    assert retrieved_lab.lab_input.get(Prototype.AutomationSciencePack, 0) == 1, (
        "Failed to consume science pack"
    )


def test_get_turret(game):
    """
    Test to ensure that the inventory of a turret is correctly updated after shooting a target
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    turret_count = inventory.get(Prototype.GunTurret, 0)
    assert turret_count != 0, "Failed to get turret count"

    turret = game.place_entity(Prototype.GunTurret, position=Position(x=0, y=0))
    game.insert_item(Prototype.FirearmMagazine, turret, quantity=5)
    retrieved_turret = game.get_entity(Prototype.GunTurret, turret.position)

    assert retrieved_turret is not None, "Failed to retrieve turret"
    assert retrieved_turret.turret_ammo.get(Prototype.FirearmMagazine, 0) == 5, (
        "Failed to consume ammo"
    )


def test_get_boiler(game):
    """
    Test to ensure that the inventory of a boiler is correctly updated after burning fuel
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    boiler_count = inventory.get(Prototype.Boiler, 0)
    assert boiler_count != 0, "Failed to get boiler count"

    boiler = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, boiler, quantity=5)
    retrieved_boiler = game.get_entity(Prototype.Boiler, boiler.position)

    assert retrieved_boiler is not None, "Failed to retrieve boiler"
    assert retrieved_boiler.fuel.get(Prototype.Coal, 0) == 5, "Failed to consume fuel"


def test_get_assembling_machine_1(game):
    """
    Test to ensure that the inventory of an assembling machine is correctly updated after crafting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    assembling_machine_count = inventory.get(Prototype.AssemblingMachine1, 0)
    assert assembling_machine_count != 0, "Failed to get assembling machine count"

    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, assembling_machine, quantity=5)

    retrieved_machine = game.get_entity(
        Prototype.AssemblingMachine1, assembling_machine.position
    )

    assert retrieved_machine is not None, "Failed to retrieve assembling machine"
