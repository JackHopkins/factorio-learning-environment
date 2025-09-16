"""
Throughput task definitions for lab_play scenario.

This module contains all throughput task definitions as Pydantic models,
replacing the previous JSON-based definitions for better type safety,
validation, and code reusability.
"""

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Union
from fle.env.game_types import Prototype

# Task name constants for easy importing
ADVANCED_CIRCUIT_THROUGHPUT = "advanced_circuit_throughput"
AUTOMATION_SCIENCE_PACK_THROUGHPUT = "automation_science_pack_throughput"
BATTERY_THROUGHPUT = "battery_throughput"
CHEMICAL_SCIENCE_PACK_THROUGHPUT = "chemical_science_pack_throughput"
CRUDE_OIL_THROUGHPUT = "crude_oil_throughput"
ELECTRONIC_CIRCUIT_THROUGHPUT = "electronic_circuit_throughput"
ENGINE_UNIT_THROUGHPUT = "engine_unit_throughput"
INSERTER_THROUGHPUT = "inserter_throughput"
IRON_GEAR_WHEEL_THROUGHPUT = "iron_gear_wheel_throughput"
IRON_ORE_THROUGHPUT = "iron_ore_throughput"
IRON_PLATE_THROUGHPUT = "iron_plate_throughput"
LOGISTICS_SCIENCE_PACK_THROUGHPUT = "logistics_science_pack_throughput"
LOW_DENSITY_STRUCTURE_THROUGHPUT = "low_density_structure_throughput"
MILITARY_SCIENCE_PACK_THROUGHPUT = "military_science_pack_throughput"
PETROLEUM_GAS_THROUGHPUT = "petroleum_gas_throughput"
PIERCING_ROUND_THROUGHPUT = "piercing_round_throughput"
PLASTIC_BAR_THROUGHPUT = "plastic_bar_throughput"
PROCESSING_UNIT_THROUGHPUT = "processing_unit_throughput"
PRODUCTION_SCIENCE_PACK_THROUGHPUT = "production_science_pack_throughput"
STEEL_PLATE_THROUGHPUT = "steel_plate_throughput"
STONE_WALL_THROUGHPUT = "stone_wall_throughput"
SUFURIC_ACID_THROUGHPUT = "sufuric_acid_throughput"
SULFUR_THROUGHPUT = "sulfur_throughput"
UTILITY_SCIENCE_PACK_THROUGHPUT = "utility_science_pack_throughput"


class ThroughputTaskConfig(BaseModel):
    """Base configuration for all throughput tasks."""

    task_type: Literal["throughput"] = "throughput"
    num_agents: int = 1
    trajectory_length: int = 128
    holdout_wait_period: int = 60
    pre_holdout_wait_period: int = 60

    # These must be defined per task
    throughput_entity: Union[str, Prototype]  # Can be string or Prototype
    quota: int = Field(gt=0)
    goal_description: str
    task_key: str

    class Config:
        frozen = True  # Make instances immutable
        extra = "forbid"  # Don't allow extra fields
        arbitrary_types_allowed = True  # Allow Prototype enum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        data = self.dict()
        # Convert Prototype to string if necessary
        if isinstance(self.throughput_entity, Prototype):
            data["throughput_entity"] = self.throughput_entity.value
            if isinstance(data["throughput_entity"], tuple):
                data["throughput_entity"] = data["throughput_entity"][0]
        return data


# Define all throughput tasks as instances

# Circuit-related tasks
advanced_circuit_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic advanced-circuit factory that produces 16 advanced-circuit per 60 ingame seconds.",
    throughput_entity=Prototype.AdvancedCircuit,
    quota=16,
    task_key=ADVANCED_CIRCUIT_THROUGHPUT,
)

electronic_circuit_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic electronic-circuit factory that produces 16 electronic-circuit per 60 ingame seconds.",
    throughput_entity=Prototype.ElectronicCircuit,
    quota=16,
    task_key=ELECTRONIC_CIRCUIT_THROUGHPUT,
)

processing_unit_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic processing-unit factory that produces 16 processing-unit per 60 ingame seconds.",
    throughput_entity=Prototype.ProcessingUnit,
    quota=16,
    task_key=PROCESSING_UNIT_THROUGHPUT,
)

# Science pack tasks
automation_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic automation-science-pack factory that produces 16 automation-science-pack per 60 ingame seconds.",
    throughput_entity=Prototype.AutomationSciencePack,
    quota=16,
    task_key=AUTOMATION_SCIENCE_PACK_THROUGHPUT,
)

logistics_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic logistic-science-pack factory that produces 16 logistic-science-packs per 60 ingame seconds.",
    throughput_entity=Prototype.LogisticsSciencePack,
    quota=16,
    task_key=LOGISTICS_SCIENCE_PACK_THROUGHPUT,
)

chemical_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic chemical-science-pack factory that produces 16 chemical-science-pack per 60 ingame seconds.",
    throughput_entity=Prototype.ChemicalSciencePack,
    quota=16,
    task_key=CHEMICAL_SCIENCE_PACK_THROUGHPUT,
)

military_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic military-science-pack factory that produces 16 military-science-packs per 60 ingame seconds.",
    throughput_entity=Prototype.MilitarySciencePack,
    quota=16,
    task_key=MILITARY_SCIENCE_PACK_THROUGHPUT,
)

production_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic production-science-pack factory that produces 16 production-science-pack per 60 ingame seconds.",
    throughput_entity=Prototype.ProductionSciencePack,
    quota=16,
    task_key=PRODUCTION_SCIENCE_PACK_THROUGHPUT,
)

utility_science_pack_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic utility-science-pack factory that produces 16 utility-science-pack per 60 ingame seconds.",
    throughput_entity=Prototype.UtilitySciencePack,
    quota=16,
    task_key=UTILITY_SCIENCE_PACK_THROUGHPUT,
)

# Materials and components
battery_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic battery factory that produces 16 battery per 60 ingame seconds.",
    throughput_entity=Prototype.Battery,
    quota=16,
    task_key=BATTERY_THROUGHPUT,
)

engine_unit_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic engine-unit factory that produces 16 engine-unit per 60 ingame seconds.",
    throughput_entity=Prototype.EngineUnit,
    quota=16,
    task_key=ENGINE_UNIT_THROUGHPUT,
)

inserter_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic inserter factory that produces 16 inserter per 60 ingame seconds.",
    throughput_entity=Prototype.Inserter,
    quota=16,
    task_key=INSERTER_THROUGHPUT,
)

iron_gear_wheel_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic iron-gear-wheel factory that produces 16 iron-gear-wheel per 60 ingame seconds.",
    throughput_entity=Prototype.IronGearWheel,
    quota=16,
    task_key=IRON_GEAR_WHEEL_THROUGHPUT,
)

low_density_structure_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic low-density-structure factory that produces 16 low-density-structure per 60 ingame seconds.",
    throughput_entity=Prototype.LowDensityStructure,
    quota=16,
    task_key=LOW_DENSITY_STRUCTURE_THROUGHPUT,
)

# Raw materials and plates
iron_ore_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic iron-ore factory that produces 16 iron-ore per 60 ingame seconds.",
    throughput_entity=Prototype.IronOre,
    quota=16,
    task_key=IRON_ORE_THROUGHPUT,
)

iron_plate_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic iron-plate factory that produces 16 iron-plate per 60 ingame seconds.",
    throughput_entity=Prototype.IronPlate,
    quota=16,
    task_key=IRON_PLATE_THROUGHPUT,
)

steel_plate_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic steel-plate factory that produces 16 steel-plate per 60 ingame seconds.",
    throughput_entity=Prototype.SteelPlate,
    quota=16,
    task_key=STEEL_PLATE_THROUGHPUT,
)

plastic_bar_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic plastic-bar factory that produces 16 plastic-bar per 60 ingame seconds.",
    throughput_entity=Prototype.PlasticBar,
    quota=16,
    task_key=PLASTIC_BAR_THROUGHPUT,
)

# Oil products and chemicals
crude_oil_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic crude-oil factory that produces 250 crude-oil per 60 ingame seconds.",
    throughput_entity="crude-oil",  # CrudeOil is in Resource class, not Prototype
    quota=250,
    task_key=CRUDE_OIL_THROUGHPUT,
)

petroleum_gas_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic petroleum-gas factory that produces 250 petroleum-gas per 60 ingame seconds.",
    throughput_entity=Prototype.PetroleumGas,
    quota=250,
    task_key=PETROLEUM_GAS_THROUGHPUT,
)

sufuric_acid_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic sulfuric-acid factory that produces 250 sulfuric-acid per 60 ingame seconds.",
    throughput_entity=Prototype.SulfuricAcid,
    quota=250,
    task_key=SUFURIC_ACID_THROUGHPUT,
)

sulfur_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic sulfur factory that produces 16 sulfur per 60 ingame seconds.",
    throughput_entity=Prototype.Sulfur,
    quota=16,
    task_key=SULFUR_THROUGHPUT,
)

# Military items
piercing_round_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic piercing-rounds-magazine factory that produces 16 piercing-rounds-magazine per 60 ingame seconds.",
    throughput_entity=Prototype.PiercingRoundsMagazine,
    quota=16,
    task_key=PIERCING_ROUND_THROUGHPUT,
)

stone_wall_throughput = ThroughputTaskConfig(
    goal_description="Create an automatic stone wall factory that produces 16 stone wall per 60 ingame seconds.",
    throughput_entity=Prototype.StoneWall,
    quota=16,
    task_key=STONE_WALL_THROUGHPUT,
)


# Create a dictionary for easy lookup by task key
THROUGHPUT_TASKS = {
    ADVANCED_CIRCUIT_THROUGHPUT: advanced_circuit_throughput,
    AUTOMATION_SCIENCE_PACK_THROUGHPUT: automation_science_pack_throughput,
    BATTERY_THROUGHPUT: battery_throughput,
    CHEMICAL_SCIENCE_PACK_THROUGHPUT: chemical_science_pack_throughput,
    CRUDE_OIL_THROUGHPUT: crude_oil_throughput,
    ELECTRONIC_CIRCUIT_THROUGHPUT: electronic_circuit_throughput,
    ENGINE_UNIT_THROUGHPUT: engine_unit_throughput,
    INSERTER_THROUGHPUT: inserter_throughput,
    IRON_GEAR_WHEEL_THROUGHPUT: iron_gear_wheel_throughput,
    IRON_ORE_THROUGHPUT: iron_ore_throughput,
    IRON_PLATE_THROUGHPUT: iron_plate_throughput,
    LOGISTICS_SCIENCE_PACK_THROUGHPUT: logistics_science_pack_throughput,
    LOW_DENSITY_STRUCTURE_THROUGHPUT: low_density_structure_throughput,
    MILITARY_SCIENCE_PACK_THROUGHPUT: military_science_pack_throughput,
    PETROLEUM_GAS_THROUGHPUT: petroleum_gas_throughput,
    PIERCING_ROUND_THROUGHPUT: piercing_round_throughput,
    PLASTIC_BAR_THROUGHPUT: plastic_bar_throughput,
    PROCESSING_UNIT_THROUGHPUT: processing_unit_throughput,
    PRODUCTION_SCIENCE_PACK_THROUGHPUT: production_science_pack_throughput,
    STEEL_PLATE_THROUGHPUT: steel_plate_throughput,
    STONE_WALL_THROUGHPUT: stone_wall_throughput,
    SUFURIC_ACID_THROUGHPUT: sufuric_acid_throughput,
    SULFUR_THROUGHPUT: sulfur_throughput,
    UTILITY_SCIENCE_PACK_THROUGHPUT: utility_science_pack_throughput,
}


def get_throughput_task(task_key: str) -> ThroughputTaskConfig:
    """Get a throughput task configuration by its key.

    Args:
        task_key: The task identifier (e.g., 'iron_plate_throughput')

    Returns:
        ThroughputTaskConfig instance for the requested task

    Raises:
        KeyError: If the task_key doesn't exist
    """
    if task_key not in THROUGHPUT_TASKS:
        raise KeyError(f"Unknown throughput task: {task_key}")
    return THROUGHPUT_TASKS[task_key]


def list_throughput_tasks() -> list[str]:
    """Get a list of all available throughput task keys."""
    return list(THROUGHPUT_TASKS.keys())
