from fle.env.entities import (
    BeltGroup,
    Direction,
    Dimensions,
    ElectricityGroup,
    ElectricityPole,
    EntityStatus,
    Inventory,
    Pipe,
    PipeGroup,
    Position,
    TileDimensions,
    TransportBelt,
)
from fle.env.game_types import Prototype


def _dimensions() -> Dimensions:
    return Dimensions(width=1, height=1)


def _tile_dimensions() -> TileDimensions:
    return TileDimensions(tile_width=1, tile_height=1)


def _belt(x: float, y: float, **kwargs) -> TransportBelt:
    return TransportBelt(
        name="transport-belt",
        direction=kwargs.pop("direction", Direction.RIGHT),
        position=Position(x=x, y=y),
        energy=0,
        dimensions=_dimensions(),
        tile_dimensions=_tile_dimensions(),
        prototype=Prototype.TransportBelt,
        health=150,
        input_position=kwargs.pop("input_position", Position(x=x - 1, y=y)),
        output_position=kwargs.pop("output_position", Position(x=x + 1, y=y)),
        inventory=kwargs.pop("inventory", {"left": Inventory(), "right": Inventory()}),
        is_source=kwargs.pop("is_source", False),
        is_terminus=kwargs.pop("is_terminus", False),
        status=kwargs.pop("status", EntityStatus.WORKING),
        warnings=kwargs.pop("warnings", []),
        **kwargs,
    )


def _pipe(x: float, y: float, **kwargs) -> Pipe:
    return Pipe(
        name="pipe",
        direction=Direction.UP,
        position=Position(x=x, y=y),
        energy=0,
        dimensions=_dimensions(),
        tile_dimensions=_tile_dimensions(),
        prototype=Prototype.Pipe,
        health=100,
        status=kwargs.pop("status", EntityStatus.WORKING),
        fluidbox_id=kwargs.pop("fluidbox_id", 7),
        flow_rate=kwargs.pop("flow_rate", 12.5),
        contents=kwargs.pop("contents", 88.0),
        fluid=kwargs.pop("fluid", "water"),
        warnings=kwargs.pop("warnings", []),
        **kwargs,
    )


def _pole(x: float, y: float, **kwargs) -> ElectricityPole:
    return ElectricityPole(
        name="small-electric-pole",
        direction=Direction.UP,
        position=Position(x=x, y=y),
        energy=0,
        dimensions=_dimensions(),
        tile_dimensions=_tile_dimensions(),
        prototype=Prototype.SmallElectricPole,
        health=100,
        status=kwargs.pop("status", EntityStatus.NORMAL),
        electrical_id=kwargs.pop("electrical_id", 3),
        flow_rate=kwargs.pop("flow_rate", 42.0),
        warnings=kwargs.pop("warnings", []),
        **kwargs,
    )


def test_belt_group_connection_summary_is_machine_readable():
    source = _belt(0, 0, is_source=True, inventory={"left": Inventory(coal=2)})
    middle = _belt(1, 0)
    output = _belt(2, 0, is_terminus=True, inventory={"right": Inventory(iron_ore=1)})
    group = BeltGroup(
        id=0,
        position=source.position,
        status=EntityStatus.WORKING,
        belts=[source, middle, output],
        inputs=[source],
        outputs=[output],
        inventory=Inventory(coal=2, iron_ore=1),
    )

    summary = group.to_connection_dict()

    assert summary["type"] == "belt-group"
    assert summary["connection_kind"] == "transport"
    assert summary["status"] == "working"
    assert summary["belt_count"] == 3
    assert summary["inventory"] == {"coal": 2, "iron_ore": 1}
    assert summary["inputs"][0]["position"] == {"x": 0.0, "y": 0.0}
    assert summary["outputs"][0]["is_terminus"] is True
    assert summary["belts"][0]["prototype"] == {
        "id": "TransportBelt",
        "name": "transport-belt",
    }


def test_pipe_group_connection_summary_is_machine_readable():
    pipes = [_pipe(0, 0), _pipe(1, 0, contents=40.0)]
    group = PipeGroup(
        id=7,
        position=pipes[0].position,
        status=EntityStatus.WORKING,
        pipes=pipes,
    )

    summary = group.to_connection_dict()

    assert summary["type"] == "pipe-group"
    assert summary["connection_kind"] == "fluid"
    assert summary["fluid"] == "water"
    assert summary["pipe_count"] == 2
    assert summary["pipes"][0]["fluidbox_id"] == 7
    assert summary["pipes"][0]["flow_rate"] == 12.5


def test_electricity_group_connection_summary_is_machine_readable():
    poles = [_pole(0, 0, flow_rate=10.0), _pole(5, 0, flow_rate=25.0)]
    group = ElectricityGroup(
        id=3,
        position=Position(x=2.5, y=0),
        status=EntityStatus.WORKING,
        poles=poles,
    )

    summary = group.to_connection_dict()

    assert summary["type"] == "electricity-group"
    assert summary["connection_kind"] == "power"
    assert summary["electrical_id"] == 3
    assert summary["pole_count"] == 2
    assert summary["max_flow_rate"] == 25.0
    assert summary["poles"][1]["position"] == {"x": 5.0, "y": 0.0}
