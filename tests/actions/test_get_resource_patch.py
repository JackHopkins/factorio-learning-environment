import pytest

from fle.env import ResourcePatch
from fle.env import FactorioInstance
from fle.env.game_types import Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_get_resource_patch(game: FactorioInstance):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    resource_patch: ResourcePatch = game.get_resource_patch(
        Resource.Coal, game.nearest(Resource.Coal)
    )

    assert resource_patch.name == Resource.Coal[0]
    assert resource_patch.size > 0
    assert resource_patch.bounding_box.left_top.x
    assert resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y
    assert resource_patch.bounding_box.right_bottom.y
    assert (
        resource_patch.bounding_box.left_top.x
        < resource_patch.bounding_box.right_bottom.x
    )
    assert (
        resource_patch.bounding_box.left_top.y
        < resource_patch.bounding_box.right_bottom.y
    )
    assert (
        resource_patch.bounding_box.left_top.x
        < resource_patch.bounding_box.right_bottom.x
    )
    assert (
        resource_patch.bounding_box.left_top.y
        < resource_patch.bounding_box.right_bottom.y
    )


def test_get_water_patch(game: FactorioInstance):
    """
    Verify that an exception is raised when trying to get a resource patch that does not exist at a given position.
    :param game:
    :return:
    """
    resource_patch: ResourcePatch = game.get_resource_patch(
        Resource.Water, game.nearest(Resource.Water)
    )
    assert resource_patch.name == Resource.Water[0]
    assert resource_patch.size > 0
    assert resource_patch.bounding_box.left_top.x
    assert resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y
    assert resource_patch.bounding_box.right_bottom.y
    assert (
        resource_patch.bounding_box.left_top.x
        < resource_patch.bounding_box.right_bottom.x
    )
    assert (
        resource_patch.bounding_box.left_top.y
        < resource_patch.bounding_box.right_bottom.y
    )
    assert (
        resource_patch.bounding_box.left_top.x
        < resource_patch.bounding_box.right_bottom.x
    )
    assert (
        resource_patch.bounding_box.left_top.y
        < resource_patch.bounding_box.right_bottom.y
    )


def test_get_tree_resource_patch(game: FactorioInstance):
    """
    Verify that an exception is raised when trying to get a resource patch that does not exist at a given position.
    :param game:
    :return:
    """
    resource_patch: ResourcePatch = game.get_resource_patch(
        Resource.Wood, game.nearest(Resource.Wood)
    )
    assert resource_patch.name == Resource.Wood[0]
    assert resource_patch.size > 0
    assert resource_patch.bounding_box.left_top.x
    assert resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y
    assert resource_patch.bounding_box.right_bottom.y
    # assert resource_patch.bounding_box.left_top.x < resource_patch.bounding_box.right_bottom.x
    # assert resource_patch.bounding_box.left_top.y < resource_patch.bounding_box.right_bottom.y
    # assert resource_patch.bounding_box.left_top.x < resource_patch.bounding_box.right_bottom.x
    # assert resource_patch.bounding_box.left_top.y < resource_patch.bounding_box.right_bottom.y
