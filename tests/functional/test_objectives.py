from time import sleep
from typing import List, Union

import pytest

from fle.env.entities import (
    Entity,
    Position,
    ResourcePatch,
    Recipe,
    BurnerMiningDrill,
    EntityGroup,
    Direction,
)
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 1,
        "boiler": 5,
        "steam-engine": 5,
        "pipe": 100,
        "iron-plate": 10,
    }
    # instance.rcon_client.send_command('game.reset_game_state()')
    # instance.rcon_client.send_command('game.reload_script()')
    instance.reset()
    yield instance.namespace


def test_collect_iron_ore(game):
    """
    Collect 10 iron ore
    :param game:
    :return:
    """
    iron_ore = game.nearest(Resource.IronOre)
    # move to the iron ore
    game.move_to(iron_ore)
    game.harvest_resource(iron_ore)

    assert game.inspect_inventory()[Prototype.IronOre] == 1
    game.reset()


def test_place_ore_in_furnace(game):
    """
    Collect 10 iron ore and place it in a furnace
    :param game:
    :return:
    """
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # move to the iron ore
    iron_ore_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the coal
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    game.move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the furnace
    game.move_to(furnace.position)
    game.insert_item(Prototype.IronOre, furnace, quantity=10)
    game.insert_item(Prototype.Coal, furnace, quantity=10)

    game.reset()


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
    game.move_to(Position(x=0, y=0))
    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    game.move_to(Position(x=0, y=5))
    steam_engine: Entity = game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=10)
    )

    try:
        connection: List[Entity] = game.connect_entities(
            boiler, steam_engine, connection_type=Prototype.Pipe
        )
        assert False
    except Exception as e:
        print(e)
        assert True
    game.pickup_entity(steam_engine)
    game.pickup_entity(connection)

    # Define the offsets for the four cardinal directions
    offsets = [
        Position(x=5, y=0),
        Position(x=0, y=5),
        Position(x=-5, y=0),
        Position(x=0, y=-5),
    ]  # Up, Right, Down, Left  (0, -10),

    for offset in offsets:
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset)

        try:
            connection: List[Union[EntityGroup, Entity]] = game.connect_entities(
                boiler, steam_engine, connection_type=Prototype.Pipe
            )
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert (
            steam_engines_in_inventory - 1
            == game.inspect_inventory()[Prototype.SteamEngine]
        )

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = pipes_in_inventory - current_pipes_in_inventory
        assert spent_pipes == len(connection.pipes)

        game.pickup_entity(steam_engine)
        game.pickup_entity(connection)


def test_build_iron_gear_factory(game):
    """
    Build a factory that produces iron gears from iron plates.
    :param game:
    :return:
    """
    # move to the iron ore
    iron_ore_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 80 iron ore
    while game.inspect_inventory()[Prototype.IronOre] < 80:
        game.harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the stone patch
    stone_patch = game.get_resource_patch(Resource.Stone, game.nearest(Resource.Stone))

    # harvest 10 stone
    game.move_to(stone_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(stone_patch.bounding_box.left_top, quantity=10)

    # move to the coal patch
    coal_patch: ResourcePatch = game.get_resource_patch(
        Resource.Coal, game.nearest(Resource.Coal)
    )
    game.move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 30 coal
    while game.inspect_inventory()[Prototype.Coal] < 30:
        game.harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the copper patch
    copper_patch: ResourcePatch = game.get_resource_patch(
        Resource.CopperOre, game.nearest(Resource.CopperOre)
    )
    game.move_to(copper_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 10 copper ore
    while game.inspect_inventory()[Prototype.CopperOre] < 30:
        game.harvest_resource(copper_patch.bounding_box.left_top, quantity=10)

    # move to the origin
    game.move_to(Position(x=0, y=0))

    # place a stone furnace
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, position=Position(x=0, y=0)
    )

    # insert 20 coal into the stone furnace
    game.insert_item(Prototype.Coal, stone_furnace, quantity=20)

    # insert 80 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=50)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 50:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=50)

    # insert 30 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=30)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 30:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=30)

    # insert 20 copper ore into the stone furnace
    game.insert_item(Prototype.CopperOre, stone_furnace, quantity=20)

    # check if the stone furnace has produced copper plates
    while game.inspect_inventory(stone_furnace)[Prototype.CopperPlate] < 20:
        sleep(5)

    # extract the copper plates from the stone furnace
    game.extract_item(Prototype.CopperPlate, stone_furnace, quantity=20)

    # pick up the stone furnace
    game.pickup_entity(stone_furnace)

    # get recipe for burner mining drill
    recipe: Recipe = game.get_prototype_recipe(Prototype.BurnerMiningDrill)

    # craft any ingredient that is missing
    for ingredient in recipe.ingredients:
        if game.inspect_inventory()[ingredient.name] < ingredient.count:
            game.craft_item(ingredient.name, quantity=ingredient.count)

    # craft a burner mining drill
    game.craft_item(Prototype.BurnerMiningDrill)

    # move to the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # place a burner mining drill
    burner_mining_drill: BurnerMiningDrill = game.place_entity(
        Prototype.BurnerMiningDrill, position=iron_ore_patch.bounding_box.left_top
    )

    # fuel the burner mining drill
    game.insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

    # place the stone furnace
    stone_furnace = game.place_entity_next_to(
        Prototype.StoneFurnace,
        reference_position=burner_mining_drill.drop_position,
        direction=Direction.UP,
        spacing=0,
    )

    # place a burner inserter
    burner_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=stone_furnace.position,
        direction=Direction.UP,
        spacing=0,
    )

    def ensure_ingredients(game, recipe, quantity=1):
        for ingredient in recipe.ingredients:
            required = ingredient.count * quantity
            available = game.inspect_inventory()[ingredient.name]
            if available < required:
                craft_recursive(game, ingredient.name, required - available)

    def craft_recursive(game, item_name, quantity):
        if item_name in [
            "copper-ore",
            "iron-ore",
            "wood",
            "copper-plate",
            "iron-plate",
        ]:
            return
        recipe = game.get_prototype_recipe(item_name)
        ensure_ingredients(game, recipe, quantity)
        game.craft_item(item_name, quantity=quantity)

    recipe = game.get_prototype_recipe(Prototype.AssemblingMachine1)
    ensure_ingredients(game, recipe)

    # craft an assembly machine
    game.craft_item(Prototype.AssemblingMachine1)

    # place the assembly machine
    assembly_machine = game.place_entity_next_to(
        Prototype.AssemblingMachine1,
        reference_position=burner_inserter.drop_position,
        direction=Direction.UP,
        spacing=0,
    )
    # set the recipe for the assembly machine to produce iron gears
    game.set_entity_recipe(assembly_machine, Prototype.IronGearWheel)

    # craft an offshore pump
    recipe = game.get_prototype_recipe(Prototype.OffshorePump)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.OffshorePump)

    # place the offshore pump at nearest water source
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, position=game.nearest(Resource.Water)
    )

    # craft a boiler
    recipe = game.get_prototype_recipe(Prototype.Boiler)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.Boiler)

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=Direction.UP,
        spacing=2,
    )

    # craft a steam engine
    recipe = game.get_prototype_recipe(Prototype.SteamEngine)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.SteamEngine)

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler.position,
        direction=Direction.RIGHT,
        spacing=2,
    )

    # connect the steam engine and assembly machine with power poles

    # harvest nearby trees for wood
    tree_patch = game.get_resource_patch(Resource.Wood, game.nearest(Resource.Wood))
    game.move_to(tree_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(tree_patch.bounding_box.left_top, quantity=30)

    # craft 15 small electric poles
    recipe = game.get_prototype_recipe(Prototype.SmallElectricPole)
    ensure_ingredients(game, recipe, quantity=12)
    game.craft_item(Prototype.SmallElectricPole, quantity=12)

    # place connect the steam engine and assembly machine with power poles
    game.connect_entities(
        steam_engine, assembly_machine, connection_type=Prototype.SmallElectricPole
    )

    # game.place_entity(Prototype.OffshorePump, position=water_patch.bounding_box.left_top)
