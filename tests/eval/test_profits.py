import math

import pytest

from fle.env import FactorioInstance
from fle.env.utils.profits import eval_program_with_profits, get_profits


def _flows(*, output=None, input=None, crafted=None, harvested=None):
    return {
        "output": output or {},
        "input": input or {},
        "crafted": crafted or [],
        "harvested": harvested or {},
        "price_list": {
            "iron-ore": 1,
            "iron-plate": 2,
            "iron-gear-wheel": 5,
        },
    }


def test_static_profits_from_fixed_flows():
    pre = _flows()
    post = _flows(
        output={"iron-gear-wheel": 2},
        input={"iron-plate": 4},
        crafted=[
            {
                "crafted_count": 2,
                "outputs": {"iron-gear-wheel": 2},
                "inputs": {"iron-plate": 4},
            }
        ],
    )

    profits = get_profits(pre, post)

    assert profits == pytest.approx({"static": 2, "dynamic": 0, "total": 2})


def test_dynamic_profits_from_fixed_flows():
    pre = _flows()
    post = _flows(
        output={"iron-plate": 10},
        input={"iron-ore": 10},
    )

    profits = get_profits(pre, post)

    assert profits == pytest.approx({"static": 0, "dynamic": 100, "total": 100})


def test_profits():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        # cache_scripts=False,
        inventory={},
    )
    instance.set_speed(10)
    profit_config = {"max_static_unit_profit_cap": 5, "dynamic_profit_multiplier": 10}
    test_string_1 = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 2)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.IronOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.IronOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(25)\nextract_item(Prototype.IronPlate, furnace.position, 10)"
    _, _, _, profits = eval_program_with_profits(instance, test_string_1, profit_config)
    assert set(profits) == {"static", "dynamic", "total"}
    assert profits["static"] > 0
    assert math.isfinite(profits["dynamic"])
    assert math.isclose(profits["total"], profits["static"] + profits["dynamic"])

    test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(25)"
    _, _, _, profits = eval_program_with_profits(instance, test_string, profit_config)
    assert set(profits) == {"static", "dynamic", "total"}
    assert profits["static"] > 0
    assert math.isfinite(profits["dynamic"])
    assert math.isclose(profits["total"], profits["static"] + profits["dynamic"])
    test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(25)"
    _, _, _, profits = eval_program_with_profits(instance, test_string, profit_config)
    assert set(profits) == {"static", "dynamic", "total"}
    assert profits["static"] > 0
    assert math.isfinite(profits["dynamic"])
    assert math.isclose(profits["total"], profits["static"] + profits["dynamic"])


if __name__ == "__main__":
    test_profits()
