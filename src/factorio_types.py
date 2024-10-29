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
    BurnerMiningDrill = "burner-mining-drill", BurnerMiningDrill
    ElectricMiningDrill = "electric-mining-drill", MiningDrill
    StoneFurnace = "stone-furnace", Furnace
    TransportBelt = "transport-belt", TransportBelt
    OffshorePump = "offshore-pump", OffshorePump
    PumpJack = "pumpjack", PumpJack
    Boiler = "boiler", Boiler
    SteamEngine = "steam-engine", Generator
    Pipe = "pipe", Entity
    IronChest = "iron-chest", Chest
    WoodenChest = "wooden-chest", Chest
    IronGearWheel = "iron-gear-wheel", Entity
    Coal = "coal", None
    IronPlate = "iron-plate", None # Crafting requires smelting 1 iron ore, smelts for 0.5 seconds per ore
    SteelPlate = "steel-plate", None # Crafting requires smelting 5 iron plates, smelts for 4 seconds per ore
    CopperPlate = "copper-plate", None # Crafting requires smelting 1 copper ore, smelts for 0.5 seconds per ore
    SmallElectricPole = "small-electric-pole", Entity
    IronOre = "iron-ore", None
    CopperOre = "copper-ore", None
    Stone = "stone", None
    CopperCable = "copper-cable", None # Crafting 2 copper cables requires 1 copper plate
    ElectronicCircuit = "electronic-circuit", None # Crafting requires 3 copper cables, 1 iron plate
    Lab = "lab", Lab # Crafting requires 10 electronic circuits, 10 iron gear wheels, 4 transport belts
    AutomationSciencePack = "automation-science-pack", None
    Accumulator = "accumulator", Accumulator
    GunTurret = "gun-turret", GunTurret # Crafting requires 10 copper plates, 10 iron gear wheels, 20 iron plates
    FirearmMagazine = "firearm-magazine", Ammo # Crafting requires 4 iron plates
    StoneBrick = "stone-brick", None # Crafting requires smelting 2 stone to make one stone brick
    Radar = "radar", Entity # Crafting requires 5 electronic circuits, 5 iron gear wheels, 10 iron plates
    StoneWall = "stone-wall", Entity # Crafting requires 5 stone bricks
    PumpJack = "pumpjack", PumpJack

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