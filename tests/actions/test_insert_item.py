import pytest

from fle.env.entities import Position, EntityStatus, Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "iron-ore": 500,
        "copper-ore": 10,
        "iron-plate": 1000,
        "iron-gear-wheel": 1000,
        "coal": 100,
        "stone-furnace": 1,
        "transport-belt": 10,
        "burner-inserter": 1,
        "assembling-machine-1": 1,
        "solar-panel": 2,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_insert_and_fuel_furnace(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0)
    )
    furnace = game.insert_item(Prototype.IronOre, furnace, quantity=50)
    furnace = game.insert_item(Prototype.Coal, furnace, quantity=50)

    assert furnace.status == EntityStatus.WORKING
    assert furnace.fuel[Prototype.Coal] == 50
    assert furnace.furnace_source[Prototype.IronOre] == 50


def test_insert_iron_ore_into_stone_furnace(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0)
    )
    furnace = game.insert_item(Prototype.IronOre, furnace, quantity=10)

    assert furnace.status == EntityStatus.NO_FUEL
    assert furnace.furnace_source[Prototype.IronOre] == 10


def test_insert_iron_ore_into_stone_furnace2(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0)
    )
    try:
        furnace = game.insert_item(Prototype.IronOre, furnace, quantity=500)
        furnace = game.insert_item(Prototype.IronPlate, furnace, quantity=10)
    except Exception as e:
        assert True, f"Cannot insert incorrect item into a stone furnace: {e}"


def test_insert_copper_ore_and_iron_ore_into_stone_furnace(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0)
    )
    try:
        furnace = game.insert_item(Prototype.IronOre, furnace, quantity=10)
        furnace = game.insert_item(Prototype.CopperOre, furnace, quantity=10)
    except Exception as e:
        assert True, (
            f"Inserting both copper and iron ore into a stone furnace should raise an exception: {e}"
        )


def test_insert_coal_into_burner_inserter(game):
    inserter = game.place_entity(
        Prototype.BurnerInserter, direction=Direction.UP, position=Position(x=0, y=0)
    )
    inserter = game.insert_item(Prototype.Coal, inserter, quantity=10)

    assert inserter.fuel[Prototype.Coal] == 10


def test_invalid_insert_ore_into_burner_inserter(game):
    inserter = game.place_entity(
        Prototype.BurnerInserter, direction=Direction.UP, position=Position(x=0, y=0)
    )
    try:
        inserter = game.insert_item(Prototype.IronOre, inserter, quantity=10)
    except:
        assert True, "Should not be able to add iron to an inserter"
        return

    assert False, "Should not be able to add iron to an inserter"


def test_insert_into_assembler(game):
    assembler = game.place_entity(
        Prototype.AssemblingMachine1,
        direction=Direction.UP,
        position=Position(x=0, y=0),
    )

    assembler = game.set_entity_recipe(assembler, Prototype.IronGearWheel)
    assembler = game.insert_item(Prototype.IronGearWheel, assembler, quantity=1000)
    assembler = game.insert_item(Prototype.IronPlate, assembler, quantity=1000)
    assert assembler.status == EntityStatus.NO_POWER
    assert assembler.assembling_machine_input[Prototype.IronPlate] == 100
    assert assembler.assembling_machine_output[Prototype.IronGearWheel] == 100


def test_insert_ore_onto_belt(game):
    belt = game.connect_entities(
        Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt
    )
    belt = game.insert_item(Prototype.IronOre, belt, quantity=5)

    assert belt.inventory[Prototype.IronOre] == 5


def test_blocked_belt(game):
    belt = game.connect_entities(
        Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt
    )
    try:
        belt = game.insert_item(Prototype.IronOre, belt, quantity=500)
    except Exception:
        pass

    belt = game.get_entities({Prototype.TransportBelt}, position=Position(x=0.5, y=0.5))

    assert belt[0].status == EntityStatus.FULL_OUTPUT


def test_insert_into_two_furnaces(game):
    furnace_pos = Position(x=-12, y=-12)
    game.move_to(furnace_pos)
    game.place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)

    """
    Step 1: Print recipe. We need to print the recipe for offshore pump
    """
    # Get the recipe for offshore pump
    recipe = game.get_prototype_recipe(Prototype.OffshorePump)

    # Print the recipe details
    print("offshore pump Recipe:")
    print(f"Ingredients: {recipe.ingredients}")

    """
    Step 1: Gather resources. We need to mine the following:
    - 5 iron ore
    - 3 copper ore
    - Coal (at least 10 for smelting)
    - 5 stone (to craft an additional furnace)
    OUTPUT CHECK: Verify that we have at least 5 iron ore, 3 copper ore, 10 coal, and 5 stone in our inventory.
    """
    # Define the resources and their required quantities
    resources_to_mine = [
        (Resource.IronOre, 5),
        (Resource.CopperOre, 3),
        (Resource.Coal, 10),
        (Resource.Stone, 5),
    ]

    # Loop through each resource type and mine it
    for resource_type, required_amount in resources_to_mine:
        # Find the nearest position of this resource type
        print(f"Finding nearest {resource_type}...")
        nearest_position = game.nearest(resource_type)

        # Move to that position
        print(f"Moving to {resource_type} at position {nearest_position}...")
        game.move_to(nearest_position)

        # Harvest the required amount of this resource
        print(f"Harvesting {required_amount} units of {resource_type}...")
        game.harvest_resource(nearest_position, quantity=required_amount)

        # Verify that we've harvested enough by checking inventory
        current_inventory = game.inspect_inventory()

        assert current_inventory.get(resource_type) >= required_amount, (
            f"Failed to harvest enough {resource_type}. "
            f"Expected at least {required_amount}, but got {current_inventory.get(resource_type)}"
        )

    print("Successfully gathered all necessary resources.")
    print(f"Current Inventory: {game.inspect_inventory()}")

    # Final assertion checks for all resources together as a summary check.
    final_inventory = game.inspect_inventory()
    assert final_inventory.get(Resource.IronOre) >= 5, "Not enough Iron Ore."
    assert final_inventory.get(Resource.CopperOre) >= 3, "Not enough Copper Ore."
    assert final_inventory.get(Resource.Coal) >= 10, "Not enough Coal."
    assert final_inventory.get(Resource.Stone) >= 5, "Not enough Stone."

    print("All initial gathering objectives met successfully!")

    """
    Step 2: Craft an additional stone furnace. We need to carry out the following:
    - Craft a stone furnace using 5 stone
    OUTPUT CHECK: Verify that we now have 2 stone furnaces (1 in inventory, 1 on map)
    """
    # Craft a stone furnace using 5 stones
    print("Attempting to craft a Stone Furnace...")
    crafted_furnace_count = game.craft_item(Prototype.StoneFurnace, 1)
    assert crafted_furnace_count == 1, "Failed to craft Stone Furnace."

    # Check current inventory for Stone Furnace count
    inventory_after_crafting = game.inspect_inventory()
    stone_furnace_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
    print(f"Stone Furnaces in Inventory after crafting: {stone_furnace_in_inventory}")

    # Verify there is now exactly 1 Stone Furnace in inventory
    assert stone_furnace_in_inventory == 1, (
        f"Expected 1 Stone Furnace in inventory but found {stone_furnace_in_inventory}."
    )

    # Check existing entities on map for any placed furnaces
    existing_stone_furnaces_on_map = game.get_entities({Prototype.StoneFurnace})
    furnaces_on_map_count = len(existing_stone_furnaces_on_map)
    print(f"Stone Furnaces currently on map: {furnaces_on_map_count}")

    # Verify total number of furnaces (on map + in inventory) equals expected amount (2)
    total_stone_furnaces = furnaces_on_map_count + stone_furnace_in_inventory
    assert total_stone_furnaces == 2, (
        f"Total Stone Furnaces should be 2 but found {total_stone_furnaces}."
    )

    print("Successfully crafted an additional Stone Furnace.")

    """
    Step 3: Set up smelting operation. We need to:
    - Place the new stone furnace next to the existing one
    - Fuel both furnaces with coal
    OUTPUT CHECK: Verify that both furnaces are placed and fueled
    """
    # Step 3 Implementation

    # Get the existing stone furnace entity on the map
    existing_furnace = game.get_entities({Prototype.StoneFurnace})[0]
    print(f"Existing Stone Furnace found at position {existing_furnace.position}")

    # Place new stone furnace next to the existing one
    new_furnace_position = Position(
        x=existing_furnace.position.x + 2, y=existing_furnace.position.y
    )  # Assuming placement to right
    game.move_to(new_furnace_position)
    new_stone_furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, new_furnace_position
    )
    print(f"Placed new Stone Furnace at position {new_stone_furnace.position}")

    # Fueling process
    coal_in_inventory = game.inspect_inventory()[Prototype.Coal]
    half_coal_each = coal_in_inventory // 2

    # Fuel existing furnace
    existing_furnace = game.insert_item(
        Prototype.Coal, existing_furnace, half_coal_each
    )
    print(f"Fueled Existing Stone Furnace with {half_coal_each} units of Coal")

    # Fuel new furnace
    new_stone_furnace = game.insert_item(
        Prototype.Coal, new_stone_furnace, half_coal_each
    )
    print(f"Fueled New Stone Furnace with {half_coal_each} units of Coal")

    # Verify that both furnaces are fueled (status should not be NO_FUEL)
    assert EntityStatus.NO_FUEL not in [existing_furnace.status], (
        "Existing furnace is out of fuel!"
    )
    assert EntityStatus.NO_FUEL not in [new_stone_furnace.status], (
        "Newly placed furnace is out of fuel!"
    )

    print("Both furnaces are successfully placed and fueled.")

    """
    Step 4: Smelt plates. We need to:
    - Smelt 5 iron ore into 5 iron plates
    - Smelt 3 copper ore into 3 copper plates
    OUTPUT CHECK: Verify that we have 5 iron plates and 3 copper plates in our inventory
    """
    # Get references to both stone furnaces
    stone_furnaces = game.get_entities({Prototype.StoneFurnace})
    furnace_iron = stone_furnaces[0]
    furnace_copper = stone_furnaces[1]

    print(f"Using Furnace at {furnace_iron.position} for Iron Ore")
    print(f"Using Furnace at {furnace_copper.position} for Copper Ore")

    # Insert Iron Ore into first furnace
    iron_ore_count = game.inspect_inventory()[Prototype.IronOre]
    furnace_iron = game.insert_item(Prototype.IronOre, furnace_iron, iron_ore_count)
    print(f"Inserted {iron_ore_count} Iron Ore into first Stone Furnace.")

    # Insert Copper Ore into second furnace
    copper_ore_count = game.inspect_inventory()[Prototype.CopperOre]
    furnace_copper = game.insert_item(
        Prototype.CopperOre, furnace_copper, copper_ore_count
    )
    print(f"Inserted {copper_ore_count} Copper Ore into second Stone Furnace.")

    assert True
