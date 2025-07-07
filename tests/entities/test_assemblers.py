import pytest

from fle.env import Direction, Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "solar-panel": 3,
        "accumulator": 3,
        "steam-engine": 3,
        "small-electric-pole": 4,
        "assembling-machine-2": 2,
        "offshore-pump": 1,
        "pipe": 100,
        "storage-tank": 4,
        "stone-brick": 20,
        "iron-ore": 20,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace


def test_solar_panel_charge_accumulator(game):
    assembly_pos = Position(x=0, y=0)
    game.move_to(assembly_pos)
    ass_machine = game.place_entity(Prototype.AssemblingMachine2, position=assembly_pos)
    ass_machine = game.set_entity_recipe(ass_machine, Prototype.Concrete)
    # Find water for power generation
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place offshore pump
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {pump.position}")
    group = game.connect_entities(pump, ass_machine, Prototype.Pipe)
    print(f"Connected ass_machine to water {ass_machine.position} with {group}")

    game.sleep(5)
    ass_machine = game.get_entity(Prototype.AssemblingMachine2, ass_machine.position)
    assert len(ass_machine.fluid_box) != 0


def test_assembler_2_connect_to_storage(game):
    for direction in [Direction.UP, Direction.LEFT, Direction.RIGHT, Direction.DOWN]:
        assembly_pos = Position(x=-37, y=-15.5)
        game.move_to(assembly_pos)
        ass_machine = game.place_entity(
            Prototype.AssemblingMachine2,
            position=assembly_pos,
            direction=Direction.LEFT,
        )
        game.set_entity_recipe(entity=ass_machine, prototype=Prototype.Concrete)
        ass_machine = game.rotate_entity(ass_machine, direction)

        tank_pos = Position(x=-37, y=6.5)
        game.move_to(tank_pos)
        tank = game.place_entity(
            Prototype.StorageTank, position=tank_pos, direction=direction
        )
        print(f"Placed storage tank at {tank.position}")
        game.connect_entities(tank, ass_machine, Prototype.Pipe)
        game.instance.reset()


def test_assembler_2_concrete(game):
    assembly_pos = Position(x=-37, y=-15.5)
    game.move_to(assembly_pos)
    ass_machine = game.place_entity(
        Prototype.AssemblingMachine2, position=assembly_pos, direction=Direction.LEFT
    )
    game.set_entity_recipe(entity=ass_machine, prototype=Prototype.Concrete)
    game.insert_item(Prototype.StoneBrick, ass_machine, 20)
    game.insert_item(Prototype.IronOre, ass_machine, 20)

    game.move_to(Position(x=-27, y=-15.5))
    panel = game.place_entity(Prototype.SolarPanel, position=Position(x=-27, y=-15.5))
    game.connect_entities(panel, ass_machine, Prototype.SmallElectricPole)

    pump_pos = game.nearest(Resource.Water)
    game.move_to(pump_pos)
    pump = game.place_entity(Prototype.OffshorePump, position=pump_pos)
    print(f"Placed pump at {pump_pos}")
    game.connect_entities(pump, ass_machine, Prototype.Pipe)

    game.sleep(40)

    assembly_machine = game.get_entity(
        Prototype.AssemblingMachine2, ass_machine.position
    )
    output_inventory = assembly_machine.assembling_machine_output
    concrete = output_inventory["concrete"]
    assert concrete > 0
