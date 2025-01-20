import enum
from difflib import get_close_matches

from factorio_entities import *


class PrototypeName(enum.Enum):
    AssemblingMachine = "assembling-machine-1"
    BurnerInserter = "burner-inserter"
    BurnerMiningDrill = "burner-mining-drill"
    ElectricMiningDrill = "electric-mining-drill"
    StoneFurnace = "stone-furnace"
    TransportBelt = "transport-belt"
    OffshorePump = "offshore-pump"
    Boiler = "boiler"
    SteamEngine = "steam-engine"
    Pipe = "pipe"
    SmallElectricPole = "small-electric-pole"
    IronChest = "iron-chest"
    ElectronicCircuit = "electronic-circuit"
    Lab = "lab"
    GunTurret = "gun-turret"

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
            return super().__getattr__(name)
        except AttributeError:
            # Get all valid prototype names
            valid_names = [member.name for member in cls]

            # Find closest matches
            matches = get_close_matches(name, valid_names, n=3, cutoff=0.6)

            suggestion_msg = ""
            if matches:
                suggestion_msg = f". Did you mean: {', '.join(matches)}?"

            raise AttributeError(f"'{cls.__name__}' has no attribute '{name}'{suggestion_msg}")

class Prototype(enum.Enum, metaclass=PrototypeMetaclass):
    AssemblingMachine1 = "assembling-machine-1", AssemblingMachine
    AssemblingMachine2 = "assembling-machine-2", AssemblingMachine
    AssemblingMachine3 = "assembling-machine-3", AssemblingMachine
    BurnerInserter = "burner-inserter", BurnerInserter
    FastInserter = "fast-inserter", Inserter
    ExpressInserter = "express-inserter", Inserter
    Inserter = "inserter", Inserter
    BurnerMiningDrill = "burner-mining-drill", BurnerMiningDrill
    ElectricMiningDrill = "electric-mining-drill", MiningDrill
    StoneFurnace = "stone-furnace", Furnace
    FastTransportBelt = "fast-transport-belt", TransportBelt
    ExpressTransportBelt = "express-transport-belt", TransportBelt
    Splitter = "splitter", Splitter
    FastSplitter = "fast-splitter", Splitter
    ExpressSplitter = "express-splitter", Splitter
    TransportBelt = "transport-belt", TransportBelt
    ExpressUndergroundBelt = "express-underground-belt", UndergroundBelt
    FastUndergroundBelt = "fast-underground-belt", UndergroundBelt
    UndergroundBelt = "underground-belt", UndergroundBelt

    OffshorePump = "offshore-pump", OffshorePump
    PumpJack = "pumpjack", PumpJack
    Boiler = "boiler", Boiler
    SteamEngine = "steam-engine", Generator
    Pipe = "pipe", Pipe
    IronChest = "iron-chest", Chest
    WoodenChest = "wooden-chest", Chest
    IronGearWheel = "iron-gear-wheel", Entity
    Coal = "coal", None
    Wood = "wood", None
    IronPlate = "iron-plate", None # Crafting requires smelting 1 iron ore, smelts for 0.5 seconds per ore
    SteelPlate = "steel-plate", None # Crafting requires smelting 5 iron plates, smelts for 4 seconds per ore
    CopperPlate = "copper-plate", None # Crafting requires smelting 1 copper ore, smelts for 0.5 seconds per ore
    SmallElectricPole = "small-electric-pole", ElectricityPole
    MediumElectricPole = "medium-electric-pole", ElectricityPole
    BigElectricPole = "big-electric-pole", ElectricityPole
    IronOre = "iron-ore", None
    CopperOre = "copper-ore", None
    Stone = "stone", None
    CopperCable = "copper-cable", None # Crafting 2 copper cables requires 1 copper plate
    ElectronicCircuit = "electronic-circuit", None # Crafting requires 3 copper cables, 1 iron plate
    AdvancedCircuit = "advanced-circuit", None # Crafting requires 2 electronic circuits, 2 plastic bars, 4 copper cables
    Lab = "lab", Lab # Crafting requires 10 electronic circuits, 10 iron gear wheels, 4 transport belts
    AutomationSciencePack = "automation-science-pack", None
    Accumulator = "accumulator", Accumulator
    GunTurret = "gun-turret", GunTurret # Crafting requires 10 copper plates, 10 iron gear wheels, 20 iron plates
    FirearmMagazine = "firearm-magazine", Ammo # Crafting requires 4 iron plates
    StoneBrick = "stone-brick", None # Crafting requires smelting 2 stone to make one stone brick
    Radar = "radar", Entity # Crafting requires 5 electronic circuits, 5 iron gear wheels, 10 iron plates
    StoneWall = "stone-wall", Entity # Crafting requires 5 stone bricks
    SmallLamp = "small-lamp", Entity # Crafting requires 1 electronic circuit, 3 iron plates
    SciencePack1 = "science-pack-1", None # Crafting requires 1 copper plate, 1 iron gear wheel
    SciencePack2 = "science-pack-2", None # Crafting requires 1 inserter, 1 transport belt
    SciencePack3 = "science-pack-3", None # Crafting requires 1 advanced circuit, 1 engine unit, 1 electric mining drill
    MilitarySciencePack = "military-science-pack", None # Crafting requires 1 piercing round magazine, 1 grenade, 1 gun turret
    EngineUnit = "engine-unit", None # Crafting requires 1 iron gear wheel, 1 pipe, 2 engine units

    BeltGroup = "belt-group", BeltGroup
    PipeGroup = "pipe-group", PipeGroup

    def __init__(self, prototype_name, entity_class):
        self.prototype_name = prototype_name
        self.entity_class = entity_class

prototype_by_name = {prototype.value[0]: prototype for prototype in Prototype}

import enum


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
    # AdvancedElectronics = "advanced-electronics"
    # AdvancedElectronics2 = "advanced-electronics-2"

    # Power technologies
    Electronics = "electronics"
    ElectricEnergy = "electric-energy-distribution-1"
    ElectricEnergy2 = "electric-energy-distribution-2"
    SolarEnergy = "solar-energy"
    ElectricEngineering = "electric-engine"
    BatteryTechnology = "battery"
    # AdvancedBattery = "battery-mk2-equipment"
    # NuclearPower = "nuclear-power"

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
    # RailwayTransportation = "railway"
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
    # ProductivityModule = "productivity-module"
    # ProductivityModule2 = "productivity-module-2"
    # ProductivityModule3 = "productivity-module-3"
    # EfficiencyModule = "efficiency-module"
    # EfficiencyModule2 = "efficiency-module-2"
    # EfficiencyModule3 = "efficiency-module-3"

    # Robot technologies
    # Robotics = "robotics"
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
    # Grenades = "grenades"
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
    # SpaceScience = "space-science-pack"
    # RocketFuel = "rocket-fuel"
    # RocketControl = "rocket-control-unit"
    # LowDensityStructure = "low-density-structure"
    # RocketSiloTechnology = "rocket-silo"


# Helper dictionary to look up technology by name string
technology_by_name = {tech.value: tech for tech in Technology}

class Resource:
    Coal = "coal", ResourcePatch
    IronOre = "iron-ore", ResourcePatch
    CopperOre = "copper-ore", ResourcePatch
    Stone = "stone", ResourcePatch
    Water = "water", ResourcePatch
    CrudeOil = "crude-oil", ResourcePatch
    UraniumOre = "uranium-ore", ResourcePatch
    Wood = "wood", ResourcePatch