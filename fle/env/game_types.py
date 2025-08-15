from __future__ import annotations
import enum
import json
from difflib import get_close_matches
from fle.env import entities as ent


class ResourceName(enum.Enum):
    Coal = "coal"
    IronOre = "iron-ore"
    CopperOre = "copper-ore"
    Stone = "stone"
    Water = "water"
    CrudeOil = "crude-oil"
    UraniumOre = "uranium-ore"


class PrototypeMetaclass(enum.EnumMeta):
    def __getattr__(cls, name):
        try:
            attr = super().__getattr__(name)
            return attr
        except AttributeError:
            # Get all valid prototype names
            valid_names = [member.name for member in cls]

            # Find closest matches
            matches = get_close_matches(name, valid_names, n=3, cutoff=0.6)

            suggestion_msg = ""
            if matches:
                suggestion_msg = f". Did you mean: {', '.join(matches)}?"

            raise AttributeError(
                f"'{cls.__name__}' has no attribute '{name}'{suggestion_msg}"
            )


class RecipeName(enum.Enum):
    """
    Recipe names that can be used in the game for fluids
    """

    NuclearFuelReprocessing = "nuclear-fuel-reprocessing"
    UraniumProcessing = "uranium-processing"
    SulfuricAcid = (
        "sulfuric-acid"  # Recipe for producing sulfuric acid with a chemical plant
    )
    BasicOilProcessing = (
        "basic-oil-processing"  # Recipe for producing petroleum gas with a oil refinery
    )
    AdvancedOilProcessing = "advanced-oil-processing"  # Recipe for producing petroleum gas, heavy oil and light oil with a oil refinery
    CoalLiquefaction = (
        "coal-liquefaction"  # Recipe for producing petroleum gas in a oil refinery
    )
    HeavyOilCracking = (
        "heavy-oil-cracking"  # Recipe for producing light oil in a chemical plant
    )
    LightOilCracking = (
        "light-oil-cracking"  # Recipe for producing petroleum gas in a chemical plant
    )

    SolidFuelFromHeavyOil = "solid-fuel-from-heavy-oil"  # Recipe for producing solid fuel in a chemical plant
    SolidFuelFromLightOil = "solid-fuel-from-light-oil"  # Recipe for producing solid fuel in a chemical plant
    SolidFuelFromPetroleumGas = "solid-fuel-from-petroleum-gas"  # Recipe for producing solid fuel in a chemical plant

    FillCrudeOilBarrel = "fill-crude-oil-barrel"
    FillHeavyOilBarrel = "fill-heavy-oil-barrel"
    FillLightOilBarrel = "fill-light-oil-barrel"
    FillLubricantBarrel = "fill-lubricant-barrel"
    FillPetroleumGasBarrel = "fill-petroleum-gas-barrel"
    FillSulfuricAcidBarrel = "fill-sulfuric-acid-barrel"
    FillWaterBarrel = "fill-water-barrel"

    EmptyCrudeOilBarrel = "empty-crude-oil-barrel"
    EmptyHeavyOilBarrel = "empty-heavy-oil-barrel"
    EmptyLightOilBarrel = "empty-light-oil-barrel"
    EmptyLubricantBarrel = "empty-lubricant-barrel"
    EmptyPetroleumGasBarrel = "empty-petroleum-gas-barrel"
    EmptySulfuricAcidBarrel = "empty-sulfuric-acid-barrel"
    EmptyWaterBarrel = "empty-water-barrel"


class PrototypeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Prototype objects and Pydantic BaseModel instances."""

    def default(self, obj):
        # Import here to avoid circular imports
        from pydantic import BaseModel

        if isinstance(obj, Prototype):
            return obj.to_dict()
        elif isinstance(obj, BaseModel):
            # Handle Pydantic BaseModel instances (like Position)
            return {
                "__pydantic__": True,
                "model": obj.__class__.__name__,
                "data": obj.model_dump(),
            }
        return super().default(obj)


def prototype_json_hook(dct):
    """JSON decode hook for Prototype objects and Pydantic BaseModel instances."""
    if isinstance(dct, dict):
        if dct.get("__prototype__"):
            return Prototype.from_dict(dct)
        elif dct.get("__pydantic__"):
            # Handle Pydantic BaseModel instances
            model_name = dct["model"]
            data = dct["data"]

            # Map model names to classes
            if model_name == "Position":
                return ent.Position(**data)
            elif model_name == "BoundingBox":
                return ent.BoundingBox(**data)
            # Add more model mappings as needed
            else:
                # Fallback: return the data dict for unknown models
                return data
    return dct


def encode_prototypes(obj):
    """Encode objects containing Prototypes and Pydantic models to JSON string."""
    return json.dumps(obj, cls=PrototypeJSONEncoder)


def decode_prototypes(json_str):
    """Decode JSON string back to objects with Prototypes and Pydantic models."""
    return json.loads(json_str, object_hook=prototype_json_hook)


def encode_prototypes_safe(obj):
    """Safely encode objects that might contain Prototypes and Pydantic models."""
    try:
        return json.dumps(obj, cls=PrototypeJSONEncoder)
    except (TypeError, ValueError):
        # Fallback: convert complex objects to their string representation
        from pydantic import BaseModel

        def convert_objects(item):
            if isinstance(item, Prototype):
                return str(item)
            elif isinstance(item, BaseModel):
                return item.model_dump()
            elif isinstance(item, dict):
                return {k: convert_objects(v) for k, v in item.items()}
            elif isinstance(item, (list, tuple)):
                return type(item)(convert_objects(i) for i in item)
            return item

        return json.dumps(convert_objects(obj))


class Prototype(enum.Enum, metaclass=PrototypeMetaclass):
    AssemblingMachine1 = "assembling-machine-1", ent.AssemblingMachine
    AssemblingMachine2 = "assembling-machine-2", ent.AdvancedAssemblingMachine
    AssemblingMachine3 = "assembling-machine-3", ent.AdvancedAssemblingMachine
    Centrifuge = "centrifuge", ent.AssemblingMachine

    BurnerInserter = "burner-inserter", ent.BurnerInserter
    FastInserter = "fast-inserter", ent.Inserter
    ExpressInserter = "express-inserter", ent.Inserter

    LongHandedInserter = "long-handed-inserter", ent.Inserter
    StackInserter = "stack-inserter", ent.Inserter
    StackFilterInserter = "stack-filter-inserter", ent.FilterInserter
    FilterInserter = "filter-inserter", ent.FilterInserter

    Inserter = "inserter", ent.Inserter

    BurnerMiningDrill = "burner-mining-drill", ent.BurnerMiningDrill
    ElectricMiningDrill = "electric-mining-drill", ent.ElectricMiningDrill

    StoneFurnace = "stone-furnace", ent.Furnace
    SteelFurnace = "steel-furnace", ent.Furnace
    ElectricFurnace = "electric-furnace", ent.ElectricFurnace

    Splitter = "splitter", ent.Splitter
    FastSplitter = "fast-splitter", ent.Splitter
    ExpressSplitter = "express-splitter", ent.Splitter

    Rail = "rail", ent.Rail

    TransportBelt = "transport-belt", ent.TransportBelt
    FastTransportBelt = "fast-transport-belt", ent.TransportBelt
    ExpressTransportBelt = "express-transport-belt", ent.TransportBelt
    ExpressUndergroundBelt = "express-underground-belt", ent.UndergroundBelt
    FastUndergroundBelt = "fast-underground-belt", ent.UndergroundBelt
    UndergroundBelt = "underground-belt", ent.UndergroundBelt
    OffshorePump = "offshore-pump", ent.OffshorePump
    PumpJack = "pumpjack", ent.PumpJack
    Pump = "pump", ent.Pump
    Boiler = "boiler", ent.Boiler
    OilRefinery = "oil-refinery", ent.OilRefinery
    ChemicalPlant = "chemical-plant", ent.ChemicalPlant

    SteamEngine = "steam-engine", ent.Generator
    SolarPanel = "solar-panel", ent.SolarPanel

    UndergroundPipe = "pipe-to-ground", ent.Pipe
    HeatPipe = "heat-pipe", ent.Pipe
    Pipe = "pipe", ent.Pipe

    SteelChest = "steel-chest", ent.Chest
    IronChest = "iron-chest", ent.Chest
    WoodenChest = "wooden-chest", ent.Chest
    IronGearWheel = "iron-gear-wheel", ent.Entity
    StorageTank = "storage-tank", ent.StorageTank

    SmallElectricPole = "small-electric-pole", ent.ElectricityPole
    MediumElectricPole = "medium-electric-pole", ent.ElectricityPole
    BigElectricPole = "big-electric-pole", ent.ElectricityPole

    Coal = "coal", None
    Wood = "wood", None
    Sulfur = "sulfur", None
    IronOre = "iron-ore", None
    CopperOre = "copper-ore", None
    Stone = "stone", None
    Concrete = "concrete", None
    UraniumOre = "uranium-ore", None

    IronPlate = "iron-plate", None  # Crafting requires smelting 1 iron ore
    IronStick = "iron-stick", None
    SteelPlate = "steel-plate", None  # Crafting requires smelting 5 iron plates
    CopperPlate = "copper-plate", None  # Crafting requires smelting 1 copper ore
    StoneBrick = "stone-brick", None  # Crafting requires smelting 2 stone
    CopperCable = "copper-cable", None
    PlasticBar = "plastic-bar", None
    EmptyBarrel = "empty-barrel", None
    Battery = "battery", None
    SulfuricAcid = "sulfuric-acid", None
    Uranium235 = "uranium-235", None
    Uranium238 = "uranium-238", None

    Lubricant = "lubricant", None
    PetroleumGas = "petroleum-gas", None
    AdvancedOilProcessing = (
        "advanced-oil-processing",
        None,
    )  # These are recipes, not prototypes.
    CoalLiquifaction = "coal-liquifaction", None  # These are recipes, not prototypes.
    SolidFuel = "solid-fuel", None  # These are recipes, not prototypes.
    LightOil = "light-oil", None
    HeavyOil = "heavy-oil", None

    ElectronicCircuit = "electronic-circuit", None
    AdvancedCircuit = "advanced-circuit", None
    ProcessingUnit = "processing-unit", None
    EngineUnit = "engine-unit", None
    ElectricEngineUnit = "electric-engine-unit", None

    Lab = "lab", ent.Lab
    Accumulator = "accumulator", ent.Accumulator
    GunTurret = "gun-turret", ent.GunTurret

    PiercingRoundsMagazine = "piercing-rounds-magazine", ent.Ammo
    FirearmMagazine = "firearm-magazine", ent.Ammo
    Grenade = "grenade", None

    Radar = "radar", ent.Entity
    StoneWall = "stone-wall", ent.Entity
    Gate = "gate", ent.Entity
    SmallLamp = "small-lamp", ent.Entity

    NuclearReactor = "nuclear-reactor", ent.Reactor
    UraniumFuelCell = "uranium-fuel-cell", None
    HeatExchanger = "heat-exchanger", ent.HeatExchanger

    AutomationSciencePack = "automation-science-pack", None
    MilitarySciencePack = "military-science-pack", None
    LogisticsSciencePack = "logistic-science-pack", None
    ProductionSciencePack = "production-science-pack", None
    UtilitySciencePack = "utility-science-pack", None
    ChemicalSciencePack = "chemical-science-pack", None

    ProductivityModule = "productivity-module", None
    ProductivityModule2 = "productivity-module-2", None
    ProductivityModule3 = "productivity-module-3", None

    FlyingRobotFrame = "flying-robot-frame", None

    RocketSilo = "rocket-silo", ent.RocketSilo
    Rocket = "rocket", ent.Rocket
    Satellite = "satellite", None
    RocketPart = "rocket-part", None
    RocketControlUnit = "rocket-control-unit", None
    LowDensityStructure = "low-density-structure", None
    RocketFuel = "rocket-fuel", None
    SpaceSciencePack = "space-science-pack", None

    BeltGroup = "belt-group", ent.BeltGroup
    PipeGroup = "pipe-group", ent.PipeGroup
    ElectricityGroup = "electricity-group", ent.ElectricityGroup

    def __init__(self, prototype_name, entity_class_name):
        self.prototype_name = prototype_name
        self.entity_class = entity_class_name

    def __reduce_ex__(self, protocol):
        """Enable pickling/JSON serialization by returning the prototype name."""
        return (self.__class__._prototype_reconstructor, (self.name,))

    @classmethod
    def _prototype_reconstructor(cls, name):
        """Reconstruct a Prototype instance from its name."""
        return getattr(cls, name)

    def __str__(self):
        """Return the prototype name for string representation."""
        return self.prototype_name

    @property
    def WIDTH(self):
        return self.entity_class._width.default  # Access the class attribute directly

    @property
    def HEIGHT(self):
        return self.entity_class._height.default

    def __json__(self):
        """Custom JSON serialization method."""
        return {
            "__prototype__": True,
            "name": self.name,
            "prototype_name": self.prototype_name,
        }

    @classmethod
    def from_json(cls, data):
        """Create a Prototype instance from JSON data."""
        if isinstance(data, dict) and data.get("__prototype__"):
            prototype_name = data["name"]
            # Look up the prototype by name
            for prototype in cls:
                if prototype.name == prototype_name:
                    return prototype
            raise ValueError(f"Unknown prototype name: {prototype_name}")
        return data

    def to_dict(self):
        """Convert to a simple dictionary for JSON serialization."""
        return {
            "__prototype__": True,
            "name": self.name,
            "prototype_name": self.prototype_name,
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Prototype instance from a dictionary."""
        if isinstance(data, dict) and data.get("__prototype__"):
            name = data["name"]
            return getattr(cls, name)
        return data


prototype_by_name = {prototype.value[0]: prototype for prototype in Prototype}
prototype_by_title = {str(prototype): prototype for prototype in Prototype}


class Technology(enum.Enum):
    # Basic automation technologies
    Automation = "automation"  # Unlocks assembling machine 1
    Automation2 = "automation-2"  # Unlocks assembling machine 2
    Automation3 = "automation-3"  # Unlocks assembling machine 3

    # Logistics technologies
    Logistics = "logistics"  # Unlocks basic belts and inserters
    Logistics2 = "logistics-2"  # Unlocks fast belts and inserters
    Logistics3 = "logistics-3"  # Unlocks express belts and inserters

    # Circuit technologies
    # CircuitNetwork = "circuit-network"
    AdvancedElectronics = "advanced-electronics"
    AdvancedElectronics2 = "advanced-electronics-2"

    # Power technologies
    Electronics = "electronics"
    ElectricEnergy = "electric-energy-distribution-1"
    ElectricEnergy2 = "electric-energy-distribution-2"
    SolarEnergy = "solar-energy"
    ElectricEngineering = "electric-engine"
    BatteryTechnology = "battery"
    # AdvancedBattery = "battery-mk2-equipment"
    NuclearPower = "nuclear-power"

    # Mining technologies
    SteelProcessing = "steel-processing"
    AdvancedMaterialProcessing = "advanced-material-processing"
    AdvancedMaterialProcessing2 = "advanced-material-processing-2"

    # Military technologies
    MilitaryScience = "military"
    # MilitaryScience2 = "military-2"
    # MilitaryScience3 = "military-3"
    # MilitaryScience4 = "military-4"
    # Artillery = "artillery"
    # Flamethrower = "flamethrower"
    # LandMines = "land-mines"
    # Turrets = "turrets"
    # LaserTurrets = "laser-turrets"
    # RocketSilo = "rocket-silo"

    # Armor and equipment
    ModularArmor = "modular-armor"
    PowerArmor = "power-armor"
    PowerArmor2 = "power-armor-mk2"
    NightVision = "night-vision-equipment"
    EnergyShield = "energy-shields"
    EnergyShield2 = "energy-shields-mk2-equipment"

    # Train technologies
    RailwayTransportation = "railway"
    # AutomatedRailTransportation = "automated-rail-transportation"
    # RailSignals = "rail-signals"

    # Oil processing
    OilProcessing = "oil-processing"
    AdvancedOilProcessing = "advanced-oil-processing"
    SulfurProcessing = "sulfur-processing"
    Plastics = "plastics"
    Lubricant = "lubricant"

    # Modules
    # Modules = "modules"
    # SpeedModule = "speed-module"
    # SpeedModule2 = "speed-module-2"
    # SpeedModule3 = "speed-module-3"
    ProductivityModule = "productivity-module"
    ProductivityModule2 = "productivity-module-2"
    ProductivityModule3 = "productivity-module-3"
    # EfficiencyModule = "efficiency-module"
    # EfficiencyModule2 = "efficiency-module-2"
    # EfficiencyModule3 = "efficiency-module-3"

    # Robot technologies
    Robotics = "robotics"
    # ConstructionRobotics = "construction-robotics"
    # LogisticRobotics = "logistic-robotics"
    # LogisticSystem = "logistic-system"
    # CharacterLogisticSlots = "character-logistic-slots"
    # CharacterLogisticSlots2 = "character-logistic-slots-2"

    # Science technologies
    LogisticsSciencePack = "logistic-science-pack"
    MilitarySciencePack = "military-science-pack"
    ChemicalSciencePack = "chemical-science-pack"
    ProductionSciencePack = "production-science-pack"
    # UtilitySciencePack = "utility-science-pack"
    # SpaceSciencePack = "space-science-pack"

    # Inserter technologies
    FastInserter = "fast-inserter"
    StackInserter = "stack-inserter"
    StackInserterCapacity1 = "stack-inserter-capacity-bonus-1"
    StackInserterCapacity2 = "stack-inserter-capacity-bonus-2"

    # Storage technologies
    StorageTanks = "fluid-handling"
    BarrelFilling = "barrel-filling"
    # Warehouses = "warehousing"

    # Vehicle technologies
    # Automobiles = "automobilism"
    # TankTechnology = "tank"
    # SpiderVehicle = "spidertron"

    # Weapon technologies
    Grenades = "grenades"
    # ClusterGrenades = "cluster-grenades"
    # RocketLauncher = "rocketry"
    # ExplosiveRocketry = "explosive-rocketry"
    # AtomicBomb = "atomic-bomb"
    # CombatRobotics = "combat-robotics"
    # CombatRobotics2 = "combat-robotics-2"
    # CombatRobotics3 = "combat-robotics-3"

    # Misc technologies
    Landfill = "landfill"
    CharacterInventorySlots = "character-inventory-slots"
    ResearchSpeed = "research-speed"
    # Toolbelt = "toolbelt"
    # BrakinPower = "braking-force"

    # # Endgame technologies
    SpaceScience = "space-science-pack"
    RocketFuel = "rocket-fuel"
    RocketControl = "rocket-control-unit"
    LowDensityStructure = "low-density-structure"
    RocketSiloTechnology = "rocket-silo"


# Helper dictionary to look up technology by name string
technology_by_name = {tech.value: tech for tech in Technology}


class Resource:
    Coal = "coal", ent.ResourcePatch
    IronOre = "iron-ore", ent.ResourcePatch
    CopperOre = "copper-ore", ent.ResourcePatch
    Stone = "stone", ent.ResourcePatch
    Water = "water", ent.ResourcePatch
    CrudeOil = "crude-oil", ent.ResourcePatch
    UraniumOre = "uranium-ore", ent.ResourcePatch
    Wood = "wood", ent.ResourcePatch
