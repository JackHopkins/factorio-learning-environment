import pytest

from fle.env.entities import Position, Entity
from fle.env import DirectionInternal as Direction
from fle.env.game_types import Prototype, Resource, RecipeName


@pytest.fixture()
def base_game(instance):
    instance.initial_inventory = {
        "pumpjack": 1,
        "pipe": 300,
        "burner-inserter": 6,
        "coal": 50,
        "boiler": 1,
        "steam-engine": 1,
        "small-electric-pole": 50,
        "offshore-pump": 1,
        "chemical-plant": 1,
        "oil-refinery": 1,
        "transport-belt": 50,
        "burner-mining-drill": 5,
    }
    instance.reset()
    instance.set_speed(10)
    yield instance.namespace


@pytest.fixture()
def game(base_game):
    """Create electricity system"""
    base_game.inspect_inventory()
    # move to the nearest water source
    water_location = base_game.nearest(Resource.Water)
    base_game.move_to(water_location)

    offshore_pump = base_game.place_entity(
        Prototype.OffshorePump, position=water_location
    )
    # Get offshore pump direction
    direction = offshore_pump.direction

    # place the boiler next to the offshore pump
    boiler = base_game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=direction,
        spacing=2,
    )
    assert boiler.direction.value == direction.value

    # rotate the boiler to face the offshore pump
    boiler = base_game.rotate_entity(boiler, Direction.next_clockwise(direction))

    # insert coal into the boiler
    base_game.insert_item(Prototype.Coal, boiler, quantity=5)

    # connect the boiler and offshore pump with a pipe
    base_game.connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)

    base_game.move_to(Position(x=0, y=10))
    steam_engine: Entity = base_game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler.position,
        direction=boiler.direction,
        spacing=1,
    )

    base_game.connect_entities(steam_engine, boiler, connection_type=Prototype.Pipe)

    yield base_game


def test_build_chemical_plant(game):
    # Start at the origin
    game.move_to(game.nearest(Resource.CrudeOil))
    pumpjack = game.place_entity(
        Prototype.PumpJack,
        direction=Direction.DOWN,
        position=game.nearest(Resource.CrudeOil),
    )

    # Start at the origin
    game.move_to(Position(x=0, y=-6))

    refinery = game.place_entity(
        Prototype.OilRefinery, direction=Direction.DOWN, position=Position(x=0, y=-6)
    )

    refinery = game.set_entity_recipe(refinery, RecipeName.AdvancedOilProcessing)
    # Start at the origin
    game.move_to(Position(x=0, y=0))

    chemical_plant = game.place_entity(
        Prototype.ChemicalPlant, direction=Direction.DOWN, position=Position(x=0, y=6)
    )
    chemical_plant = game.set_entity_recipe(chemical_plant, RecipeName.LightOilCracking)

    steam_engine = game.get_entity(
        Prototype.SteamEngine, game.nearest(Prototype.SteamEngine)
    )

    game.connect_entities(pumpjack, refinery, connection_type=Prototype.Pipe)
    game.connect_entities(refinery, chemical_plant, connection_type=Prototype.Pipe)
    game.connect_entities(
        pumpjack,
        refinery,
        chemical_plant,
        steam_engine,
        connection_type=Prototype.SmallElectricPole,
    )


# The game's own input ports of the chemical plant at (x, y): the point between
# each input port tile and the tile a pipe must occupy (FLE's connection point).
game_input_ports = """
local plant = game.surfaces[1].find_entities_filtered{{name = "chemical-plant", position = {{{x}, {y}}}}}[1]
local out = {{}}
for i = 1, #plant.fluidbox do
    local proto = plant.fluidbox.get_prototype(i)
    if proto.production_type == "input" then
        for _, pc in pairs(plant.fluidbox.get_pipe_connections(i)) do
            out[#out + 1] = ((pc.position.x + pc.target_position.x) / 2) .. ","
                .. ((pc.position.y + pc.target_position.y) / 2)
        end
    end
end
rcon.print(table.concat(out, ";"))
"""


@pytest.mark.parametrize(
    "direction", [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]
)
def test_chemical_plant_input_connection_points_match_game(base_game, direction):
    position = Position(x=0.5, y=6.5)
    base_game.move_to(position)
    plant = base_game.place_entity(
        Prototype.ChemicalPlant, direction=direction, position=position
    )
    plant = base_game.set_entity_recipe(plant, RecipeName.LightOilCracking)

    response = base_game.instance.rcon_client.send_command(
        "/sc " + game_input_ports.format(x=plant.position.x, y=plant.position.y)
    )
    expected = {
        (float(px), float(py))
        for px, py in (point.split(",") for point in response.split(";"))
    }
    reported = {(p.x, p.y) for p in plant.input_connection_points}
    assert reported == expected
