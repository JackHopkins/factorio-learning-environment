import pytest

from fle.env.utils.rcon import _lua2python


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace


def test_lua_2_python():
    lua_response = '{ ["a"] = false,["b"] = ["string global"],}'
    command = "pcall(global.actions.move_to,1,11.5,20)"
    response, timing = _lua2python(command, lua_response)

    assert response == {"a": False, "b": "string global", 2: "]"}
