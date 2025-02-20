import pytest

from entities import Position, Direction, Entity
from game_types import Prototype, RecipeName, prototype_by_name, Resource
from env.src.instance import FactorioInstance


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'pipe': 200,
        'offshore-pump': 1,
        'steam-engine': 5,
        'oil-refinery': 3,
        'chemical-plant': 3,
        'uranium-ore': 100,
        'inserter': 5,
        'iron-chest': 5,
        'storage-tank': 8,
        'iron-plate': 200,
        'steel-chest': 5,
        'pipe-to-ground': 20,
        'sulfur': 100,
        'coal': 200,
        'solar-panel': 3,
        'small-electric-pole': 10,
        "burner-inserter": 25,
        "transport-belt": 200,
        "wooden-chest": 5,
        "copper-plate": 50,
        "pumpjack": 1,
        
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace




def _insert_fluid_at_position(game, position, fluid="water"):
    command = f'/c game.surfaces[1].find_entity("storage-tank", {{{position.x},{position.y}}}).fluidbox[1] = {{ name = "{fluid}", amount = 25000 }}'
    game.instance.rcon_client.send_command(command)

def setup_power(game, power_position, building):
    game.move_to(power_position)
    panel = game.place_entity(Prototype.SolarPanel, Direction.UP, power_position)
    panel = game.get_entity(Prototype.SolarPanel, power_position)
    game.connect_entities(panel, building,
                          connection_type=Prototype.SmallElectricPole)


def create_filled_tank_at_position(game, position, fluid):
    game.move_to(position)
    tank = game.place_entity(Prototype.StorageTank, Direction.UP, position)
    _insert_fluid_at_position(game, position, fluid)
    return game.get_entity(Prototype.StorageTank, position)


def setup_fluid_input(game, fluid_name: str, base_position: Position) -> tuple:
    """Creates a filled storage tank for fluid input"""
    tank = create_filled_tank_at_position(game, base_position, fluid_name)
    return tank, base_position


def create_solid_input_line(game, item_prototype: Prototype, start_position: Position, building: Entity, y_offset=0):
    """Creates a chest + inserter system for solid inputs, connecting to a target position"""
    # Place chest with items at the right side
    game.move_to(start_position)
    chest = game.place_entity(Prototype.SteelChest, Direction.UP, start_position)
    game.insert_item(item_prototype, chest, quantity=100)

    # Place chest output inserter
    chest_inserter = game.place_entity(Prototype.BurnerInserter, Direction.LEFT,
                                       Position(x=start_position.x-1, y=start_position.y))
    game.insert_item(Prototype.Coal, chest_inserter, quantity=5)

    # Place target input inserter
    target_inserter = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=building.position.up() + Position(x=0, y=y_offset), direction=Direction.RIGHT)
    target_inserter = game.rotate_entity(target_inserter, Direction.LEFT)

    # Connect inserters with transport belt
    game.connect_entities(chest_inserter, target_inserter,
                          connection_type=Prototype.TransportBelt)

    game.insert_item(Prototype.Coal, target_inserter, quantity=5)
    return target_inserter


def setup_processing_building(game, recipe_name: RecipeName, position: Position, prototype: Prototype, direction):
    """Places and configures the appropriate processing building for a recipe"""
    requirements = game.get_prototype_recipe(recipe_name)

    building = game.place_entity(prototype, direction, position)

    # Set the recipe
    building = game.set_entity_recipe(building, recipe_name)

    return building, requirements

def test_coal_liquefaction(game):
    recipe_setup(game, [RecipeName.CoalLiquefaction], Prototype.OilRefinery)
    #recipe_setup(game, [RecipeName.CoalLiquefaction], Prototype.OilRefinery, Direction.UP)
    #AWrecipe_setup(game, [RecipeName.CoalLiquefaction], Prototype.OilRefinery, Direction.RIGHT)

def test_advanced_oil_processing(game):
    recipe_setup(game, [RecipeName.AdvancedOilProcessing], Prototype.OilRefinery)

def test_basic_oil_processing(game):
    recipe_setup(game, [RecipeName.BasicOilProcessing], Prototype.OilRefinery)

def test_sulfuric_acid_production(game):
    recipe_setup(game, [RecipeName.SulfuricAcid], Prototype.ChemicalPlant)

def test_heavy_oil_cracking(game):
    recipe_setup(game, [RecipeName.HeavyOilCracking], Prototype.ChemicalPlant)

def test_light_oil_cracking(game):
    recipe_setup(game, [RecipeName.LightOilCracking], Prototype.ChemicalPlant)

def test_solid_fuel_from_light_oil(game):
    recipe_setup(game, [RecipeName.SolidFuelFromLightOil], Prototype.ChemicalPlant)

def test_solid_fuel_from_heavy_oil(game):
    recipe_setup(game, [RecipeName.SolidFuelFromHeavyOil], Prototype.ChemicalPlant)

def test_solid_fuel_from_petroleum_gas(game):
    recipe_setup(game, [RecipeName.SolidFuelFromPetroleumGas], Prototype.ChemicalPlant)

def test_lubricant(game):
    recipe_setup(game, [Prototype.Lubricant], Prototype.ChemicalPlant)

def test_sulfur(game):
    recipe_setup(game, [Prototype.Sulfur], Prototype.ChemicalPlant)

def test_plastic_bar(game):
    recipe_setup(game, [Prototype.PlasticBar], Prototype.ChemicalPlant)

def test_battery(game):
    recipe_setup(game, [Prototype.Battery], Prototype.ChemicalPlant)

def test_end_to_end_lubricant_tanks(game):
    pumpjack_pos = game.nearest(Resource.CrudeOil)
    game.move_to(pumpjack_pos)
    game.move_to(Position(pumpjack_pos.x, pumpjack_pos.y - 5))
    pumpjack = game.place_entity(Prototype.PumpJack, position = pumpjack_pos)


    setup_power(game, pumpjack_pos.up(10), pumpjack)

    oil_refinery_pos = Position(pumpjack_pos.x + 15, pumpjack_pos.y)
    game.move_to(oil_refinery_pos)
    oil_refinery = game.place_entity(Prototype.OilRefinery, position = oil_refinery_pos)
    game.set_entity_recipe(oil_refinery, RecipeName.AdvancedOilProcessing)

    setup_power(game, oil_refinery_pos.up(10), oil_refinery)

    game.connect_entities(pumpjack, oil_refinery, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})

    storage_tank_1_pos = Position(oil_refinery_pos.x + 10, oil_refinery_pos.y)
    game.move_to(storage_tank_1_pos)
    storage_tank_1 = game.place_entity(Prototype.StorageTank, position = storage_tank_1_pos)
    game.connect_entities(oil_refinery, storage_tank_1, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})

    storage_tank_2_pos = Position(oil_refinery_pos.x + 10, oil_refinery_pos.y + 5)
    game.move_to(storage_tank_2_pos)
    storage_tank_2 = game.place_entity(Prototype.StorageTank, position = storage_tank_2_pos)
    game.connect_entities(storage_tank_1, storage_tank_2, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})

    storage_tank_3_pos = Position(oil_refinery_pos.x + 10, oil_refinery_pos.y - 5)
    game.move_to(storage_tank_3_pos)
    storage_tank_3 = game.place_entity(Prototype.StorageTank, position = storage_tank_3_pos)
    game.connect_entities(storage_tank_1, storage_tank_3, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})


def test_end_to_end_lubricant_direct(game):
    pumpjack_pos = game.nearest(Resource.CrudeOil)
    game.move_to(pumpjack_pos)
    game.move_to(Position(pumpjack_pos.x, pumpjack_pos.y - 5))
    pumpjack = game.place_entity(Prototype.PumpJack, position = pumpjack_pos)


    setup_power(game, pumpjack_pos.up(10), pumpjack)

    oil_refinery_pos = Position(pumpjack_pos.x + 15, pumpjack_pos.y)
    game.move_to(oil_refinery_pos)
    oil_refinery = game.place_entity(Prototype.OilRefinery, position = oil_refinery_pos)
    oil_refinery = game.set_entity_recipe(oil_refinery, RecipeName.AdvancedOilProcessing)

    setup_power(game, oil_refinery_pos.up(10), oil_refinery)

    game.connect_entities(pumpjack, oil_refinery, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})

    chemical_plant_pos = Position(pumpjack_pos.x + 25, pumpjack_pos.y)
    game.move_to(chemical_plant_pos)
    chem_plant = game.place_entity(Prototype.ChemicalPlant, position = chemical_plant_pos)
    chem_plant = game.set_entity_recipe(chem_plant, Prototype.Lubricant)

    setup_power(game, chemical_plant_pos.up(10), chem_plant)
    game.connect_entities(oil_refinery, chem_plant, connection_type={Prototype.Pipe, Prototype.UndergroundPipe})
    game.sleep(10)

def recipe_setup(game, recipes_to_test, prototype, direction=Direction.DOWN):
    """Test setup for various recipes with proper positioning"""
    for recipe in recipes_to_test:
        # Reset game state for each recipe
        game.instance.reset()

        # Start with placing the processing building
        building_position = Position(x=-50, y=15)
        game.move_to(building_position)
        building, requirements = setup_processing_building(game, recipe, building_position, prototype, direction)
        power = setup_power(game, building_position.up(10), building)

        # Set up fluid inputs (to the left of building)
        fluid_inputs = {}
        current_x = 0
        for ingredient in requirements.ingredients:
            if ingredient.type == 'fluid':
                tank, position = setup_fluid_input(
                    game,
                    ingredient.name,
                    Position(x=building_position.x + current_x, y=building_position.y-20)
                )
                fluid_inputs[ingredient.name] = position
                current_x += 4

        # Set up solid inputs (from the right side)
        solid_inputs = {}
        current_x = 8
        current_y = 0
        for ingredient in requirements.ingredients:
            if ingredient.type != 'fluid':
                # Calculate positions for the input line
                chest_position = Position(x=building_position.x + current_x, y=building_position.y+current_y)

                # Create input line
                inserter = create_solid_input_line(
                    game,
                    prototype_by_name[ingredient.name],
                    chest_position,
                    building,
                    y_offset=current_y
                )
                solid_inputs[ingredient.name] = inserter.position
                current_y += 2

        # Create output tanks for fluid products
        output_tanks = {}
        current_x = 0

        solid_chests = []
        for product in requirements.products:
            if product.type == 'fluid':
                game.move_to(Position(x=building_position.x + current_x, y=building_position.y + 16))
                tank = game.place_entity(
                    Prototype.StorageTank,
                    Direction.UP,
                    Position(x=building_position.x + current_x, y=building_position.y + 16)
                )
                output_tanks[product.name] = tank.position
                current_x += 8
            else:
                game.move_to(building.position)
                output_inserter = game.place_entity_next_to(Prototype.BurnerInserter, reference_position = building.position,
                                          direction=Direction.LEFT)
                output_inserter = game.insert_item(Prototype.Coal, output_inserter, quantity=10)
                solid_output_chest = game.place_entity(Prototype.WoodenChest, position = output_inserter.drop_position)
                solid_chests.append((solid_output_chest, product.name))
        for name, position in output_tanks.items():
            game.connect_entities(building, position, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})

        # Connect fluid inputs and outputs
        for name, position in fluid_inputs.items():
            game.connect_entities(position, building, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})


        game.sleep(40)

        successes = []
        for contents, tank in output_tanks.items():
            tank = game.get_entity(Prototype.StorageTank, tank)
            for fluid_box in tank.fluid_box:
                if fluid_box['amount'] > 0:
                    successes.append(True)

        if len(successes) == len(output_tanks.values()):
            assert all(successes), "Some outputs were not detected"
        else:
            assert False, "Not all tanks are filling up"
        if solid_chests:
            chest = game.get_entity(Prototype.WoodenChest, solid_chests[0][0].position)
            chest_inventory = game.inspect_inventory(chest)
            assert chest_inventory[solid_chests[0][1]] > 0, "Solid output not detected"
