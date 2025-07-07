import pytest

from fle.env.entities import Position
from fle.env.game_types import Resource, Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    # instance.reset()


def test_harvest_resource_with_full_inventory(game):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    game.instance.initial_inventory = {**game.instance.initial_inventory, "coal": 4000}
    game.instance.reset()

    # Find nearest coal resource
    nearest_coal = game.nearest(Resource.Coal)
    # Move to the coal resource
    game.move_to(nearest_coal)
    try:
        # Harvest coal
        game.harvest_resource(
            nearest_coal, quantity=100
        )  # Assuming there is a coal resource at (10, 10)
        assert False, "Cannot harvest with a full inventory"
    except Exception:
        assert True


def test_harvest_resource(game):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    quantity = 50
    for resource in [
        Resource.Coal,
        Resource.IronOre,
        Resource.Stone,
        Resource.CopperOre,
    ]:
        inventory = game.inspect_inventory()
        # Check initial inventory
        initial_coal = inventory[resource]
        # Find nearest coal resource
        nearest_coal = game.nearest(resource)
        # Move to the coal resource
        game.move_to(nearest_coal)
        try:
            # Harvest coal
            game.harvest_resource(
                nearest_coal, quantity=quantity
            )  # Assuming there is a coal resource at (10, 10)
        except Exception as e:
            print(e)
        # Check the inventory after harvesting
        final_coal = game.inspect_inventory()[resource]
        # Assert that the coal has been added to the inventory
        assert quantity <= final_coal - initial_coal


create_stump = """
game.surfaces[1].create_entity({
    name = "dead-grey-trunk",
    position = {x = 1, y = 0}
})
"""


def test_harvest_stump(game):
    instance = game.instance

    instance.add_command(f"/c {create_stump}", raw=True)
    instance.execute_transaction()
    harvested = game.harvest_resource(Position(x=0, y=0), quantity=1)

    assert harvested == 2


create_rock = """
game.surfaces[1].create_entity({
    name = "rock-big",
    position = {x = 1, y = 0}
})
"""


def test_harvest_rock(game):
    instance = game.instance

    instance.add_command(f"/c {create_rock}", raw=True)
    instance.execute_transaction()
    harvested = game.harvest_resource(Position(x=0, y=0), quantity=1)

    assert harvested == 20


def test_harvest_trees(game):
    """
    Find the nearest tree resource patch and harvest 5 wood from it.
    :param game:
    :return:
    """
    quantity = 50
    inventory = game.inspect_inventory()
    # Check initial inventory
    initial_wood = inventory[Resource.Wood]
    # Find nearest wood resource
    nearest_wood = game.nearest(Resource.Wood)
    # Move to the wood resource
    game.move_to(nearest_wood)
    # Harvest coal
    game.harvest_resource(
        nearest_wood, quantity=quantity, radius=50
    )  # Assuming there is a wood resource here

    # Check the inventory after harvesting
    final_wood = game.inspect_inventory()[Resource.Wood]
    # Assert that the coal has been added to the inventory
    assert quantity < final_wood - initial_wood


def test_harvest_bug(game):
    # Get stone for furnace
    stone_pos = game.nearest(Resource.Stone)
    game.move_to(stone_pos)
    game.harvest_resource(stone_pos, 5)

    # Craft stone furnace
    game.craft_item(Prototype.StoneFurnace, 1)

    # Verify we have stone furnace in inventory
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"


def test_harvest_bug_2(game):
    """
    Planning:
    1. Gather stone to craft a furnace
    2. Craft a stone furnace
    3. Place the furnace
    4. Mine coal for fuel
    5. Mine iron ore
    6. Smelt iron ore into iron plates
    7. Verify the production of iron plates
    """

    """
    Step 1: Gather stone to craft a furnace
    """
    # Move to the nearest stone resource
    stone_position = game.nearest(Resource.Stone)
    game.move_to(stone_position)

    # Mine 5 stone (enough for one furnace)
    stone_needed = 5
    stone_mined = game.harvest_resource(stone_position, stone_needed)
    print(f"Mined {stone_mined} stone")

    # Verify that we have enough stone
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.Stone) >= stone_needed, (
        f"Failed to mine enough stone. Current inventory: {inventory}"
    )

    """
    Step 2: Craft a stone furnace
    """
    game.craft_item(Prototype.StoneFurnace, 1)
    print("Crafted 1 stone furnace")

    # Verify that we have a stone furnace in our inventory
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.StoneFurnace) >= 1, (
        f"Failed to craft stone furnace. Current inventory: {inventory}"
    )

    """
    Step 3: Place the furnace
    """
    origin = Position(x=0, y=0)
    game.move_to(origin)
    furnace = game.place_entity(Prototype.StoneFurnace, position=origin)
    print(f"Placed stone furnace at {furnace.position}")

    """
    Step 4: Mine coal for fuel
    """
    # Move to the nearest coal resource
    coal_position = game.nearest(Resource.Coal)
    game.move_to(coal_position)

    # Mine 10 coal
    coal_needed = 10
    coal_mined = game.harvest_resource(coal_position, coal_needed)
    print(f"Mined {coal_mined} coal")

    # Verify that we have enough coal
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.Coal) >= coal_needed, (
        f"Failed to mine enough coal. Current inventory: {inventory}"
    )

    # Move back to the furnace and insert coal
    game.move_to(furnace.position)
    updated_furnace = game.insert_item(Prototype.Coal, furnace, 10)
    print("Inserted coal into the furnace")

    """
    Step 5: Mine iron ore
    """
    # Move to the nearest iron ore resource
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    # Mine 10 iron ore
    iron_ore_needed = 10
    iron_ore_mined = game.harvest_resource(iron_position, iron_ore_needed)
    print(f"Mined {iron_ore_mined} iron ore")

    # Verify that we have enough iron ore
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.IronOre) >= iron_ore_needed, (
        f"Failed to mine enough iron ore. Current inventory: {inventory}"
    )

    """
    Step 6: Smelt iron ore into iron plates
    """
    # Move back to the furnace
    game.move_to(furnace.position)

    # Insert iron ore into the furnace
    updated_furnace = game.insert_item(Prototype.IronOre, updated_furnace, 10)
    print("Inserted iron ore into the furnace")

    # Wait for the smelting process to complete
    smelting_time = 10 * 0.7  # 10 items * 0.7 seconds per item
    game.sleep(int(smelting_time))

    # Extract iron plates
    max_attempts = 5
    for _ in range(max_attempts):
        game.extract_item(Prototype.IronPlate, updated_furnace.position, 10)
        inventory = game.inspect_inventory()
        if inventory.get(Prototype.IronPlate, 0) >= 10:
            break
        game.sleep(5)

    print("Extracted iron plates from the furnace")

    """
    Step 7: Verify the production of iron plates
    """
    # Check the inventory for iron plates
    inventory = game.inspect_inventory()
    iron_plates = inventory.get(Prototype.IronPlate, 0)
    print(f"Current inventory: {inventory}")
    assert iron_plates >= 10, (
        f"Failed to produce enough iron plates. Expected 10, got {iron_plates}"
    )

    print("Successfully produced 10 iron plates!")


def test_harvest_provides_score(game):
    # Move to the nearest stone resource
    stone_position = game.nearest(Resource.Stone)
    game.move_to(stone_position)

    stats = game._production_stats()  # noqa
    reward, _ = game.score()
    # Mine 5 stone (enough for one furnace)
    stone_needed = 5
    stone_mined = game.harvest_resource(stone_position, stone_needed)
    print(f"Mined {stone_mined} stone")

    nstats = game._production_stats()  # noqa
    nreward, _ = game.score()

    assert nreward > reward
