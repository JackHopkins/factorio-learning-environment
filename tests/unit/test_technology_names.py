"""Technology enum vs the technologies of Factorio 2.0 (base game). Server-free."""

import pytest

from fle.env.game_types import Technology, closest_technology_names, technology_by_name

# game.forces.player.technologies on a Factorio 2.0.73 headless server, base mod only
FACTORIO_2_0_TECHNOLOGIES = (
    "advanced-circuit",
    "advanced-combinators",
    "advanced-material-processing",
    "advanced-material-processing-2",
    "advanced-oil-processing",
    "artillery",
    "artillery-shell-range-1",
    "artillery-shell-speed-1",
    "atomic-bomb",
    "automated-rail-transportation",
    "automation",
    "automation-2",
    "automation-3",
    "automation-science-pack",
    "automobilism",
    "battery",
    "battery-equipment",
    "battery-mk2-equipment",
    "belt-immunity-equipment",
    "braking-force-1",
    "braking-force-2",
    "braking-force-3",
    "braking-force-4",
    "braking-force-5",
    "braking-force-6",
    "braking-force-7",
    "bulk-inserter",
    "chemical-science-pack",
    "circuit-network",
    "cliff-explosives",
    "coal-liquefaction",
    "concrete",
    "construction-robotics",
    "defender",
    "destroyer",
    "discharge-defense-equipment",
    "distractor",
    "effect-transmission",
    "efficiency-module",
    "efficiency-module-2",
    "efficiency-module-3",
    "electric-energy-accumulators",
    "electric-energy-distribution-1",
    "electric-energy-distribution-2",
    "electric-engine",
    "electric-mining-drill",
    "electronics",
    "energy-shield-equipment",
    "energy-shield-mk2-equipment",
    "engine",
    "exoskeleton-equipment",
    "explosive-rocketry",
    "explosives",
    "fast-inserter",
    "fission-reactor-equipment",
    "flamethrower",
    "flammables",
    "fluid-handling",
    "fluid-wagon",
    "follower-robot-count-1",
    "follower-robot-count-2",
    "follower-robot-count-3",
    "follower-robot-count-4",
    "follower-robot-count-5",
    "gate",
    "gun-turret",
    "heavy-armor",
    "inserter-capacity-bonus-1",
    "inserter-capacity-bonus-2",
    "inserter-capacity-bonus-3",
    "inserter-capacity-bonus-4",
    "inserter-capacity-bonus-5",
    "inserter-capacity-bonus-6",
    "inserter-capacity-bonus-7",
    "kovarex-enrichment-process",
    "lamp",
    "land-mine",
    "landfill",
    "laser",
    "laser-shooting-speed-1",
    "laser-shooting-speed-2",
    "laser-shooting-speed-3",
    "laser-shooting-speed-4",
    "laser-shooting-speed-5",
    "laser-shooting-speed-6",
    "laser-shooting-speed-7",
    "laser-turret",
    "laser-weapons-damage-1",
    "laser-weapons-damage-2",
    "laser-weapons-damage-3",
    "laser-weapons-damage-4",
    "laser-weapons-damage-5",
    "laser-weapons-damage-6",
    "laser-weapons-damage-7",
    "logistic-robotics",
    "logistic-science-pack",
    "logistic-system",
    "logistics",
    "logistics-2",
    "logistics-3",
    "low-density-structure",
    "lubricant",
    "military",
    "military-2",
    "military-3",
    "military-4",
    "military-science-pack",
    "mining-productivity-1",
    "mining-productivity-2",
    "mining-productivity-3",
    "mining-productivity-4",
    "modular-armor",
    "modules",
    "night-vision-equipment",
    "nuclear-fuel-reprocessing",
    "nuclear-power",
    "oil-gathering",
    "oil-processing",
    "personal-laser-defense-equipment",
    "personal-roboport-equipment",
    "personal-roboport-mk2-equipment",
    "physical-projectile-damage-1",
    "physical-projectile-damage-2",
    "physical-projectile-damage-3",
    "physical-projectile-damage-4",
    "physical-projectile-damage-5",
    "physical-projectile-damage-6",
    "physical-projectile-damage-7",
    "plastics",
    "power-armor",
    "power-armor-mk2",
    "processing-unit",
    "production-science-pack",
    "productivity-module",
    "productivity-module-2",
    "productivity-module-3",
    "radar",
    "railway",
    "refined-flammables-1",
    "refined-flammables-2",
    "refined-flammables-3",
    "refined-flammables-4",
    "refined-flammables-5",
    "refined-flammables-6",
    "refined-flammables-7",
    "repair-pack",
    "research-speed-1",
    "research-speed-2",
    "research-speed-3",
    "research-speed-4",
    "research-speed-5",
    "research-speed-6",
    "robotics",
    "rocket-fuel",
    "rocket-silo",
    "rocketry",
    "solar-energy",
    "solar-panel-equipment",
    "space-science-pack",
    "speed-module",
    "speed-module-2",
    "speed-module-3",
    "spidertron",
    "steam-power",
    "steel-axe",
    "steel-processing",
    "stone-wall",
    "stronger-explosives-1",
    "stronger-explosives-2",
    "stronger-explosives-3",
    "stronger-explosives-4",
    "stronger-explosives-5",
    "stronger-explosives-6",
    "stronger-explosives-7",
    "sulfur-processing",
    "tank",
    "toolbelt",
    "uranium-ammo",
    "uranium-mining",
    "uranium-processing",
    "utility-science-pack",
    "weapon-shooting-speed-1",
    "weapon-shooting-speed-2",
    "weapon-shooting-speed-3",
    "weapon-shooting-speed-4",
    "weapon-shooting-speed-5",
    "weapon-shooting-speed-6",
    "worker-robots-speed-1",
    "worker-robots-speed-2",
    "worker-robots-speed-3",
    "worker-robots-speed-4",
    "worker-robots-speed-5",
    "worker-robots-speed-6",
    "worker-robots-storage-1",
    "worker-robots-storage-2",
    "worker-robots-storage-3",
)


def test_every_factorio_2_technology_has_a_member():
    values = {tech.value for tech in Technology}
    assert len(FACTORIO_2_0_TECHNOLOGIES) == 196
    assert set(FACTORIO_2_0_TECHNOLOGIES) == values
    assert set(technology_by_name) == values


def test_new_members_are_named_after_the_prototype():
    assert Technology.BulkInserter.value == "bulk-inserter"
    assert Technology.ResearchSpeed2.value == "research-speed-2"
    assert Technology.Military3.value == "military-3"
    assert Technology.ElectricMiningDrill.value == "electric-mining-drill"


@pytest.mark.parametrize(
    "name,first",
    [
        ("BulkInserter", "bulk-inserter"),
        ("research-speed", "research-speed-1"),
        ("stack-inserter", "fast-inserter"),
    ],
)
def test_closest_technology_names(name, first):
    close = closest_technology_names(name)
    assert close[0] == first and len(close) <= 8
    assert all(t in technology_by_name for t in close)


def _tool(cls, reply):
    tool = cls.__new__(cls)
    tool.player_index = 1
    tool.execute = lambda *args: (reply, 0)
    return tool


def test_set_research_unknown_name_lists_closest_names():
    from fle.env.tools.agent.set_research.client import SetResearch

    reply = '[string "..."]:7: "Technology research-speed does not exist"'
    with pytest.raises(Exception) as exc_info:
        _tool(SetResearch, reply)("research-speed")
    assert str(exc_info.value).startswith(
        "Technology research-speed does not exist. Closest technology names: "
        "research-speed-1, research-speed-2"
    )


def test_get_research_progress_unknown_name_lists_closest_names():
    from fle.env.tools.agent.get_research_progress.client import GetResearchProgress

    reply = '[string "..."]:16: "Technology BulkInserter doesn\'t exist"'
    with pytest.raises(Exception) as exc_info:
        _tool(GetResearchProgress, reply)("BulkInserter")
    assert str(exc_info.value).startswith(
        "Technology BulkInserter doesn't exist. Closest technology names: bulk-inserter"
    )
