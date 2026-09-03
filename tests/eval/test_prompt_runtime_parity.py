from types import SimpleNamespace

from fle.env.game_types import (
    Technology,
    prototype_by_title,
    technology_by_name,
)
from fle.env.namespace import FactorioNamespace
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)


TASK_UNLOCK_TECHNOLOGIES = {
    "advanced-circuit",
    "automation-science-pack",
    "battery",
    "chemical-science-pack",
    "electronics",
    "engine",
    "logistic-science-pack",
    "low-density-structure",
    "military-2",
    "military-science-pack",
    "plastics",
    "processing-unit",
    "production-science-pack",
    "steel-processing",
    "stone-wall",
    "sulfur-processing",
    "utility-science-pack",
}


def test_prompt_lookup_helpers_are_executable() -> None:
    prompt_types = SystemPromptGenerator("fle/env").types()
    namespace = FactorioNamespace(SimpleNamespace(tcp_port=27000), agent_index=0)

    for helper in ("prototype_by_title", "technology_by_name"):
        assert helper in prompt_types
        assert hasattr(namespace, helper)

    assert namespace.prototype_by_title is prototype_by_title
    assert namespace.technology_by_name is technology_by_name


def test_all_throughput_unlock_technologies_are_exposed() -> None:
    assert TASK_UNLOCK_TECHNOLOGIES <= set(technology_by_name)


def test_obsolete_factorio_technology_names_are_not_advertised() -> None:
    obsolete_names = {
        "advanced-electronics",
        "advanced-electronics-2",
        "barrel-filling",
        "character-inventory-slots",
        "energy-shields",
        "energy-shields-mk2-equipment",
        "grenades",
        "research-speed",
        "rocket-control-unit",
        "stack-inserter",
        "stack-inserter-capacity-bonus-1",
        "stack-inserter-capacity-bonus-2",
    }

    assert obsolete_names.isdisjoint(
        member.value for member in Technology.__members__.values()
    )
