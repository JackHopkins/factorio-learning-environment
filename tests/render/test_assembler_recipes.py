"""
Test assembler rendering with various recipes to isolate rendering failures.
"""

import pytest
from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "assembling-machine-1": 10,
        "assembling-machine-2": 10,
        "assembling-machine-3": 10,
        "iron-plate": 500,
        "copper-plate": 500,
        "steel-plate": 100,
        "iron-gear-wheel": 100,
        "copper-cable": 200,
        "electronic-circuit": 100,
        "advanced-circuit": 50,
        "processing-unit": 20,
        "plastic-bar": 100,
        "coal": 100,
        "stone": 100,
        "stone-brick": 100,
        "iron-stick": 100,
        "pipe": 50,
        "engine-unit": 20,
        "electric-engine-unit": 10,
        "battery": 50,
        "sulfur": 50,
        "low-density-structure": 10,
        "rocket-fuel": 10,
        "rocket-control-unit": 10,
        "flying-robot-frame": 10,
        "grenade": 20,
        "firearm-magazine": 50,
        "piercing-rounds-magazine": 20,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


# Recipes as Prototype enum values that assemblers can craft
ASSEMBLER_RECIPE_PROTOTYPES = [
    # Basic intermediates
    Prototype.IronGearWheel,
    Prototype.IronStick,
    Prototype.CopperCable,
    Prototype.ElectronicCircuit,
    Prototype.AdvancedCircuit,
    Prototype.ProcessingUnit,
    Prototype.EngineUnit,
    Prototype.ElectricEngineUnit,
    Prototype.Battery,
    Prototype.FlyingRobotFrame,
    # Logistics - use strings for those not in Prototype enum
    Prototype.TransportBelt,
    Prototype.FastTransportBelt,
    Prototype.ExpressTransportBelt,
    Prototype.UndergroundBelt,
    Prototype.FastUndergroundBelt,
    Prototype.ExpressUndergroundBelt,
    Prototype.Splitter,
    Prototype.FastSplitter,
    Prototype.ExpressSplitter,
    # Inserters
    Prototype.Inserter,
    Prototype.BurnerInserter,
    Prototype.FastInserter,
    Prototype.LongHandedInserter,
    Prototype.FilterInserter,
    Prototype.StackInserter,
    Prototype.StackFilterInserter,
    # Machines
    Prototype.AssemblingMachine1,
    Prototype.AssemblingMachine2,
    Prototype.AssemblingMachine3,
    Prototype.StoneFurnace,
    Prototype.SteelFurnace,
    Prototype.ElectricFurnace,
    Prototype.BurnerMiningDrill,
    Prototype.ElectricMiningDrill,
    # Power
    Prototype.Boiler,
    Prototype.SteamEngine,
    Prototype.SolarPanel,
    Prototype.Accumulator,
    Prototype.SmallElectricPole,
    Prototype.MediumElectricPole,
    Prototype.BigElectricPole,
    # Fluid handling
    Prototype.Pipe,
    Prototype.UndergroundPipe,
    Prototype.StorageTank,
    Prototype.Pump,
    Prototype.EmptyBarrel,
    # Storage
    Prototype.WoodenChest,
    Prototype.IronChest,
    Prototype.SteelChest,
    # Science
    Prototype.AutomationSciencePack,
    Prototype.LogisticsSciencePack,
    Prototype.MilitarySciencePack,
    Prototype.ChemicalSciencePack,
    Prototype.ProductionSciencePack,
    Prototype.UtilitySciencePack,
    # Military
    Prototype.FirearmMagazine,
    Prototype.PiercingRoundsMagazine,
    Prototype.Grenade,
    Prototype.GunTurret,
    Prototype.StoneWall,
    Prototype.Gate,
    Prototype.Radar,
    # Modules
    Prototype.ProductivityModule,
    Prototype.ProductivityModule2,
    Prototype.ProductivityModule3,
    # Rocket parts
    Prototype.RocketFuel,
    Prototype.LowDensityStructure,
    Prototype.RocketControlUnit,
    Prototype.Satellite,
    # Misc
    Prototype.SmallLamp,
    Prototype.Lab,
]


@pytest.fixture()
def clear_terrain(game):
    """Clear cliffs and rocks before each test"""
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end "
        "for _, rock in pairs(game.surfaces[1].find_entities_filtered{type='simple-entity'}) do "
        "if rock.name:find('rock') then rock.destroy() end "
        "end"
    )
    return game


# List of all recipes that assemblers can craft
ASSEMBLER_RECIPES = [
    # Basic intermediates
    "iron-gear-wheel",
    "iron-stick",
    "copper-cable",
    "electronic-circuit",
    "advanced-circuit",
    "processing-unit",
    "engine-unit",
    "electric-engine-unit",
    "battery",
    "flying-robot-frame",
    # Logistics
    "transport-belt",
    "fast-transport-belt",
    "express-transport-belt",
    "underground-belt",
    "fast-underground-belt",
    "express-underground-belt",
    "splitter",
    "fast-splitter",
    "express-splitter",
    # Inserters
    "inserter",
    "burner-inserter",
    "fast-inserter",
    "long-handed-inserter",
    "filter-inserter",
    "stack-inserter",
    "stack-filter-inserter",
    # Machines
    "assembling-machine-1",
    "assembling-machine-2",
    "assembling-machine-3",
    "stone-furnace",
    "steel-furnace",
    "electric-furnace",
    "burner-mining-drill",
    "electric-mining-drill",
    "pumpjack",
    "offshore-pump",
    # Power
    "boiler",
    "steam-engine",
    "solar-panel",
    "accumulator",
    "small-electric-pole",
    "medium-electric-pole",
    "big-electric-pole",
    # Fluid handling
    "pipe",
    "pipe-to-ground",
    "storage-tank",
    "pump",
    "empty-barrel",
    # Storage
    "wooden-chest",
    "iron-chest",
    "steel-chest",
    # Science
    "automation-science-pack",
    "logistic-science-pack",
    "military-science-pack",
    "chemical-science-pack",
    "production-science-pack",
    "utility-science-pack",
    # Military
    "firearm-magazine",
    "piercing-rounds-magazine",
    "grenade",
    "gun-turret",
    "stone-wall",
    "gate",
    "radar",
    # Modules
    "productivity-module",
    "productivity-module-2",
    "productivity-module-3",
    "speed-module",
    "speed-module-2",
    "speed-module-3",
    "effectivity-module",
    "effectivity-module-2",
    "effectivity-module-3",
    # Rocket parts
    "rocket-fuel",
    "low-density-structure",
    "rocket-control-unit",
    "satellite",
    # Misc
    "small-lamp",
    "concrete",
    "hazard-concrete",
    "refined-concrete",
    "refined-hazard-concrete",
    "landfill",
    "lab",
    "centrifuge",
    "nuclear-reactor",
    "heat-exchanger",
    "heat-pipe",
    "steam-turbine",
    "uranium-fuel-cell",
    "rail",
    "train-stop",
    "rail-signal",
    "rail-chain-signal",
    "locomotive",
    "cargo-wagon",
    "fluid-wagon",
    "artillery-wagon",
    "car",
    "tank",
    "spidertron",
    "construction-robot",
    "logistic-robot",
    "roboport",
    "logistic-chest-active-provider",
    "logistic-chest-passive-provider",
    "logistic-chest-storage",
    "logistic-chest-buffer",
    "logistic-chest-requester",
    "arithmetic-combinator",
    "decider-combinator",
    "constant-combinator",
    "power-switch",
    "programmable-speaker",
]


def test_assembler_render_all_recipes(clear_terrain):
    """Test rendering assemblers with all possible recipes."""
    game = clear_terrain

    failed_recipes = []
    successful_recipes = []
    skipped_recipes = []

    for recipe in ASSEMBLER_RECIPE_PROTOTYPES:
        recipe_name = recipe.value[0] if hasattr(recipe, "value") else str(recipe)
        try:
            # Reset position for each test
            game.move_to(Position(x=0, y=0))

            # Place an assembler
            assembler = game.place_entity(
                Prototype.AssemblingMachine2,  # Use assembler 2 for wider recipe support
                position=Position(x=0, y=0),
            )

            # Try to set the recipe using the Prototype enum
            try:
                result = game.set_entity_recipe(assembler, recipe)
                if not result:
                    skipped_recipes.append((recipe_name, "Recipe not available"))
                    game.pickup_entity(assembler)
                    continue
            except Exception as e:
                # Recipe might not be valid for this assembler type
                skipped_recipes.append((recipe_name, f"set_recipe failed: {str(e)}"))
                game.pickup_entity(assembler)
                continue

            # Try to render
            try:
                image = game._render(position=Position(x=0, y=0), radius=5)
                if image is None:
                    failed_recipes.append((recipe_name, "Render returned None"))
                else:
                    successful_recipes.append(recipe_name)
            except Exception as e:
                failed_recipes.append((recipe_name, str(e)))

            # Clean up
            game.pickup_entity(assembler)

        except Exception as e:
            failed_recipes.append((recipe_name, f"Setup failed: {str(e)}"))

    print("\n=== RECIPE RENDERING TEST RESULTS ===")
    print(f"Successful: {len(successful_recipes)}")
    print(f"Skipped: {len(skipped_recipes)}")
    print(f"Failed: {len(failed_recipes)}")

    if successful_recipes:
        print("\nSuccessful recipes:")
        for recipe in successful_recipes[:20]:
            print(f"  - {recipe}")
        if len(successful_recipes) > 20:
            print(f"  ... and {len(successful_recipes) - 20} more")

    if skipped_recipes:
        print("\nSkipped recipes (not available for assembler-2):")
        for recipe, reason in skipped_recipes[:10]:
            print(f"  - {recipe}: {reason}")
        if len(skipped_recipes) > 10:
            print(f"  ... and {len(skipped_recipes) - 10} more")

    if failed_recipes:
        print("\nFailed recipes:")
        for recipe, error in failed_recipes:
            print(f"  - {recipe}: {error}")

    # The test passes but reports failures for investigation
    assert len(failed_recipes) == 0, (
        f"Rendering failed for {len(failed_recipes)} recipes"
    )


def test_assembler_recipes_one_by_one(clear_terrain):
    """Test each recipe individually with detailed output."""
    game = clear_terrain

    # Test a subset of common recipes
    test_recipes = [
        "iron-gear-wheel",
        "copper-cable",
        "electronic-circuit",
        "advanced-circuit",
        "processing-unit",
        "transport-belt",
        "inserter",
        "automation-science-pack",
        "firearm-magazine",
    ]

    for recipe in test_recipes:
        print(f"\nTesting recipe: {recipe}")

        game.move_to(Position(x=0, y=0))
        assembler = game.place_entity(
            Prototype.AssemblingMachine1, position=Position(x=0, y=0)
        )

        try:
            assembler.set_recipe(recipe)
            print("  Recipe set successfully")

            # Check assembler state
            entities = game.get_entities()
            for e in entities:
                if e.name == "assembling-machine-1":
                    print(f"  Assembler recipe: {getattr(e, 'recipe', 'N/A')}")

            # Render
            image = game._render(position=Position(x=0, y=0), radius=5)
            print(f"  Render: {'SUCCESS' if image else 'FAILED'}")

        except Exception as e:
            print(f"  ERROR: {e}")

        game.pickup_entity(assembler)


def test_single_assembler_with_recipe(clear_terrain):
    """Test a single assembler with a specific recipe."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))
    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )

    # Set a recipe
    game.set_entity_recipe(assembler, Prototype.IronGearWheel)

    # Render and show
    image = game._render(position=Position(x=0, y=0), radius=6)
    # image.show()
    assert image is not None


def test_assembler_without_recipe(clear_terrain):
    """Test rendering an assembler without any recipe set."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))
    _assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )

    # Don't set a recipe

    # Render and show
    image = game._render(position=Position(x=0, y=0), radius=6)
    # image.show()
    assert image is not None


def test_all_assembler_tiers_with_recipe(clear_terrain):
    """Test all 3 tiers of assemblers with the same recipe."""
    game = clear_terrain

    # Place all 3 tiers
    game.move_to(Position(x=-5, y=0))
    a1 = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=-5, y=0))
    game.set_entity_recipe(a1, Prototype.IronGearWheel)

    game.move_to(Position(x=0, y=0))
    a2 = game.place_entity(Prototype.AssemblingMachine2, position=Position(x=0, y=0))
    game.set_entity_recipe(a2, Prototype.IronGearWheel)

    game.move_to(Position(x=5, y=0))
    a3 = game.place_entity(Prototype.AssemblingMachine3, position=Position(x=5, y=0))
    game.set_entity_recipe(a3, Prototype.IronGearWheel)

    # Render and show
    image = game._render(position=Position(x=0, y=0), radius=10)
    # image.show()
    assert image is not None


def test_assembler_complex_recipe(clear_terrain):
    """Test assembler with more complex recipes that might have different icons."""
    game = clear_terrain

    recipes_to_test = [
        Prototype.ElectronicCircuit,
        Prototype.AdvancedCircuit,
        Prototype.ProcessingUnit,
        Prototype.EngineUnit,
        Prototype.AutomationSciencePack,
    ]

    x_pos = -10
    for recipe in recipes_to_test:
        game.move_to(Position(x=x_pos, y=0))
        try:
            assembler = game.place_entity(
                Prototype.AssemblingMachine2, position=Position(x=x_pos, y=0)
            )
            game.set_entity_recipe(assembler, recipe)
            print(f"Placed assembler at x={x_pos} with recipe {recipe}")
        except Exception as e:
            print(f"Failed to set recipe {recipe}: {e}")
        x_pos += 5

    # Render and show
    image = game._render(position=Position(x=0, y=0), radius=20)
    # image.show()
    assert image is not None


def test_render_assembler_directly(clear_terrain):
    """Test rendering assembler by manually checking the entity data."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))
    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(assembler, Prototype.IronGearWheel)

    # Get entities and examine
    entities = game.get_entities()
    print("\n=== ENTITIES ===")
    for e in entities:
        print(f"Entity: {e.name}")
        if hasattr(e, "recipe"):
            print(f"  Recipe: {e.recipe}")
        if hasattr(e, "status"):
            print(f"  Status: {e.status}")
        if hasattr(e, "__dict__"):
            for key, value in vars(e).items():
                if not key.startswith("_"):
                    print(f"  {key}: {value}")

    # Now render
    image = game._render(position=Position(x=0, y=0), radius=6)
    # image.show()
    assert image is not None
