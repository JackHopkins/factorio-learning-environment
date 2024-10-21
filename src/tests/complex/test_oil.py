import pytest
from time import sleep
from factorio_entities import Position, ResourcePatch
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 10,
        'burner-mining-drill': 10,
        'electric-mining-drill': 5,
        'transport-belt': 200,
        'underground-belt': 20,
        'splitter': 10,
        'burner-inserter': 50,
        'fast-inserter': 20,
        'pipe': 100,
        'pipe-to-ground': 20,
        'offshore-pump': 5,
        'boiler': 5,
        'steam-engine': 10,
        'small-electric-pole': 50,
        'medium-electric-pole': 20,
        'assembling-machine-1': 10,
        'iron-chest': 20,
        'coal': 500,
        'iron-plate': 200,
        'copper-plate': 200,
        'pumpjack': 5
    }
    instance.reset()
    instance.add_command('/c game.surfaces[1].create_entity{name="crude-oil", position={x=0, y=0}}', raw=True)
    instance.execute_transaction()
    yield instance


def test_place_pump_jack(game):
    """Test placement of pump jack on oil patch."""
    oil_location = game.nearest(Resource.CrudeOil)
    pump_jack = game.place_entity(Prototype.PumpJack, position=oil_location)
    assembler = game.place_entity_next_to(Prototype.AssemblingMachine1, reference_position=pump_jack.position, direction=Direction.UP, spacing=1)

    game.connect_entities(pump_jack, assembler, Prototype.Pipe)
    pass