# Changelog

All notable changes to the Factorio Learning Environment will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**ChatGPT subscription (Codex OAuth) support**

- New `codex/<model>` Inspect model provider: run evals against the ChatGPT
  Codex backend using a ChatGPT Plus/Pro subscription instead of an
  `OPENAI_API_KEY` (e.g. `fle inspect-eval --model codex/gpt-5.6-sol`).
- New `fle codex login|status|logout` command implementing the OAuth PKCE flow.
  Credentials are stored in `~/.fle/codex_auth.json`; an existing
  `~/.codex/auth.json` from the official Codex CLI is reused automatically.
- Access tokens are refreshed transparently. Because OpenAI rotates refresh
  tokens on use, rotated tokens are written back to the file they were loaded
  from, so borrowing the Codex CLI's credentials no longer logs it out.

### Fixed

- The Inspect solvers no longer send the OpenRouter-only `transforms`
  parameter to every provider. It was hardcoded in the throughput generation
  path, which made `GenerateConfig` raise `Unknown GenerateConfig field(s):
  transforms` for any non-OpenRouter model. The gate now tests the qualified
  model name (`str(model)`), since `Model.name` omits the provider prefix and
  could never match.

---

## [0.4.2] - 2026-03-27

### Added

**Comprehensive Lab Observation Test Coverage**

- Added extensive test coverage for lab entity observation in `get_entities()` API
- 2 new test functions (`test_get_lab` and `test_get_lab_edge_cases`) with 13 total permutations:
  - Empty labs (just placed)
  - Labs with science packs (no power)
  - Labs with power connected
  - Multiple labs
  - Labs in mixed entity queries
  - Labs with position/radius filtering
  - Labs with full/empty inventories
  - Labs queried immediately after placement
  - Labs at far distances

**Test Coverage Improvements**

- All 20 tests in `test_get_entities.py` now pass
- Validates that labs are fully observable on player's force in all scenarios
- Confirms force filtering works as designed (enemy/neutral labs not visible)

### Notes

This release adds regression tests to ensure lab entities remain observable through the `get_entities()` API. The comprehensive test suite covers edge cases and validates that the only scenario where labs don't appear is when on a different force (enemy/neutral), which is intentional security design.

---

## [0.4.1] - 2026-03-27

### Fixed

**Critical Direction System Hotfix**

This hotfix resolves direction-related test failures introduced in v0.4.0. The issue was caused by an incorrect divide-by-2 conversion that was added in PR #359.

- **Problem**: PR #359 added direction conversion logic assuming Python's Direction enum used values (0,2,4,6), but it actually uses Factorio 2.0's native values (0,4,8,12). This caused direction values to be incorrectly converted (e.g., LEFT=12 became 6=DOWNRIGHT).

- **Solution**: Removed all divide-by-2 conversion logic:
  - Simplified `serialize_direction_fix.lua` to pass through Factorio 2.0 values unchanged
  - Removed Python-side fallback in `controller.py` that was dividing directions by 2
  - Direction values now flow correctly: Factorio (0,4,8,12) → Python Direction enum (0,4,8,12)

- **Tests Fixed**:
  - All placement direction tests now pass (test_place_in_all_directions, test_place_offshore_pumps, test_place_burner_inserters, test_place_splitter)
  - All 9 rotation tests now pass (test_rotate.py)
  - Fixes ~20 direction-related test failures from v0.4.0

**Users should upgrade from v0.4.0 to v0.4.1 immediately** to get correct direction handling for entity placement and rotation.

---

## [0.4.0] - 2026-03-27

### 🎮 Factorio 2.0 Migration

This is a major release that migrates FLE from Factorio 1.1.110 to **Factorio 2.0.73**, addressing all breaking API changes and ensuring full compatibility with the latest version of Factorio. This release includes comprehensive updates across ~180 files with enhanced test coverage and improved reliability.

### Added

- **New Test Suites**
  - `tests/invariants/` — Entity lifecycle, status, fluid, and placement invariant tests
  - `tests/render/` — Pipe connections, splitters, vision render, viewport, assembler recipes, render ordering (62 tests)
  - `tests/entities/test_modules.py` — Module insertion and effect tests
  - `tests/actions/test_beacon.py` — Beacon entity tests
  - `tests/test_character_persistence.py` — Character state persistence tests

- **Improved RCON Reliability**
  - Automatic RCON reconnection (`ensure_connected()`) to prevent cascading test failures
  - Retry logic for transient `[processing]` RCON errors
  - Enhanced inventory error messages showing current contents

- **New Prototypes and Enums**
  - `Prototype.BulkInserter` — New Factorio 2.0 bulk inserter entity type
  - `Technology.SteamPower` and `Technology.AutomationSciencePack` — New tech tree entries for 2.0
  - Direction serialization conversion layer for Factorio 2.0 compatibility (#359)

### Changed

- **Docker Image**: Updated from `factoriotools/factorio:1.1.x` to `factoriotools/factorio:2.0.73`

- **Direction System**: Complete overhaul for Factorio 2.0's 16-direction system
  - `DirectionInternal` enum updated: `UP=0, RIGHT=4, DOWN=8, LEFT=12` (was 0,2,4,6 in 1.1)
  - Added Lua-side conversion layer to translate 16-dir values (0,4,8,12) to Python enum values (0,2,4,6)
  - Includes special inverse mapping for entities with reversed direction semantics (inserters, offshore-pumps)
  - Python-side fallback to handle any unconverted numeric direction values > 6
  - Updated all 13 entity renderers to handle new direction values

- **Inserter System Overhaul**
  - `filter-inserter` entity removed in 2.0; all inserters can now filter via `use_filters` flag
  - `stack-inserter` and `stack-filter-inserter` deprecated, replaced with `bulk-inserter`
  - `Prototype.FilterInserter` now maps to `fast-inserter` with filtering enabled
  - `Prototype.StackFilterInserter` now maps to `bulk-inserter`
  - Updated `game_types.py` and `groupable_entities.py` for new inserter types

- **Inventory API Changes**
  - `inventory.get_contents()` now returns array of `{name, count}` instead of dictionary
  - Updated `inspect_inventory`, `insert_item`, and `craft_item` to handle new format

- **Recipe Changes**
  - Barrel-filling recipes renamed: `fill-X-barrel` → `X-barrel` (7 recipes affected)
  - Updated `RecipeName` enum with new barrel recipe names

- **Prototype Access**
  - `game.xxx_prototypes` → `prototypes.xxx` (global namespace change)
  - Updated `get_prototype_recipe` and related functions

### Fixed

- **Lua API Migration** (Factorio 2.0 breaking changes)
  - `global.*` → `storage.*` across all ~50 Lua scripts
  - `game.table_to_json()` / `game.json_to_table()` → `helpers.table_to_json()` / `helpers.json_to_table()`
  - `force.item_production_statistics` → `force.get_item_production_statistics(surface)`
  - `force.set_saved_technology_progress()` → `tech.saved_progress = value`
  - `collision_mask` strings → `type`/`name` filters + layers dict
  - `event.created_entity` → `event.entity` (on_built_entity events)
  - Removed `electric_output_flow_limit` for solar panels (no longer exists in 2.0)

- **Test Infrastructure Improvements**
  - Added `clear_terrain` fixtures that replace water tiles with grass-1 to prevent placement failures
  - Added `move_to()` calls before entity placement where player would be >10 tiles away
  - Replaced hardcoded positions with `game.nearest(Resource.X)` for map-independent tests
  - Added `game.sleep()` calls for steam power system stabilization
  - Added delays before connecting fluid entities to prevent "source has no fluid" errors
  - Fixed `rotate_entity` to use destroy/recreate pattern for assemblers with fluid recipes

- **Research System**
  - Zero-ingredient "trigger" techs can no longer use `add_research()`, must set `.researched = true`
  - Updated technology research tests for 2.0 compatibility

- **Duplicate Dependencies** (#358 - @Mutdogus)
  - Removed 9 duplicate dependency entries from `pyproject.toml`
  - Fixed duplicates in both `[project.dependencies]` (5 packages) and `[project.optional-dependencies.cluster]` (4 packages)

- **AST Test Fixture** (#357 - @Mutdogus)
  - Fixed hardcoded `localhost:27000` in `test_ast_comprehensive.py` to use environment variables
  - Now respects `FACTORIO_HOST` and `FACTORIO_RCON_PORT` env vars with localhost:27000 fallback
  - Enables running AST tests against remote Factorio servers

- **Map Settings**
  - Added `asteroids` section for Space Age compatibility

### Breaking Changes

⚠️ **This release includes significant breaking changes for users upgrading from v0.3.x:**

1. **Factorio Version Requirement**
   - **Now requires Factorio 2.0.73 or later** (was 1.1.110)
   - Docker image updated to `factoriotools/factorio:2.0.73`

2. **Direction Values**
   - If you're working with raw direction values, they now use the 16-direction system (0,4,8,12 for N,E,S,W)
   - Most users won't be affected as the conversion layer handles this automatically
   - The Python `Direction` enum remains unchanged (UP=0, RIGHT=2, DOWN=4, LEFT=6)

3. **Inserter Types**
   - `Prototype.FilterInserter` now creates a `fast-inserter` with filtering enabled (not a dedicated filter-inserter entity)
   - `Prototype.StackFilterInserter` now maps to `bulk-inserter` (replaces stack-filter-inserter)
   - If you're checking entity types directly, update your code to use the new entity names

4. **Barrel Recipe Names**
   - Recipe names changed from `fill-crude-oil-barrel` to `crude-oil-barrel` format
   - Update any code that references barrel-filling recipes by name

5. **Inventory API**
   - `inventory.get_contents()` returns `[{name: string, count: int}]` instead of `{name: count}`
   - Update any code that processes inventory contents

### Migration Guide

#### For Users

If you're upgrading from FLE v0.3.x to v0.4.0:

1. **Update Factorio**: Install Factorio 2.0.73 or later from [factorio.com](https://www.factorio.com/)

2. **Update FLE**:
   ```bash
   pip install --upgrade factorio-learning-environment
   ```

3. **Docker Users**: The Docker image will automatically use `factoriotools/factorio:2.0.73`

4. **Code Changes**: Most agent code should work without changes due to the conversion layers. However, review your code if you:
   - Directly access direction values (use `Direction` enum instead)
   - Reference inserter entity types by name
   - Parse barrel recipe names
   - Process inventory contents from `get_contents()`

#### For Contributors

If you're developing against FLE:

1. **Test Suite**: All 385+ tests now pass with Factorio 2.0.73
   ```bash
   fle cluster start -n 4
   pytest -n 4 --dist=load -v
   ```

2. **Lua Changes**: All Lua code now uses `storage.*` instead of `global.*`

3. **New Test Suites**: Review `tests/invariants/` and `tests/render/` for new test patterns

### Test Coverage

- ✅ **205/205** tests passing in `tests/actions/`
- ✅ **83/83** tests passing in `tests/connect/`
- ✅ **62/62** tests passing in `tests/render/`
- ✅ **35/35** tests passing in `tests/functional/`
- ✅ All tests passing in `tests/entities/`, `tests/status/`, `tests/benchmarks/`, `tests/gym_env/`
- ✅ **Total: 385+ tests** with parallel execution support

### Community Contributions

Special thanks to [@Mutdogus](https://github.com/Mutdogus) for contributing:
- PR #357: AST test fixture environment variable support
- PR #358: Duplicate dependency cleanup
- PR #359: Direction serialization conversion layer

### Links

- **Full PR**: [#355 - Upgrade to Factorio 2.0](https://github.com/JackHopkins/factorio-learning-environment/pull/355)
- **Documentation**: [https://jackhopkins.github.io/factorio-learning-environment/](https://jackhopkins.github.io/factorio-learning-environment/)
- **Leaderboard**: [https://jackhopkins.github.io/factorio-learning-environment/leaderboard/](https://jackhopkins.github.io/factorio-learning-environment/leaderboard/)
- **Discord**: [#factorio-learning-env channel](https://discord.gg/zKaV2skewa)

---

## [0.3.1] - 2025-12-XX

### Changed
- Previous stable release with Factorio 1.1.110 support

---

## [0.3.0] - 2025-XX-XX

### Changed
- Initial public release with comprehensive test coverage

---

**Note**: For the complete history of changes, see the [GitHub releases page](https://github.com/JackHopkins/factorio-learning-environment/releases).
