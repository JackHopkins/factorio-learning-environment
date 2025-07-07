import pytest
from fle.env import Direction, Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "solar-panel": 3,
        "small-electric-pole": 4,
        "long-handed-inserter": 2,
        "filter-inserter": 2,
        "stack-inserter": 2,
        "iron-chest": 4,
        "steel-chest": 4,
        "iron-plate": 100,
        "copper-plate": 100,
        "electronic-circuit": 100,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace


def setup_power_and_chests(game, inserter_type, origin_pos=Position(x=0, y=0)):
    """Helper function to set up power and chest configuration for inserter tests"""
    # Place solar panel for power
    solar_panel = game.place_entity(Prototype.SolarPanel, position=origin_pos)

    # Place power pole
    pole = game.place_entity_next_to(
        Prototype.SmallElectricPole, solar_panel.position, Direction.RIGHT
    )

    # Place input chest (source)
    input_chest = game.place_entity_next_to(
        Prototype.SteelChest, pole.position, Direction.DOWN
    )

    # Place output chest (destination)
    if inserter_type != Prototype.LongHandedInserter:
        # Place inserter
        inserter = game.place_entity_next_to(
            inserter_type, input_chest.position, Direction.RIGHT, spacing=0
        )
        output_chest = game.place_entity_next_to(
            Prototype.SteelChest, inserter.position, Direction.RIGHT
        )
    else:
        # Place inserter
        inserter = game.place_entity_next_to(
            inserter_type, input_chest.position, Direction.RIGHT, spacing=1
        )
        output_chest = game.place_entity_next_to(
            Prototype.SteelChest, inserter.position, Direction.RIGHT, spacing=1
        )
    # Connect power
    game.connect_entities(pole, inserter, Prototype.SmallElectricPole)

    return input_chest, inserter, output_chest


def test_long_handed_inserter(game):
    """Test long-handed inserter's ability to move items between chests"""
    input_chest, inserter, output_chest = setup_power_and_chests(
        game, Prototype.LongHandedInserter
    )

    # Insert test items
    game.insert_item(Prototype.IronPlate, input_chest, quantity=50)

    # Wait for inserter to operate
    game.sleep(20)

    # Verify items were moved
    output_inventory = game.inspect_inventory(output_chest)
    assert output_inventory.get(Prototype.IronPlate, 0) > 0, (
        "Long-handed inserter failed to move items"
    )


def test_filter_inserter(game):
    """Test filter inserter's ability to selectively move items"""
    input_chest, inserter, output_chest = setup_power_and_chests(
        game, Prototype.FilterInserter
    )

    # Set filter to only move iron plates
    game.set_entity_recipe(inserter, Prototype.IronPlate)

    # Insert mixed items
    game.insert_item(Prototype.IronPlate, input_chest, quantity=50)
    game.insert_item(Prototype.CopperPlate, input_chest, quantity=50)

    # Wait for inserter to operate
    game.sleep(20)

    # Verify only iron plates were moved
    output_inventory = game.inspect_inventory(output_chest)
    assert output_inventory.get(Prototype.IronPlate, 0) > 0, (
        "Filter inserter failed to move iron plates"
    )
    assert output_inventory.get(Prototype.CopperPlate, 0) == 0, (
        "Filter inserter incorrectly moved copper plates"
    )


def test_stack_inserter(game):
    """Test stack inserter's ability to move multiple items at once"""
    input_chest, inserter, output_chest = setup_power_and_chests(
        game, Prototype.StackInserter
    )

    # Insert large quantity of items
    game.insert_item(Prototype.ElectronicCircuit, input_chest, quantity=100)
    # Check first transfer
    first_transfer = game.inspect_inventory(output_chest).get(
        Prototype.ElectronicCircuit, 0
    )

    # Wait for another transfer
    game.sleep(5)

    # Check second transfer
    second_transfer = game.inspect_inventory(output_chest).get(
        Prototype.ElectronicCircuit, 0
    )

    # Verify stack inserter moved more items per operation than regular inserters would
    assert second_transfer > first_transfer, (
        "Stack inserter failed to move multiple items at once"
    )
    assert second_transfer >= 12, "Stack inserter not moving expected quantity of items"


def test_filter_stack_inserter(game):
    """Test stack inserter's ability to move multiple items at once"""
    input_chest, inserter, output_chest = setup_power_and_chests(
        game, Prototype.StackFilterInserter
    )

    # Set filter to only move iron plates
    game.set_entity_recipe(inserter, Prototype.ElectronicCircuit)

    # Insert large quantity of items
    game.insert_item(Prototype.ElectronicCircuit, input_chest, quantity=100)
    # Check first transfer
    first_transfer = game.inspect_inventory(output_chest).get(
        Prototype.ElectronicCircuit, 0
    )

    # Wait for another transfer
    game.sleep(5)

    # Check second transfer
    second_transfer = game.inspect_inventory(output_chest).get(
        Prototype.ElectronicCircuit, 0
    )

    # Verify stack inserter moved more items per operation than regular inserters would
    assert second_transfer > first_transfer, (
        "Stack inserter failed to move multiple items at once"
    )
    assert second_transfer >= 12, "Stack inserter not moving expected quantity of items"
