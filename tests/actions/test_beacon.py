"""
Beacon Action Tests

Tests verifying beacon placement and interaction with module effects.
"""

import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "beacon": 5,
            "speed-module": 10,
            "speed-module-2": 5,
            "efficiency-module": 10,
            "assembling-machine-1": 5,
            "small-electric-pole": 20,
        }
    )


def test_place_beacon(game):
    """Test basic beacon placement."""
    beacon = game.place_entity(Prototype.Beacon, position=Position(x=0, y=0))
    assert beacon is not None
    # Beacon is 3x3 so it centers at half-tile offsets
    assert beacon.position.is_close(Position(x=0.5, y=0.5))


def test_beacon_inventory_access(game):
    """Test that beacon count decrements on placement."""
    beacons_before = game.inspect_inventory()[Prototype.Beacon]
    game.place_entity(Prototype.Beacon, position=Position(x=0, y=0))
    beacons_after = game.inspect_inventory()[Prototype.Beacon]
    assert beacons_before - 1 == beacons_after


def test_place_multiple_beacons(game):
    """Test placing multiple beacons."""
    positions = [
        Position(x=0, y=0),
        Position(x=5, y=0),
        Position(x=10, y=0),
    ]
    beacons = []
    for pos in positions:
        game.move_to(pos)
        beacon = game.place_entity(Prototype.Beacon, position=pos)
        beacons.append(beacon)

    assert len(beacons) == 3
    for beacon in beacons:
        assert beacon is not None


def test_beacon_can_be_retrieved(game):
    """Test that placed beacon can be retrieved via get_entity."""
    beacon = game.place_entity(Prototype.Beacon, position=Position(x=0, y=0))
    retrieved = game.get_entity(Prototype.Beacon, beacon.position)
    assert retrieved is not None
    assert retrieved.position.x == beacon.position.x
    assert retrieved.position.y == beacon.position.y


def test_beacon_pickup(game):
    """Test picking up a beacon."""
    beacons_before = game.inspect_inventory()[Prototype.Beacon]
    beacon = game.place_entity(Prototype.Beacon, position=Position(x=0, y=0))
    game.pickup_entity(beacon)
    beacons_after = game.inspect_inventory()[Prototype.Beacon]
    assert beacons_before == beacons_after
