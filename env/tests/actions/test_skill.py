import pytest
from contextlib import contextmanager

from game_types import Prototype

class SkillExample:
    def __init__(self, instance):
        self.instance = instance

    def setup(self):
        # Add any setup logic here
        self.instance.reset()
        # For example, you might want to add some initial items to the inventory
        self.instance.add_to_inventory(Prototype.IronPlate, 50)
        self.instance.add_to_inventory(Prototype.CopperPlate, 50)

    def teardown(self):
        self.instance.reset()

@pytest.fixture()
def game(instance):
    test_setup = GameTestSetup(instance)

    @contextmanager
    def game_context():
        test_setup.setup()
        try:
            yield test_setup.instance
        finally:
            test_setup.teardown()

    return game_context()

def test_craft_item(game):
    """
    Craft an iron chest and assert that the iron plate has been deducted and the iron chest has been added.
    :param game:
    :return:
    """

    # Check initial inventory
    initial_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    initial_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Craft an iron chest
    game.craft_item(Prototype.IronChest, quantity=1)

    # Check the inventory after crafting
    final_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    final_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Assert that the iron plate has been deducted and the iron chest has been added
    assert initial_iron_plate - 8 == final_iron_plate
    assert initial_iron_chest + 1 == final_iron_chest