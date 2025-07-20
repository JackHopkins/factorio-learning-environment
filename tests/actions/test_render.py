import pytest

from fle.env.entities import Position, Layer
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "small-electric-pole": 20,
        "iron-plate": 10,
        "assembling-machine-1": 1,
        "pipe-to-ground": 10,
        "pipe": 30,
        "transport-belt": 50,
        "underground-belt": 30,
        'splitter': 1,
        'lab': 1
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_basic_render(game):
    game.instance.rcon_client.send_command(
        "/sc for i=1,5 do "
        "game.surfaces[1].create_entity{"
        "name='rock-huge', "
        "position={x=-10+i*4, y=-5}} "
        "end"
    )
    game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))

    game.place_entity(Prototype.Splitter, position=Position(x=5, y=0))

    game.place_entity(Prototype.Lab, position=Position(x=10, y=0))

    game.connect_entities(
        Position(x=0, y=-2),
        Position(x=15, y=5),
        {Prototype.TransportBelt, Prototype.UndergroundBelt},
    )

    game.connect_entities(
        Position(x=15, y=9),
        Position(x=0, y=2),
        {Prototype.TransportBelt, Prototype.UndergroundBelt},
    )

    game.connect_entities(
        Position(x=0, y=-10), Position(x=15, y=-10), {Prototype.SmallElectricPole}
    )

    #observation = game._observe_all(radius=20)
    #json_observation = json.dumps(observation)

    image = game._render(position=Position(x=0, y=5), layers=Layer.ALL)
    image.show()
    pass
