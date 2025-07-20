"""Constants for the rendering system."""

from typing import Dict, Final

# Direction mappings
DIRECTIONS: Final[Dict[int, str]] = {
    0: "north",
    2: "east", 
    4: "south",
    6: "west"
}

RELATIVE_DIRECTIONS: Final[Dict[int, str]] = {
    0: "up",
    2: "right",
    4: "down",
    6: "left"
}

# Direction constants
NORTH: Final[int] = 0
EAST: Final[int] = 2
SOUTH: Final[int] = 4
WEST: Final[int] = 6

VERTICAL: Final[list[int]] = [NORTH, SOUTH]
HORIZONTAL: Final[list[int]] = [EAST, WEST]

# Combinator operation mappings
COMBINATOR_TO_NORMAL: Final[Dict[str, str]] = {
    "+": "plus",
    "-": "minus",
    "*": "multiply",
    "/": "divide",
    "%": "modulo",
    "^": "power",
    "<<": "left_shift",
    ">>": "right_shift",
    "&": "and",
    "and": "and",
    "AND": "and",
    "|": "or",
    "or": "or",
    "OR": "or",
    "xor": "xor",
    "XOR": "xor",
    ">": "gt",
    "<": "lt",
    "=": "eq",
    "!=": "neq",
    "≠": "neq",
    ">=": "gte",
    "≥": "gte",
    "<=": "lte",
    "≤": "lte"
}

# Rendering constants
DEFAULT_SCALING: Final[int] = 32
GRID_LINE_WIDTH: Final[int] = 2
BACKGROUND_COLOR: Final[str] = '#282828'
GRID_COLOR: Final[str] = '#3c3c3c'

# Resource constants
DEFAULT_MAX_RESOURCE_AMOUNT: Final[int] = 10000
MIN_RESOURCE_VOLUME: Final[int] = 1
MAX_RESOURCE_VOLUME: Final[int] = 8
DEFAULT_RESOURCE_VARIANTS: Final[int] = 8
OIL_RESOURCE_VARIANTS: Final[int] = 4

# Tree constants
TREE_VARIATIONS: Final[list[str]] = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']
TREE_FOLIAGE_STATES: Final[list[str]] = ['full', 'medium', 'minimal', 'trunk_only']
TREE_FILES_PER_VARIATION: Final[int] = 5

# Renderer mappings
RENDERERS: Final[Dict[str, str]] = {
    "transport-belt": "transport-belt",
    "fast-transport-belt": "transport-belt",
    "express-transport-belt": "transport-belt",
    "underground-belt": "underground-belt",
    "fast-underground-belt": "underground-belt",
    "express-underground-belt": "underground-belt",
    "splitter": "splitter",
    "fast-splitter": "splitter",
    "express-splitter": "splitter",
    "pipe": "pipe",
    "pipe-to-ground": "pipe-to-ground",
    "stack-inserter": "inserter",
    "long-handed-inserter": "inserter",
    "fast-inserter": "inserter",
    "inserter": "inserter",
    "filter-inserter": "inserter",
    "stack-filter-inserter": "inserter",
    "burner-inserter": "inserter",
    "assembling-machine-1": "assembling-machine",
    "assembling-machine-2": "assembling-machine",
    "assembling-machine-3": "assembling-machine",
    "chemical-plant": "chemical-plant",
    "storage-tank": "storage-tank",
    "oil-refinery": "oil-refinery",
    "decider-combinator": "decider-combinator",
    "arithmetic-combinator": "arithmetic-combinator",
    "pump": "pump",
    "heat-pipe": "heat-pipe",
    "stone-wall": "stone-wall",
    "gate": "gate",
    "boiler": "boiler",
    "heat-exchanger": "heat-exchanger",
    "steam-engine": "steam-engine",
    "steam-turbine": "steam-turbine",
    "constant-combinator": "constant-combinator",
    "electric-mining-drill": "electric-mining-drill",
    "offshore-pump": "offshore-pump",
    "burner-mining-drill": "burner-mining-drill",
    "flamethrower-turret": "flamethrower-turret",
    "straight-rail": "straight-rail",
    "curved-rail": "curved-rail",
    "rail-signal": "rail-signal",
    "rail-chain-signal": "rail-signal",
    "tree-01": "tree",
    "tree-02": "tree",
    "tree-03": "tree",
    "tree-04": "tree",
    "tree-05": "tree",
    "tree-06": "tree",
    "tree-07": "tree",
    "tree-08": "tree",
    "tree-09": "tree",
    "dead-tree-desert": "tree",
    "dead-dry-hairy-tree": "tree",
    "dead-grey-trunk": "tree",
    "dry-hairy-tree": "tree",
    "dry-tree": "tree",
    #"lab": "lab"
}