from __future__ import annotations
import enum
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
        # Try to get the attribute normally first
        try:
            return cls._member_map_[name]
        except KeyError:
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

    FillCrudeOilBarrel = "crude-oil-barrel"
    FillHeavyOilBarrel = "heavy-oil-barrel"
    FillLightOilBarrel = "light-oil-barrel"
    FillLubricantBarrel = "lubricant-barrel"
    FillPetroleumGasBarrel = "petroleum-gas-barrel"
    FillSulfuricAcidBarrel = "sulfuric-acid-barrel"
    FillWaterBarrel = "water-barrel"

    EmptyCrudeOilBarrel = "empty-crude-oil-barrel"
    EmptyHeavyOilBarrel = "empty-heavy-oil-barrel"
    EmptyLightOilBarrel = "empty-light-oil-barrel"
    EmptyLubricantBarrel = "empty-lubricant-barrel"
    EmptyPetroleumGasBarrel = "empty-petroleum-gas-barrel"
    EmptySulfuricAcidBarrel = "empty-sulfuric-acid-barrel"
    EmptyWaterBarrel = "empty-water-barrel"


class Prototype(enum.Enum, metaclass=PrototypeMetaclass):
    AssemblingMachine1 = "assembling-machine-1", ent.AssemblingMachine
    AssemblingMachine2 = "assembling-machine-2", ent.AdvancedAssemblingMachine
    AssemblingMachine3 = "assembling-machine-3", ent.AdvancedAssemblingMachine
    Centrifuge = "centrifuge", ent.AssemblingMachine

    BurnerInserter = "burner-inserter", ent.BurnerInserter
    FastInserter = "fast-inserter", ent.Inserter
    # Factorio 2.0: express-inserter removed, filter-inserter removed (all inserters can filter)
    # stack-filter-inserter renamed to bulk-inserter

    LongHandedInserter = "long-handed-inserter", ent.Inserter
    BulkInserter = (
        "bulk-inserter",
        ent.Inserter,
    )  # Factorio 2.0: old stack-inserter renamed to bulk-inserter
    # Backwards compatibility aliases - map to closest equivalent
    StackInserter = (
        "bulk-inserter",
        ent.Inserter,
    )  # Factorio 2.0: old stack-inserter renamed to bulk-inserter
    FilterInserter = (
        "fast-inserter",
        ent.Inserter,
    )  # Factorio 2.0: filter-inserter removed, use fast-inserter
    StackFilterInserter = (
        "bulk-inserter",
        ent.Inserter,
    )  # Factorio 2.0: renamed to bulk-inserter

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

    # Logistic Chests
    PassiveProviderChest = "passive-provider-chest", ent.LogisticChest
    ActiveProviderChest = "active-provider-chest", ent.LogisticChest
    StorageChest = "storage-chest", ent.LogisticChest
    RequesterChest = "requester-chest", ent.LogisticChest
    BufferChest = "buffer-chest", ent.LogisticChest

    # Beacon
    Beacon = "beacon", ent.Beacon

    # Modules (items only)
    SpeedModule = "speed-module", None
    SpeedModule2 = "speed-module-2", None
    SpeedModule3 = "speed-module-3", None
    EfficiencyModule = "efficiency-module", None
    EfficiencyModule2 = "efficiency-module-2", None
    EfficiencyModule3 = "efficiency-module-3", None

    # Power
    Substation = "substation", ent.ElectricityPole
    SteamTurbine = "steam-turbine", ent.Generator

    # Circuit Network
    ArithmeticCombinator = "arithmetic-combinator", ent.Combinator
    DeciderCombinator = "decider-combinator", ent.Combinator
    ConstantCombinator = "constant-combinator", ent.Combinator
    PowerSwitch = "power-switch", ent.Combinator
    ProgrammableSpeaker = "programmable-speaker", ent.Entity

    # Trains
    TrainStop = "train-stop", ent.TrainStop
    RailSignal = "rail-signal", ent.RailSignal
    RailChainSignal = "rail-chain-signal", ent.RailSignal
    Locomotive = "locomotive", ent.RollingStock
    CargoWagon = "cargo-wagon", ent.RollingStock
    FluidWagon = "fluid-wagon", ent.RollingStock

    # Logistics
    Roboport = "roboport", ent.Roboport

    # Defense
    LaserTurret = "laser-turret", ent.Turret
    FlamethrowerTurret = "flamethrower-turret", ent.FluidTurret
    ArtilleryTurret = "artillery-turret", ent.Turret
    LandMine = "land-mine", ent.Entity

    # Vehicles
    Car = "car", ent.Vehicle
    Tank = "tank", ent.Vehicle
    Spidertron = "spidertron", ent.Vehicle

    def __init__(self, prototype_name, entity_class_name):
        self.prototype_name = prototype_name
        self.entity_class = entity_class_name

    @property
    def WIDTH(self):
        return self.entity_class._width.default  # Access the class attribute directly

    @property
    def HEIGHT(self):
        return self.entity_class._height.default


prototype_by_name = {prototype.value[0]: prototype for prototype in Prototype}
prototype_by_title = {str(prototype): prototype for prototype in Prototype}


class Technology(enum.Enum):
    # Science pack technologies (Factorio 2.0 prerequisites)
    SteamPower = "steam-power"  # Starting tech, no prerequisites
    AutomationSciencePack = "automation-science-pack"  # Requires steam-power

    # Basic automation technologies
    Automation = "automation"  # Unlocks assembling machine 1
    Automation2 = "automation-2"  # Unlocks assembling machine 2
    Automation3 = "automation-3"  # Unlocks assembling machine 3

    # Logistics technologies
    Logistics = "logistics"  # Unlocks basic belts and inserters
    Logistics2 = "logistics-2"  # Unlocks fast belts and inserters
    Logistics3 = "logistics-3"  # Unlocks express belts and inserters

    # Circuit technologies
    CircuitNetwork = "circuit-network"
    AdvancedCircuit = "advanced-circuit"
    ProcessingUnit = "processing-unit"

    # Backwards-compatible aliases for the Factorio 1.x names. The values must
    # still resolve to real Factorio 2.0 technology prototypes.
    AdvancedElectronics = "advanced-circuit"
    AdvancedElectronics2 = "processing-unit"

    # Power technologies
    Electronics = "electronics"
    ElectricEnergy = "electric-energy-distribution-1"
    ElectricEnergy2 = "electric-energy-distribution-2"
    SolarEnergy = "solar-energy"
    ElectricEngineering = "electric-engine"
    BatteryTechnology = "battery"
    AdvancedBattery = "battery-mk2-equipment"
    NuclearPower = "nuclear-power"

    # Mining technologies
    SteelProcessing = "steel-processing"
    AdvancedMaterialProcessing = "advanced-material-processing"
    AdvancedMaterialProcessing2 = "advanced-material-processing-2"

    # Military technologies
    MilitaryScience = "military"
    MilitaryScience2 = "military-2"
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
    EnergyShield = "energy-shield-equipment"
    EnergyShield2 = "energy-shield-mk2-equipment"

    # Train technologies
    RailwayTransportation = "railway"
    # AutomatedRailTransportation = "automated-rail-transportation"
    # RailSignals = "rail-signals"

    # Oil processing
    OilGathering = "oil-gathering"
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
    UtilitySciencePack = "utility-science-pack"
    # SpaceSciencePack = "space-science-pack"

    # Inserter technologies
    FastInserter = "fast-inserter"
    BulkInserter = "bulk-inserter"
    StackInserter = "bulk-inserter"
    StackInserterCapacity1 = "inserter-capacity-bonus-1"
    StackInserterCapacity2 = "inserter-capacity-bonus-2"

    # Storage technologies
    StorageTanks = "fluid-handling"
    # Warehouses = "warehousing"

    # Vehicle technologies
    # Automobiles = "automobilism"
    # TankTechnology = "tank"
    # SpiderVehicle = "spidertron"

    # Weapon technologies
    Grenades = "military-2"
    # ClusterGrenades = "cluster-grenades"
    # RocketLauncher = "rocketry"
    # ExplosiveRocketry = "explosive-rocketry"
    # AtomicBomb = "atomic-bomb"
    # CombatRobotics = "combat-robotics"
    # CombatRobotics2 = "combat-robotics-2"
    # CombatRobotics3 = "combat-robotics-3"

    # Misc technologies
    Landfill = "landfill"
    Toolbelt = "toolbelt"
    ResearchSpeed = "research-speed-1"
    StoneWall = "stone-wall"
    Engine = "engine"
    # BrakinPower = "braking-force"

    # # Endgame technologies
    SpaceScience = "space-science-pack"
    RocketFuel = "rocket-fuel"
    LowDensityStructure = "low-density-structure"
    RocketSiloTechnology = "rocket-silo"

    # Every other technology in Factorio 2.0 (base game), named after its prototype
    # name: bulk-inserter -> BulkInserter, research-speed-2 -> ResearchSpeed2.
    AdvancedCombinators = "advanced-combinators"
    Artillery = "artillery"
    ArtilleryShellRange1 = "artillery-shell-range-1"
    ArtilleryShellSpeed1 = "artillery-shell-speed-1"
    AtomicBomb = "atomic-bomb"
    AutomatedRailTransportation = "automated-rail-transportation"
    Automobilism = "automobilism"
    BatteryEquipment = "battery-equipment"
    BeltImmunityEquipment = "belt-immunity-equipment"
    BrakingForce1 = "braking-force-1"
    BrakingForce2 = "braking-force-2"
    BrakingForce3 = "braking-force-3"
    BrakingForce4 = "braking-force-4"
    BrakingForce5 = "braking-force-5"
    BrakingForce6 = "braking-force-6"
    BrakingForce7 = "braking-force-7"
    CliffExplosives = "cliff-explosives"
    CoalLiquefaction = "coal-liquefaction"
    Concrete = "concrete"
    ConstructionRobotics = "construction-robotics"
    Defender = "defender"
    Destroyer = "destroyer"
    DischargeDefenseEquipment = "discharge-defense-equipment"
    Distractor = "distractor"
    EffectTransmission = "effect-transmission"
    EfficiencyModule = "efficiency-module"
    EfficiencyModule2 = "efficiency-module-2"
    EfficiencyModule3 = "efficiency-module-3"
    ElectricEnergyAccumulators = "electric-energy-accumulators"
    ElectricMiningDrill = "electric-mining-drill"
    ExoskeletonEquipment = "exoskeleton-equipment"
    ExplosiveRocketry = "explosive-rocketry"
    Explosives = "explosives"
    FissionReactorEquipment = "fission-reactor-equipment"
    Flamethrower = "flamethrower"
    Flammables = "flammables"
    FluidWagon = "fluid-wagon"
    FollowerRobotCount1 = "follower-robot-count-1"
    FollowerRobotCount2 = "follower-robot-count-2"
    FollowerRobotCount3 = "follower-robot-count-3"
    FollowerRobotCount4 = "follower-robot-count-4"
    FollowerRobotCount5 = "follower-robot-count-5"
    Gate = "gate"
    GunTurret = "gun-turret"
    HeavyArmor = "heavy-armor"
    InserterCapacityBonus3 = "inserter-capacity-bonus-3"
    InserterCapacityBonus4 = "inserter-capacity-bonus-4"
    InserterCapacityBonus5 = "inserter-capacity-bonus-5"
    InserterCapacityBonus6 = "inserter-capacity-bonus-6"
    InserterCapacityBonus7 = "inserter-capacity-bonus-7"
    KovarexEnrichmentProcess = "kovarex-enrichment-process"
    Lamp = "lamp"
    LandMine = "land-mine"
    Laser = "laser"
    LaserShootingSpeed1 = "laser-shooting-speed-1"
    LaserShootingSpeed2 = "laser-shooting-speed-2"
    LaserShootingSpeed3 = "laser-shooting-speed-3"
    LaserShootingSpeed4 = "laser-shooting-speed-4"
    LaserShootingSpeed5 = "laser-shooting-speed-5"
    LaserShootingSpeed6 = "laser-shooting-speed-6"
    LaserShootingSpeed7 = "laser-shooting-speed-7"
    LaserTurret = "laser-turret"
    LaserWeaponsDamage1 = "laser-weapons-damage-1"
    LaserWeaponsDamage2 = "laser-weapons-damage-2"
    LaserWeaponsDamage3 = "laser-weapons-damage-3"
    LaserWeaponsDamage4 = "laser-weapons-damage-4"
    LaserWeaponsDamage5 = "laser-weapons-damage-5"
    LaserWeaponsDamage6 = "laser-weapons-damage-6"
    LaserWeaponsDamage7 = "laser-weapons-damage-7"
    LogisticRobotics = "logistic-robotics"
    LogisticSystem = "logistic-system"
    Military3 = "military-3"
    Military4 = "military-4"
    MiningProductivity1 = "mining-productivity-1"
    MiningProductivity2 = "mining-productivity-2"
    MiningProductivity3 = "mining-productivity-3"
    MiningProductivity4 = "mining-productivity-4"
    Modules = "modules"
    NuclearFuelReprocessing = "nuclear-fuel-reprocessing"
    PersonalLaserDefenseEquipment = "personal-laser-defense-equipment"
    PersonalRoboportEquipment = "personal-roboport-equipment"
    PersonalRoboportMk2Equipment = "personal-roboport-mk2-equipment"
    PhysicalProjectileDamage1 = "physical-projectile-damage-1"
    PhysicalProjectileDamage2 = "physical-projectile-damage-2"
    PhysicalProjectileDamage3 = "physical-projectile-damage-3"
    PhysicalProjectileDamage4 = "physical-projectile-damage-4"
    PhysicalProjectileDamage5 = "physical-projectile-damage-5"
    PhysicalProjectileDamage6 = "physical-projectile-damage-6"
    PhysicalProjectileDamage7 = "physical-projectile-damage-7"
    Radar = "radar"
    RefinedFlammables1 = "refined-flammables-1"
    RefinedFlammables2 = "refined-flammables-2"
    RefinedFlammables3 = "refined-flammables-3"
    RefinedFlammables4 = "refined-flammables-4"
    RefinedFlammables5 = "refined-flammables-5"
    RefinedFlammables6 = "refined-flammables-6"
    RefinedFlammables7 = "refined-flammables-7"
    RepairPack = "repair-pack"
    ResearchSpeed2 = "research-speed-2"
    ResearchSpeed3 = "research-speed-3"
    ResearchSpeed4 = "research-speed-4"
    ResearchSpeed5 = "research-speed-5"
    ResearchSpeed6 = "research-speed-6"
    Rocketry = "rocketry"
    SolarPanelEquipment = "solar-panel-equipment"
    SpeedModule = "speed-module"
    SpeedModule2 = "speed-module-2"
    SpeedModule3 = "speed-module-3"
    Spidertron = "spidertron"
    SteelAxe = "steel-axe"
    StrongerExplosives1 = "stronger-explosives-1"
    StrongerExplosives2 = "stronger-explosives-2"
    StrongerExplosives3 = "stronger-explosives-3"
    StrongerExplosives4 = "stronger-explosives-4"
    StrongerExplosives5 = "stronger-explosives-5"
    StrongerExplosives6 = "stronger-explosives-6"
    StrongerExplosives7 = "stronger-explosives-7"
    Tank = "tank"
    UraniumAmmo = "uranium-ammo"
    UraniumMining = "uranium-mining"
    UraniumProcessing = "uranium-processing"
    WeaponShootingSpeed1 = "weapon-shooting-speed-1"
    WeaponShootingSpeed2 = "weapon-shooting-speed-2"
    WeaponShootingSpeed3 = "weapon-shooting-speed-3"
    WeaponShootingSpeed4 = "weapon-shooting-speed-4"
    WeaponShootingSpeed5 = "weapon-shooting-speed-5"
    WeaponShootingSpeed6 = "weapon-shooting-speed-6"
    WorkerRobotsSpeed1 = "worker-robots-speed-1"
    WorkerRobotsSpeed2 = "worker-robots-speed-2"
    WorkerRobotsSpeed3 = "worker-robots-speed-3"
    WorkerRobotsSpeed4 = "worker-robots-speed-4"
    WorkerRobotsSpeed5 = "worker-robots-speed-5"
    WorkerRobotsSpeed6 = "worker-robots-speed-6"
    WorkerRobotsStorage1 = "worker-robots-storage-1"
    WorkerRobotsStorage2 = "worker-robots-storage-2"
    WorkerRobotsStorage3 = "worker-robots-storage-3"


# Helper dictionary to look up technology by name string
technology_by_name = {tech.value: tech for tech in Technology}


def closest_technology_names(name: str, limit: int = 8) -> list[str]:
    """Technology names closest to `name`, for error messages about unknown technologies.

    Lists the same name written as an enum member (e.g. "BulkInserter"), then the levels
    of a leveled technology (e.g. "research-speed" -> "research-speed-1", ...), then the
    most similar names.
    """
    names = sorted(technology_by_name)
    low = str(name).strip().lower()
    key = low.replace("-", "").replace("_", "").replace(" ", "")
    close = [t for t in names if t.replace("-", "") == key]
    close += [t for t in names if t.startswith(low + "-")]
    close += get_close_matches(low, names, n=5, cutoff=0.6)
    return list(dict.fromkeys(close))[:limit]


class Resource:
    Coal = "coal", ent.ResourcePatch
    IronOre = "iron-ore", ent.ResourcePatch
    CopperOre = "copper-ore", ent.ResourcePatch
    Stone = "stone", ent.ResourcePatch
    Water = "water", ent.ResourcePatch
    CrudeOil = "crude-oil", ent.ResourcePatch
    UraniumOre = "uranium-ore", ent.ResourcePatch
    Wood = "wood", ent.ResourcePatch
