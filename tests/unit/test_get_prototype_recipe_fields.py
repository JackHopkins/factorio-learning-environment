"""get_prototype_recipe keeps the recipe's time, category and enabled state. Server-free."""

from fle.env.tools.agent.get_prototype_recipe.client import GetPrototypeRecipe


def _tool(reply):
    tool = GetPrototypeRecipe.__new__(GetPrototypeRecipe)
    tool.player_index = 1
    tool.execute = lambda *args: (reply, 0)
    return tool


def test_recipe_fields_are_passed_through():
    # Shape of storage.utils.serialize_recipe's reply (numbers come back as strings)
    reply = {
        "name": "engine-unit",
        "category": "advanced-crafting",
        "enabled": False,
        "energy": "10",
        "ingredients": [
            {"name": "steel-plate", "amount": "1", "type": "item"},
            {"name": "iron-gear-wheel", "amount": "1", "type": "item"},
            {"name": "pipe", "amount": "2", "type": "item"},
        ],
        "products": [
            {"name": "engine-unit", "amount": "1", "type": "item", "probability": "1"}
        ],
    }
    recipe = _tool(reply)("engine-unit")

    assert recipe.energy == 10.0
    assert recipe.category == "advanced-crafting"
    assert recipe.enabled is False
    assert [i.name for i in recipe.ingredients] == [
        "steel-plate",
        "iron-gear-wheel",
        "pipe",
    ]


def test_enabled_recipe():
    reply = {
        "name": "iron-gear-wheel",
        "category": "crafting",
        "enabled": True,
        "energy": "0.5",
        "ingredients": [{"name": "iron-plate", "amount": "2", "type": "item"}],
        "products": [
            {
                "name": "iron-gear-wheel",
                "amount": "1",
                "type": "item",
                "probability": "1",
            }
        ],
    }
    recipe = _tool(reply)("iron-gear-wheel")

    assert recipe.energy == 0.5
    assert recipe.category == "crafting"
    assert recipe.enabled is True
