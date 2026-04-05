import pytest

from fle.env.game_types import Technology


@pytest.fixture()
def game(configure_game):
    return configure_game(all_technologies_researched=False)


def test_set_research(game):
    # Use SteamPower (no prerequisites in Factorio 2.0 tech tree)
    ingredients = game.set_research(Technology.SteamPower)
    assert ingredients[0].count > 0


def test_fail_to_research_locked_technology(game):
    try:
        game.set_research(Technology.Automation2)
    except Exception:
        assert True
        return
    assert False, "Was able to research locked technology. Expected exception."
