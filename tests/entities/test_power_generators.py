import pytest

from fle.env.game import Direction, EntityStatus
from fle.env.game.game_types import Prototype


@pytest.fixture()
def game(instance: FactorioInstance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "solar-panel": 3,
        "accumulator": 3,
        "steam-engine": 3,
        "small-electric-pole": 4,
    }
    instance.set_speed(10)
    instance.reset()
    yield instance.namespace


def test_solar_panel_charge_accumulator(game):
    solar_panel = game.place_entity(Prototype.SolarPanel)
    pole = game.place_entity_next_to(
        Prototype.SmallElectricPole, solar_panel.position, Direction.UP
    )
    game.place_entity_next_to(Prototype.Accumulator, pole.position, Direction.UP)
    game.sleep(1)
    accumulator = game.get_entities({Prototype.Accumulator})[0]
    assert accumulator.status == EntityStatus.CHARGING
