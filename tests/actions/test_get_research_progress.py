import pytest

from fle.env import FactorioInstance
from fle.env.game_types import Technology
from fle.commons.cluster_ips import get_local_container_ips


@pytest.fixture()
def game(instance):
    # game.initial_inventory = {'assembling-machine-1': 1}
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


def test_get_research_progress_automation(game):
    ingredients = game.get_research_progress(Technology.Automation)
    assert ingredients[0].count == 10


def test_get_research_progress_none_fail(game):
    try:
        game.get_research_progress()
    except:
        assert True
        return

    assert False, (
        "Need to set research before calling get_research_progress() without an argument"
    )


def test_get_research_progress_none(game):
    ingredients1 = game.set_research(Technology.Automation)
    ingredients2 = game.get_research_progress()

    assert len(ingredients1) == len(ingredients2)
