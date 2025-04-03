import pytest

from entities import Position, Furnace
from instance import Direction, FactorioInstance
from game_types import Prototype, Resource



@pytest.fixture()
def game(instance):
    instance.initial_inventory = {}
    instance.reset()
    yield instance.namespace
    instance.reset()
def test_get_information(game):
    """
    Test to see if we can get a page info using the query_information tool
    :param game:
    :return:
    """
    # Check initial inventory
    page_id = "how_to_connect_entities"
    content = game.query_information(page_id)
    assert content

def test_get_nonexistent_information(game):
    """
    Test to see if the tool errors out when asking for nonexistent information
    :param game:
    :return:
    """
    # Check initial inventory
    page_id = "something_really_random"
    errors = False
    try:
        content = game.query_information(page_id)
    except AssertionError:
        errors = True
    assert errors, "Query information tool should have errored out"