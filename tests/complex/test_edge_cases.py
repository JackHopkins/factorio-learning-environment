import pytest
from time import monotonic
from fle.env.entities import Position, ResourcePatch, Direction, BuildingBox
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 10,
        "burner-mining-drill": 10,
        "electric-mining-drill": 5,
        "transport-belt": 200,
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
    edge_position = Position(x=1_000_000, y=1_000_000)
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

    # Verify that all drills were placed on the requested resource patch.
    # ElectricMiningDrill no longer exposes the old ``mining_target`` field.
    drills = [
        entity
        for entity in game.get_entities(
            position=iron_patch.bounding_box.left_top, radius=10
        )
        if entity.name == Prototype.ElectricMiningDrill.value[0]
    ]
    assert len(drills) == len(drill_positions)


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
    belt_count = 25
    for i in range(belt_count):
        position = Position(x=i, y=0)
        game.move_to(position)
        game.place_entity(Prototype.TransportBelt, position=position)

    # Rotate all belts
    belt_groups = game.get_entities(
        Prototype.TransportBelt, Position(x=0, y=0), radius=belt_count
    )
    belts = [belt for group in belt_groups for belt in group.belts]
    assert len(belts) == belt_count
    for belt in belts:
        game.rotate_entity(belt, Direction.LEFT)

    end_time = monotonic()
    assert (
        end_time - start_time < 60
    )  # Ensure operation completed in less than 1 minute of game time


def test_entity_interactions(game):
    """Test complex interactions between different types of entities."""
    # Create a small power network
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, Direction.RIGHT, spacing=1
    )
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, Direction.RIGHT, spacing=1
    )
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)

    # Create an assembly line
    assembler = game.place_entity_next_to(
        Prototype.AssemblingMachine1, steam_engine.position, Direction.DOWN, spacing=5
    )
    game.set_entity_recipe(assembler, Prototype.IronGearWheel)

    # Connect power
    game.connect_entities(steam_engine, assembler, Prototype.SmallElectricPole)

    # Insert materials directly so this test covers powered assembling without
    # also depending on inserter/chest timing (covered by dedicated tests).
    game.insert_item(Prototype.IronPlate, assembler, 50)
    game.insert_item(Prototype.Coal, boiler, 50)

    # Advance deterministic simulation time, rather than sleeping wall time.
    game.sleep(10)

    # Check if iron gear wheels were produced
    output_inventory = game.inspect_inventory(assembler)
    assert output_inventory[Prototype.IronGearWheel] > 0, (
        "No iron gear wheels were produced"
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
