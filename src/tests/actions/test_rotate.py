import pytest

from factorio_instance import Direction
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_rotate_boiler(game):
    # place the boiler next to the offshore pump
    from factorio_entities import Position
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=Position(x=0, y=0),
                                       direction=Direction.RIGHT,
                                       spacing=2)
    # orthogonal direction to the boiler
    orthogonal_direction = Direction.UP

    # rotate the boiler to face the offshore pump
    boiler = game.rotate_entity(boiler, orthogonal_direction)

    # assert that the boiler is facing the offshore pump
    assert boiler.direction == orthogonal_direction.value

def test_rotate_transport_belt(game):
    # Place a transport belt
    transport_belt = game.place_entity(Prototype.TransportBelt, position=(0, 0), direction=Direction.UP)
    rotate_entity(game, transport_belt)


def test_rotate_inserter(game):
    # Place a burner inserter
    inserter = game.place_entity(Prototype.BurnerInserter, position=(0, 0), direction=Direction.UP)
    rotate_entity(game, inserter)

def rotate_entity(game, entity):
    # Rotate the transport belt right
    entity = game.rotate_entity(entity, direction=Direction.RIGHT)

    # Assert that the direction of the transport belt has been updated
    assert entity.direction == Direction.RIGHT.value

    entity = game.rotate_entity(entity, direction=Direction.LEFT)

    assert entity.direction == Direction.LEFT.value

    entity = game.rotate_entity(entity, direction=Direction.DOWN)

    assert entity.direction == Direction.DOWN.value

    entity = game.rotate_entity(entity, direction=Direction.UP)

    assert entity.direction == Direction.UP.value

    game.reset()