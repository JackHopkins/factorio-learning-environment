import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Resource, Prototype, PrototypeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 100,
        'small-electric-pole': 50,
        'transport-belt': 100,
        'lab': 1
    }
    instance.reset()
    yield instance


def test_craft_automation_packs_and_research(game):
    # Gather resources
    game.move_to(game.nearest(Resource.IronOre))
    game.harvest_resource(game.nearest(Resource.IronOre), 20)

    game.move_to(game.nearest(Resource.CopperOre))
    game.harvest_resource(game.nearest(Resource.CopperOre), 20)

    # Set up basic infrastructure
    game.move_to(Position(x=0, y=0))
    furnace = game.place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
    assert furnace, "Failed to place stone furnace"

    # Create iron and copper plates
    game.insert_item(Prototype.IronOre, furnace, quantity=10)
    game.insert_item(Prototype.Coal, furnace, quantity=10)
    game.sleep(10)  # Wait for smelting
    iron_plates = game.extract_item(Prototype.IronPlate, furnace.position, 10)

    game.insert_item(Prototype.CopperOre, furnace, quantity=10)
    game.sleep(10)  # Wait for smelting
    copper_plates = game.extract_item(Prototype.CopperPlate, furnace.position, 10)
    assert iron_plates and copper_plates, "Failed to create iron or copper plates"

    # Craft necessary components
    game.craft_item(Prototype.IronGearWheel, 10)
    game.craft_item(Prototype.CopperCable, 10)

    # Craft automation science packs
    game.craft_item(Prototype.AutomationSciencePack, 10)

    # Verify the crafting result
    inventory = game.inspect_inventory()
    assert inventory.get(
        Prototype.AutomationSciencePack) >= 10, f"Failed to craft 10 automation science packs. Current count: {inventory.get(Prototype.AutomationSciencePack)}"

    print(f"Successfully crafted {inventory.get(Prototype.AutomationSciencePack)} automation science packs")

    # Place a Lab
    lab = game.place_entity(Prototype.Lab, Direction.UP, Position(x=2, y=0))
    assert lab, "Failed to place Lab"

    # Insert science packs into the Lab
    game.insert_item(Prototype.AutomationSciencePack, lab, quantity=10)

    # Verify science packs were inserted
    lab_inventory = game.inspect_inventory(lab)
    assert lab_inventory.get(
        Prototype.AutomationSciencePack) == 10, f"Failed to insert science packs into Lab. Current count: {lab_inventory.get(Prototype.AutomationSciencePack)}"

    # Start researching (assuming a function to start research exists)
    initial_research = game.get_research_progress("automation")  # Get initial research progress
    game.start_research("automation")  # Start researching automation technology

    # Wait for some time to allow research to progress
    game.sleep(30)

    # Check if research has progressed
    current_research = game.get_research_progress("automation")
    assert current_research > initial_research, f"Research did not progress. Initial: {initial_research}, Current: {current_research}"

    print(f"Successfully started research. Progress: {current_research}")
