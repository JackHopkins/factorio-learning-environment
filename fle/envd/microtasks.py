"""Small, engine-verified tasks for Factorio API competence evaluation.

The suite deliberately begins from a fresh default scenario with a narrowly
provisioned inventory.  Tasks are short enough for grouped evaluation, but the
success signal always comes from Factorio state rather than matching text or
trusting the generated program's return value.
"""

from collections.abc import Callable

from fle.envd.models import (
    ConstraintSpec,
    CurriculumSpec,
    FactorioTaskSpec,
    ObjectiveSpec,
    ProvisioningSpec,
    VerifierSpec,
)
from fle.envd.task_builder import DEFAULT_KNOWLEDGE_SOURCES


def _task(
    *,
    task_id: str,
    goal: str,
    objectives: list[ObjectiveSpec],
    inventory: dict[str, int],
    max_interventions: int,
    constraints: list[ConstraintSpec] | None = None,
    all_technologies_researched: bool = True,
    researched_technologies: list[str] | None = None,
) -> FactorioTaskSpec:
    hard_constraints = [
        ConstraintSpec(
            constraint_id="intervention-budget",
            kind="max_interventions",
            description=(
                f"Use no more than {max_interventions} intervention programs."
            ),
            limit=max_interventions,
        ),
        *(constraints or []),
    ]
    return FactorioTaskSpec(
        task_id=task_id,
        backend_task_id="open_play",
        goal=goal,
        task_family="construction",
        objectives=objectives,
        constraints=hard_constraints,
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="binary",
        ),
        curriculum=CurriculumSpec(
            stage="api-microtasks",
            suggested_strategies=["sft", "opd", "opsd", "grpo", "evaluation"],
            episode_mode="independent",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        provisioning=ProvisioningSpec(
            starting_inventory=inventory,
            all_technologies_researched=all_technologies_researched,
            researched_technologies=researched_technologies or [],
        ),
        max_interventions=max_interventions,
        holdout_seconds=0,
    )


def harvest_coal_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_harvest_coal_v1",
        goal="Locate a coal patch, move within reach, and harvest at least 5 coal.",
        objectives=[
            ObjectiveSpec(
                objective_id="carry-coal",
                kind="inventory",
                description="The character inventory contains at least 5 coal.",
                target="coal",
                comparator="gte",
                threshold=5,
            )
        ],
        inventory={},
        max_interventions=3,
        all_technologies_researched=False,
    )


def craft_gear_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_craft_iron_gear_v1",
        goal="Craft at least one iron gear wheel from the supplied iron plates.",
        objectives=[
            ObjectiveSpec(
                objective_id="carry-gear",
                kind="inventory",
                description="The character inventory contains an iron gear wheel.",
                target="iron-gear-wheel",
                comparator="gte",
                threshold=1,
            )
        ],
        inventory={"iron-plate": 2},
        max_interventions=2,
        all_technologies_researched=False,
    )


def place_lab_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_place_lab_v1",
        goal="Place the supplied laboratory on valid ground.",
        objectives=[
            ObjectiveSpec(
                objective_id="lab-exists",
                kind="entity_exists",
                description="At least one laboratory exists in the world.",
                target="lab",
                comparator="gte",
                threshold=1,
            )
        ],
        inventory={"lab": 1},
        max_interventions=2,
    )


def place_adjacent_pole_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_place_entity_next_to_v1",
        goal=(
            "Place the lab, then use place_entity_next_to to place a small "
            "electric pole adjacent to it without overlapping either footprint."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="lab-exists",
                kind="entity_exists",
                description="A laboratory exists.",
                target="lab",
                comparator="gte",
                threshold=1,
            ),
            ObjectiveSpec(
                objective_id="pole-exists",
                kind="entity_exists",
                description="A small electric pole exists.",
                target="small-electric-pole",
                comparator="gte",
                threshold=1,
            ),
        ],
        inventory={"lab": 1, "small-electric-pole": 1},
        max_interventions=3,
        constraints=[
            ConstraintSpec(
                constraint_id="use-adjacent-placement",
                kind="required_action",
                description="Use the audited adjacency placement helper.",
                limit="place_entity_next_to",
            )
        ],
    )


def configure_assembler_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_configure_assembler_recipe_v1",
        goal=(
            "Place the supplied assembling machine 1 and configure its recipe "
            "to iron gear wheels."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="gear-recipe-set",
                kind="entity_recipe",
                description="An assembling machine 1 has the iron gear wheel recipe.",
                target="assembling-machine-1",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "iron-gear-wheel"},
            )
        ],
        inventory={"assembling-machine-1": 1},
        max_interventions=3,
    )


def fuel_furnace_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_fuel_furnace_v1",
        goal="Place the supplied stone furnace and insert at least 1 coal as fuel.",
        objectives=[
            ObjectiveSpec(
                objective_id="furnace-has-fuel",
                kind="entity_inventory",
                description="A stone furnace contains coal.",
                target="stone-furnace",
                comparator="gte",
                threshold=1,
                parameters={"item": "coal"},
            )
        ],
        inventory={"stone-furnace": 1, "coal": 5},
        max_interventions=3,
    )


def load_lab_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_load_lab_v1",
        goal=(
            "Place the supplied laboratory and insert at least 5 automation "
            "science packs into it."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="lab-has-science",
                kind="entity_inventory",
                description="A lab contains at least 5 automation science packs.",
                target="lab",
                comparator="gte",
                threshold=5,
                parameters={"item": "automation-science-pack"},
            )
        ],
        inventory={"lab": 1, "automation-science-pack": 5},
        max_interventions=3,
        all_technologies_researched=False,
        researched_technologies=["automation-science-pack"],
    )


def start_furnace_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_start_furnace_v1",
        goal=(
            "Place and load the supplied stone furnace so that it begins "
            "smelting iron ore."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="furnace-operates",
                kind="entity_status",
                description="A stone furnace is working or has completed into a full output.",
                target="stone-furnace",
                comparator="gte",
                threshold=1,
                parameters={"statuses": ["working", "full_output"]},
            )
        ],
        inventory={"stone-furnace": 1, "coal": 5, "iron-ore": 5},
        max_interventions=4,
    )


def connect_water_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_connect_offshore_pump_v1",
        goal=(
            "Place the offshore pump on water and use connect_entities to "
            "connect it to at least one pipe so the pump operates."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="pump-operates",
                kind="entity_status",
                description="An offshore pump is actively working.",
                target="offshore-pump",
                comparator="gte",
                threshold=1,
                parameters={"statuses": ["working"]},
            ),
            ObjectiveSpec(
                objective_id="pipe-exists",
                kind="entity_exists",
                description="At least one pipe exists.",
                target="pipe",
                comparator="gte",
                threshold=1,
            ),
        ],
        inventory={"offshore-pump": 1, "pipe": 20},
        max_interventions=5,
        constraints=[
            ConstraintSpec(
                constraint_id="use-connect-entities",
                kind="required_action",
                description="Use the audited connection helper.",
                limit="connect_entities",
            )
        ],
    )


def route_belt_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_connect_belt_v1",
        goal=(
            "Place two transport-belt endpoints and use connect_entities to "
            "construct a continuous belt route containing at least 5 belts."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="belt-route-exists",
                kind="entity_exists",
                description="At least five transport belts exist.",
                target="transport-belt",
                comparator="gte",
                threshold=5,
            )
        ],
        inventory={"transport-belt": 20},
        max_interventions=4,
        constraints=[
            ConstraintSpec(
                constraint_id="use-connect-entities",
                kind="required_action",
                description="Use the audited connection helper.",
                limit="connect_entities",
            )
        ],
    )


def transfer_to_chest_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_transfer_to_chest_v1",
        goal=(
            "Place the supplied wooden chest and insert at least 10 iron plates "
            "into its inventory."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="chest-has-plates",
                kind="entity_inventory",
                description="A wooden chest contains at least 10 iron plates.",
                target="wooden-chest",
                comparator="gte",
                threshold=10,
                parameters={"item": "iron-plate"},
            )
        ],
        inventory={"wooden-chest": 1, "iron-plate": 10},
        max_interventions=3,
    )


def power_assembler_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_power_assembler_v1",
        goal=(
            "Use the supplied solar panel and electric pole to power an "
            "assembling machine configured for iron gear wheels; load iron "
            "plates and make the assembler operate."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="assembler-recipe",
                kind="entity_recipe",
                description="The assembler is configured for iron gear wheels.",
                target="assembling-machine-1",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "iron-gear-wheel"},
            ),
            ObjectiveSpec(
                objective_id="assembler-operates",
                kind="entity_status",
                description="The assembler works or completes into a full output.",
                target="assembling-machine-1",
                comparator="gte",
                threshold=1,
                parameters={"statuses": ["working", "full_output"]},
            ),
        ],
        inventory={
            "assembling-machine-1": 1,
            "solar-panel": 1,
            "small-electric-pole": 2,
            "iron-plate": 10,
        },
        max_interventions=6,
    )


def configure_chemical_plant_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_configure_chemical_plant_v1",
        goal=(
            "Place the supplied chemical plant and configure its recipe to "
            "produce plastic bars."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="plastic-recipe-set",
                kind="entity_recipe",
                description="A chemical plant has the plastic bar recipe.",
                target="chemical-plant",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "plastic-bar"},
            )
        ],
        inventory={"chemical-plant": 1},
        max_interventions=3,
    )


def configure_oil_refinery_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_configure_oil_refinery_v1",
        goal=("Place the supplied oil refinery and configure advanced oil processing."),
        objectives=[
            ObjectiveSpec(
                objective_id="advanced-oil-recipe-set",
                kind="entity_recipe",
                description="An oil refinery uses advanced oil processing.",
                target="oil-refinery",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "advanced-oil-processing"},
            )
        ],
        inventory={"oil-refinery": 1},
        max_interventions=3,
    )


def configure_centrifuge_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_configure_centrifuge_v1",
        goal=(
            "Place the supplied centrifuge and configure the uranium-processing recipe."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="uranium-recipe-set",
                kind="entity_recipe",
                description="A centrifuge uses uranium processing.",
                target="centrifuge",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "uranium-processing"},
            )
        ],
        inventory={"centrifuge": 1},
        max_interventions=3,
    )


def install_speed_module_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_install_speed_module_v1",
        goal=(
            "Place the supplied assembling machine 2, configure iron gear "
            "wheels, and install one speed module."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="gear-recipe-set",
                kind="entity_recipe",
                description="The assembler uses the iron gear wheel recipe.",
                target="assembling-machine-2",
                comparator="gte",
                threshold=1,
                parameters={"recipe": "iron-gear-wheel"},
            ),
            ObjectiveSpec(
                objective_id="speed-module-installed",
                kind="entity_inventory",
                description="The assembler contains a speed module.",
                target="assembling-machine-2",
                comparator="gte",
                threshold=1,
                parameters={"item": "speed-module"},
            ),
        ],
        inventory={"assembling-machine-2": 1, "speed-module": 1},
        max_interventions=4,
    )


def place_pumpjack_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_place_pumpjack_v1",
        goal=(
            "Locate crude oil, move within reach, and place the supplied "
            "pumpjack on a valid oil deposit."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="pumpjack-exists",
                kind="entity_exists",
                description="A pumpjack exists on a valid crude-oil deposit.",
                target="pumpjack",
                comparator="gte",
                threshold=1,
            )
        ],
        inventory={"pumpjack": 1},
        max_interventions=4,
    )


def place_rocket_silo_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_place_rocket_silo_v1",
        goal=(
            "Find sufficient valid ground and place the supplied rocket silo "
            "without overlapping another entity."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="rocket-silo-exists",
                kind="entity_exists",
                description="A rocket silo exists.",
                target="rocket-silo",
                comparator="gte",
                threshold=1,
            )
        ],
        inventory={"rocket-silo": 1},
        max_interventions=3,
    )


def automate_gear_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_automate_iron_gear_v1",
        goal=(
            "Use the supplied assembler, solar panel, pole, and iron plates to "
            "automatically produce at least one iron gear wheel."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="automatic-gear",
                kind="production",
                description="Automatically produce an iron gear wheel.",
                target="iron-gear-wheel",
                comparator="gte",
                threshold=1,
                parameters={"automatic": True},
            )
        ],
        inventory={
            "assembling-machine-1": 1,
            "solar-panel": 1,
            "small-electric-pole": 2,
            "iron-plate": 10,
        },
        max_interventions=7,
    )


def automate_red_science_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_automate_red_science_v1",
        goal=(
            "Use the supplied powered assembly equipment and ingredients to "
            "automatically produce at least one automation science pack."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="automatic-red-science",
                kind="production",
                description="Automatically produce an automation science pack.",
                target="automation-science-pack",
                comparator="gte",
                threshold=1,
                parameters={"automatic": True},
            )
        ],
        inventory={
            "assembling-machine-1": 1,
            "solar-panel": 1,
            "small-electric-pole": 2,
            "iron-gear-wheel": 10,
            "copper-plate": 10,
        },
        max_interventions=7,
    )


def automate_circuit_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_automate_electronic_circuit_v1",
        goal=(
            "Use the supplied powered assembly equipment and ingredients to "
            "automatically produce at least one electronic circuit."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="automatic-circuit",
                kind="production",
                description="Automatically produce an electronic circuit.",
                target="electronic-circuit",
                comparator="gte",
                threshold=1,
                parameters={"automatic": True},
            )
        ],
        inventory={
            "assembling-machine-1": 1,
            "solar-panel": 1,
            "small-electric-pole": 2,
            "iron-plate": 10,
            "copper-cable": 30,
        },
        max_interventions=7,
    )


def automate_steel_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_automate_steel_plate_v1",
        goal=(
            "Load and fuel the supplied stone furnace so it automatically "
            "produces at least one steel plate from iron plates."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="automatic-steel",
                kind="production",
                description="Automatically produce a steel plate.",
                target="steel-plate",
                comparator="gte",
                threshold=1,
                parameters={"automatic": True},
            )
        ],
        inventory={"stone-furnace": 1, "coal": 10, "iron-plate": 10},
        max_interventions=5,
    )


def research_logistics_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_research_logistics_v1",
        goal=(
            "Power and load the supplied laboratory, select Logistics research, "
            "and complete the technology."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="research-logistics",
                kind="research",
                description="Complete the Logistics technology.",
                target="logistics",
                comparator="eq",
                threshold=1,
            )
        ],
        inventory={
            "lab": 1,
            "solar-panel": 2,
            "small-electric-pole": 2,
            "automation-science-pack": 50,
        },
        max_interventions=8,
        all_technologies_researched=False,
        researched_technologies=[
            "automation",
            "automation-science-pack",
        ],
    )


def place_roboport_task() -> FactorioTaskSpec:
    return _task(
        task_id="micro_place_roboport_v1",
        goal=(
            "Place the supplied roboport and connect it to a solar power source "
            "through small electric poles."
        ),
        objectives=[
            ObjectiveSpec(
                objective_id="roboport-powered",
                kind="entity_status",
                description="A roboport is connected and not reporting no power.",
                target="roboport",
                comparator="gte",
                threshold=1,
                parameters={
                    "statuses": [
                        "normal",
                        "working",
                        "low_power",
                        "charging",
                        "fully_charged",
                    ]
                },
            )
        ],
        inventory={
            "roboport": 1,
            "solar-panel": 4,
            "small-electric-pole": 4,
        },
        max_interventions=6,
    )


MICROTASKS: dict[str, Callable[[], FactorioTaskSpec]] = {
    "micro_automate_electronic_circuit_v1": automate_circuit_task,
    "micro_automate_iron_gear_v1": automate_gear_task,
    "micro_automate_red_science_v1": automate_red_science_task,
    "micro_automate_steel_plate_v1": automate_steel_task,
    "micro_configure_assembler_recipe_v1": configure_assembler_task,
    "micro_configure_centrifuge_v1": configure_centrifuge_task,
    "micro_configure_chemical_plant_v1": configure_chemical_plant_task,
    "micro_configure_oil_refinery_v1": configure_oil_refinery_task,
    "micro_connect_belt_v1": route_belt_task,
    "micro_connect_offshore_pump_v1": connect_water_task,
    "micro_craft_iron_gear_v1": craft_gear_task,
    "micro_fuel_furnace_v1": fuel_furnace_task,
    "micro_harvest_coal_v1": harvest_coal_task,
    "micro_install_speed_module_v1": install_speed_module_task,
    "micro_load_lab_v1": load_lab_task,
    "micro_place_entity_next_to_v1": place_adjacent_pole_task,
    "micro_place_lab_v1": place_lab_task,
    "micro_place_pumpjack_v1": place_pumpjack_task,
    "micro_place_roboport_v1": place_roboport_task,
    "micro_place_rocket_silo_v1": place_rocket_silo_task,
    "micro_power_assembler_v1": power_assembler_task,
    "micro_start_furnace_v1": start_furnace_task,
    "micro_transfer_to_chest_v1": transfer_to_chest_task,
    "micro_research_logistics_v1": research_logistics_task,
}


def get_microtask(task_id: str) -> FactorioTaskSpec:
    try:
        return MICROTASKS[task_id]()
    except KeyError as exc:
        raise KeyError(
            f"Unknown Factorio microtask {task_id!r}; "
            f"available: {', '.join(sorted(MICROTASKS))}"
        ) from exc
