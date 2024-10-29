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
    AssemblingMachine1 = "assembling-machine-1", AssemblingMachine1 # Crafting requires 3 electronic circuits, 5 iron gear wheels, 9 iron plates
    BurnerInserter = "burner-inserter", BurnerInserter # Crafting requires 1 iron gear wheel, 1 iron plate,
    BurnerMiningDrill = "burner-mining-drill", BurnerMiningDrill # Crafting requires 3 iron gear wheels, 3 iron plates AND 1 stone furnace AS INGEREDIENG
    ElectricMiningDrill = "electric-mining-drill", MiningDrill # Crafting requires 3 electronic circuits, 5 iron gear wheels, 10 iron plates
    StoneFurnace = "stone-furnace", Furnace # Crafting requires 5 stone
    TransportBelt = "transport-belt", TransportBelt # Crafting 2 transport belts requires 1 iron gear wheel, 1 iron plate
    OffshorePump = "offshore-pump", OffshorePump # Crafting requires 2 electronic circuits, 1 iron gear wheels, 1 pipe
    Boiler = "boiler", Boiler # Crafting requires 4 pipes AND 1 stone furnace AS CRAFTING INGREDIENT
    #Generator = "generator", Generator
    SteamEngine = "steam-engine", Generator # Crafting requires 8 iron gear wheels, 10 iron plates, 5 pipes
    Pipe = "pipe", Pipe # Crafting requires 1 iron plate
    IronChest = "iron-chest", Chest # Crafting requires 8 iron plates
    WoodenChest = "wooden-chest", Chest # Crafting requires 2 wood
    IronGearWheel = "iron-gear-wheel", Entity # Crafting requires 2 iron plate
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