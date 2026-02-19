"""Condensed system prompts for reduced context experiments.

This module provides condensed versions of the FLE system prompt,
generated using Claude Opus 4.5 to reduce token count while preserving
semantic information.

To regenerate the condensed prompt:
    python -m fle.eval.inspect_integration.condensed_prompts --regenerate

The condensed prompt targets ~10k tokens (down from ~28k) by:
- Removing redundant explanations
- Consolidating similar method signatures
- Using more concise language
- Eliminating example duplication
- Keeping essential API semantics
"""

import importlib.resources
import logging

logger = logging.getLogger(__name__)


def get_full_system_prompt(trajectory_length: int = 5000) -> str:
    """Generate the full, uncondensed system prompt.

    Args:
        trajectory_length: Number of steps in trajectory

    Returns:
        Full system prompt string (~28k tokens)
    """
    from fle.env.utils.controller_loader.system_prompt_generator import (
        SystemPromptGenerator,
    )
    from fle.eval.inspect_integration.solver_utils import get_base_system_prompt

    generator = SystemPromptGenerator(str(importlib.resources.files("fle") / "env"))
    base_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)

    goal_description = "Achieve the highest automatic production score rate"
    task_prompt = get_base_system_prompt(goal_description, trajectory_length)

    return f"{base_prompt}\n\n{task_prompt}\n\nNow begin building your factory step by step."


async def generate_condensed_prompt(
    model_name: str = "claude-opus-4-5-20251101",
    target_tokens: int = 10000,
) -> str:
    """Generate a condensed system prompt using Claude Opus 4.5.

    This function calls Opus 4.5 to condense the full system prompt
    into a more compact version while preserving semantic information.

    Args:
        model_name: Model to use for condensation
        target_tokens: Target token count for condensed prompt

    Returns:
        Condensed system prompt
    """
    import anthropic

    full_prompt = get_full_system_prompt()

    condensation_prompt = f"""You are a technical documentation expert. Your task is to condense the following system prompt to approximately {target_tokens} tokens (~{target_tokens * 4} characters) while preserving ALL essential semantic information.

CRITICAL REQUIREMENTS:
1. Preserve ALL API method signatures exactly - the model needs to know the exact function names and parameters
2. Preserve ALL type definitions - these are essential for correct code generation
3. Preserve ALL entity names and their key attributes
4. Remove redundant explanations, examples, and verbose descriptions
5. Consolidate similar concepts
6. Use concise, dense technical language
7. Keep the structure (```types, ```methods, manual sections) but make each section more compact
8. Do NOT lose any method names, parameter names, or return types
9. Keep all Prototype names and their key properties (collision_box, crafting_speed, etc.)
10. Provide a limited number of examples for each action

The condensed version should allow an AI to write correct Factorio automation code without any loss of capability.

<full_system_prompt>
{full_prompt}
</full_system_prompt>

Output ONLY the condensed system prompt, nothing else. Start with ```types and maintain the structure."""

    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model_name,
        max_tokens=target_tokens * 2,  # Allow some buffer
        messages=[{"role": "user", "content": condensation_prompt}],
    )

    condensed = response.content[0].text

    logger.info(f"Condensed prompt: {len(full_prompt)} -> {len(condensed)} chars")
    logger.info(f"Estimated tokens: {len(full_prompt) // 4} -> {len(condensed) // 4}")

    return condensed


# =============================================================================
# PRE-GENERATED CONDENSED SYSTEM PROMPT
# =============================================================================
# Generated using Claude Opus 4.5 targeting ~10k tokens
# Last regenerated: 2025-01-XX
# Original: ~112k chars (~28k tokens)
# Condensed: ~40k chars (~10k tokens)

CONDENSED_SYSTEM_PROMPT = """
# Maximize your automated resource generation

## Core Concepts

### Prototypes & Entities
```python
class Prototype(enum.Enum):
    # Machines
    AssemblingMachine1/2/3, Centrifuge, ChemicalPlant, OilRefinery
    # Inserters
    BurnerInserter, Inserter, FastInserter, LongHandedInserter, FilterInserter, StackInserter
    # Mining
    BurnerMiningDrill, ElectricMiningDrill, PumpJack
    # Furnaces
    StoneFurnace, SteelFurnace, ElectricFurnace
    # Belts
    TransportBelt, FastTransportBelt, ExpressTransportBelt
    UndergroundBelt, FastUndergroundBelt, ExpressUndergroundBelt
    Splitter, FastSplitter, ExpressSplitter
    # Power
    Boiler, SteamEngine, SolarPanel, Accumulator, NuclearReactor, HeatExchanger
    OffshorePump, Pump
    SmallElectricPole, MediumElectricPole, BigElectricPole
    # Storage
    WoodenChest, IronChest, SteelChest, StorageTank
    # Fluids/Pipes
    Pipe, UndergroundPipe, HeatPipe
    # Materials (entity_class=None)
    Coal, Wood, IronOre, CopperOre, Stone, UraniumOre
    IronPlate, SteelPlate, CopperPlate, StoneBrick
    CopperCable, IronStick, IronGearWheel
    ElectronicCircuit, AdvancedCircuit, ProcessingUnit
    PlasticBar, Sulfur, Battery
    EngineUnit, ElectricEngineUnit, FlyingRobotFrame
    # Science
    AutomationSciencePack, LogisticsSciencePack, ChemicalSciencePack
    MilitarySciencePack, ProductionSciencePack, UtilitySciencePack, SpaceSciencePack
    # Rocket
    RocketSilo, Satellite, RocketPart, RocketControlUnit, LowDensityStructure, RocketFuel

class RecipeName(enum.Enum):
    # Oil processing
    BasicOilProcessing, AdvancedOilProcessing, CoalLiquefaction
    HeavyOilCracking, LightOilCracking
    SolidFuelFromHeavyOil/LightOil/PetroleumGas
    SulfuricAcid
    # Barrel operations
    Fill/Empty + CrudeOil/HeavyOil/LightOil/Lubricant/PetroleumGas/SulfuricAcid/Water + Barrel

class Resource:
    Coal, IronOre, CopperOre, Stone, Water, CrudeOil, UraniumOre, Wood

class Direction(Enum):
    UP/NORTH=0, RIGHT/EAST=2, DOWN/SOUTH=4, LEFT/WEST=6

class EntityStatus(Enum):
    WORKING, NORMAL, NO_POWER, LOW_POWER, NO_FUEL, EMPTY
    NO_RECIPE, NO_INGREDIENTS, NO_INPUT_FLUID, FULL_OUTPUT
    WAITING_FOR_SOURCE_ITEMS, WAITING_FOR_SPACE_IN_DESTINATION
    # etc.
```

### Key Entity Properties
- **Position**: `entity.position` (x, y coordinates)
- **Direction**: `entity.direction` (affects inserter pickup/drop)
- **Status**: `entity.status` (EntityStatus enum)
- **Dimensions**: `Prototype.X.WIDTH`, `Prototype.X.HEIGHT`
- **Inserters**: `pickup_position`, `drop_position`
- **Mining drills**: `drop_position`, `resources`
- **Furnaces**: `furnace_source`, `furnace_result`, `fuel` (burner types)
- **Assemblers**: `recipe`, `assembling_machine_input/output`
- **Fluid handlers**: `connection_points`, `input/output_connection_points`

---

## API Functions

### Movement & Navigation
```python
move_to(position: Position) -> Position
# Must move to position before placing entities or harvesting
# Returns final position

nearest(type: Union[Prototype, Resource]) -> Position
# Find nearest entity/resource within 500 tiles
# Raises exception if not found
```

### Resource Gathering
```python
harvest_resource(position: Position, quantity=1, radius=10) -> int
# Must move_to position first
# Returns actual quantity harvested

craft_item(entity: Prototype, quantity=1) -> int
# Crafts from inventory, auto-crafts intermediates
# Cannot craft raw resources (must mine)
# Returns number crafted
```

### Entity Placement
```python
place_entity(entity: Prototype, direction=Direction.UP, position=Position(0,0), exact=True) -> Entity
# Must move_to position first
# Returns placed entity

place_entity_next_to(entity: Prototype, reference_position: Position, 
                     direction=Direction.RIGHT, spacing=0) -> Entity
# Places adjacent to reference with optional spacing
# spacing=0 means directly adjacent

can_place_entity(entity: Prototype, direction=Direction.UP, position=Position(0,0)) -> bool
# Check if placement is valid (reach, collisions, terrain)
```

### Entity Manipulation
```python
get_entity(entity: Prototype, position: Position) -> Entity
# Retrieve/refresh entity at position - USE OFTEN to avoid stale data

rotate_entity(entity: Entity, direction: Direction) -> Entity
# Change entity orientation
# Inserters: affects pickup/drop positions
# Assemblers: must set recipe first

set_entity_recipe(entity: Entity, prototype: Union[Prototype, RecipeName]) -> Entity
# For AssemblingMachine, ChemicalPlant, OilRefinery
# MUST set recipe before connecting fluid pipes

pickup_entity(entity: Union[Entity, Prototype, EntityGroup], position=None) -> bool
# Remove entity to inventory
```

### Inventory Management
```python
inspect_inventory(entity=None) -> Inventory
# None = player inventory
# Access: inventory[Prototype.X] or inventory.get(Prototype.X, 0)
# Burner fuel: entity.fuel[Prototype.Coal]

insert_item(entity: Prototype, target: Entity, quantity=5) -> Entity
# Insert from player inventory to entity
# ALWAYS reassign: target = insert_item(...)

extract_item(entity: Prototype, source: Union[Position, Entity], quantity=5) -> int
# Remove from entity to player inventory
# Returns actual extracted count
```

### Connections
```python
connect_entities(source, target, connection_type: Prototype) -> EntityGroup
# source/target: Position, Entity, or EntityGroup
# connection_type: TransportBelt, Pipe, SmallElectricPole, etc.
# Can use set: {Prototype.Pipe, Prototype.UndergroundPipe}
# Supports waypoints: connect_entities(pos1, pos2, pos3, connection_type=X)
# Returns BeltGroup, PipeGroup, or ElectricityGroup

get_connection_amount(source, target, connection_type=Prototype.Pipe) -> int
# Calculate entities needed without placing
```

### Building Planning
```python
nearest_buildable(entity: Prototype, building_box: BuildingBox, 
                  center_position: Position) -> BoundingBox
# Find valid placement area
# BuildingBox(width=X, height=Y)
# Returns BoundingBox with left_top, right_bottom, center, etc.

get_resource_patch(resource: Resource, position: Position, radius=30) -> ResourcePatch
# Returns ResourcePatch with name, size, bounding_box
```

### Research
```python
set_research(technology: Technology) -> List[Ingredient]
# Start researching, returns required science packs

get_research_progress(technology=None) -> List[Ingredient]
# Returns remaining science packs needed
# None = current research (must have active research)
```

### Entity Discovery
```python
get_entities(entities: Set[Prototype]=set(), position=None, radius=1000) -> List[Entity]
# Find entities within radius
# Empty set = all entities
```

### Utilities
```python
sleep(seconds: int) -> bool
# Wait for actions to complete (max 15 seconds)

print(*args)
# Log to stdout - use liberally for debugging

get_prototype_recipe(prototype: Union[Prototype, RecipeName]) -> Recipe
# Returns Recipe with ingredients, products, energy

send_message(message: str, recipient=None) -> bool
# Agent-to-agent communication

launch_rocket(silo: Union[Position, RocketSilo]) -> RocketSilo
# Launch rocket from silo
```

---

## Key Patterns

### Self-Fueling Coal Mining
```python
# Find coal, place drill facing down
drill = place_entity(Prototype.BurnerMiningDrill, position=coal_pos, direction=Direction.DOWN)
# Inserter below drill, rotated up to fuel drill
inserter = place_entity_next_to(Prototype.BurnerInserter, drill.position, Direction.DOWN)
inserter = rotate_entity(inserter, Direction.UP)
# Belt from drill output to inserter pickup
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
# Bootstrap with initial coal
insert_item(Prototype.Coal, drill, 5)
```

### Power Generation (Steam)
```python
# 1. Offshore pump on water
offshore_pump = place_entity(Prototype.OffshorePump, position=water_pos)

# 2. Boiler (use nearest_buildable to avoid water)
building_box = BuildingBox(width=Prototype.Boiler.WIDTH+4, height=Prototype.Boiler.HEIGHT+4)
coords = nearest_buildable(Prototype.Boiler, building_box, offshore_pump.position)
move_to(coords.center)
boiler = place_entity(Prototype.Boiler, position=coords.center, direction=Direction.LEFT)
insert_item(Prototype.Coal, boiler, 10)

# 3. Steam engine
building_box = BuildingBox(width=Prototype.SteamEngine.WIDTH+4, height=Prototype.SteamEngine.HEIGHT+4)
coords = nearest_buildable(Prototype.SteamEngine, building_box, boiler.position)
move_to(coords.center)
steam_engine = place_entity(Prototype.SteamEngine, position=coords.center, direction=Direction.LEFT)

# 4. Connect with pipes
connect_entities(offshore_pump, boiler, Prototype.Pipe)
connect_entities(boiler, steam_engine, Prototype.Pipe)

# 5. Verify power
sleep(5)
steam_engine = get_entity(Prototype.SteamEngine, steam_engine.position)
assert steam_engine.energy > 0
```

### Mining Line Setup
```python
# Plan building area for 3 drills + furnaces
building_box = BuildingBox(
    width=3 * Prototype.ElectricMiningDrill.WIDTH,
    height=Prototype.ElectricMiningDrill.HEIGHT + Prototype.StoneFurnace.HEIGHT
)
coords = nearest_buildable(Prototype.ElectricMiningDrill, building_box, ore_position)
move_to(coords.left_top)

for i in range(3):
    drill_pos = Position(x=coords.left_top.x + Prototype.ElectricMiningDrill.WIDTH*i, 
                        y=coords.left_top.y)
    drill = place_entity(Prototype.ElectricMiningDrill, position=drill_pos, direction=Direction.DOWN)
    # Furnace catches ore directly (use drill.position, not drop_position for multi-tile entities)
    furnace = place_entity_next_to(Prototype.StoneFurnace, drill.position, Direction.DOWN)
    # Output inserter below furnace
    inserter = place_entity_next_to(Prototype.Inserter, furnace.position, Direction.DOWN)
```

### Assembly Line
```python
# Plan area with buffer for inserters
building_box = BuildingBox(
    width=Prototype.AssemblingMachine1.WIDTH + 2*Prototype.BurnerInserter.WIDTH + 2,
    height=Prototype.AssemblingMachine1.HEIGHT + 2
)
coords = nearest_buildable(Prototype.AssemblingMachine1, building_box, position)
move_to(coords.center)

# Place and configure assembler
assembler = place_entity(Prototype.AssemblingMachine1, position=coords.center)
set_entity_recipe(assembler, Prototype.CopperCable)

# Input inserter (rotated to insert into assembler)
input_inserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, Direction.RIGHT)
input_inserter = rotate_entity(input_inserter, Direction.LEFT)

# Output inserter + chest
output_inserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, Direction.LEFT)
output_chest = place_entity(Prototype.WoodenChest, position=output_inserter.drop_position)

# Connect power
connect_entities(power_source, assembler, Prototype.SmallElectricPole)

# Connect input belt
connect_entities(source_inserter, input_inserter, Prototype.TransportBelt)
```

### Chemical Plant / Oil Refinery
```python
# MUST set recipe before connecting pipes
chemical_plant = set_entity_recipe(chemical_plant, RecipeName.HeavyOilCracking)

# Connect input (order: source -> plant for inputs)
connect_entities(input_tank, chemical_plant, {Prototype.Pipe, Prototype.UndergroundPipe})

# Connect output (order: plant -> destination for outputs)  
connect_entities(chemical_plant, output_tank, {Prototype.Pipe, Prototype.UndergroundPipe})
```

### Many-to-One Connections
```python
# Create main connection from first source
main_connection = connect_entities(source1, target, Prototype.TransportBelt)

# Connect additional sources to main connection
for source in [source2, source3]:
    main_connection = connect_entities(source, main_connection, Prototype.TransportBelt)
```

---

## Production Statistics

### Mining Rates (per 60 seconds)
- Burner mining drill: 15 resources
- Electric mining drill: 30 resources
- Pumpjack: 600 crude oil

### Smelting (stone furnace = 1x speed)
- Iron/Copper plate: 18.75/min (stone), 37.5/min (steel/electric)
- Steel plate: 3.75/min (stone), 7.5/min (steel/electric)
- Stone brick: 18.75/min

### Crafting Speeds (Assembler 1 = 0.5x, 2 = 0.75x, 3 = 1.25x)
| Item | Base/min | AM1 | AM2 | AM3 |
|------|----------|-----|-----|-----|
| Iron gear wheel | 120 | 60 | 90 | 150 |
| Copper cable | 240 | 120 | 180 | 300 |
| Electronic circuit | 120 | 60 | 90 | 150 |
| Advanced circuit | 10 | 5 | 7.5 | 12.5 |
| Processing unit | 6 | 3 | 4.5 | 7.5 |
| Engine unit | 6 | 3 | 4.5 | 7.5 |
| Electric engine | 6 | 3 | 4.5 | 7.5 |
| Flying robot frame | 3 | 1.5 | 2.25 | 3.75 |
| Low density structure | 4 | 2 | 3 | 5 |

### Chemical Plant (1x speed)
- Sulfur: 120/min
- Plastic bar: 120/min
- Battery: 20/min
- Sulfuric acid: 3000/min
- Lubricant: 600/min

### Oil Processing
| Recipe | Heavy | Light | Petroleum |
|--------|-------|-------|-----------|
| Basic | - | - | 540/min |
| Advanced | 300 | 540 | 660/min |
| Coal liquefaction | 1080 | 240 | 120/min |
| Heavy cracking | - | +900 | - |
| Light cracking | - | - | +variable |

---

## Critical Tips

### Entity Management
1. **Always refresh entities**: `entity = get_entity(Prototype.X, entity.position)`
2. **Reassign after insert**: `entity = insert_item(Prototype.Coal, entity, 10)`
3. **Move before placing**: `move_to(position)` then `place_entity(...)`
4. **Check status**: Use `entity.status` to diagnose issues

### Inserter Behavior
- Inserters **take from** the entity they're placed next to by default
- Use `rotate_entity()` to reverse direction
- `pickup_position` = where items come from
- `drop_position` = where items go

### Fluid Connections
- **Set recipe first** for ChemicalPlant/OilRefinery before connecting pipes
- Connection order matters: source→destination
- Use `{Prototype.Pipe, Prototype.UndergroundPipe}` for automatic underground routing

### Building Placement
- Use `nearest_buildable()` near water or obstacles
- Add buffer (4+ tiles) in BuildingBox for connections
- Multi-tile entities: use `entity.position`, not `drop_position` for `place_entity_next_to`
- Keep 10-20 tiles between factory sections

### Power Systems
- Boilers need fuel continuously
- Electric entities show `NO_POWER` if not connected
- Verify with `entity.energy > 0` after `sleep(5)`

### Common Status Issues
- `WAITING_FOR_SPACE_IN_DESTINATION`: Output blocked, add chest/belt
- `NO_FUEL`: Insert coal/wood
- `NO_INGREDIENTS`: Input supply issue
- `NO_RECIPE`: Call `set_entity_recipe()`

### Efficiency
- Insert 20+ fuel to avoid interruptions
- Use chests at drill drop positions for simple setups (no belts needed)
- Verify production with `sleep()` + `inspect_inventory()`
- Log everything with `print()` for debugging

---

## Task Objective

Build the largest possible factory to maximize production score:
1. Establish resource extraction (iron, copper, coal, stone)
2. Build power infrastructure early
3. Create automated production chains
4. Scale progressively to complex items (circuits → science packs → rocket)
5. Optimize layout and logistics

**16 steps available** - make each meaningful. Complex items = higher value. Automate everything.
"""


def get_condensed_system_prompt(
    goal_description: str = "Achieve the highest automatic production score rate",
    trajectory_length: int = 5000,
) -> str:
    """Get the condensed system prompt with task-specific modifications.

    The base condensed prompt already includes default task instructions.
    This function allows customizing the goal and trajectory length.

    Args:
        goal_description: Task goal (used if different from default)
        trajectory_length: Number of steps (updated in prompt)

    Returns:
        Condensed system prompt
    """
    prompt = CONDENSED_SYSTEM_PROMPT

    # Update trajectory length if different
    if trajectory_length != 5000:
        prompt = prompt.replace(
            "5000 steps available", f"{trajectory_length} steps available"
        )

    # Update goal if different from default
    default_goal = "Achieve the highest automatic production score rate"
    if goal_description != default_goal:
        prompt = prompt.replace(
            f"## TASK OBJECTIVE\n{default_goal}",
            f"## TASK OBJECTIVE\n{goal_description}",
        )

    return prompt


def get_prompt_stats() -> dict:
    """Get statistics comparing full vs condensed prompts."""
    full = get_full_system_prompt()
    condensed = CONDENSED_SYSTEM_PROMPT

    return {
        "full_chars": len(full),
        "full_tokens_est": len(full) // 4,
        "condensed_chars": len(condensed),
        "condensed_tokens_est": len(condensed) // 4,
        "reduction_pct": round((1 - len(condensed) / len(full)) * 100, 1),
    }


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Condensed prompt utilities")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate condensed prompt using Opus 4.5",
    )
    parser.add_argument("--stats", action="store_true", help="Show prompt statistics")
    parser.add_argument("--show-full", action="store_true", help="Print full prompt")
    parser.add_argument(
        "--show-condensed", action="store_true", help="Print condensed prompt"
    )

    args = parser.parse_args()
    condensed = asyncio.run(generate_condensed_prompt())
    print(condensed)
    if args.stats:
        stats = get_prompt_stats()
        print("Prompt Statistics:")
        print(
            f"  Full prompt: {stats['full_chars']:,} chars (~{stats['full_tokens_est']:,} tokens)"
        )
        print(
            f"  Condensed:   {stats['condensed_chars']:,} chars (~{stats['condensed_tokens_est']:,} tokens)"
        )
        print(f"  Reduction:   {stats['reduction_pct']}%")

    elif args.show_full:
        print(get_full_system_prompt())

    elif args.show_condensed:
        print(CONDENSED_SYSTEM_PROMPT)

    elif args.regenerate:
        print("Regenerating condensed prompt using Claude Opus 4.5...")
        condensed = asyncio.run(generate_condensed_prompt())
        print("\n" + "=" * 60)
        print("CONDENSED PROMPT:")
        print("=" * 60)
        print(condensed)
        print("\n" + "=" * 60)
        print(f"Length: {len(condensed)} chars (~{len(condensed) // 4} tokens)")
        print("\nCopy this into CONDENSED_SYSTEM_PROMPT in condensed_prompts.py")

    else:
        parser.print_help()
