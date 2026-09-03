import pytest

from fle.env.game_types import Technology


@pytest.fixture()
def game(configure_game):
    return configure_game(all_technologies_researched=False)


def test_set_research(game):
    ingredients = game.set_research(Technology.Automation)
    assert ingredients[0].count == 10


def test_fail_to_research_locked_technology(game):
    current_research_ingredients = game.set_research(Technology.Automation)

    with pytest.raises(Exception) as exc_info:
        game.set_research(Technology.Automation2)

    message = str(exc_info.value)
    assert message.startswith(
        "Cannot start research for automation-2. Missing prerequisites:"
    )
    assert "automation" in message

    # A rejected research request must not cancel the research already underway.
    remaining_ingredients = game.get_research_progress()
    assert [ingredient.model_dump() for ingredient in remaining_ingredients] == [
        ingredient.model_dump() for ingredient in current_research_ingredients
    ]
