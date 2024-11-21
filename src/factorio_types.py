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
    SmallElectricPole = "small-electric-pole", Entity
    MediumElectricPole = "medium-electric-pole", Entity
    BigElectricPole = "big-electric-pole", Entity
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

prototype_by_name = {prototype.value[0]: prototype for prototype in Prototype}

class Resource:
    Coal = "coal", ResourcePatch
    IronOre = "iron-ore", ResourcePatch
    CopperOre = "copper-ore", ResourcePatch
    Stone = "stone", ResourcePatch
    Water = "water", ResourcePatch
    CrudeOil = "crude-oil", ResourcePatch
    UraniumOre = "uranium-ore", ResourcePatch
    Wood = "wood", ResourcePatch