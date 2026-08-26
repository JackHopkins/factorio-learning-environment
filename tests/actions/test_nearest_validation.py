import pytest

from fle.env.game_types import Prototype, Resource
from fle.env.tools.agent.nearest.client import Nearest

pytestmark = pytest.mark.no_factorio


def test_nearest_accepts_specific_resource_and_prototype_members():
    assert Nearest._normalize_type(Resource.Coal)[0] == "coal"
    assert Nearest._normalize_type(Prototype.StoneFurnace)[0] == "stone-furnace"


@pytest.mark.parametrize("value", [Resource, Prototype, "coal"])
def test_nearest_rejects_bare_namespaces_and_strings_with_correction(value):
    with pytest.raises(ValueError, match="requires one specific enum member") as exc:
        Nearest._normalize_type(value)

    assert "Resource.Coal" in str(exc.value)
