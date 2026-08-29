"""Compact public API reference injected into model-facing task prompts."""

from __future__ import annotations

import hashlib

ACTION_PROFILE_REFERENCE_ID = "fle-program-v1/reference-v5"

ACTION_PROFILE_REFERENCE = """\
There are two tool boundaries. The harness calls `factorio_observe_factory`
directly when it needs a factory snapshot, and calls
`factorio_execute_program` directly to submit one program. Inside
`factorio_execute_program`, write ordinary short Python using the names
already loaded below. Calls made by that program are the programmatic action
composition path: they run synchronously in source order, can use normal
Python control flow, and together count as one environment intervention.
Do not try to emit MCP calls from the program.
Do not import FLE or use reflection (dir, type, getattr, private/dunder
attributes); host, file, and network access are unavailable.

Parallel-call semantics: a harness may issue requests concurrently, including
multiple requests for one lease, but envd serializes all operations for a
lease. Do not assume same-lease world mutations overlap or that completion
order is the submission order; use the returned event sequence. Independent
leases may run in parallel when capacity is available.

Core signatures and return values:
- inspect_inventory(entity=None) -> Inventory
- get_entities(entities=set(), position=None, radius=1000) -> list[Entity]
- nearest(Prototype.X or Resource.X) -> Position
    X must be one specific member. Bare Resource/Prototype classes and strings
    are invalid; use Resource.Coal, Resource.IronOre, Prototype.StoneFurnace, etc.
- move_to(position: Position) -> Position
- harvest_resource(position: Position, quantity=1) -> int
- get_prototype_recipe(Prototype.X or RecipeName.X) -> Recipe
- craft_item(Prototype.X, quantity=1) -> int
- can_place_entity(Prototype.X, direction=Direction.UP, position=Position(x, y)) -> bool
- place_entity(Prototype.X, direction=Direction.UP, position=Position(x, y), exact=True) -> Entity
- place_entity_next_to(Prototype.X, reference_position: Position, direction, spacing=0) -> Entity
- get_entity(Prototype.X, position: Position) -> Entity or None
- pickup_entity(entity: Entity) -> bool
- rotate_entity(entity: Entity, direction=Direction.UP) -> Entity
- insert_item(Prototype.X, target: Entity, quantity=5) -> Entity
- extract_item(Prototype.X, source: Entity or Position, quantity=5) -> int
- set_entity_recipe(entity: Entity, RecipeName.X) -> Entity
- connect_entities(source, target, Prototype.TransportBelt/Pipe/SmallElectricPole)
- get_resource_patch(Resource.X, position: Position, radius=30) -> ResourcePatch
- set_research(Technology.X), get_research_progress(Technology.X)
- wait(ticks, until=None, poll_ticks=300) -> dict
    Advances the live factory for up to `ticks`. Machines, belts, research,
    power, and deliveries continue normally. An optional inventory condition
    stops early, for example:
    wait(18000, until={'inventory': {'entity': furnace,
         'item': Prototype.StoneBrick, 'at_least': 100}})
    Returns requested/waited ticks, actual simulation ticks advanced, action
    ticks charged, condition_met, and the last observed value. Contract
    deadlines continue to apply while waiting.
- sleep(seconds), retained as a compatibility wrapper for short waits
- print(...) for measured feedback

Blueprint library (reusable factory fragments):
- blueprint('save', name='smelter', x=0, y=0, radius=32) -> dict
    Captures player-owned entities in the area around Position(x, y) and
    stores them under `name` for this episode (and later episodes when a
    persistent library is provisioned). radius=0 captures everything you own.
    Returns {'saved': name, 'entity_count': n, ...}.
- blueprint('place', source, x, y) -> dict
    Places a stored blueprint by its name, or an inline Factorio exchange
    string. Placement debits every required item from your character
    inventory up front (all-or-nothing: if anything is missing you get back
    {'error': 'missing_materials', 'missing': {...}} and nothing is built),
    then charges construction time on the task clock. Returns
    {'placed': count, 'items_consumed': {...}, ...}.
- blueprint('list') -> {'blueprints': [{'name', 'entity_count', ...}]}
- blueprint('get', name) -> {'name', 'content'}  # full exchange string
Prefer placing saved blueprints by name; reserve raw strings for novel
designs. Blueprints reuse designs, they do not create matter: stockpile the
materials a design needs before placing it.

RecipeName is the canonical recipe namespace. Use it for every recipe, including
RecipeName.IronGearWheel, RecipeName.AutomationSciencePack,
RecipeName.PlasticBar, RecipeName.BasicOilProcessing,
RecipeName.UraniumProcessing, and RecipeName.LightOilCracking. Prototype names
identify entities and items and are not accepted by set_entity_recipe.

Reference and recipe-name details:
- `get_prototype_recipe(Prototype.Lab)` is the normal way to inspect the
  lab's exact crafting recipe. `Prototype.Lab` names the placeable entity; it
  is not a valid argument to `set_entity_recipe`.
- `RecipeName.FillLubricantBarrel` maps to the Factorio recipe ID
  `lubricant-barrel`. The phrase `fill-lubricant-barrel` is a compatibility
  alias for reference lookup, not the ID emitted by the Factorio 2.0 export.
- `petroleum-gas` is a fluid product, not a unique recipe. Ask
  `factorio_search_reference` for petroleum-gas, then select one exact recipe
  ID such as `basic-oil-processing`, `advanced-oil-processing`,
  `coal-liquefaction`, or `light-oil-cracking` before planning or configuring
  a refinery or chemical plant.

Examples:
  coal_position = nearest(Resource.Coal)  # nearest returns a Position
  move_to(coal_position)
  harvest_resource(coal_position, 5)

  machine = place_entity(Prototype.AssemblingMachine1, position=Position(0, 0))
  machine = set_entity_recipe(machine, RecipeName.IronGearWheel)

  labs = get_entities({Prototype.Lab}, position=Position(0, 0), radius=20)
  if labs:
      insert_item(Prototype.AutomationSciencePack, labs[0], 1)

Names use CamelCase enums such as Prototype.IronPlate, Prototype.PumpJack,
Resource.IronOre, Technology.Automation, Direction.UP, and Position(x, y).
Inspect recipes, inventories, entities, status, and production before assuming
a plan worked. Re-fetch entities after the world changes because returned entity
objects can become stale. Entity values use attributes such as entity.name and
entity.position, not dictionary indexing; a Position has x and y only.

The character can normally act only within about 10 tiles. Call move_to(target)
before harvesting or placing at a distant target. Use the supplied starting
inventory before mining or crafting, and do not build production chains that
the stated objective does not require.
"""

ACTION_PROFILE_REFERENCE_SHA256 = hashlib.sha256(
    ACTION_PROFILE_REFERENCE.encode("utf-8")
).hexdigest()
