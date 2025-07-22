import json
from pathlib import Path

import pytest

from fle.env.entities import Position, Layer
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "small-electric-pole": 20,
        "iron-plate": 10,
        "assembling-machine-1": 1,
        "pipe-to-ground": 10,
        'burner-inserter': 1,
        "pipe": 30,
        "transport-belt": 50,
        "underground-belt": 30,
        'splitter': 1,
        'lab': 1,
        'coal': 10,
        'iron-ore': 100
    }
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_blueprint_render(game):
    #image = game._render(position=Position(x=0, y=5), layers=Layer.ALL)
    #image.show()

    # Find all JSON files
    blueprints_path = Path("/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/fle/agents/data/blueprints_to_policies/blueprints/other")
    json_files = list(blueprints_path.glob("*.json"))

    # Load the JSON file
    with open(json_files[0], 'r') as f:
        blueprint_data = json.load(f)

        image = game._render(blueprint=blueprint_data)
        image.show()
    pass

def test_basic_render(game):
    game.reset()

    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))

    game.insert_item(Prototype.IronOre, chest, 100)

    entity = game.place_entity(Prototype.BurnerInserter, position=chest.position.above())
    game.insert_item(Prototype.Coal, entity, 10)

    game.place_entity(Prototype.Splitter, position=Position(x=5, y=0))

    game.place_entity(Prototype.Lab, position=Position(x=10, y=0))

    game.connect_entities(
        Position(x=0, y=-2),
        Position(x=15, y=5),
        {Prototype.TransportBelt, Prototype.UndergroundBelt},
    )

    game.connect_entities(
        Position(x=15, y=9),
        Position(x=0, y=2),
        {Prototype.TransportBelt, Prototype.UndergroundBelt},
    )

    game.connect_entities(
        Position(x=0, y=-10), Position(x=15, y=-10), {Prototype.SmallElectricPole}
    )

    #observation = game._observe_all(radius=20)
    #json_observation = json.dumps(observation)

    image = game._render(position=Position(x=0, y=5), layers=Layer.ALL)
    image.show()
    pass


def test_cliff_orientations(game):
    game.reset()

    # Clear existing cliffs
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end"
    )

    # Create all cliff orientations in a grid pattern
    game.instance.rcon_client.send_command(
        "/sc "
        "-- All possible cliff orientations\n"
        "local orientations = {"
        "  'west-to-east', 'north-to-south', 'east-to-west', 'south-to-north',"
        "  'west-to-north', 'north-to-east', 'east-to-south', 'south-to-west',"
        "  'west-to-south', 'north-to-west', 'east-to-north', 'south-to-east',"
        "  'west-to-none', 'none-to-east', 'east-to-none', 'none-to-west',"
        "  'north-to-none', 'none-to-south', 'south-to-none', 'none-to-north'"
        "} "

        "-- Place each orientation in a grid\n"
        "for i, orientation in ipairs(orientations) do "
        "  local row = math.floor((i-1) / 5) "
        "  local col = (i-1) % 5 "
        "  local x = col * 6 - 15 "
        "  local y = row * 6 - 10 "
        "  game.surfaces[1].create_entity{"
        "    name='cliff', "
        "    position={x=x, y=y}, "
        "    cliff_orientation=orientation"
        "  } "
        "  -- Add label (using flying text for visualization)\n"
        "  game.surfaces[1].create_entity{"
        "    name='flying-text', "
        "    position={x=x, y=y-2}, "
        "    text=orientation"
        "  } "
        "end"
    )

    # Create test patterns for each cliff type
    game.instance.rcon_client.send_command(
        "/sc "
        "-- Straight line (cliff-sides)\n"
        "for i=-3,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=20}, cliff_orientation='west-to-east'} "
        "end "

        "-- L-shaped outer corner (cliff-outer)\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-20, y=20}, cliff_orientation='west-to-north'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-18, y=20}, cliff_orientation='west-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-20, y=22}, cliff_orientation='north-to-south'} "

        "-- L-shaped inner corner (cliff-inner)\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=20, y=20}, cliff_orientation='north-to-south'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=20, y=22}, cliff_orientation='west-to-south'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=22, y=22}, cliff_orientation='west-to-east'} "

        "-- Terminal pieces (cliff-entrance)\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=30}, cliff_orientation='west-to-none'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-8, y=30}, cliff_orientation='west-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-6, y=30}, cliff_orientation='none-to-east'} "

        "-- T-junction pattern\n"
        "for i=-2,2 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=35}, cliff_orientation='west-to-east'} "
        "end "
        "for i=1,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=0, y=35+i*2}, cliff_orientation='north-to-south'} "
        "end"
    )

    image = game._render(position=Position(x=0, y=10), radius=40, layers=Layer.ALL)
    image.show()