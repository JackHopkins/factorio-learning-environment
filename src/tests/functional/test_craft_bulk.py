import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Resource, Prototype, PrototypeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 100,
        'small-electric-pole': 50,
        'transport-belt': 100,
        PrototypeName.AssemblingMachine.value: 10,
    }
    instance.reset()
    yield instance

def test_craft_automation_packs(game):
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

    # Build an assembly machine
    game.craft_item(Prototype.AssemblingMachine1, 1)
    assembler = game.place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=2, y=0))
    assert assembler, "Failed to place assembly machine"

    # Set up automated science pack production
    recipe_set = game.set_entity_recipe(assembler, Prototype.AutomationSciencePack)
    assert recipe_set, "Failed to set recipe for automated science pack"

    # Feed materials into the assembly machine
    game.insert_item(Prototype.IronGearWheel, assembler, 10)
    game.insert_item(Prototype.CopperPlate, assembler, 10)

    # Wait for production
    game.sleep(50)  # Wait for 10 science packs to be produced (5 seconds each)

    # Collect the science packs
    science_packs = game.extract_item(Prototype.AutomationSciencePack, assembler.position, 10)
    assert science_packs, "Failed to extract science packs from assembler"

    # Verify the result
    inventory = game.inspect_inventory()
    assert inventory.get(
        Prototype.ElectronicCircuit) >= 10, f"Failed to craft 10 automated science packs. Current count: {inventory.get(Prototype.ElectronicCircuit)}"

    print(f"Successfully crafted {inventory.get(Prototype.ElectronicCircuit)} automated science packs")
