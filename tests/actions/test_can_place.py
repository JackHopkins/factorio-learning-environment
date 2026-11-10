from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource


def test_can_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place

    # attempt to place a pipe beyond the reach of the player
    can_place = game.can_place_entity(Prototype.Pipe, position=(100, 0))
    assert not can_place

    game.place_entity(Prototype.Pipe, position=(5, 0))
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert not can_place


def test_can_place_over_resources(game):
    copper_ore = game.nearest(Resource.CopperOre)
    game.move_to(copper_ore)
    can_build = game.can_place_entity(Prototype.BurnerMiningDrill, position=copper_ore)
    assert can_build


def test_can_place_over_player_large(game):
    game.move_to(Position(x=0, y=0))
    assert game.can_place_entity(Prototype.SteamEngine, position=Position(x=0, y=0))

    game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=0), direction=Direction.UP
    )


def test_can_place_depends_on_direction(game):
    # A steam engine is 3x5 facing UP and 5x3 facing RIGHT
    game.move_to(Position(x=0, y=6))
    engine = game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=0), direction=Direction.UP
    )
    position = engine.position
    assert game.pickup_entity(engine)

    # A pipe inside the vertical footprint only
    game.place_entity(Prototype.Pipe, position=Position(x=position.x, y=position.y + 2))

    assert not game.can_place_entity(
        Prototype.SteamEngine, direction=Direction.UP, position=position
    )
    assert game.can_place_entity(
        Prototype.SteamEngine, direction=Direction.RIGHT, position=position
    )
