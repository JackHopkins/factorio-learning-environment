import time

import pytest

from fle.env import BurnerMiningDrill, EntityStatus, Layer
from fle.env import FactorioInstance, Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 1,
        "burner-mining-drill": 3,
        "transport-belt": 100,
        "small-electric-pole": 50,
        "boiler": 1,
        "steam-engine": 1,
        "offshore-pump": 4,
        "pipe": 100,
        "burner-inserter": 50,
        "coal": 50,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_steam_engines(game):
    # game.craft_item(Prototype.OffshorePump)
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, position=game.nearest(Resource.Water)
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler.position,
        direction=boiler.direction,
        spacing=5,
    )
    game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    coal_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=boiler.position,
        direction=Direction.DOWN,
        spacing=0,
    )
    coal_inserter = game.rotate_entity(coal_inserter, Direction.UP)
    game.move_to(game.nearest(Resource.Coal))

    burner_mining_drill = game.place_entity(
        Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal)
    )
    burner_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=burner_mining_drill.position,
        direction=Direction.DOWN,
        spacing=0,
    )
    burner_inserter = game.rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter

    belts = game.connect_entities(
        burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt
    )
    assert len(belts.outputs) == 1

    coal_to_boiler_belts = game.connect_entities(
        belts, coal_inserter.pickup_position, connection_type=Prototype.TransportBelt
    )
    assert coal_to_boiler_belts

    assembler = game.place_entity_next_to(
        Prototype.AssemblingMachine1,
        reference_position=steam_engine.position,
        direction=Direction.UP,
        spacing=5,
    )

    steam_engine_to_assembler_poles = game.connect_entities(
        assembler, steam_engine, connection_type=Prototype.SmallElectricPole
    )

    assert steam_engine_to_assembler_poles

    # insert coal into the drill
    burner_mining_drill: BurnerMiningDrill = game.insert_item(
        Prototype.Coal, burner_mining_drill, 5
    )

    game.sleep(60)

    # inspect assembler
    inspected_assembler = game.get_entity(
        Prototype.AssemblingMachine1, assembler.position
    )
    assert inspected_assembler.status == EntityStatus.NO_RECIPE

    image = game._render(position=assembler.position, layers=Layer.ALL)
    image.show()
    pass


def test_iron_smelting(game: FactorioInstance):
    """
    Create an auto driller for coal.
    Create a miner for iron ore and a nearby furnace. Connect the miner to the furnace.

    :return:
    """
    game.move_to(game.nearest(Resource.Coal))

    burner_mining_drill = game.place_entity(
        Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal)
    )
    burner_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=burner_mining_drill.position,
        direction=game.DOWN,
        spacing=0,
    )
    burner_inserter = game.rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter

    belts = game.connect_entities(
        burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt
    )
    assert belts

    burner_mining_drill: BurnerMiningDrill = game.insert_item(
        Prototype.Coal, burner_mining_drill, 5
    )

    assert burner_mining_drill.fuel[Prototype.Coal] == 5
    nearest_iron_ore = game.nearest(Resource.IronOre)

    game.move_to(nearest_iron_ore)
    try:
        iron_mining_drill = game.place_entity(
            Prototype.BurnerMiningDrill, position=nearest_iron_ore
        )
        stone_furnace = game.place_entity(
            Prototype.StoneFurnace, position=iron_mining_drill.drop_position.up()
        )

        coal_to_iron_drill_inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=iron_mining_drill.position,
            direction=game.DOWN,
            spacing=0,
        )
        coal_to_iron_drill_inserter = game.rotate_entity(
            coal_to_iron_drill_inserter, Direction.UP
        )
        coal_to_smelter_inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=stone_furnace.position,
            direction=game.RIGHT,
            spacing=0,
        )
        coal_to_smelter_inserter = game.rotate_entity(
            coal_to_smelter_inserter, Direction.LEFT
        )

        coal_to_drill_belt = game.connect_entities(
            coal_to_smelter_inserter.pickup_position,
            coal_to_iron_drill_inserter.pickup_position,
            connection_type=Prototype.TransportBelt,
        )

        game.connect_entities(
            belts, coal_to_drill_belt, connection_type=Prototype.TransportBelt
        )
        pass
    except Exception as e:
        print(e)
        assert False


def test_auto_driller(game: FactorioInstance):
    game.move_to(game.nearest(Resource.Coal))
    burner_mining_drill = game.place_entity(
        Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal)
    )

    burner_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=burner_mining_drill.position,
        direction=game.DOWN,
        spacing=0,
    )
    burner_inserter = game.rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter

    belts = game.connect_entities(
        burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt
    )
    assert belts

    game.insert_item(Prototype.Coal, burner_mining_drill, 5)
    game.move_to(burner_mining_drill.position.right().right().right())

    game.get_entities()
    start_score, _ = game.score()
    time.sleep(10)
    end_score, _ = game.score()

    assert end_score > start_score
