import pytest

from fle.env import FactorioInstance
from fle.env.game_types import Technology
from fle.commons.cluster_ips import get_local_container_ips


@pytest.fixture()
def game(instance):
    # game.initial_inventory = {'assembling-machine-1': 1}
    # from gym import FactorioInstance
    ips, udp_ports, tcp_ports = get_local_container_ips()
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=tcp_ports[-1],  # 27019,
        all_technologies_researched=False,
        fast=True,
        inventory={},
    )
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_set_research(game):
    ingredients = game.set_research(Technology.Automation)
    assert ingredients[0].count == 10


def test_fail_to_research_locked_technology(game):
    try:
        game.set_research(Technology.Automation2)
    except Exception:
        assert True
        return
    assert False, "Was able to research locked technology. Expected exception."
