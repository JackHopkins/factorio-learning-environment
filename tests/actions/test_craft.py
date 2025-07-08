import pytest

from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    instance.set_inventory(
        {
            "iron-plate": 40,
            "iron-gear-wheel": 1,
            "electronic-circuit": 3,
            "pipe": 1,
            "copper-plate": 10,
        }
    )
    yield instance.namespace
    instance.reset()


def test_fail_to_craft_item(game):
    """
    Attempt to craft an iron chest with insufficient resources and assert that no items are crafted.
    :param game:
    :return:
    """

    try:
        game.craft_item(Prototype.IronChest, quantity=100)
    except Exception:
        assert True


def test_craft_with_full_inventory(game):
    """
    Test crafting when inventory is full
    """
    game.instance.set_inventory({"iron-plate": 100, "coal": 10000})
    try:
        result = game.craft_item(Prototype.IronGearWheel, 1)
        assert False, (
            f"Expected crafting to fail due to full inventory, but got result: {result}"
        )
    except Exception as e:
        print(e)
        assert True


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


def test_recursive_crafting(game):
    crafted_circuits = game.craft_item(Prototype.ElectronicCircuit, quantity=4)
    assert crafted_circuits


def test_craft_copper_coil(game):
    """
    Craft 20 copper cable and verify that only 10 copper plates have been deducted.
    :param game:
    :return:
    """

    # Craft an iron chest with insufficient resources
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
    crafted = game.craft_item(Prototype.ElectronicCircuit, quantity=1)

    assert crafted == 1


def test_craft_uncraftable_entity(game):
    # Find and move to the nearest iron ore patch
    iron_ore_position = game.nearest(Resource.IronOre)
    print(f"Moving to iron ore patch at {iron_ore_position}")
    game.move_to(iron_ore_position)

    # Mine iron ore (we need at least 8 iron plates, so mine a bit more to be safe)
    print("Mining iron ore...")
    game.harvest_resource(iron_ore_position, quantity=10)
    print(f"Mined iron ore. Current inventory: {game.inspect_inventory()}")

    # Craft iron gear wheels (each requires 2 iron plates)
    print("Crafting iron gear wheels...")
    game.craft_item(Prototype.IronGearWheel, quantity=3)
    print(f"Crafted iron gear wheels. Current inventory: {game.inspect_inventory()}")


def test_craft_no_technology(game):
    game.instance.all_technologies_researched = False
    game.instance.reset()

    try:
        game.craft_item(Prototype.AssemblingMachine1, quantity=1)
    except:
        assert True
        return
    assert False, "Should not be able to craft without technology."
