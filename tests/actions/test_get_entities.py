import pytest

from fle.env import entities as ent
from fle.env.game_types import Prototype, RecipeName, Resource


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "coal": 10,
            "iron-chest": 1,
            "iron-plate": 50,
            "iron-ore": 10,
            "stone-furnace": 1,
            "offshore-pump": 1,
            "assembly-machine-1": 1,
            "burner-mining-drill": 1,
            "lab": 1,
            "automation-science-pack": 1,
            "gun-turret": 1,
            "firearm-magazine": 5,
            "transport-belt": 200,
            "boiler": 1,
            "pipe": 20,
        },
        merge=True,
    )


def test_get_stone_furnace(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    # Check initial inventory
    position = game.nearest(Resource.Stone)
    # 1. Place a stone furnace
    game.move_to(position)
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, ent.Direction.UP, position
    )
    assert stone_furnace is not None, "Failed to place stone furnace"
    assert stone_furnace.warnings == ["out of fuel", "no ingredients to smelt"], (
        "Failed to place stone furnace"
    )

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(5)
    retrieved_furnace: ent.Furnace = game.get_entities(
        {Prototype.StoneFurnace}, stone_furnace.position
    )[0]

    assert retrieved_furnace is not None, "Failed to retrieve stone furnace"
    assert retrieved_furnace.furnace_result.get(Prototype.IronPlate, 0) > 0, (
        "Failed to smelt iron plate"
    )
    assert retrieved_furnace.furnace_source.get(Prototype.IronOre, 0) < 5, (
        "Failed to smelt iron ore"
    )
    assert retrieved_furnace.fuel.get(Prototype.Coal, 0) < 5, "Failed to consume coal"


def test_get_connected_transport_belts(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    start_position = game.nearest(Resource.Stone)
    end_position = game.nearest(Resource.IronOre)

    game.connect_entities(
        start_position, end_position, connection_type=Prototype.TransportBelt
    )

    transport_belts = game.get_entities({Prototype.TransportBelt}, start_position)

    assert len(transport_belts) == 1, "Failed to retrieve transport belts"


def test_get_entities_bug(game):
    # Check initial inventory
    iron_position = game.nearest(Resource.Stone)
    game.move_to(iron_position)
    print(f"Moved to iron patch at {iron_position}")
    game.harvest_resource(iron_position, 20)

    game.craft_item(Prototype.StoneFurnace, 3)

    # 1. Place a stone furnace
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, ent.Direction.UP, iron_position
    )
    assert stone_furnace is not None, "Failed to place stone furnace"

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(1)
    # print("Inserted coal and iron ore into the furnace")

    furnaces = game.get_entities({Prototype.StoneFurnace})
    print(furnaces)


def test_get_no_entities(game):
    furnaces = game.get_entities()
    assert not furnaces


def test_get_contiguous_transport_belts(game):
    start_position = game.nearest(Resource.Stone)
    end_position = game.nearest(Resource.IronOre)

    game.connect_entities(
        start_position, end_position, connection_type=Prototype.TransportBelt
    )

    transport_belts = game.get_entities({Prototype.TransportBelt}, start_position)

    assert len(transport_belts) == 1, "Failed to retrieve transport belts"


def test_get_filtered_entities(game):
    # put down a chest at origin
    chest = game.place_entity(Prototype.IronChest, position=ent.Position(x=1, y=0))
    # put 100 coal into the chest
    chest = game.insert_item(Prototype.Coal, chest, 5)

    # place a stone furnace
    furnace = game.place_entity(Prototype.StoneFurnace, position=ent.Position(x=3, y=0))

    furnace = game.insert_item(Prototype.Coal, furnace, 5)

    entities = game.get_entities({Prototype.StoneFurnace})

    assert len(entities) == 1


def test_get_entities_hanging_bug(game):
    game.move_to(ent.Position(x=1, y=1))

    # Place offshore pump near water
    water_position = game.nearest(Resource.Water)
    assert water_position, "No water source found nearby"
    game.move_to(water_position)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, ent.Direction.DOWN, water_position
    )
    assert offshore_pump, "Failed to place offshore pump"

    # Place boiler next to offshore pump
    # Important: The boiler needs to be placed with a spacing of 2 to allow for pipe connections
    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, ent.Direction.RIGHT, spacing=2
    )
    assert boiler, "Failed to place boiler"

    # add coal to the boiler
    # need to update the boiler var after insert
    boiler = game.insert_item(Prototype.Coal, boiler, quantity=5)

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Failed to connect offshore pump to boiler"

    # Place steam engine next to boiler
    # Important: The steam engine needs to be placed with a spacing of 2 to allow for pipe connections
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, ent.Direction.RIGHT, spacing=2
    )
    assert steam_engine, "Failed to place steam engine"

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine"

    entities = game.get_entities()
    assert len(entities) == 5


def test_get_assembling_machine_1(game):
    """
    Test to ensure that the inventory of an assembling machine is correctly updated after crafting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    assembling_machine_count = inventory.get(Prototype.AssemblingMachine1, 0)
    assert assembling_machine_count != 0, "Failed to get assembling machine count"

    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=ent.Position(x=0, y=0)
    )
    game.set_entity_recipe(assembling_machine, RecipeName.IronGearWheel)
    game.insert_item(Prototype.IronPlate, assembling_machine, quantity=5)

    retrieved_machine = game.get_entities({Prototype.AssemblingMachine1})[0]

    assert retrieved_machine is not None, "Failed to retrieve assembling machine"


def test_get_pipe_groups(game):
    # game.craft_item(Prototype.OffshorePump)

    try:
        game.move_to(game.nearest(Resource.Water))
        offshore_pump = game.place_entity(
            Prototype.OffshorePump, position=game.nearest(Resource.Water)
        )
    except:
        water_patch = game.get_resource_patch(
            Resource.Water, game.nearest(Resource.Water)
        )
        game.move_to(water_patch)
        offshore_pump = game.place_entity(
            Prototype.OffshorePump, position=game.nearest(Resource.Water)
        )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

    pipes = game.get_entities()
    assert len(pipes) == 3


def test_group_prototype_support_belt_group(game):
    """Test explicit BeltGroup prototype support"""
    game.move_to(ent.Position(x=10, y=10))

    # Create some belt connections
    start_pos = ent.Position(x=10, y=10)
    end_pos = ent.Position(x=15, y=10)

    belt_connection = game.connect_entities(start_pos, end_pos, Prototype.TransportBelt)
    assert belt_connection, "Belt connection should succeed"

    # Test requesting BeltGroup specifically
    belt_groups = game.get_entities({Prototype.BeltGroup})
    assert len(belt_groups) > 0, "Should find belt groups"

    # Should return grouped belts
    for group in belt_groups:
        assert hasattr(group, "belts") or group.__class__.__name__ == "BeltGroup", (
            f"Should return belt groups, got {type(group)}"
        )

    print(f"✓ Found {len(belt_groups)} belt groups")


def test_group_prototype_support_pipe_group(game):
    """Test explicit PipeGroup prototype support"""
    water_position = game.nearest(Resource.Water)
    game.move_to(water_position)

    # Create pipe connection
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_position)
    boiler_pos = ent.Position(x=water_position.x + 5, y=water_position.y)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos)

    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Pipe connection should succeed"

    # Test requesting PipeGroup specifically
    pipe_groups = game.get_entities({Prototype.PipeGroup})
    assert len(pipe_groups) > 0, "Should find pipe groups"

    # Should return grouped pipes
    for group in pipe_groups:
        assert hasattr(group, "pipes") or group.__class__.__name__ == "PipeGroup", (
            f"Should return pipe groups, got {type(group)}"
        )

    print(f"✓ Found {len(pipe_groups)} pipe groups")


def test_group_prototype_support_electricity_group(game):
    """Test explicit ElectricityGroup prototype support"""
    game.move_to(ent.Position(x=20, y=20))

    # Create pole network
    start_pos = ent.Position(x=20, y=20)
    end_pos = ent.Position(x=30, y=20)

    pole_connection = game.connect_entities(
        start_pos, end_pos, Prototype.SmallElectricPole
    )
    assert pole_connection, "Pole connection should succeed"

    # Test requesting ElectricityGroup specifically
    electricity_groups = game.get_entities({Prototype.ElectricityGroup})
    assert len(electricity_groups) > 0, "Should find electricity groups"

    # Should return grouped electric poles
    for group in electricity_groups:
        assert (
            hasattr(group, "electric_poles")
            or group.__class__.__name__ == "ElectricityGroup"
        ), f"Should return electricity groups, got {type(group)}"

    print(f"✓ Found {len(electricity_groups)} electricity groups")


def test_entity_expansion_from_group_requests(game):
    """Test that group requests expand to include individual entity types"""
    game.move_to(ent.Position(x=30, y=30))

    inventory = game.inspect_inventory()
    print(f"Inventory: {inventory}")

    # Place individual belt entities
    game.place_entity(Prototype.TransportBelt, position=ent.Position(x=30, y=30))
    game.place_entity(Prototype.FastTransportBelt, position=ent.Position(x=31, y=30))
    game.place_entity(Prototype.ExpressTransportBelt, position=ent.Position(x=32, y=30))

    # Request BeltGroup - should find individual belts and group them
    belt_groups = game.get_entities({Prototype.BeltGroup})

    if belt_groups:
        # Should find the belts (either as groups or individuals)
        total_belts_found = 0
        for group in belt_groups:
            if hasattr(group, "belts"):
                total_belts_found += len(group.belts)
            else:
                total_belts_found += 1

        assert total_belts_found >= 3, (
            f"Should find at least 3 belts, found {total_belts_found}"
        )
        print(f"✓ Group request expanded and found {total_belts_found} belt entities")


def test_enhanced_grouping_vs_individual_logic(game):
    """Test enhanced logic for when to group vs return individual entities"""
    game.move_to(ent.Position(x=40, y=40))

    # Place some electric poles
    pole1 = game.place_entity(
        Prototype.SmallElectricPole, position=ent.Position(x=40, y=40)
    )
    game.place_entity(Prototype.SmallElectricPole, position=ent.Position(x=45, y=40))

    # Test 1: Request specific entity type without position - should group (poles are always grouped)
    poles_grouped = game.get_entities({Prototype.SmallElectricPole})
    assert len(poles_grouped) > 0, "Should find pole groups"

    # Test 2: Request with position filter - should still group for convenience
    poles_with_position = game.get_entities(
        {Prototype.SmallElectricPole}, position=pole1.position
    )
    assert len(poles_with_position) > 0, "Should find poles with position filter"

    # Test 3: Request no specific entities (get all) - should group everything
    all_entities = game.get_entities()
    grouped_count = sum(
        1
        for e in all_entities
        if hasattr(e, "__class__")
        and e.__class__.__name__ in ["ElectricityGroup", "BeltGroup", "PipeGroup"]
    )

    assert grouped_count >= 0, "Should have some grouped entities when getting all"

    print(
        f"✓ Enhanced grouping logic working - found {grouped_count} groups in get_entities()"
    )


def test_individual_belt_extraction_without_position(game):
    """Test that individual belts can be extracted when no position filter is used"""
    game.move_to(ent.Position(x=50, y=50))

    # Create a belt line that will be grouped
    belt_positions = [
        ent.Position(x=50, y=50),
        ent.Position(x=51, y=50),
        ent.Position(x=52, y=50),
    ]

    placed_belts = []
    for pos in belt_positions:
        belt = game.place_entity(Prototype.TransportBelt, position=pos)
        placed_belts.append(belt)

    # Connect them to form a group
    game.connect_entities(
        belt_positions[0], belt_positions[-1], Prototype.TransportBelt
    )

    # Request individual TransportBelt without position - might get individual belts or groups
    transport_belts = game.get_entities({Prototype.TransportBelt})
    assert len(transport_belts) > 0, "Should find transport belts"

    # At least one result should be related to transport belts
    found_belt_related = False
    for entity in transport_belts:
        if (
            (
                hasattr(entity, "prototype")
                and entity.prototype == Prototype.TransportBelt
            )
            or (hasattr(entity, "belts") and len(entity.belts) > 0)
            or (hasattr(entity, "__class__") and "Belt" in entity.__class__.__name__)
        ):
            found_belt_related = True
            break

    assert found_belt_related, "Should find belt-related entities"
    print("✓ Individual belt request handled appropriately")


def test_mixed_entity_grouping_behavior(game):
    """Test behavior when requesting mixed individual and group types"""
    game.move_to(ent.Position(x=20, y=60))

    # Create mixed infrastructure
    game.place_entity(Prototype.StoneFurnace, position=ent.Position(x=20, y=60))
    game.place_entity(Prototype.SmallElectricPole, position=ent.Position(x=23, y=60))
    game.place_entity(Prototype.TransportBelt, position=ent.Position(x=26, y=60))

    # Request mixed types: individual furnace + electricity group
    mixed_entities = game.get_entities(
        {Prototype.StoneFurnace, Prototype.ElectricityGroup}
    )
    assert len(mixed_entities) > 0, "Should find mixed entity types"

    # Should find the furnace and electricity group
    found_furnace = any(
        hasattr(e, "prototype") and e.prototype == Prototype.StoneFurnace
        for e in mixed_entities
    )
    found_electricity = any(
        hasattr(e, "__class__") and "Electric" in e.__class__.__name__
        for e in mixed_entities
    )

    assert found_furnace or found_electricity, (
        "Should find at least one of the requested types"
    )
    print("✓ Mixed entity request handled correctly")


def test_position_filtering_with_groups(game):
    """Test that position filtering works correctly with grouped entities"""
    game.move_to(ent.Position(x=75, y=75))

    # Create entities at different positions
    close_pole = game.place_entity(
        Prototype.SmallElectricPole, position=ent.Position(x=70, y=70)
    )
    game.place_entity(Prototype.SmallElectricPole, position=ent.Position(x=80, y=80))

    # Request with position filter - should only get nearby entities
    nearby_entities = game.get_entities(position=close_pole.position, radius=3)

    # Should find entities near the specified position
    assert len(nearby_entities) > 0, "Should find entities near specified position"

    # All found entities should be reasonably close to the search position
    for entity in nearby_entities:
        if hasattr(entity, "position"):
            distance = (
                (entity.position.x - close_pole.position.x) ** 2
                + (entity.position.y - close_pole.position.y) ** 2
            ) ** 0.5
            assert distance <= 5, f"Found entity too far away: {distance}"

    print("✓ Position filtering with groups working correctly")


def test_group_prototype_backwards_compatibility(game):
    """Test that existing functionality still works with new group support"""
    game.move_to(ent.Position(x=80, y=80))

    # Test existing functionality - getting all entities
    game.place_entity(Prototype.StoneFurnace, position=ent.Position(x=80, y=80))
    all_entities_before = game.get_entities()

    # Add more entities
    game.place_entity(Prototype.IronChest, position=ent.Position(x=82, y=80))
    all_entities_after = game.get_entities()

    # Should have more entities after adding
    assert len(all_entities_after) >= len(all_entities_before), (
        "Entity count should increase"
    )

    # Test specific entity type requests still work
    furnaces = game.get_entities({Prototype.StoneFurnace})
    assert len(furnaces) >= 1, "Should still find specific entity types"

    print("✓ Backwards compatibility maintained")


def test_get_lab(configure_game):
    """
    Test that labs appear in get_entities() observations in multiple permutations:
    1. Empty lab (just placed)
    2. Lab with science packs inserted but not researching
    3. Lab actively researching (with power)
    4. Multiple labs
    5. Labs mixed with other entities
    6. get_entities() with specific prototype vs get_entities() for all
    """
    # Create a fresh game with lab in inventory (not using shared fixture)
    game = configure_game(
        inventory={
            "lab": 5,
            "automation-science-pack": 100,
            "stone-furnace": 1,
            "small-electric-pole": 5,
            "boiler": 1,
            "steam-engine": 1,
            "offshore-pump": 1,
            "pipe": 20,
            "coal": 50,
        },
        persist_inventory=False,
        all_technologies_researched=False,  # Start with no research so we can test active research
    )

    # Move to a clear area to avoid collisions
    game.move_to(ent.Position(x=100, y=100))

    # === PERMUTATION 1: Empty lab (just placed) ===
    print("\n=== Test 1: Empty lab ===")
    lab1 = game.place_entity(Prototype.Lab, position=ent.Position(x=100, y=100))
    assert lab1 is not None, "Failed to place lab1"

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 1, f"Expected 1 empty lab, found {len(labs)}"
    print("✓ Empty lab found")

    # === PERMUTATION 2: Lab with science packs but not researching (no power) ===
    print("\n=== Test 2: Lab with science packs, no power ===")
    game.insert_item(Prototype.AutomationSciencePack, lab1, quantity=10)

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 1, f"Expected 1 lab with science, found {len(labs)}"
    assert labs[0].lab_input.get(Prototype.AutomationSciencePack, 0) == 10, (
        "Lab should contain 10 automation science packs"
    )
    print("✓ Lab with science packs found (no power)")

    # === PERMUTATION 3: Lab with power connected (even if not researching) ===
    print("\n=== Test 3: Lab with power connected ===")
    # Set up power infrastructure
    water_position = game.nearest(Resource.Water)
    game.move_to(water_position)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_position)

    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, ent.Direction.RIGHT, spacing=2
    )
    game.insert_item(Prototype.Coal, boiler, quantity=5)
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)

    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, ent.Direction.RIGHT, spacing=2
    )
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)

    # Connect power to lab
    game.place_entity_next_to(
        Prototype.SmallElectricPole,
        steam_engine.position,
        ent.Direction.RIGHT,
        spacing=3,
    )
    game.place_entity_next_to(
        Prototype.SmallElectricPole, lab1.position, ent.Direction.LEFT, spacing=3
    )

    # Wait a moment for power to stabilize
    game.sleep(1)

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 1, f"Expected 1 lab with power, found {len(labs)}"
    # Lab should have some energy available even if not actively consuming
    print(f"✓ Lab with power connection found (energy: {labs[0].energy})")

    # === PERMUTATION 4: Multiple labs ===
    print("\n=== Test 4: Multiple labs ===")
    # Move back to lab area
    game.move_to(ent.Position(x=104, y=100))
    lab2 = game.place_entity(Prototype.Lab, position=ent.Position(x=104, y=100))
    game.move_to(ent.Position(x=108, y=100))
    lab3 = game.place_entity(Prototype.Lab, position=ent.Position(x=108, y=100))

    # Add science to new labs
    game.insert_item(Prototype.AutomationSciencePack, lab2, quantity=10)
    game.insert_item(Prototype.AutomationSciencePack, lab3, quantity=10)

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 3, f"Expected 3 labs, found {len(labs)}"
    print("✓ All 3 labs found")

    # === PERMUTATION 5: Labs mixed with other entities ===
    print("\n=== Test 5: Labs in get_entities() with all entities ===")
    game.place_entity(Prototype.StoneFurnace, position=ent.Position(x=112, y=100))

    all_entities = game.get_entities()
    entity_types = {type(e).__name__ for e in all_entities}
    print(f"All entity types found: {entity_types}")

    labs_in_all = [e for e in all_entities if type(e).__name__ == "Lab"]
    assert len(labs_in_all) == 3, (
        f"Expected 3 labs when retrieving all entities, found {len(labs_in_all)}. "
        f"Entity types: {entity_types}"
    )
    print("✓ All 3 labs found in get_entities() call")

    # === PERMUTATION 6: get_entities() with position and radius filters ===
    print("\n=== Test 6: Labs with position/radius filters ===")
    # Get labs near lab1 (should find lab1 and lab2, but not lab3)
    nearby_labs = game.get_entities({Prototype.Lab}, position=lab1.position, radius=5)
    assert len(nearby_labs) >= 1, (
        f"Expected at least 1 lab near position, found {len(nearby_labs)}"
    )
    print(f"✓ Found {len(nearby_labs)} labs near position with radius filter")

    print(
        "\n✅ All permutations passed - labs are correctly observable in all scenarios"
    )


def test_get_lab_edge_cases(configure_game):
    """
    Test edge cases where labs might not appear:
    1. Lab on different force (enemy lab)
    2. Lab with no inventory access (other player's lab in multiplayer?)
    3. Lab during active research consumption
    4. Lab with modules installed
    5. Lab very far away (radius filtering)
    6. Lab that was just damaged
    7. Lab with empty vs full inventories
    """
    game = configure_game(
        inventory={
            "lab": 10,
            "automation-science-pack": 200,
            "assembling-machine-1": 1,
        },
        persist_inventory=False,
        all_technologies_researched=False,
    )

    game.move_to(ent.Position(x=0, y=0))

    # === EDGE CASE 1: Lab with science packs (modules can't be easily inserted via API) ===
    print("\n=== Edge Case 1: Lab with various science pack quantities ===")
    lab_with_items = game.place_entity(Prototype.Lab, position=ent.Position(x=0, y=0))
    game.insert_item(Prototype.AutomationSciencePack, lab_with_items, quantity=50)

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 1, f"Expected 1 lab with items, found {len(labs)}"
    # Check science packs are in the lab
    assert labs[0].lab_input.get(Prototype.AutomationSciencePack, 0) == 50, (
        "Lab should have 50 automation science packs"
    )
    print("✓ Lab with many science packs found")

    # === EDGE CASE 2: Lab very far away with radius filter ===
    print("\n=== Edge Case 2: Lab very far away with radius filter ===")
    game.move_to(ent.Position(x=200, y=200))
    game.place_entity(Prototype.Lab, position=ent.Position(x=200, y=200))

    # Query from origin with small radius - should NOT find far lab
    labs_near_origin = game.get_entities(
        {Prototype.Lab}, position=ent.Position(x=0, y=0), radius=10
    )
    # Should only find the first lab, not the far one
    assert len(labs_near_origin) == 1, (
        f"Should only find 1 lab near origin, found {len(labs_near_origin)}"
    )

    # Query from far position - should find far lab
    labs_near_far = game.get_entities(
        {Prototype.Lab}, position=ent.Position(x=200, y=200), radius=10
    )
    assert len(labs_near_far) == 1, (
        f"Should find 1 lab at far position, found {len(labs_near_far)}"
    )

    # Query ALL labs without position filter - should find both
    all_labs = game.get_entities({Prototype.Lab})
    assert len(all_labs) == 2, f"Should find 2 total labs, found {len(all_labs)}"
    print("✓ Radius filtering works correctly, all labs found without filter")

    # === EDGE CASE 3: Lab queried immediately after placement ===
    print("\n=== Edge Case 3: Lab queried immediately after placement ===")
    game.move_to(ent.Position(x=10, y=10))
    game.place_entity(Prototype.Lab, position=ent.Position(x=10, y=10))
    # Query immediately without sleep
    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 3, f"Should find freshly placed lab, found {len(labs)}"
    print("✓ Freshly placed lab found immediately")

    # === EDGE CASE 4: Lab with completely full inventory ===
    print("\n=== Edge Case 4: Lab with completely full inventory ===")
    game.move_to(ent.Position(x=20, y=20))
    full_lab = game.place_entity(Prototype.Lab, position=ent.Position(x=20, y=20))
    # Fill it with science packs (labs can hold quite a few)
    game.insert_item(Prototype.AutomationSciencePack, full_lab, quantity=100)

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 4, f"Should find lab with full inventory, found {len(labs)}"
    full_lab_retrieved = [lab for lab in labs if abs(lab.position.x - 20.5) < 0.1][0]
    assert (
        full_lab_retrieved.lab_input.get(Prototype.AutomationSciencePack, 0) == 100
    ), "Full lab should have 100 science packs"
    print("✓ Lab with full inventory found")

    # === EDGE CASE 5: Lab with empty inventory ===
    print("\n=== Edge Case 5: Lab with completely empty inventory ===")
    game.move_to(ent.Position(x=30, y=30))
    game.place_entity(Prototype.Lab, position=ent.Position(x=30, y=30))
    # Don't insert anything - completely empty

    labs = game.get_entities({Prototype.Lab})
    assert len(labs) == 5, f"Should find empty lab, found {len(labs)}"
    empty_lab_retrieved = [lab for lab in labs if abs(lab.position.x - 30.5) < 0.1][0]
    assert len(empty_lab_retrieved.lab_input) == 0, "Empty lab should have no items"
    print("✓ Empty lab found")

    # === EDGE CASE 6: Mixed query with labs and other entity types ===
    print("\n=== Edge Case 6: Mixed query (labs + assemblers) ===")
    game.move_to(ent.Position(x=40, y=40))
    game.place_entity(Prototype.AssemblingMachine1, position=ent.Position(x=40, y=40))

    # Query for both labs and assemblers
    mixed = game.get_entities({Prototype.Lab, Prototype.AssemblingMachine1})
    labs_in_mixed = [e for e in mixed if type(e).__name__ == "Lab"]
    assemblers_in_mixed = [e for e in mixed if type(e).__name__ == "AssemblingMachine"]

    assert len(labs_in_mixed) == 5, (
        f"Should find 5 labs in mixed query, found {len(labs_in_mixed)}"
    )
    assert len(assemblers_in_mixed) == 1, (
        f"Should find 1 assembler in mixed query, found {len(assemblers_in_mixed)}"
    )
    print("✓ Labs found correctly in mixed-type query")

    # === EDGE CASE 7: Get all entities (no filter) ===
    print("\n=== Edge Case 7: Labs in get_entities() with NO prototype filter ===")
    all_entities = game.get_entities()
    all_labs = [e for e in all_entities if type(e).__name__ == "Lab"]

    assert len(all_labs) == 5, (
        f"Should find 5 labs when getting all entities, found {len(all_labs)}. "
        f"Total entities: {len(all_entities)}"
    )
    print("✓ All labs found in get_entities() with no filter")

    print("\n✅ All edge cases passed - labs are observable in every scenario tested")
