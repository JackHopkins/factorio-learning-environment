# Controllers Directory

This directory contains controller classes that handle different actions and interactions within the Factorio environment.

They are loaded in dynamically when Factorio Instance starts.
## Core Controllers
- `_controller.py` - Base controller class with common functionality
- `_action.py` - Base class for agent-specific controllers
- `_init.py` - Initialization controller

## Entity Management
- `get_entity.py`, `get_entities.py` - Retrieve entity information
- `place_entity.py`, `place_entity_next_to.py` - Place entities in the world
- `connect_entities.py` - Connect entities like belts, pipes etc.
- `rotate_entity.py` - Change entity orientation
- `clear_entities.py` - Remove entities
- `set_entity_recipe.py` - Configure entity recipes

## Resource Management
- `get_resource_patch.py` - Find resource deposits
- `harvest_resource.py` - Extract resources
- `regenerate_resources.py` - Replenish resources
- `_inspect_resources.py` - Analyze resource locations and quantities

## Inventory & Items
- `inspect_inventory.py` - Check inventory contents
- `insert_item.py` - Put items into entities
- `extract_item.py` - Take items from entities
- `pickup_entity.py` - Pick up placed entities
- `craft_item.py` - Create new items

## Navigation & Pathfinding
- `get_path.py`, `request_path.py` - Calculate paths between points
- `move_to.py` - Move player character
- `nearest.py`, `nearest_buildable.py` - Find closest entities

## Observation & Analysis
- `observe_all.py` - Get comprehensive world state
- `inspect_entities.py` - Analyze specific entities
- `production_stats.py` - Track production metrics
- `score.py` - Calculate performance scores

## Blueprint Management
- `_load_blueprint.py`, `_save_blueprint.py` - Handle blueprint strings

## Utility
- `print.py` - Output formatted information
- `sleep.py` - Add delays between actions
- `can_place_entity.py` - Check if placement is valid

Each controller follows a consistent pattern of inheriting from either `_controller.py` or `_action.py` base classes and implements specific functionality for interacting with the Factorio environment through the RCON interface.