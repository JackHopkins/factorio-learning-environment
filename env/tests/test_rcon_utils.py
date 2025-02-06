import pytest

from utils.rcon import _lua2python


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace

def test_lua_2_python():
    lua_response = '{ ["a"] = false,["b"] = [string "global.actions.place_entity_next_to = functio..."]:204: Cannot place entity at the position {x = -8.5, y = 20.5} with direction 2. Nearby entities: {},}'
    command = 'pcall(global.actions.place_entity_next_to, 1,"steam-engine",-11.5,20.0,1,0)'
    response, timing = _lua2python(command, lua_response)

    assert response['b'] == '"global.actions.place_entity_next_to = functio..."]:204: Cannot place entity at the position {x = -8.5, y = 20.5} with direction 2. Nearby entities: {}'