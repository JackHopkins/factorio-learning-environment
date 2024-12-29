
def test_defence(game):
    # First, gather available resources
    iron_ore_position = nearest(Resource.IronOre)
    coal_position = nearest(Resource.Coal)

    # Harvest iron ore and coal
    move_to(iron_ore_position)
    iron_ore_harvested = 0
    while iron_ore_harvested < 400:
        iron_ore_harvested += harvest_resource(iron_ore_position, 50)

    copper_ore_position = nearest(Resource.CopperOre)
    move_to(copper_ore_position)
    copper_ore_harvested = 0
    while copper_ore_harvested < 200:
        copper_ore_harvested += harvest_resource(copper_ore_position, 50)

    coal_harvested = harvest_resource(coal_position, 50)

    print(f"Harvested {iron_ore_harvested} iron ore and {coal_harvested} coal")

    # Craft iron plates
    iron_plates = craft_item(Prototype.IronPlate, iron_ore_harvested)
    print(f"Crafted {iron_plates} iron plates")

    # Craft copper plates
    copper_plates = craft_item(Prototype.CopperPlate, copper_ore_harvested)
    print(f"Crafted {copper_plates} copper plates")

    # Calculate how many items we can craft based on available iron plates
    max_gears = iron_plates // 8
    max_ammo = iron_plates // 8
    max_turrets = min(5, iron_plates // 20)  # Cap at 5 turrets

    # Craft necessary items
    gears_crafted = craft_item(Prototype.IronGearWheel, max_gears)
    ammo_crafted = craft_item(Prototype.FirearmMagazine, max_ammo)
    turrets_crafted = craft_item(Prototype.GunTurret, max_turrets)

    print(
        f"Crafted {gears_crafted} iron gear wheels, {ammo_crafted} firearm magazines, and {turrets_crafted} gun turrets")

    # Choose a defensive location (adjust as needed)
    defensive_position = Position(x=10, y=10)

    # Place the gun turrets in a line
    turrets = []
    for i in range(turrets_crafted):
        turret_position = Position(x=defensive_position.x + i * 2, y=defensive_position.y)
        move_to(turret_position)
        turret = place_entity(Prototype.GunTurret, direction=Direction.SOUTH, position=turret_position)
        if turret:
            turrets.append(turret)

    print(f"Placed {len(turrets)} gun turrets")

    # Supply ammunition to each turret
    if turrets:
        ammo_per_turret = min(20, ammo_crafted // len(turrets))
        for turret in turrets:
            inserted_ammo = insert_item(Prototype.FirearmMagazine, turret, ammo_per_turret)
            if inserted_ammo:
                print(f"Inserted {ammo_per_turret} ammunition into turret at {turret.position}")
            else:
                print(f"Failed to insert ammunition into turret at {turret.position}")

    # Verify total ammunition used
    player_inventory = inspect_inventory()
    remaining_ammo = player_inventory.get(Prototype.FirearmMagazine, 0)

    print(f"Defensive line of {len(turrets)} gun turrets built and supplied with {ammo_per_turret} ammunition each")
    print(f"Remaining ammunition in inventory: {remaining_ammo}")

    # Final assertions to check if we met the objective
    assert len(turrets) > 0, "Failed to build any gun turrets"
    assert len(turrets) <= 5, f"Built too many turrets: {len(turrets)}"
    assert remaining_ammo < ammo_crafted, "Failed to supply turrets with ammunition"

    # Additional assertion to ensure we built as many turrets as possible
    assert len(turrets) == turrets_crafted, f"Expected to place {turrets_crafted} turrets, but placed {len(turrets)}"

    print("Objective completed: Built a defensive line of gun turrets and manually supplied them with ammunition")


def test_collect_iron_ore(game):
    """
    Collect 10 iron ore
    :param game:
    :return:
    """
    iron_ore = nearest(Resource.IronOre)
    # move to the iron ore
    move_to(iron_ore)
    harvest_resource(iron_ore)

    assert inspect_inventory()[Prototype.IronOre] == 1
    reset()


def test_place_ore_in_furnace(game):
    """
    Collect 10 iron ore and place it in a furnace
    :param game:
    :return:
    """
    furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # move to the iron ore
    iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
    move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the coal
    coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
    move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the furnace
    move_to(furnace.position)
    insert_item(Prototype.IronOre, furnace, quantity=10)
    insert_item(Prototype.Coal, furnace, quantity=10)

    reset()


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = inspect_inventory()[Prototype.Pipe]

    boiler: Entity = place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    move_to(Position(x=0, y=10))
    steam_engine: Entity = place_entity(Prototype.SteamEngine, position=Position(x=0, y=10))

    try:
        connection: List[Entity] = connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        assert False
    except Exception as e:
        print(e)
        assert True
    reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),

    for offset in offsets:
        boiler: Entity = place_entity(Prototype.Boiler, position=Position(x=0, y=0))
        move_to(offset)

        steam_engine: Entity = place_entity(Prototype.SteamEngine, position=offset)

        try:
            connection: List[Union[EntityGroup, Entity]] = connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection[0].pipes)

        reset()  # Reset the game state after each iteration


def test_build_iron_gear_factory(game):
    """
    Build a factory that produces iron gears from iron plates.
    :param game:
    :return:
    """
    # move to the iron ore
    iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
    move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 80 iron ore
    while inspect_inventory()[Prototype.IronOre] < 80:
        harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the stone patch
    stone_patch = get_resource_patch(Resource.Stone, nearest(Resource.Stone))

    # harvest 10 stone
    move_to(stone_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(stone_patch.bounding_box.left_top, quantity=10)

    # move to the coal patch
    coal_patch: ResourcePatch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
    move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 30 coal
    while inspect_inventory()[Prototype.Coal] < 30:
        harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the copper patch
    copper_patch: ResourcePatch = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
    move_to(copper_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 10 copper ore
    while inspect_inventory()[Prototype.CopperOre] < 30:
        harvest_resource(copper_patch.bounding_box.left_top, quantity=10)

    # move to the origin
    move_to(Position(x=0, y=0))

    # place a stone furnace
    stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # insert 20 coal into the stone furnace
    insert_item(Prototype.Coal, stone_furnace, quantity=20)

    # insert 80 iron ore into the stone furnace
    insert_item(Prototype.IronOre, stone_furnace, quantity=50)

    # check if the stone furnace has produced iron plates
    while inspect_inventory(stone_furnace)[Prototype.IronPlate] < 50:
        sleep(1)

    # extract the iron plates from the stone furnace
    extract_item(Prototype.IronPlate, stone_furnace, quantity=50)

    # insert 30 iron ore into the stone furnace
    insert_item(Prototype.IronOre, stone_furnace, quantity=30)

    # check if the stone furnace has produced iron plates
    while inspect_inventory(stone_furnace)[Prototype.IronPlate] < 30:
        sleep(1)

    # extract the iron plates from the stone furnace
    extract_item(Prototype.IronPlate, stone_furnace, quantity=30)

    # insert 20 copper ore into the stone furnace
    insert_item(Prototype.CopperOre, stone_furnace, quantity=20)

    # check if the stone furnace has produced copper plates
    while inspect_inventory(stone_furnace)[Prototype.CopperPlate] < 20:
        sleep(5)

    # extract the copper plates from the stone furnace
    extract_item(Prototype.CopperPlate, stone_furnace, quantity=20)

    # pick up the stone furnace
    pickup_entity(stone_furnace)

    # get recipe for burner mining drill
    recipe: Recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

    # craft any ingredient that is missing
    for ingredient in recipe.ingredients:
        if inspect_inventory()[ingredient.name] < ingredient.count:
            craft_item(ingredient.name, quantity=ingredient.count)

    # craft a burner mining drill
    craft_item(Prototype.BurnerMiningDrill)

    # move to the iron ore patch
    move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # place a burner mining drill
    burner_mining_drill: BurnerMiningDrill = place_entity(Prototype.BurnerMiningDrill,
                                                               position=iron_ore_patch.bounding_box.left_top)

    # fuel the burner mining drill
    insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

    # place the stone furnace
    stone_furnace = place_entity_next_to(Prototype.StoneFurnace,
                                              reference_position=burner_mining_drill.drop_position,
                                              direction=Direction.UP,
                                              spacing=0)

    # place a burner inserter
    burner_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=stone_furnace.position,
                                                direction=Direction.UP,
                                                spacing=0)

    def ensure_ingredients(game, recipe, quantity=1):
        for ingredient in recipe.ingredients:
            required = ingredient.count * quantity
            available = inspect_inventory()[ingredient.name]
            if available < required:
                craft_recursive(game, ingredient.name, required - available)

    def craft_recursive(game, item_name, quantity):
        recipe = get_prototype_recipe(item_name)
        ensure_ingredients(game, recipe, quantity)
        craft_item(item_name, quantity=quantity)

    recipe = get_prototype_recipe(Prototype.AssemblingMachine1)
    ensure_ingredients(game, recipe)

    # craft an assembly machine
    craft_item(Prototype.AssemblingMachine1)

    # place the assembly machine
    assembly_machine = place_entity_next_to(Prototype.AssemblingMachine1,
                                                 reference_position=burner_inserter.drop_position,
                                                 direction=Direction.UP,
                                                 spacing=0)
    # set the recipe for the assembly machine to produce iron gears
    set_entity_recipe(assembly_machine, Prototype.IronGearWheel)

    # craft an offshore pump
    recipe = get_prototype_recipe(Prototype.OffshorePump)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.OffshorePump)

    # place the offshore pump at nearest water source
    move_to(nearest(Resource.Water))
    offshore_pump = place_entity(Prototype.OffshorePump,
                                      position=nearest(Resource.Water))

    # craft a boiler
    recipe = get_prototype_recipe(Prototype.Boiler)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.Boiler)

    # place the boiler next to the offshore pump
    boiler = place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=Direction.UP,
                                       spacing=2)

    # craft a steam engine
    recipe = get_prototype_recipe(Prototype.SteamEngine)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.SteamEngine)

    # place the steam engine next to the boiler
    steam_engine = place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=Direction.RIGHT,
                                             spacing=2)

    # connect the steam engine and assembly machine with power poles

    # harvest nearby trees for wood
    tree_patch = get_resource_patch(Resource.Wood, nearest(Resource.Wood))
    move_to(tree_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(tree_patch.bounding_box.left_top, quantity=30)

    # craft 15 small electric poles
    recipe = get_prototype_recipe(Prototype.SmallElectricPole)
    ensure_ingredients(game, recipe, quantity=12)
    craft_item(Prototype.SmallElectricPole, quantity=12)

    # place connect the steam engine and assembly machine with power poles
    connect_entities(steam_engine, assembly_machine, connection_type=Prototype.SmallElectricPole)

    #place_entity(Prototype.OffshorePump, position=water_patch.bounding_box.left_top)

def test_auto_fueling_iron_smelting_factory(game):
    """
    Builds an auto-fueling iron smelting factory:
    - Mines coal and iron ore.
    - Uses transport belts to deliver coal to fuel the iron miner and furnace.
    - Smelts iron ore into iron plates.
    - Stores iron plates in an iron chest.
    """
    # Move to the nearest coal resource and place a burner mining drill
    coal_position = nearest(Resource.Coal)
    move_to(coal_position)
    coal_drill = place_entity(Prototype.BurnerMiningDrill, position=coal_position, direction=Direction.DOWN)

    # Find the nearest iron ore resource
    iron_position = nearest(Resource.IronOre)

    # Place the iron mining drill at iron_position, facing down
    move_to_iron = move_to(iron_position)
    iron_drill = place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)

    # Place an inserter to fuel the iron drill from the coal belt
    inserter_position = Position(x=iron_drill.position.x + iron_drill.tile_dimensions.tile_width/2, y=iron_drill.position.y-1)
    iron_drill_fuel_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                           reference_position=iron_drill.position,
                                                           direction=Direction.RIGHT,
                                                           spacing=0)
    iron_drill_fuel_inserter = rotate_entity(iron_drill_fuel_inserter, Direction.LEFT)

    coal_belt = connect_entities(source=coal_drill, target=iron_drill_fuel_inserter, connection_type=Prototype.TransportBelt)

    # Extend coal belt to pass next to the furnace position
    furnace_position = Position(x=iron_drill.drop_position.x, y=iron_drill.drop_position.y + 1)

    # Place the furnace at the iron drill's drop position
    iron_furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

    # Place an inserter to fuel the furnace from the coal belt
    furnace_fuel_inserter_position = Position(x=iron_furnace.position.x + 1, y=iron_furnace.position.y)
    furnace_fuel_inserter = place_entity(Prototype.BurnerInserter, position=furnace_fuel_inserter_position, direction=Direction.LEFT)

    coal_belt_to_furnace = connect_entities(iron_drill_fuel_inserter.pickup_position, furnace_fuel_inserter.pickup_position, connection_type=Prototype.TransportBelt)
    coal_belt.extend(coal_belt_to_furnace)

    furnace_to_chest_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                          reference_position=iron_furnace.position,
                                                          direction=Direction.DOWN,
                                                          spacing=0)
    # Place an iron chest to store iron plates
    iron_chest = place_entity_next_to(Prototype.IronChest,
                                           reference_position=iron_furnace.position,
                                           direction=Direction.DOWN,
                                           spacing=1)

    # Start the system by fueling the coal drill
    move_to(coal_position)
    insert_item(Prototype.Coal, coal_drill, quantity=10)

    # Wait for some time to let the system produce iron plates
    sleep(60)  # Wait for 60 seconds

    # Check the iron chest to see if iron plates have been produced
    chest_inventory = inspect_inventory(iron_chest)
    iron_plates_in_chest = chest_inventory.get(Prototype.IronPlate, 0)

    # Assert that some iron plates have been produced
    assert iron_plates_in_chest > 0, "No iron plates were produced"

    print(f"Successfully produced {iron_plates_in_chest} iron plates.")


def test_create_offshore_pump_to_steam_engine(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = inspect_inventory()[Prototype.Pipe]

    # move to the nearest water source
    water_location = nearest(Resource.Water)
    move_to(water_location)

    offshore_pump = place_entity(Prototype.OffshorePump,
                                      position=water_location,
                                      direction=Direction.UP)
    assert offshore_pump.direction.value == Direction.UP.value
    # Get offshore pump direction
    direction = offshore_pump.direction

    # pump connection point
    pump_connection_point = offshore_pump.connection_points[0]

    # place the boiler next to the offshore pump
    boiler = place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=direction,
                                       spacing=2)
    assert boiler.direction.value == direction.value

    # rotate the boiler to face the offshore pump
    boiler = rotate_entity(boiler, Direction.next_clockwise(direction))

    # insert coal into the boiler
    insert_item(Prototype.Coal, boiler, quantity=5)

    # connect the boiler and offshore pump with a pipe
    offshore_pump_to_boiler_pipes = connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)

    move_to(Position(x=0, y=10))
    steam_engine: Entity = place_entity_next_to(Prototype.SteamEngine,
                                                     reference_position=boiler.position,
                                                     direction=boiler.direction,
                                                     spacing=1)

    # connect the boiler and steam engine with a pipe
    boiler_to_steam_engine_pipes = connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    inspected_steam_engine = inspect_entities(position=steam_engine.position, radius=1).get_entity(Prototype.SteamEngine)
    assert inspected_steam_engine.warning == 'not connected to power network'

    assert steam_engine.direction.value == boiler.direction.value
    add_command(f"/c take_screenshot{{zoom=1, anti_alias=true, show_entity_info=true, position={{x={boiler.position.x}, y={boiler.position.y}}}}}", raw=True)
    execute_transaction()


def test_build_iron_gear_factory(game):
    """
    Build a factory that produces iron gears from iron plates.
    :param game:
    :return:
    """
    # move to the iron ore
    iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
    move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 80 iron ore
    while inspect_inventory()[Prototype.IronOre] < 80:
        harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the stone patch
    stone_patch = get_resource_patch(Resource.Stone, nearest(Resource.Stone))

    # harvest 10 stone
    move_to(stone_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(stone_patch.bounding_box.left_top, quantity=10)

    # move to the coal patch
    coal_patch: ResourcePatch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
    move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 30 coal
    while inspect_inventory()[Prototype.Coal] < 30:
        harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the copper patch
    copper_patch: ResourcePatch = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
    move_to(copper_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 10 copper ore
    while inspect_inventory()[Prototype.CopperOre] < 30:
        harvest_resource(copper_patch.bounding_box.left_top, quantity=10)

    # move to the origin
    move_to(Position(x=0, y=0))

    # place a stone furnace
    stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # insert 20 coal into the stone furnace
    insert_item(Prototype.Coal, stone_furnace, quantity=20)

    # insert 80 iron ore into the stone furnace
    insert_item(Prototype.IronOre, stone_furnace, quantity=50)

    # check if the stone furnace has produced iron plates
    while inspect_inventory(stone_furnace)[Prototype.IronPlate] < 50:
        sleep(1)

    # extract the iron plates from the stone furnace
    extract_item(Prototype.IronPlate, stone_furnace, quantity=50)

    # insert 80 iron ore into the stone furnace
    insert_item(Prototype.IronOre, stone_furnace, quantity=30)

    # check if the stone furnace has produced iron plates
    while inspect_inventory(stone_furnace)[Prototype.IronPlate] < 30:
        sleep(1)

    # extract the iron plates from the stone furnace
    extract_item(Prototype.IronPlate, stone_furnace, quantity=30)

    # insert 20 copper ore into the stone furnace
    insert_item(Prototype.CopperOre, stone_furnace, quantity=20)

    # check if the stone furnace has produced copper plates
    while inspect_inventory(stone_furnace)[Prototype.CopperPlate] < 20:
        sleep(5)

    # extract the copper plates from the stone furnace
    extract_item(Prototype.CopperPlate, stone_furnace, quantity=20)

    # pick up the stone furnace
    pickup_entity(stone_furnace)

    # get recipe for burner mining drill
    recipe: Recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

    # craft any ingredient that is missing
    for ingredient in recipe.ingredients:
        if inspect_inventory()[ingredient.name] < ingredient.count:
            craft_item(ingredient.name, quantity=ingredient.count)

    # craft a burner mining drill
    craft_item(Prototype.BurnerMiningDrill)

    # move to the iron ore patch
    move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # place a burner mining drill
    burner_mining_drill: BurnerMiningDrill = place_entity(Prototype.BurnerMiningDrill,
                                                               position=iron_ore_patch.bounding_box.left_top)

    # fuel the burner mining drill
    insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

    # place the stone furnace
    stone_furnace = place_entity_next_to(Prototype.StoneFurnace,
                                              reference_position=burner_mining_drill.drop_position,
                                              direction=Direction.UP,
                                              spacing=0)

    # place a burner inserter
    burner_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=stone_furnace.position,
                                                direction=Direction.UP,
                                                spacing=0)

    def ensure_ingredients(game, recipe, quantity=1):
        for ingredient in recipe.ingredients:
            required = ingredient.count * quantity
            available = inspect_inventory()[ingredient.name]
            if available < required:
                craft_recursive(game, ingredient.name, required - available)

    def craft_recursive(game, item_name, quantity):
        recipe = get_prototype_recipe(item_name)
        ensure_ingredients(game, recipe, quantity)
        craft_item(item_name, quantity=quantity)

    recipe = get_prototype_recipe(Prototype.AssemblingMachine1)
    ensure_ingredients(game, recipe)

    # craft an assembly machine
    craft_item(Prototype.AssemblingMachine1)

    # place the assembly machine
    assembly_machine = place_entity_next_to(Prototype.AssemblingMachine1,
                                                 reference_position=burner_inserter.position,
                                                 direction=Direction.UP,
                                                 spacing=0)
    # set the recipe for the assembly machine to produce iron gears
    set_entity_recipe(assembly_machine, Prototype.IronGearWheel)

    # craft an offshore pump
    recipe = get_prototype_recipe(Prototype.OffshorePump)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.OffshorePump)

    # place the offshore pump at nearest water source
    move_to(nearest(Resource.Water))
    offshore_pump = place_entity(Prototype.OffshorePump,
                                      position=nearest(Resource.Water),
                                      direction=Direction.LEFT)

    # craft a boiler
    recipe = get_prototype_recipe(Prototype.Boiler)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.Boiler)

    # place the boiler next to the offshore pump
    boiler = place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=Direction.LEFT,
                                       spacing=2)


    # craft a steam engine
    recipe = get_prototype_recipe(Prototype.SteamEngine)
    ensure_ingredients(game, recipe)
    craft_item(Prototype.SteamEngine)

    # place the steam engine next to the boiler
    steam_engine = place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=Direction.LEFT,
                                             spacing=2)

    # connect the steam engine and assembly machine with power poles

    # harvest nearby trees for wood
    tree_patch = get_resource_patch(Resource.Wood, nearest(Resource.Wood))
    move_to(tree_patch.bounding_box.left_top + Position(x=1, y=1))
    harvest_resource(tree_patch.bounding_box.left_top, quantity=40)

    # craft 5 small electric poles
    recipe = get_prototype_recipe(Prototype.SmallElectricPole)
    ensure_ingredients(game, recipe, quantity=10)
    craft_item(Prototype.SmallElectricPole, quantity=10)

    # place connect the steam engine and assembly machine with power poles
    connect_entities(steam_engine, assembly_machine, connection_type=Prototype.SmallElectricPole)

    # place connective pipes between the boiler and steam engine
    connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    # place connective pipes between the boiler and offshore pump
    connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

    move_to(boiler.position)
    insert_item(Prototype.Coal, boiler, quantity=10)
    insert_item(Prototype.Coal, burner_inserter, quantity=10)
    insert_item(Prototype.Coal, stone_furnace, quantity=10)

    move_to(burner_mining_drill.position)
    insert_item(Prototype.Coal, burner_mining_drill, quantity=10)

    sleep(15)

    # extract the iron gears from the assembly machine
    extract_item(Prototype.IronGearWheel, assembly_machine, quantity=5)

    inventory = inspect_inventory(entity=assembly_machine)

    assert inventory.get(Prototype.IronGearWheel) >= 0


def test_craft_automation_packs_and_research(game):
    # Gather resources
    move_to(nearest(Resource.IronOre))
    harvest_resource(nearest(Resource.IronOre), 20)

    move_to(nearest(Resource.CopperOre))
    harvest_resource(nearest(Resource.CopperOre), 20)

    # Set up basic infrastructure
    move_to(Position(x=0, y=0))
    furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
    assert furnace, "Failed to place stone furnace"

    # Create iron and copper plates
    insert_item(Prototype.IronOre, furnace, quantity=10)
    insert_item(Prototype.Coal, furnace, quantity=10)
    sleep(10)  # Wait for smelting
    iron_plates = extract_item(Prototype.IronPlate, furnace.position, 10)

    insert_item(Prototype.CopperOre, furnace, quantity=10)
    sleep(10)  # Wait for smelting
    copper_plates = extract_item(Prototype.CopperPlate, furnace.position, 10)
    assert iron_plates and copper_plates, "Failed to create iron or copper plates"

    # Craft necessary components
    craft_item(Prototype.IronGearWheel, 10)
    craft_item(Prototype.CopperCable, 10)

    # Craft automation science packs
    craft_item(Prototype.AutomationSciencePack, 10)

    # Verify the crafting result
    inventory = inspect_inventory()
    assert inventory.get(
        Prototype.AutomationSciencePack) >= 10, f"Failed to craft 10 automation science packs. Current count: {inventory.get(Prototype.AutomationSciencePack)}"

    print(f"Successfully crafted {inventory.get(Prototype.AutomationSciencePack)} automation science packs")

    # Place a Lab
    lab = place_entity(Prototype.Lab, Direction.UP, Position(x=2, y=0))
    assert lab, "Failed to place Lab"

    # Insert science packs into the Lab
    insert_item(Prototype.AutomationSciencePack, lab, quantity=10)

    # Verify science packs were inserted
    lab_inventory = inspect_inventory(lab)
    assert lab_inventory.get(
        Prototype.AutomationSciencePack) == 10, f"Failed to insert science packs into Lab. Current count: {lab_inventory.get(Prototype.AutomationSciencePack)}"

    # Start researching (assuming a function to start research exists)
    initial_research = get_research_progress("automation")  # Get initial research progress
    start_research("automation")  # Start researching automation technology

    # Wait for some time to allow research to progress
    sleep(30)

    # Check if research has progressed
    current_research = get_research_progress("automation")
    assert current_research > initial_research, f"Research did not progress. Initial: {initial_research}, Current: {current_research}"

    print(f"Successfully started research. Progress: {current_research}")
    

def test_build_auto_refilling_coal_system(game):
    num_drills = 3

    # Start at the origin
    move_to(Position(x=0, y=0))

    # Find the nearest coal patch
    coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))

    # Move to the center of the coal patch
    move_to(coal_patch.bounding_box.left_top)

    # Place the first drill
    drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Place a chest next to the first drill to collect coal
    chest = place_entity(Prototype.IronChest, Direction.RIGHT, drill.drop_position)

    # Connect the first drill to the chest with an inserter
    inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)
    first_inserter = inserter

    # Place an inserter south of the drill to insert coal into the drill
    drill_bottom_y = drill.position.y + drill.dimensions.height
    drill_inserter = place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=drill.position.x, y=drill_bottom_y))
    drill_inserter = rotate_entity(drill_inserter, Direction.UP)
    first_drill_inserter = drill_inserter

    # Start the transport belt from the chest
    move_to(inserter.drop_position)

    drills = []
    belts = []

    # Place additional drills and connect them to the belt
    for i in range(1, num_drills):
        # Place the next drill
        next_drill = place_entity_next_to(Prototype.BurnerMiningDrill, drill.position, Direction.RIGHT, spacing=2)
        next_drill = rotate_entity(next_drill, Direction.UP)
        drills.append(next_drill)

        try:
            # Place a chest next to the next drill to collect coal
            chest = place_entity(Prototype.IronChest, Direction.RIGHT, next_drill.drop_position)
        except Exception as e:
            print(f"Could not place chest next to drill: {e}")

        # Place an inserter to connect the chest to the transport belt
        next_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)

        # Place an insert underneath the drill to insert coal into the drill
        drill_bottom_y = next_drill.position.y + next_drill.dimensions.height
        drill_inserter = place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=next_drill.position.x, y=drill_bottom_y))
        drill_inserter = rotate_entity(drill_inserter, Direction.UP)

        # Extend the transport belt to the next drill
        belts.extend(connect_entities(inserter.drop_position, next_inserter.drop_position, Prototype.TransportBelt))

        # Update the drill reference for the next iteration
        drill = next_drill
        inserter = next_inserter
        next_drill_inserter = drill_inserter

    # Connect the drop position of the final drill block to the inserter that is loading it with coal
    belts.extend(connect_entities(next_inserter.drop_position, next_drill_inserter.pickup_position, Prototype.TransportBelt))

    # Connect that inserter to the inserter that is loading the first drill with coal
    belts.extend(connect_entities(next_drill_inserter.pickup_position, first_drill_inserter.pickup_position, Prototype.TransportBelt))

    # Connect the first drill inserter to the drop point of the first inserter
    belts.extend(connect_entities(belts[-1].belts[-1].output_position, belts[0].belts[0].input_position, Prototype.TransportBelt))

    rotate_entity(belts[-1].belts[-1], Direction.RIGHT)
    # Initialize the system by adding some coal to each drill and inserter
    for drill in drills:
        insert_item(Prototype.Coal, drill, 5)

    print(f"Auto-refilling coal mining system with {num_drills} drills has been built!")

def test_simple_automated_drill(game):
    # Find nearest coal patch
    coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
    assert coal_patch, "No coal patch found nearby"

    # Place coal burner mining drill
    drill_position = coal_patch.bounding_box.center
    move_to(drill_position)
    drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, drill_position)
    assert drill, f"Failed to place burner mining drill at {drill_position}"
    print(f"Placed burner mining drill at {drill.position}")

    # Place inserter next to the drill
    inserter_position = Position(x=drill.position.x, y=drill.position.y+1)
    inserter = place_entity(Prototype.BurnerInserter, Direction.UP, inserter_position)
    assert inserter, f"Failed to place inserter at {inserter_position}"
    print(f"Placed inserter at {inserter.position}")

    # Verify inserter is facing the drill
    assert inserter.direction.name == Direction.UP.name, f"Inserter is not facing the drill. Current direction: {inserter.direction}"

    # Place transport belt connecting drill to inserter
    belt_start = drill.drop_position
    belt_end = inserter.pickup_position
    belts = connect_entities(belt_start, belt_end, Prototype.TransportBelt)
    assert belts, f"Failed to place transport belt from {belt_start} to {belt_end}"
    print(f"Placed {len(belts)} transport belt(s) from drill to inserter")

    # Verify the setup
    entities = inspect_entities(drill.position, radius=5)
    assert entities.get_entity(Prototype.BurnerMiningDrill), "Burner mining drill not found in setup"
    assert entities.get_entity(Prototype.BurnerInserter), "Inserter not found in setup"
    assert any(e.name == "transport-belt" for e in entities.entities), "Transport belts not found in setup"

    print("Successfully set up coal mining loop with burner mining drill, inserter, and transport belts")


def test_another_self_fueling_coal_belt(game):
    # Find the nearest coal patch
    coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
    assert coal_patch is not None, "No coal patch found nearby"
    assert coal_patch.size >= 25, f"Coal patch too small: {coal_patch.size} tiles (need at least 25)"

    # Place 5 burner mining drills in a line
    drills = []
    inserters = []
    move_to(coal_patch.bounding_box.center)
    for i in range(5):
        drill_position = Position(x=coal_patch.bounding_box.left_top.x + i * 2, y=coal_patch.bounding_box.center.y)

        drill = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, drill_position)
        inserter = place_entity_next_to(Prototype.BurnerInserter, drill_position, direction=Direction.UP, spacing=0)
        inserter = rotate_entity(inserter, Direction.DOWN)
        assert drill is not None, f"Failed to place burner mining drill at {drill_position}"
        assert inserter is not None, f"Failed to place inserter at {drill_position}"
        drills.append(drill)
        inserters.append(inserter)


    print(f"Placed {len(drills)} burner mining drills")

    # Place transport belt parallel to the drills
    belt_start = Position(x=drills[0].drop_position.x, y=drills[0].drop_position.y)
    belt_end = Position(x=drills[-1].drop_position.x, y=drills[0].drop_position.y)
    belt_entities = connect_entities(belt_start, belt_end, Prototype.TransportBelt)
    assert len(belt_entities) > 0, "Failed to place transport belt"

    belt_to_last_inserter = connect_entities(belt_end, inserters[-1].pickup_position, Prototype.TransportBelt)
    assert len(belt_to_last_inserter) > 0, "Failed to connect belt to last inserter"

    belt_to_first_inserter = connect_entities(inserters[-1].pickup_position, inserters[0].pickup_position, Prototype.TransportBelt)
    assert len(belt_to_first_inserter) > 0, "Failed to connect belt to first inserter"

    belt_to_close_loop = connect_entities(inserters[0].pickup_position, belt_start, Prototype.TransportBelt)
    assert len(belt_to_close_loop) > 0, "Failed to connect belt to close the loop"

    print(f"Placed {len(belt_entities)} transport belt segments")

    print("Completed the belt loop")

    # Verify the setup
    inspection = inspect_entities(coal_patch.bounding_box.center, radius=15)
    assert len([e for e in inspection.entities if
                e.name == Prototype.BurnerMiningDrill.value[0]]) == 5, "Not all burner mining drills were placed"
    assert len([e for e in inspection.entities if
                e.name == Prototype.BurnerInserter.value[0]]) == 5, "Not all inserters were placed"
    # sum all inspected entities with the name transport-belt
    total_belts = sum([e.quantity if e.quantity else 1 for e in inspection.entities if e.name == Prototype.TransportBelt.value[0]])

    assert total_belts >= 15, "Not enough transport belt segments were placed"

    print("All components verified")

    # Kickstart the system by placing coal on the belt
    move_to(drills[0].position)
    coal_placed = insert_item(Prototype.Coal, drills[0], quantity=10)
    assert coal_placed is not None, "Failed to place coal on the belt"

    print("System kickstarted with coal")
    print("Self-fueling belt of 5 burner mining drills successfully set up")

def test_basic_iron_smelting_chain(game):
    # Place iron ore patch
    iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
    assert iron_ore_patch, "No iron ore patch found"
    print(f"Iron ore patch found at {iron_ore_patch.bounding_box.center}")

    # Place burner mining drill on iron ore patch
    move_to(iron_ore_patch.bounding_box.center)
    drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.RIGHT,
                         position=iron_ore_patch.bounding_box.center)
    assert drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {drill.position}")

    # Fuel the burner mining drill
    drill_with_coal = insert_item(Prototype.Coal, drill, quantity=5)
    assert drill_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel burner mining drill"
    print(f"Inserted {drill_with_coal.fuel.get(Prototype.Coal, 0)} coal into burner mining drill")

    # Place stone furnace next to drill
    furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.RIGHT)
    assert furnace, "Failed to place stone furnace"
    print(f"Stone furnace placed at {furnace.position}")

    # Fuel the stone furnace
    furnace_with_coal = insert_item(Prototype.Coal, furnace, quantity=5)
    assert furnace_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel stone furnace"
    print(f"Inserted {furnace_with_coal.fuel.get(Prototype.Coal, 0)} coal into stone furnace")

    # Place inserter next to furnace
    inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position,
                                    direction=Direction.RIGHT)
    assert inserter, "Failed to place inserter"
    print(f"Inserter placed at {inserter.position}")

    # Fuel the inserter
    inserter_with_coal = insert_item(Prototype.Coal, inserter, quantity=2)
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"
    print(f"Inserted {inserter_with_coal.fuel.get(Prototype.Coal, 0)} coal into inserter")

    # Place chest next to inserter
    chest = place_entity_next_to(Prototype.WoodenChest, reference_position=inserter.position, direction=Direction.RIGHT)
    assert chest, "Failed to place chest"
    print(f"Chest placed at {chest.position}")

    # Verify setup
    sleep(60)  # Wait for the system to produce some iron plates

    chest_inventory = inspect_inventory(chest)
    iron_plates = chest_inventory.get(Prototype.IronPlate, 0)
    assert iron_plates > 0, f"No iron plates produced after 60 seconds. Check fuel levels and connections."
    print(f"Success! {iron_plates} iron plates produced and stored in the chest.")

def test_steel_smelting_chain(game):
    # Find the nearest iron ore patch
    iron_ore_position = nearest(Resource.IronOre)
    move_to(iron_ore_position)
    assert iron_ore_position, "No iron ore patch found"

    # Place burner mining drill on iron ore patch
    burner_drill = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, iron_ore_position)
    assert burner_drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {burner_drill.position}")

    # Place two stone furnaces near the burner mining drill
    furnace1 = place_entity_next_to(Prototype.StoneFurnace, burner_drill.position, Direction.RIGHT, spacing=0)
    assert furnace1, "Failed to place first stone furnace"
    print(f"First stone furnace placed at {furnace1.position}")

    furnace2 = place_entity_next_to(Prototype.StoneFurnace, furnace1.position, Direction.RIGHT, spacing=1)
    assert furnace2, "Failed to place second stone furnace"
    print(f"Second stone furnace placed at {furnace2.position}")

    # Place inserters between entities
    inserter1 = place_entity_next_to(Prototype.BurnerInserter, furnace1.position, Direction.RIGHT)
    assert inserter1, "Failed to place second inserter"
    rotate_entity(inserter1, Direction.RIGHT)
    print(f"Second inserter placed at {inserter1.position}")

    # Add fuel to entities (assuming coal is in inventory)
    insert_item(Prototype.Coal, burner_drill, 5)
    insert_item(Prototype.Coal, furnace1, 5)
    insert_item(Prototype.Coal, furnace2, 5)
    insert_item(Prototype.Coal, inserter1, 1)

    # Verify setup
    entities = inspect_entities(burner_drill.position, radius=10)
    assert any(
        e.name == "burner-mining-drill" for e in entities.entities), "Burner mining drill not found in inspection"
    assert sum(
        1 for e in entities.entities if e.name == "stone-furnace") == 2, "Two stone furnaces not found in inspection"
    assert sum(1 for e in entities.entities if
               e.name == "burner-inserter") == 1, "A burner inserter not found in inspection"

    # Test that the stone furnace has steel after 60 seconds
    sleep(60)
    furnace_inventory = inspect_inventory(furnace2)
    steel = furnace_inventory.get(Prototype.SteelPlate, 0)
    assert steel > 0, f"No steel produced after 60 seconds. Check fuel levels and connections."

    print("Steel smelting chain setup complete and verified")


def test_build_iron_plate_factory(game):

    WIDTH_SPACING = 1 # Spacing between entities in our factory the x-axis

    # Find the nearest iron ore patch
    iron_ore_patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))

    # Move to the center of the iron ore patch
    move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.left_top)

    # Place an iron chest above the drill and insert coal
    chest = place_entity_next_to(Prototype.IronChest, miner.position, Direction.UP, spacing=miner.dimensions.height)
    insert_item(Prototype.Coal, chest, 50)

    # Place an inserter to insert coal into the drill to get started
    coal_drill_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.DOWN, spacing=0)

    # Place an inserter to insert coal into the chest
    coal_chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.UP, spacing=0)
    coal_chest_inserter = rotate_entity(coal_chest_inserter, Direction.DOWN)

    # Place an inserter to insert coal into the coal belt to power the drills
    coal_belt_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=0)
    coal_belt_inserter = rotate_entity(coal_belt_inserter, Direction.RIGHT)

    iron_drill_coal_belt_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT, spacing=0)

    # Place a transport belt form the coal belt inserter to the end of the
    coal_belt_start = place_entity_next_to(Prototype.TransportBelt, coal_belt_inserter.position, Direction.RIGHT, spacing=0)

    # Place a transport belt from the miner's output
    iron_belt_start = place_entity_next_to(Prototype.TransportBelt, miner.position, Direction.DOWN, spacing=0)

    # Place 5 stone furnaces along the belt
    furnace_line_start = place_entity_next_to(Prototype.StoneFurnace, miner.position, Direction.DOWN,
                                                   spacing=2)
    current_furnace = furnace_line_start

    for _ in range(3):
        current_furnace = place_entity_next_to(Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT,
                                                    spacing=WIDTH_SPACING)

    # Connect furnaces with transport belt
    above_current_furnace = Position(x=current_furnace.position.x, y=current_furnace.position.y - 2.5)
    iron_belt = connect_entities(iron_belt_start.position, above_current_furnace, Prototype.TransportBelt)

    coal_to_iron_belt = connect_entities(iron_drill_coal_belt_inserter.drop_position, iron_belt[0], Prototype.TransportBelt)

    next_coal_belt_position = coal_belt_start.position

    # Place 4 more drills
    miners = [miner]
    for i in range(3):
        miner = place_entity_next_to(Prototype.BurnerMiningDrill, miner.position, Direction.RIGHT,
                                                     spacing=WIDTH_SPACING)
        miner = rotate_entity(miner, Direction.DOWN)
        miners.append(miner)

        # Connect furnaces with coal belt
        above_current_drill = Position(x=miner.position.x, y=miner.position.y - miner.dimensions.height - 1)
        connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)

        miner_coal_inserter = place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=miner.drop_position.x, y=above_current_drill.y + 1))
        miner_coal_inserter = rotate_entity(miner_coal_inserter, Direction.DOWN)
        next_coal_belt_position = above_current_drill

    # Place inserters for each furnace
    for i in range(4):
        furnace_pos = Position(x=miners[i].drop_position.x, y=furnace_line_start.position.y + 1)
        move_to(furnace_pos)
        place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - (current_furnace.dimensions.height + 2)))
        place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - 1))

    # Place output belt for iron plates
    output_belt = connect_entities(Position(x=furnace_line_start.position.x, y=furnace_line_start.position.y + 2.5),
                          Position(x=current_furnace.position.x, y=furnace_line_start.position.y + 2.5), Prototype.TransportBelt)

    # Place a chest at the end of the output belt
    output_chest = place_entity_next_to(Prototype.IronChest,
                                             Position(x=output_belt[-1].output_positions[0].x,
                                                      y=output_belt[-1].output_positions[0].y),
                                             Direction.RIGHT, spacing=0)

    # Place an inserter to move plates from belt to chest
    place_entity(Prototype.BurnerInserter, Direction.RIGHT,
                      Position(x=output_chest.position.x-1, y=output_chest.position.y))

    # Find nearest coal patch
    coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))

    # Move to the top left of the coal patch
    move_to(coal_patch.bounding_box.left_top)

    # Place a burner mining drill on the coal patch
    coal_miner = place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Connect coal to furnaces with transport belt
    long_coal_belt = connect_entities(coal_miner.drop_position, coal_chest_inserter, Prototype.TransportBelt)

    # Insert coal into the coal miner
    insert_item(Prototype.Coal, coal_miner, 50)

    # Connect the coal belt back to the miner to keep it fueled
    reinserter = place_entity_next_to(Prototype.BurnerInserter, Position(x=coal_miner.position.x-1, y=coal_miner.position.y-1), Direction.LEFT, spacing=0)
    reinserter = rotate_entity(reinserter, Direction.RIGHT)
    print("Simple iron plate factory has been built!")

def test_steam_engines():
    #craft_item(Prototype.OffshorePump)
    move_to(nearest(Resource.Water))
    offshore_pump = place_entity(Prototype.OffshorePump,
                                      position=nearest(Resource.Water))
    boiler = place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    water_pipes = connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

    steam_engine = place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=boiler.direction,
                                             spacing=5)
    steam_pipes = connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    coal_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                              reference_position=boiler.position,
                                              direction=Direction.RIGHT,
                                              spacing=0)
    coal_inserter = rotate_entity(coal_inserter, Direction.LEFT)
    move_to(nearest(Resource.Coal))

    burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, position=nearest(Resource.Coal))
    burner_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                direction=Direction.DOWN,
                                                spacing=0)
    burner_inserter = rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter

    belts = connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)
    assert belts

    coal_to_boiler_belts = connect_entities(belts[0], coal_inserter.pickup_position, connection_type=Prototype.TransportBelt)
    assert coal_to_boiler_belts

    assembler = place_entity_next_to(Prototype.AssemblingMachine1,
                                          reference_position=steam_engine.position,
                                          direction=Direction.LEFT,
                                          spacing=5)

    steam_engine_to_assembler_poles = connect_entities(assembler, steam_engine, connection_type=Prototype.SmallElectricPole)

    assert steam_engine_to_assembler_poles

    # insert coal into the drill
    burner_mining_drill: BurnerMiningDrill = insert_item(Prototype.Coal, burner_mining_drill, 5)

    sleep(30)

    # inspect assembler
    inspected_assembler = inspect_entities(assembler.position, radius=1).get_entity(Prototype.AssemblingMachine1)
    assert not inspected_assembler.warning



def test_iron_smelting():
    """
    Create an auto driller for coal.
    Create a miner for iron ore and a nearby furnace. Connect the miner to the furnace.

    :return:
    """
    move_to(nearest(Resource.Coal))

    burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, position=nearest(Resource.Coal))
    burner_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                direction=DOWN,
                                                spacing=0)
    burner_inserter = rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter

    belts = connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)
    assert belts

    burner_mining_drill: BurnerMiningDrill = insert_item(Prototype.Coal, burner_mining_drill, 5)

    assert burner_mining_drill.fuel[Prototype.Coal] == 5
    nearest_iron_ore = nearest(Resource.IronOre)

    move_to(nearest_iron_ore)
    try:
        iron_mining_drill = place_entity(Prototype.BurnerMiningDrill, position=nearest_iron_ore)
        stone_furnace = place_entity(Prototype.StoneFurnace, position=iron_mining_drill.drop_position)

        coal_to_iron_drill_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                                reference_position=iron_mining_drill.position,
                                                                direction=DOWN,
                                                                spacing=0)
        coal_to_iron_drill_inserter = rotate_entity(coal_to_iron_drill_inserter, Direction.UP)
        coal_to_smelter_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                             reference_position=stone_furnace.position,
                                                             direction=RIGHT,
                                                             spacing=0)
        coal_to_smelter_inserter = rotate_entity(coal_to_smelter_inserter, Direction.LEFT)

        coal_to_drill_belt = connect_entities(coal_to_smelter_inserter.pickup_position,
                                                   coal_to_iron_drill_inserter.pickup_position,
                                                   connection_type=Prototype.TransportBelt)

        coal_to_smelter_belt = connect_entities(belts[-1], coal_to_drill_belt[-1],
                                                     connection_type=Prototype.TransportBelt)
        pass
    except Exception as e:
        print(e)
        assert False


def test_auto_driller():
    move_to(nearest(Resource.Coal))
    burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, position=nearest(Resource.Coal))


    burner_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                direction=DOWN,
                                                spacing=0)
    burner_inserter = rotate_entity(burner_inserter, Direction.UP)
    assert burner_inserter


    belts = connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)
    assert belts

    insert_item(Prototype.Coal, burner_mining_drill, 5)
    move_to(burner_mining_drill.position.right().right().right())


```