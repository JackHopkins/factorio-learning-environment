import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance
    instance.reset()

def test_craft_item(game):
    """
    Craft an iron chest and assert that the iron plate has been deducted and the iron chest has been added.
    :param game:
    :return:
    """
    quantity = 5
    iron_cost = 8
    # Check initial inventory
    initial_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    initial_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Craft an iron chest
    game.craft_item(Prototype.IronChest, quantity=quantity)

    # Check the inventory after crafting
    final_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    final_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Assert that the iron plate has been deducted and the iron chest has been added
    assert initial_iron_plate - final_iron_plate == iron_cost * quantity
    assert initial_iron_chest + quantity == final_iron_chest

def test_craft_copper_coil(game):
    """
    Craft 20 copper cable and verify that only 10 copper plates have been deducted.
    :param game:
    :return:
    """
    # Check initial inventory
    initial_copper_plate = game.inspect_inventory()[Prototype.CopperPlate]
    initial_copper_coil = game.inspect_inventory()[Prototype.CopperCable]

    # Craft 20 copper coil
    game.craft_item(Prototype.CopperCable, quantity=20)

    # Check the inventory after crafting
    final_copper_plate = game.inspect_inventory()[Prototype.CopperPlate]
    final_copper_coil = game.inspect_inventory()[Prototype.CopperCable]

    # Assert that only 10 copper plates have been deducted
    assert initial_copper_plate - 10 == final_copper_plate
    assert initial_copper_coil + 20 == final_copper_coil

def test_craft_entity_with_missing_intermediate_resources(game):
    """
    Some entities like offshore pumps require intermediate resources, which we may also need to craft.
    :param game:
    :return:
    """
    # Craft 20 copper coil
    crafted = game.craft_item(Prototype.OffshorePump, quantity=1)

    assert crafted == 1
