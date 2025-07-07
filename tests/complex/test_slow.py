import pytest
from fle.env.instance import FactorioInstance
from fle.env.game_types import Resource


@pytest.fixture()
def game():
    instance = FactorioInstance(
        address="localhost", bounding_box=200, tcp_port=27000, fast=True, inventory={}
    )
    instance.speed(1)
    instance.reset()
    yield instance.namespace


def test_slow_harvest(game):
    """Test placement of entities at the edge of the map and in tight spaces."""
    # Place entity at map edge
    coal_position = game.nearest(Resource.Coal)
    game.move_to(coal_position)
    game.harvest_resource(coal_position, 20)
    game.inspect_inventory()


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
