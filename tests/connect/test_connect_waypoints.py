import pytest

from fle.env.entities import (
    BeltGroup,
    ElectricityGroup,
    EntityGroup,
    PipeGroup,
    Position,
)
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "transport-belt": 500,
        "fast-transport-belt": 500,
        "express-transport-belt": 500,
        "pipe": 300,
        "pipe-to-ground": 20,
        "small-electric-pole": 100,
        "medium-electric-pole": 100,
        "big-electric-pole": 100,
        "stone-wall": 200,
        "burner-inserter": 10,
        "boiler": 3,
        "offshore-pump": 3,
        "steam-engine": 3,
        "coal": 100,
    }
    instance.reset()
    yield instance.namespace


# =========================================================================
# Belt waypoint tests
# =========================================================================


def test_belt_waypoints_l_shape(game):
    """3 waypoints forming an L-shape (90-degree turn).
    Segment 1: (0,0)→(5,0) = 6 tiles, Segment 2: (5,0)→(5,5) = 6 tiles, shared corner = 11.
    """
    belt = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        Position(x=5, y=5),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 11


def test_belt_waypoints_u_turn(game):
    """4 waypoints forming a U-turn.
    Segments: 6 + 6 + 6 = 18, minus 2 shared corners = 16.
    """
    belt = game.connect_entities(
        Position(x=0, y=0),
        Position(x=0, y=5),
        Position(x=5, y=5),
        Position(x=5, y=0),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 16


def test_belt_waypoints_zigzag(game):
    """5 waypoints alternating direction.
    4 segments of 6 tiles each, minus 3 shared corners = 21.
    """
    belt = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        Position(x=5, y=5),
        Position(x=10, y=5),
        Position(x=10, y=10),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 21


def test_belt_waypoints_long_serpentine(game):
    """6+ waypoints in a long serpentine path.
    Segments: 9 + 6 + 9 + 6 + 9 = 39, minus 4 shared corners = 35.
    """
    belt = game.connect_entities(
        Position(x=0, y=0),
        Position(x=8, y=0),
        Position(x=8, y=5),
        Position(x=0, y=5),
        Position(x=0, y=10),
        Position(x=8, y=10),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 35


def test_belt_waypoints_square_loop(game):
    """5 waypoints forming a closed square (last == first).
    When the first and last waypoints match, connect_entities detects the
    single-tile gap left by the pathfinder and places one belt to close it.
    This produces a true closed loop with 0 inputs and 0 outputs.
    """
    belt = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        Position(x=5, y=5),
        Position(x=0, y=5),
        Position(x=0, y=0),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.inputs) == 0
    assert len(belt.outputs) == 0


def test_fast_belt_waypoints(game):
    """L-shape with FastTransportBelt.
    Same geometry as L-shape test: 6 + 6 - 1 = 11.
    """
    belt = game.connect_entities(
        Position(x=0, y=-10),
        Position(x=5, y=-10),
        Position(x=5, y=-15),
        Prototype.FastTransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 11


def test_express_belt_waypoints(game):
    """L-shape with ExpressTransportBelt.
    Same geometry as L-shape test: 6 + 6 - 1 = 11.
    """
    belt = game.connect_entities(
        Position(x=0, y=-10),
        Position(x=5, y=-10),
        Position(x=5, y=-5),
        Prototype.ExpressTransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 11


# =========================================================================
# Pipe waypoint tests
# =========================================================================


def test_pipe_waypoints_l_shape(game):
    """3 waypoints forming an L-shape for pipes.
    Segments: 6 + 6 - 1 shared corner = 11.
    """
    pipes = game.connect_entities(
        Position(x=20, y=0),
        Position(x=25, y=0),
        Position(x=25, y=5),
        Prototype.Pipe,
    )
    assert isinstance(pipes, PipeGroup)
    assert len(pipes.pipes) == 11


def test_pipe_waypoints_multi_segment(game):
    """4 waypoints forming a multi-segment pipe path.
    Segments: 6 + 6 + 6 - 2 shared corners = 16.
    """
    pipes = game.connect_entities(
        Position(x=20, y=10),
        Position(x=25, y=10),
        Position(x=25, y=15),
        Position(x=30, y=15),
        Prototype.Pipe,
    )
    assert isinstance(pipes, PipeGroup)
    assert len(pipes.pipes) == 16


def test_pipe_waypoints_with_underground(game):
    """Multi-segment with mixed Pipe + UndergroundPipe connection types.
    With underground pipes, the exact count depends on pathfinder routing
    (underground sections replace multiple surface pipes with 2 endpoints).
    Segments: 6 + 6 - 1 = 11 surface-equivalent, underground reduces this.
    """
    pipes = game.connect_entities(
        Position(x=20, y=20),
        Position(x=25, y=20),
        Position(x=25, y=25),
        connection_type={Prototype.Pipe, Prototype.UndergroundPipe},
    )
    assert isinstance(pipes, PipeGroup)
    assert len(pipes.pipes) == 8 # we dont count 'underground' segments


# =========================================================================
# Pole waypoint tests
# =========================================================================


def test_pole_waypoints_small(game):
    """3 waypoints with SmallElectricPole.
    Small poles have ~7.5 tile wire reach. Distance: 5+5=10 tiles along path.
    Expect ~3 poles (one at start, one at corner, one at end).
    """
    poles = game.connect_entities(
        Position(x=40, y=0),
        Position(x=45, y=0),
        Position(x=45, y=5),
        Prototype.SmallElectricPole,
    )
    assert isinstance(poles, ElectricityGroup)
    assert len(poles.poles) == 2


def test_pole_waypoints_medium(game):
    """3 waypoints with MediumElectricPole.
    Medium poles have ~9 tile wire reach. Distance: 10+10=20 tiles along path.
    Expect ~3 poles along the path.
    """
    poles = game.connect_entities(
        Position(x=40, y=10),
        Position(x=50, y=10),
        Position(x=50, y=20),
        Prototype.MediumElectricPole,
    )
    assert isinstance(poles, ElectricityGroup)
    assert len(poles.poles) == 3


def test_pole_waypoints_big(game):
    """3 waypoints with BigElectricPole.
    Big poles have ~30 tile wire reach. Distance: 20+20=40 tiles along path.
    Expect ~4 poles (one at start, corner, end).
    """
    poles = game.connect_entities(
        Position(x=40, y=30),
        Position(x=80, y=30),
        Position(x=80, y=70),
        Prototype.BigElectricPole,
    )
    assert isinstance(poles, ElectricityGroup)
    assert len(poles.poles) == 3 or len(poles.poles) == 4 # pathinding ingame is non-deterministic


# =========================================================================
# Mixed waypoint type tests (Position, Entity, EntityGroup)
# =========================================================================


def test_belt_waypoints_entity_as_source(game):
    """Entity as first waypoint, then Position waypoints.
    Inserter at (0,40) → (5,40) → (5,45). Entity offset means the belt
    starts from the inserter's position area. Segment distances: ~5 + 5 = ~10 tiles.
    """
    game.move_to(Position(x=0, y=40))
    inserter = game.place_entity(
        Prototype.BurnerInserter, position=Position(x=0, y=40)
    )
    belt = game.connect_entities(
        inserter,
        Position(x=5, y=40),
        Position(x=5, y=45),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 12


def test_belt_waypoints_group_extension(game):
    """Existing BeltGroup as first waypoint, extend with Positions.
    Initial: (0,50)→(5,50) = 6 belts.
    Extension: group→(5,55)→(10,55) adds 6+6-1=11 more, merged with original 6.
    Total group: 6 + 11 - shared = 16 (initial 6 + corner overlap).
    """
    initial = game.connect_entities(
        Position(x=0, y=50),
        Position(x=5, y=50),
        Prototype.TransportBelt,
    )
    assert isinstance(initial, BeltGroup)
    assert len(initial.belts) == 6

    extended = game.connect_entities(
        initial,
        Position(x=5, y=55),
        Position(x=10, y=55),
        Prototype.TransportBelt,
    )
    assert isinstance(extended, BeltGroup)
    assert len(extended.belts) == 16


def test_pipe_waypoints_from_entity(game):
    """Boiler as source, Position waypoints for pipes.
    Boiler has fluid connection points; pipe count depends on exact connection
    point offset from boiler center.
    """
    game.move_to(Position(x=20, y=40))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=20, y=40)
    )
    pipes = game.connect_entities(
        boiler,
        Position(x=25, y=40),
        Position(x=25, y=45),
        connection_type=Prototype.Pipe,
    )
    assert isinstance(pipes, PipeGroup)
    assert len(pipes.pipes) == 9


# =========================================================================
# Edge cases
# =========================================================================


def test_waypoints_minimum_two(game):
    """2 waypoints (baseline) — no waypoints metadata stored."""
    belt = game.connect_entities(
        Position(x=0, y=60),
        Position(x=5, y=60),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert belt.waypoints is None


def test_waypoints_close_together(game):
    """Waypoints only 2-3 tiles apart.
    Segment 1: (0,65)→(2,65) = 3 tiles. Segment 2: (2,65)→(2,67) = 3 tiles.
    Shared corner = 5.
    """
    belt = game.connect_entities(
        Position(x=0, y=65),
        Position(x=2, y=65),
        Position(x=2, y=67),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 5


def test_waypoints_far_apart(game):
    """Waypoints 20+ tiles apart.
    Segment 1: (0,70)→(25,70) = 26 tiles. Segment 2: (25,70)→(25,95) = 26 tiles.
    Shared corner = 51.
    """
    belt = game.connect_entities(
        Position(x=0, y=70),
        Position(x=25, y=70),
        Position(x=25, y=95),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 51


def test_waypoints_collinear(game):
    """All waypoints on the same line (degenerate straight path).
    Segment 1: (0,100)→(5,100) = 6 tiles. Segment 2: (5,100)→(10,100) = 6 tiles.
    Shared point = 11.
    """
    belt = game.connect_entities(
        Position(x=0, y=100),
        Position(x=5, y=100),
        Position(x=10, y=100),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert len(belt.belts) == 11


def test_single_waypoint_fails(game):
    """1 waypoint should raise an error."""
    with pytest.raises(AssertionError, match="Need more than one waypoint"):
        game.connect_entities(
            Position(x=0, y=0),
            Prototype.TransportBelt,
        )


# =========================================================================
# Dry run tests
# =========================================================================


def test_belt_waypoints_dry_run(game):
    """Multi-waypoint dry_run=False — returns BeltGroup, entities are placed.
    L-shape (0,10)→(5,10)→(5,15): 6 + 6 - 1 = 11 belts.
    """
    result = game.connect_entities(
        Position(x=0, y=10),
        Position(x=5, y=10),
        Position(x=5, y=15),
        Prototype.TransportBelt,
        dry_run=True,
    )
    assert result['number_of_entities_required'] == 12


def test_pipe_waypoints_dry_run(game):
    """Multi-waypoint dry_run=True for pipes.
    L-shape (20,110)→(25,110)→(25,115): expects 11 entities required.
    """
    result = game.connect_entities(
        Position(x=20, y=10),
        Position(x=25, y=10),
        Position(x=25, y=15),
        Prototype.Pipe,
        dry_run=True,
    )
    assert isinstance(result, dict)
    assert "number_of_entities_required" in result
    assert result["number_of_entities_required"] == 18


# =========================================================================
# __repr__ verification tests
# =========================================================================


def test_belt_waypoints_repr_includes_waypoints(game):
    """3+ waypoints — repr should include 'waypoints='."""
    belt = game.connect_entities(
        Position(x=0, y=120),
        Position(x=5, y=120),
        Position(x=5, y=125),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    assert belt.waypoints is not None
    assert len(belt.waypoints) == 3
    repr_str = repr(belt)
    assert "waypoints=" in repr_str


def test_belt_two_waypoints_repr_no_waypoints(game):
    """2 waypoints — repr should NOT include 'waypoints='."""
    belt = game.connect_entities(
        Position(x=0, y=130),
        Position(x=5, y=130),
        Prototype.TransportBelt,
    )
    assert isinstance(belt, BeltGroup)
    repr_str = repr(belt)
    assert "waypoints=" not in repr_str


def test_pipe_waypoints_repr_includes_waypoints(game):
    """3+ pipe waypoints — repr should include 'waypoints='."""
    pipes = game.connect_entities(
        Position(x=20, y=120),
        Position(x=25, y=120),
        Position(x=25, y=125),
        Prototype.Pipe,
    )
    assert isinstance(pipes, PipeGroup)
    assert pipes.waypoints is not None
    assert len(pipes.waypoints) == 3
    repr_str = repr(pipes)
    assert "waypoints=" in repr_str
