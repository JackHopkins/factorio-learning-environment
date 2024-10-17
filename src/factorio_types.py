import enum
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


class Prototype(enum.Enum):
    AssemblingMachine1 = "assembling-machine-1", AssemblingMachine1
    BurnerInserter = "burner-inserter", BurnerInserter
    BurnerMiningDrill = "burner-mining-drill", BurnerMiningDrill
    ElectricMiningDrill = "electric-mining-drill", MiningDrill
    StoneFurnace = "stone-furnace", Furnace
    TransportBelt = "transport-belt", TransportBelt
    OffshorePump = "offshore-pump", OffshorePump
    Boiler = "boiler", Boiler
    #Generator = "generator", Generator
    SteamEngine = "steam-engine", Generator
    Pipe = "pipe", Entity
    IronChest = "iron-chest", Chest
    WoodenChest = "wooden-chest", Chest
    IronGearWheel = "iron-gear-wheel", Entity
    Coal = "coal", None
    IronPlate = "iron-plate", None
    SteelPlate = "steel-plate", None
    CopperPlate = "copper-plate", None
    SmallElectricPole = "small-electric-pole", Entity
    IronOre = "iron-ore", None
    CopperOre = "copper-ore", None
    Stone = "stone", None
    CopperCable = "copper-cable", None
    ElectronicCircuit = "electronic-circuit", None
    Lab = "lab", Entity
    AutomationSciencePack = "automation-science-pack", None
    Accumulator = "accumulator", Accumulator
    GunTurret = "gun-turret", GunTurret
    FirearmMagazine = "firearm-magazine", Ammo
    StoneBrick = "stone-brick", None
    Radar = "radar", Entity


class Resource:
    Coal = "coal", ResourcePatch
    IronOre = "iron-ore", ResourcePatch
    CopperOre = "copper-ore", ResourcePatch
    Stone = "stone", ResourcePatch
    Water = "water", ResourcePatch
    CrudeOil = "crude-oil", ResourcePatch
    UraniumOre = "uranium-ore", ResourcePatch
    Wood = "wood", ResourcePatch