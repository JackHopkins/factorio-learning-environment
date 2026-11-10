"""Prototype and EntityStatus names vs Factorio 2.0 (base game). Server-free."""

import pytest

from fle.env import entities as ent
from fle.env.entities import EntityStatus
from fle.env.game_types import Prototype, prototype_by_name

# prototypes.item on a Factorio 2.0.73 headless server, base mod only
FACTORIO_2_0_ITEMS = (
    "accumulator",
    "active-provider-chest",
    "advanced-circuit",
    "arithmetic-combinator",
    "artillery-shell",
    "artillery-targeting-remote",
    "artillery-turret",
    "artillery-wagon",
    "artillery-wagon-cannon",
    "assembling-machine-1",
    "assembling-machine-2",
    "assembling-machine-3",
    "atomic-bomb",
    "automation-science-pack",
    "barrel",
    "battery",
    "battery-equipment",
    "battery-mk2-equipment",
    "beacon",
    "belt-immunity-equipment",
    "big-electric-pole",
    "blueprint",
    "blueprint-book",
    "boiler",
    "bottomless-chest",
    "buffer-chest",
    "bulk-inserter",
    "burner-generator",
    "burner-inserter",
    "burner-mining-drill",
    "cannon-shell",
    "car",
    "cargo-landing-pad",
    "cargo-wagon",
    "centrifuge",
    "chemical-plant",
    "chemical-science-pack",
    "cliff-explosives",
    "cluster-grenade",
    "coal",
    "coin",
    "combat-shotgun",
    "concrete",
    "constant-combinator",
    "construction-robot",
    "copper-cable",
    "copper-ore",
    "copper-plate",
    "copper-wire",
    "copy-paste-tool",
    "crude-oil-barrel",
    "cut-paste-tool",
    "decider-combinator",
    "deconstruction-planner",
    "defender-capsule",
    "depleted-uranium-fuel-cell",
    "destroyer-capsule",
    "discharge-defense-equipment",
    "discharge-defense-remote",
    "display-panel",
    "distractor-capsule",
    "efficiency-module",
    "efficiency-module-2",
    "efficiency-module-3",
    "electric-energy-interface",
    "electric-engine-unit",
    "electric-furnace",
    "electric-mining-drill",
    "electronic-circuit",
    "empty-module-slot",
    "energy-shield-equipment",
    "energy-shield-mk2-equipment",
    "engine-unit",
    "exoskeleton-equipment",
    "explosive-cannon-shell",
    "explosive-rocket",
    "explosive-uranium-cannon-shell",
    "explosives",
    "express-loader",
    "express-splitter",
    "express-transport-belt",
    "express-underground-belt",
    "fast-inserter",
    "fast-loader",
    "fast-splitter",
    "fast-transport-belt",
    "fast-underground-belt",
    "firearm-magazine",
    "fission-reactor-equipment",
    "flamethrower",
    "flamethrower-ammo",
    "flamethrower-turret",
    "fluid-wagon",
    "flying-robot-frame",
    "gate",
    "green-wire",
    "grenade",
    "gun-turret",
    "hazard-concrete",
    "heat-exchanger",
    "heat-interface",
    "heat-pipe",
    "heavy-armor",
    "heavy-oil-barrel",
    "infinity-cargo-wagon",
    "infinity-chest",
    "infinity-pipe",
    "inserter",
    "iron-chest",
    "iron-gear-wheel",
    "iron-ore",
    "iron-plate",
    "iron-stick",
    "item-unknown",
    "lab",
    "land-mine",
    "landfill",
    "lane-splitter",
    "laser-turret",
    "light-armor",
    "light-oil-barrel",
    "linked-belt",
    "linked-chest",
    "loader",
    "locomotive",
    "logistic-robot",
    "logistic-science-pack",
    "long-handed-inserter",
    "low-density-structure",
    "lubricant-barrel",
    "medium-electric-pole",
    "military-science-pack",
    "modular-armor",
    "night-vision-equipment",
    "no-item",
    "nuclear-fuel",
    "nuclear-reactor",
    "offshore-pump",
    "oil-refinery",
    "one-way-valve",
    "overflow-valve",
    "parameter-0",
    "parameter-1",
    "parameter-2",
    "parameter-3",
    "parameter-4",
    "parameter-5",
    "parameter-6",
    "parameter-7",
    "parameter-8",
    "parameter-9",
    "passive-provider-chest",
    "personal-laser-defense-equipment",
    "personal-roboport-equipment",
    "personal-roboport-mk2-equipment",
    "petroleum-gas-barrel",
    "piercing-rounds-magazine",
    "piercing-shotgun-shell",
    "pipe",
    "pipe-to-ground",
    "pistol",
    "plastic-bar",
    "poison-capsule",
    "power-armor",
    "power-armor-mk2",
    "power-switch",
    "processing-unit",
    "production-science-pack",
    "productivity-module",
    "productivity-module-2",
    "productivity-module-3",
    "programmable-speaker",
    "proxy-container",
    "pump",
    "pumpjack",
    "radar",
    "rail",
    "rail-chain-signal",
    "rail-signal",
    "raw-fish",
    "red-wire",
    "refined-concrete",
    "refined-hazard-concrete",
    "repair-pack",
    "requester-chest",
    "roboport",
    "rocket",
    "rocket-fuel",
    "rocket-launcher",
    "rocket-part",
    "rocket-silo",
    "satellite",
    "science",
    "selection-tool",
    "selector-combinator",
    "shotgun",
    "shotgun-shell",
    "simple-entity-with-force",
    "simple-entity-with-owner",
    "slowdown-capsule",
    "small-electric-pole",
    "small-lamp",
    "solar-panel",
    "solar-panel-equipment",
    "solid-fuel",
    "space-science-pack",
    "speed-module",
    "speed-module-2",
    "speed-module-3",
    "spidertron",
    "spidertron-remote",
    "spidertron-rocket-launcher-1",
    "spidertron-rocket-launcher-2",
    "spidertron-rocket-launcher-3",
    "spidertron-rocket-launcher-4",
    "splitter",
    "steam-engine",
    "steam-turbine",
    "steel-chest",
    "steel-furnace",
    "steel-plate",
    "stone",
    "stone-brick",
    "stone-furnace",
    "stone-wall",
    "storage-chest",
    "storage-tank",
    "submachine-gun",
    "substation",
    "sulfur",
    "sulfuric-acid-barrel",
    "tank",
    "tank-cannon",
    "tank-flamethrower",
    "tank-machine-gun",
    "top-up-valve",
    "train-stop",
    "transport-belt",
    "underground-belt",
    "upgrade-planner",
    "uranium-235",
    "uranium-238",
    "uranium-cannon-shell",
    "uranium-fuel-cell",
    "uranium-ore",
    "uranium-rounds-magazine",
    "utility-science-pack",
    "vehicle-machine-gun",
    "water-barrel",
    "wood",
    "wooden-chest",
)

# prototypes.fluid on the same server
FACTORIO_2_0_FLUIDS = (
    "crude-oil",
    "fluid-unknown",
    "heavy-oil",
    "light-oil",
    "lubricant",
    "parameter-0",
    "parameter-1",
    "parameter-2",
    "parameter-3",
    "parameter-4",
    "parameter-5",
    "parameter-6",
    "parameter-7",
    "parameter-8",
    "parameter-9",
    "petroleum-gas",
    "steam",
    "sulfuric-acid",
    "water",
)

# Rail entities placed by the "rail" item (prototypes.entity, base mod only)
FACTORIO_2_0_RAIL_ENTITIES = (
    "straight-rail",
    "curved-rail-a",
    "curved-rail-b",
    "half-diagonal-rail",
)

# Prototype members that name a recipe, not an item
RECIPE_ONLY = ("advanced-oil-processing", "coal-liquefaction")

# FLE's own entity groups; not game prototypes
FLE_GROUPS = ("belt-group", "pipe-group", "electricity-group")

# defines.entity_status in the Factorio 2.0.73 Lua API
FACTORIO_2_0_ENTITY_STATUSES = (
    "working",
    "normal",
    "ghost",
    "broken",
    "no_power",
    "low_power",
    "no_fuel",
    "frozen",
    "disabled_by_control_behavior",
    "opened_by_circuit_network",
    "closed_by_circuit_network",
    "disabled_by_script",
    "marked_for_deconstruction",
    "paused",
    "not_plugged_in_electric_network",
    "networks_connected",
    "networks_disconnected",
    "charging",
    "discharging",
    "fully_charged",
    "out_of_logistic_network",
    "no_recipe",
    "no_ingredients",
    "no_input_fluid",
    "no_research_in_progress",
    "no_minable_resources",
    "not_connected_to_hub_or_pad",
    "low_input_fluid",
    "fluid_ingredient_shortage",
    "full_output",
    "not_enough_space_in_output",
    "full_burnt_result_output",
    "item_ingredient_shortage",
    "missing_required_fluid",
    "missing_science_packs",
    "waiting_for_source_items",
    "waiting_for_more_items",
    "waiting_for_space_in_destination",
    "preparing_rocket_for_launch",
    "waiting_to_launch_rocket",
    "waiting_for_space_in_platform_hub",
    "launching_rocket",
    "thrust_not_required",
    "on_the_way",
    "waiting_in_orbit",
    "waiting_at_stop",
    "waiting_for_rockets_to_arrive",
    "not_enough_thrust",
    "destination_stop_full",
    "no_path",
    "no_modules_to_transmit",
    "recharging_after_power_outage",
    "waiting_for_target_to_be_built",
    "waiting_for_train",
    "no_ammo",
    "low_temperature",
    "disabled",
    "turned_off_during_daytime",
    "not_connected_to_rail",
    "cant_divide_segments",
    "no_filter",
    "no_spot_seedable_by_inputs",
    "waiting_for_plants_to_grow",
    "computing_navigation",
    "pipeline_overextended",
    "recipe_not_researched",
    "recipe_is_parameter",
)


def test_every_prototype_names_a_factorio_2_0_prototype():
    known = (
        set(FACTORIO_2_0_ITEMS)
        | set(FACTORIO_2_0_FLUIDS)
        | set(FACTORIO_2_0_RAIL_ENTITIES)
        | set(RECIPE_ONLY)
        | set(FLE_GROUPS)
    )
    unknown = sorted(
        f"{member.name}={member.value[0]}"
        for member in Prototype
        if member.value[0] not in known
    )
    assert unknown == []


def test_barrel_uses_the_factorio_2_0_name():
    assert Prototype.Barrel.value[0] == "barrel"
    assert Prototype.EmptyBarrel is Prototype.Barrel
    assert prototype_by_name["barrel"] is Prototype.Barrel


def test_rocket_control_unit_is_removed():
    # Factorio 2.0 has no rocket-control-unit item or recipe
    assert "rocket-control-unit" not in prototype_by_name
    with pytest.raises(AttributeError):
        Prototype.RocketControlUnit


def test_coal_liquefaction_spelling():
    assert Prototype.CoalLiquefaction.value[0] == "coal-liquefaction"
    with pytest.raises(AttributeError, match="CoalLiquefaction"):
        Prototype.CoalLiquifaction


@pytest.mark.parametrize("name", FACTORIO_2_0_RAIL_ENTITIES)
def test_placed_rails_have_a_prototype(name):
    prototype = prototype_by_name[name]
    assert prototype.entity_class is ent.Rail


def test_rail_item_is_kept():
    assert Prototype.Rail.value[0] == "rail"


@pytest.mark.parametrize(
    "name", ["explosives", "cliff-explosives", "landfill", "repair-pack"]
)
def test_new_items_have_a_prototype(name):
    assert name in prototype_by_name


def test_rocket_is_the_ammo_item():
    assert Prototype.Rocket.value[0] == "rocket"
    assert Prototype.Rocket.entity_class is ent.Ammo


def test_every_factorio_2_0_entity_status_is_known():
    values = {status.value for status in EntityStatus}
    assert sorted(set(FACTORIO_2_0_ENTITY_STATUSES) - values) == []
