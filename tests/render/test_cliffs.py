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
        "pipe": 30,
        "transport-belt": 50,
        "underground-belt": 30,
        "splitter": 1,
        "lab": 1,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def clear_terrain(game):
    """Clear cliffs and rocks before each test"""
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end "
        "for _, rock in pairs(game.surfaces[1].find_entities_filtered{type='simple-entity'}) do "
        "if rock.name:find('rock') then rock.destroy() end "
        "end"
    )
    return game


def test_cliff_straight_lines(clear_terrain):
    """Test straight cliff formations (cliff-sides)"""
    game = clear_terrain

    # Create horizontal cliff line
    game.instance.rcon_client.send_command(
        "/sc "
        "for i=-5,5 do "
        "game.surfaces[1].create_entity{"
        "name='cliff', "
        "position={x=i*2, y=0}, "
        "cliff_orientation='west-to-east'} "
        "end"
    )

    # Create vertical cliff line
    game.instance.rcon_client.send_command(
        "/sc "
        "for i=-5,5 do "
        "game.surfaces[1].create_entity{"
        "name='cliff', "
        "position={x=0, y=i*2}, "
        "cliff_orientation='north-to-south'} "
        "end"
    )

    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    image.show()  # Uncomment to view
    assert image is not None


def test_cliff_outer_corners(clear_terrain):
    """Test outer corner cliff formations (cliff-outer)"""
    game = clear_terrain

    # Create L-shaped outer corners for all 4 orientations
    game.instance.rcon_client.send_command(
        "/sc "
        "-- Bottom-left outer corner\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=0}, cliff_orientation='west-to-north'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-8, y=0}, cliff_orientation='west-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=2}, cliff_orientation='north-to-south'} "
        "-- Bottom-right outer corner\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=0}, cliff_orientation='north-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=8, y=0}, cliff_orientation='east-to-west'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=2}, cliff_orientation='north-to-south'} "
        "-- Top-right outer corner\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=10}, cliff_orientation='east-to-south'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=8, y=10}, cliff_orientation='east-to-west'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=8}, cliff_orientation='south-to-north'} "
        "-- Top-left outer corner\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=10}, cliff_orientation='south-to-west'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-8, y=10}, cliff_orientation='west-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=8}, cliff_orientation='south-to-north'} "
    )

    image = game._render(position=Position(x=0, y=5), radius=15, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_cliff_inner_corners(clear_terrain):
    """Test inner corner cliff formations (cliff-inner)"""
    game = clear_terrain

    # Create inner corners
    game.instance.rcon_client.send_command(
        "/sc "
        "-- Create a box with inner corners\n"
        "-- Top edge\n"
        "for i=-3,3 do "
        "  if i ~= 0 then "
        "    game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=-6}, cliff_orientation='west-to-east'} "
        "  end "
        "end "
        "-- Bottom edge\n"
        "for i=-3,3 do "
        "  if i ~= 0 then "
        "    game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=6}, cliff_orientation='west-to-east'} "
        "  end "
        "end "
        "-- Left edge\n"
        "for i=-2,2 do "
        "  if i ~= 0 then "
        "    game.surfaces[1].create_entity{name='cliff', position={x=-6, y=i*2}, cliff_orientation='north-to-south'} "
        "  end "
        "end "
        "-- Right edge\n"
        "for i=-2,2 do "
        "  if i ~= 0 then "
        "    game.surfaces[1].create_entity{name='cliff', position={x=6, y=i*2}, cliff_orientation='north-to-south'} "
        "  end "
        "end "
        "-- Inner corners\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-6, y=-6}, cliff_orientation='west-to-south'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=6, y=-6}, cliff_orientation='south-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=6, y=6}, cliff_orientation='east-to-north'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-6, y=6}, cliff_orientation='north-to-west'} "
    )

    image = game._render(position=Position(x=0, y=0), radius=10, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_cliff_terminals(clear_terrain):
    """Test terminal cliff pieces (cliff-entrance)"""
    game = clear_terrain

    # Create all terminal orientations
    game.instance.rcon_client.send_command(
        "/sc "
        "-- Terminals ending in each direction\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-6, y=0}, cliff_orientation='west-to-none'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=6, y=0}, cliff_orientation='east-to-none'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=0, y=-6}, cliff_orientation='north-to-none'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=0, y=6}, cliff_orientation='south-to-none'} "
        "-- Terminals starting from each direction\n"
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=10}, cliff_orientation='none-to-east'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=10}, cliff_orientation='none-to-west'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=-10, y=-10}, cliff_orientation='none-to-south'} "
        "game.surfaces[1].create_entity{name='cliff', position={x=10, y=-10}, cliff_orientation='none-to-north'} "
    )

    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_cliff_t_junctions(clear_terrain):
    """Test T-junction cliff formations"""
    game = clear_terrain

    # Create T-junctions in all 4 orientations
    game.instance.rcon_client.send_command(
        "/sc "
        "-- T-junction pointing up\n"
        "for i=-2,2 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=0}, cliff_orientation='west-to-east'} "
        "end "
        "for i=1,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=0, y=-i*2}, cliff_orientation='north-to-south'} "
        "end "
        "-- T-junction pointing down\n"
        "for i=-2,2 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=10}, cliff_orientation='west-to-east'} "
        "end "
        "for i=1,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=0, y=10+i*2}, cliff_orientation='north-to-south'} "
        "end "
        "-- T-junction pointing right\n"
        "for i=-2,2 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=-10, y=i*2}, cliff_orientation='north-to-south'} "
        "end "
        "for i=1,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=-10+i*2, y=0}, cliff_orientation='west-to-east'} "
        "end "
        "-- T-junction pointing left\n"
        "for i=-2,2 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=10, y=i*2}, cliff_orientation='north-to-south'} "
        "end "
        "for i=1,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=10-i*2, y=0}, cliff_orientation='west-to-east'} "
        "end "
    )

    image = game._render(position=Position(x=0, y=5), radius=20, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_cliff_all_orientations_grid(clear_terrain):
    """Test all 20 cliff orientations in a grid layout"""
    game = clear_terrain

    game.instance.rcon_client.send_command(
        "/sc "
        "local orientations = {"
        "  'west-to-east', 'north-to-south', 'east-to-west', 'south-to-north',"
        "  'west-to-north', 'north-to-east', 'east-to-south', 'south-to-west',"
        "  'west-to-south', 'north-to-west', 'east-to-north', 'south-to-east',"
        "  'west-to-none', 'none-to-east', 'east-to-none', 'none-to-west',"
        "  'north-to-none', 'none-to-south', 'south-to-none', 'none-to-north'"
        "} "
        "for i, orientation in ipairs(orientations) do "
        "  local row = math.floor((i-1) / 5) "
        "  local col = (i-1) % 5 "
        "  local x = col * 4 - 8 "
        "  local y = row * 4 - 6 "
        "  game.surfaces[1].create_entity{"
        "    name='cliff', "
        "    position={x=x, y=y}, "
        "    cliff_orientation=orientation"
        "  } "
        "end"
    )

    image = game._render(position=Position(x=0, y=0), radius=12, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_entities_with_cliffs(clear_terrain):
    """Test entity placement alongside cliffs"""
    game = clear_terrain

    # Create some cliffs
    game.instance.rcon_client.send_command(
        "/sc "
        "for i=-3,3 do "
        "  game.surfaces[1].create_entity{name='cliff', position={x=i*2, y=-10}, cliff_orientation='west-to-east'} "
        "end"
    )

    # Place entities
    game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.place_entity(Prototype.Splitter, position=Position(x=5, y=0))
    game.place_entity(Prototype.Lab, position=Position(x=10, y=0))

    # Create transport belt connections
    game.connect_entities(
        Position(x=0, y=-2),
        Position(x=15, y=5),
        {Prototype.TransportBelt, Prototype.UndergroundBelt},
    )

    game.connect_entities(
        Position(x=0, y=-5), Position(x=15, y=-5), {Prototype.SmallElectricPole}
    )

    image = game._render(position=Position(x=5, y=0), radius=20, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_rocks_and_decoratives(clear_terrain):
    """Test rock placement as decoratives"""
    game = clear_terrain
    #
    # game.instance.rcon_client.send_command(
    #     "/sc "
    #     "local rock_types = {'rock-huge', 'rock-big', 'sand-rock-big'} "
    #     "for i=1,10 do "
    #     "  local rock = rock_types[math.random(#rock_types)] "
    #     "  local x = math.random(-10, 10) "
    #     "  local y = math.random(-10, 10) "
    #     "  game.surfaces[1].create_entity{name=rock, position={x=x, y=y}} "
    #     "end"
    # )

    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None
