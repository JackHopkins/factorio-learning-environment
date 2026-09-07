import pytest
from math import isqrt
from time import monotonic
from fle.env.entities import Position, ResourcePatch, Direction, BuildingBox
from fle.env.game_types import Prototype, Resource

FACTORIO_MAP_BOUNDARY = 1_000_000


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 10,
        "burner-mining-drill": 10,
        "electric-mining-drill": 5,
        "transport-belt": 1000,
        "underground-belt": 20,
        "splitter": 10,
        "burner-inserter": 50,
        "fast-inserter": 20,
        "pipe": 100,
        "pipe-to-ground": 20,
        "offshore-pump": 5,
        "boiler": 5,
        "steam-engine": 10,
        "small-electric-pole": 50,
        "medium-electric-pole": 20,
        "assembling-machine-1": 10,
        "iron-chest": 20,
        "coal": 500,
        "iron-plate": 200,
        "copper-plate": 200,
    }
    instance.reset()
    yield instance.namespace


def test_edge_case_entity_placement(game):
    """Test placement of entities at the edge of the map and in tight spaces."""
    # Place entity at map edge
    edge_position = Position(x=FACTORIO_MAP_BOUNDARY, y=FACTORIO_MAP_BOUNDARY)
    with pytest.raises(Exception):
        game.place_entity(Prototype.StoneFurnace, position=edge_position)

    # Place entities in a tight space
    game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
    game.place_entity(Prototype.StoneFurnace, position=Position(x=3, y=0))
    with pytest.raises(Exception):
        game.place_entity(Prototype.StoneFurnace, position=Position(x=1.5, y=0))


def test_complex_resource_patch_interaction(game):
    """Test interactions with resource patches of varying shapes and sizes."""
    iron_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )
    assert isinstance(iron_patch, ResourcePatch)

    # Place multiple drills on the same resource patch
    drill_positions = [
        iron_patch.bounding_box.left_top,
        Position(
            x=iron_patch.bounding_box.left_top.x + 3,
            y=iron_patch.bounding_box.left_top.y,
        ),
        Position(
            x=iron_patch.bounding_box.left_top.x,
            y=iron_patch.bounding_box.left_top.y + 3,
        ),
    ]

    for pos in drill_positions:
        game.move_to(pos)
        drill = game.place_entity(Prototype.ElectricMiningDrill, position=pos)
        assert drill is not None

    drills = [
        entity
        for entity in game.get_entities(
            position=iron_patch.bounding_box.left_top, radius=10
        )
        if entity.name == Prototype.ElectricMiningDrill.value[0]
    ]
    assert len(drills) == len(drill_positions)
    for drill in drills:
        assert {resource.name for resource in drill.resources} == {Resource.IronOre[0]}


def test_error_handling_and_invalid_inputs(game):
    """Test error handling for invalid inputs and operations."""
    # Try to place an entity of the wrong type
    with pytest.raises(ValueError):
        game.place_entity("invalid_entity", position=Position(x=0, y=0))

    # Try to set an invalid recipe
    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=5, y=5)
    )
    with pytest.raises(ValueError):
        game.set_entity_recipe(assembler, "invalid_recipe")


def test_performance_under_load(game):
    """Test performance when placing and manipulating many entities."""
    start_time = monotonic()

    # Place a large number of transport belts
    belt_count = 1000
    row_width = isqrt(belt_count)
    build_distance = int(
        float(
            game.instance.rcon_client.send_command(
                '/sc rcon.print(prototypes.entity["character"].build_distance)'
            )
        )
    )
    placements_per_move = max(1, build_distance - 1)
    for i in range(belt_count):
        row, column = divmod(i, row_width)
        position = Position(x=column, y=row)
        if column % placements_per_move == 0:
            game.move_to(position.down())
        game.place_entity(Prototype.TransportBelt, position=position)

    # Rotate all belts
    belts = game.get_entities(Prototype.TransportBelt)
    assert len(belts) == belt_count
    for belt in belts:
        game.rotate_entity(belt, Direction.LEFT)

    end_time = monotonic()
    assert end_time - start_time < 120


def test_entity_interactions(game):
    """Test complex interactions between different types of entities."""
    # Create a small power network
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler_box = game.nearest_buildable(
        Prototype.Boiler,
        BuildingBox(width=3, height=2),
        center_position=offshore_pump.position,
    )
    game.move_to(boiler_box.center)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_box.center)
    steam_engine_box = game.nearest_buildable(
        Prototype.SteamEngine,
        BuildingBox(width=3, height=5),
        center_position=boiler.position,
    )
    game.move_to(steam_engine_box.center)
    steam_engine = game.place_entity(
        Prototype.SteamEngine, position=steam_engine_box.center
    )
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)

    # Create an assembly line
    assembler = game.place_entity_next_to(
        Prototype.AssemblingMachine1, steam_engine.position, Direction.DOWN, spacing=5
    )
    game.set_entity_recipe(assembler, Prototype.IronGearWheel)

    input_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        assembler.position,
        Direction.LEFT,
        spacing=0,
    )
    input_inserter = game.rotate_entity(input_inserter, Direction.RIGHT)
    input_chest = game.place_entity_next_to(
        Prototype.IronChest,
        input_inserter.position,
        Direction.LEFT,
        spacing=0,
    )
    output_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        assembler.position,
        Direction.RIGHT,
        spacing=0,
    )
    output_chest = game.place_entity_next_to(
        Prototype.IronChest,
        output_inserter.position,
        Direction.RIGHT,
        spacing=0,
    )

    game.connect_entities(steam_engine, assembler, Prototype.SmallElectricPole)

    game.insert_item(Prototype.Coal, input_inserter, 10)
    game.insert_item(Prototype.Coal, output_inserter, 10)
    game.insert_item(Prototype.IronPlate, input_chest, 50)
    game.insert_item(Prototype.Coal, boiler, 50)

    game.sleep(30)

    output_inventory = game.inspect_inventory(output_chest)
    assembler = game.get_entity(Prototype.AssemblingMachine1, assembler.position)
    input_inserter = game.get_entity(Prototype.BurnerInserter, input_inserter.position)
    output_inserter = game.get_entity(
        Prototype.BurnerInserter, output_inserter.position
    )
    assert output_inventory[Prototype.IronGearWheel] > 0, (
        "No iron gear wheels reached the output chest: "
        f"assembler_status={assembler.status}, "
        f"input_inserter_status={input_inserter.status}, "
        f"output_inserter_status={output_inserter.status}, "
        f"input_inventory={game.inspect_inventory(input_chest)}, "
        f"output_inventory={output_inventory}"
    )


@pytest.mark.skip(reason="public blueprint creation API has been removed")
def test_blueprint_functionality(game):
    """Test creating, saving, and loading blueprints."""
    # Create a simple setup
    game.move_to(Position(x=0, y=0))
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace.position, Direction.UP, spacing=1
    )
    chest = game.place_entity_next_to(
        Prototype.IronChest, inserter.position, Direction.UP, spacing=1
    )

    # Create a blueprint of the setup
    blueprint = game.create_blueprint([furnace, inserter, chest])
    assert blueprint is not None

    # Clear the area
    game.clear_area(Position(x=-5, y=-5), Position(x=5, y=5))

    # Load the blueprint at a different location
    game.load_blueprint(blueprint, Position(x=10, y=10))

    # Verify that entities were placed correctly
    placed_entities = game.inspect_entities(Position(x=10, y=10), radius=5)
    assert len(placed_entities.entities) == 3
    assert any(e.prototype == Prototype.StoneFurnace for e in placed_entities.entities)
    assert any(
        e.prototype == Prototype.BurnerInserter for e in placed_entities.entities
    )
    assert any(e.prototype == Prototype.IronChest for e in placed_entities.entities)


def test_break_7(game):
    game.instance.initial_inventory = {
        "coal": 200,
        "burner-mining-drill": 10,
        "wooden-chest": 10,
        "burner-inserter": 10,
        "transport-belt": 200,
        "stone-furnace": 5,
        "boiler": 4,
        "offshore-pump": 3,
        "steam-engine": 2,
        "iron-gear-wheel": 22,
        "iron-plate": 19,
        "copper-plate": 52,
        "electronic-circuit": 99,
        "iron-ore": 62,
        "stone": 50,
        "electric-mining-drill": 10,
        "small-electric-pole": 200,
        "pipe": 100,
        "assembling-machine-1": 5,
    }
    game.instance.reset(reset_position=True)

    # Find water and place offshore pump
    water_pos = game.nearest(Resource.Water)
    print(f"Found water at {water_pos}")
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {offshore_pump.position}")

    # Place boiler with spacing for pipes
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=Direction.RIGHT,
        spacing=3,
    )
    print(f"Placed boiler at {boiler.position}")

    # Add steam engine with spacing
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler.position,
        direction=Direction.RIGHT,
        spacing=3,
    )
    print(f"Placed steam engine at {steam_engine.position}")

    # Connect with pipes
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)

    # Fuel the boiler
    boiler = game.insert_item(Prototype.Coal, boiler, quantity=50)

    # Log positions for future reference
    print(
        f"Power system positions - Pump: {offshore_pump.position}, Boiler: {boiler.position}, Engine: {steam_engine.position}"
    )

    iron_pos = game.nearest(Resource.IronOre)
    print(f"Found iron ore at {iron_pos}")

    # Place drills individually with smaller building boxes so this regression
    # does not depend on exact coordinates in a particular generated map.
    drills = []
    for _ in range(3):
        drill_box = game.nearest_buildable(
            Prototype.ElectricMiningDrill,
            BuildingBox(width=3, height=3),
            center_position=iron_pos,
        )
        game.move_to(drill_box.center)
        drills.append(
            game.place_entity(Prototype.ElectricMiningDrill, position=drill_box.center)
        )
    # Connect power from steam engine to drills
    # First place pole near steam engine
    game.move_to(steam_engine.position)
    first_pole = game.place_entity(
        Prototype.SmallElectricPole,
        position=Position(x=steam_engine.position.x, y=steam_engine.position.y - 3),
    )
    print(f"Placed first power pole at {first_pole.position}")

    # Connect power to all drills using small electric poles
    for drill in drills:
        game.connect_entities(drill, first_pole, Prototype.SmallElectricPole)
        print(f"Connected power to drill at {drill.position}")

    pass


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
