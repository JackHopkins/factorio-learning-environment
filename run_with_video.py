#!/usr/bin/env python
"""
Run FLE eval with claude-sonnet-4-6 and produce real benchmark screenshots + MP4.

Flow:
1) Run agent loop and save game state after each step.
2) Optionally render step screenshots live while the run is in progress.
3) Copy all saves from the selected Factorio container.
4) Invoke render_saves.py once for catch-up rendering + video generation.
"""

import os
import sys
import time
import json
import re
import shutil
import asyncio
import subprocess
import tempfile
import importlib.resources
import zipfile
from uuid import uuid4
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("FACTORIO_SERVER_ADDRESS", "127.0.0.1")
os.environ.setdefault("FACTORIO_SERVER_PORT", "41000")

import gym

from fle.agents.gym_agent import GymAgent
from fle.commons.db_client import create_db_client, get_next_version
from fle.eval.tasks import TaskFactory
from fle.eval.algorithms.independent.trajectory_runner import GymTrajectoryRunner
from fle.eval.algorithms.independent.config import GymEvalConfig
from fle.env.gym_env.registry import get_environment_info
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.utils.controller_loader.system_prompt_generator import SystemPromptGenerator


# ---------- CONFIG ----------
MODEL = "claude-sonnet-4-6"
ENV_ID = os.getenv("ENV_ID", "automation_science_pack_throughput").strip()
if not ENV_ID:
    sys.exit("ERROR: ENV_ID must be non-empty")



def _env_int(name: str, default: int, minimum: int = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        sys.exit(f"ERROR: {name} must be an integer (got '{raw}')")
    if minimum is not None and value < minimum:
        sys.exit(f"ERROR: {name} must be >= {minimum} (got {value})")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "1" if default else "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    sys.exit(f"ERROR: {name} must be a boolean (got '{raw}')")


def _env_optional_int(name: str, minimum: int = None) -> Optional[int]:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return None
    try:
        value = int(raw)
    except ValueError:
        sys.exit(f"ERROR: {name} must be an integer when set (got '{raw}')")
    if minimum is not None and value < minimum:
        sys.exit(f"ERROR: {name} must be >= {minimum} (got {value})")
    return value


MAX_STEPS = _env_int("MAX_STEPS", 30, minimum=1)
SCREENSHOT_BASE = Path(".fle/run_screenshots")
SAVES_DIR = Path("/tmp/fle-run-saves")
FACTORIO_BINARY = Path("/tmp/factorio/bin/x64/factorio")
FACTORIO_DATA = Path("/tmp/factorio/data")
FLE_INCLUDE_ENTITIES = _env_bool("FLE_INCLUDE_ENTITIES", default=False)

PROMPT_MODES = {"default", "orchestrator", "build"}
FLE_PROMPT_MODE = os.getenv("FLE_PROMPT_MODE", "default").strip().lower()
if FLE_PROMPT_MODE not in PROMPT_MODES:
    sys.exit(
        f"ERROR: FLE_PROMPT_MODE must be one of {sorted(PROMPT_MODES)} "
        f"(got '{FLE_PROMPT_MODE}')"
    )

FLE_BUILD_MODE_RESET_CONTEXT = _env_bool("FLE_BUILD_MODE_RESET_CONTEXT", default=True)
FLE_BUILD_RETURN_RESET_CONTEXT = _env_bool("FLE_BUILD_RETURN_RESET_CONTEXT", default=False)
FLE_BUILD_MODULE_TARGET = os.getenv("FLE_BUILD_MODULE_TARGET", "UNSPECIFIED").strip()
FLE_BUILD_MODULE_ZONE = os.getenv("FLE_BUILD_MODULE_ZONE", "UNSPECIFIED").strip()
FLE_BUILD_MODULE_OUTPUT = os.getenv("FLE_BUILD_MODULE_OUTPUT", "UNSPECIFIED").strip()
FLE_MODULE_REGISTRY_FILE = os.getenv("FLE_MODULE_REGISTRY_FILE", "").strip()
FLE_MODULE_REGISTRY_TEXT = os.getenv("FLE_MODULE_REGISTRY_TEXT", "").strip()
FLE_ENABLE_COMMAND_MODE_SWITCH = _env_bool("FLE_ENABLE_COMMAND_MODE_SWITCH", default=True)

SCREENSHOT_BACKEND = os.getenv("SCREENSHOT_BACKEND", "benchmark").strip().lower()
if SCREENSHOT_BACKEND != "benchmark":
    sys.exit(
        "ERROR: run_with_video.py only supports SCREENSHOT_BACKEND=benchmark. "
        "Use run_video_reliable.sh for the supported workflow."
    )

CATCHUP_RENDER_PARALLEL = _env_int("CATCHUP_RENDER_PARALLEL", 1, minimum=1)
CATCHUP_RENDER_TIMEOUT = _env_int("CATCHUP_RENDER_TIMEOUT", 900, minimum=1)
CATCHUP_RENDER_RETRIES = _env_int("CATCHUP_RENDER_RETRIES", 1, minimum=0)
CATCHUP_RENDER_TICKS = _env_int("CATCHUP_RENDER_TICKS", 60, minimum=1)
CATCHUP_PHASE_TIMEOUT = _env_int("CATCHUP_PHASE_TIMEOUT", 14400, minimum=1)
LIVE_RENDER_PARALLEL = _env_int("LIVE_RENDER_PARALLEL", 1, minimum=0)
LIVE_RENDER_TIMEOUT = _env_int(
    "LIVE_RENDER_TIMEOUT", CATCHUP_RENDER_TIMEOUT, minimum=1
)
LIVE_RENDER_RETRIES = _env_int(
    "LIVE_RENDER_RETRIES", CATCHUP_RENDER_RETRIES, minimum=0
)
LIVE_RENDER_TICKS = _env_int("LIVE_RENDER_TICKS", CATCHUP_RENDER_TICKS, minimum=1)

DEFAULT_STARTER_INVENTORY_SPEC = (
    "transport-belt=500,"
    "medium-electric-pole=500,"
    "pipe=500,"
    "coal=500,"
    "underground-belt=100,"
    "pipe-to-ground=100,"
    "burner-inserter=50,"
    "inserter=50,"
    "burner-mining-drill=50,"
    "electric-mining-drill=50,"
    "wooden-chest=10,"
    "storage-tank=10,"
    "pumpjack=10,"
    "stone-furnace=10,"
    "electric-furnace=10,"
    "assembling-machine-2=10,"
    "oil-refinery=5,"
    "chemical-plant=5,"
    "boiler=2,"
    "steam-engine=2,"
    "offshore-pump=2"
)
FLE_ENSURE_STARTER_INVENTORY = _env_bool("FLE_ENSURE_STARTER_INVENTORY", default=True)
FLE_STARTER_INVENTORY_SPEC = os.getenv(
    "FLE_STARTER_INVENTORY_SPEC", DEFAULT_STARTER_INVENTORY_SPEC
).strip()

WORLD_PROFILE = os.getenv("WORLD_PROFILE", "open_world").strip()
if WORLD_PROFILE not in {"open_world", "default_lab_scenario"}:
    sys.exit(
        "ERROR: WORLD_PROFILE must be one of: open_world, default_lab_scenario"
    )

_WORLD_PROFILE_DEFAULT_RESOURCES = {
    "open_world": "iron-ore,copper-ore,coal,stone,crude-oil",
    "default_lab_scenario": "iron-ore,copper-ore,coal,stone",
}
WORLD_RESOURCE_RADIUS = _env_int("WORLD_RESOURCE_RADIUS", 600, minimum=1)
WORLD_WATER_RADIUS = _env_int("WORLD_WATER_RADIUS", 1200, minimum=1)
WORLD_REQUIRED_RESOURCES = tuple(
    resource.strip()
    for resource in os.getenv(
        "WORLD_REQUIRED_RESOURCES",
        _WORLD_PROFILE_DEFAULT_RESOURCES[WORLD_PROFILE],
    ).split(",")
    if resource.strip()
)
SKIP_WORLD_CHECK = os.getenv("SKIP_WORLD_CHECK", "0") == "1"
# ----------------------------



DEFAULT_MODULE_REGISTRY = """existing_modules: []
"""

_SCREENSHOT_MOD_INFO = """{
  "name": "fle_screenshot",
  "version": "1.0.0",
  "title": "FLE Screenshot Renderer",
  "author": "FLE",
  "factorio_version": "1.1"
}"""

_SCREENSHOT_MOD_CONTROL = r"""
local EX = {
    ["character"] = true,
    ["entity-ghost"] = true,
    ["tile-ghost"] = true,
    ["electric-energy-interface"] = true,
    ["resource"] = true,
}

local function take_factory_screenshot()
    local s = game.surfaces[1]
    local raw = s.find_entities_filtered{force = "player"}
    local es = {}
    for _, e in pairs(raw) do
        if not EX[e.type] then es[#es + 1] = e end
    end

    local cx, cy, zoom = 0, 0, 0.5
    if #es > 0 then
        local xs, ys = {}, {}
        for _, e in pairs(es) do
            xs[#xs + 1] = e.position.x
            ys[#ys + 1] = e.position.y
        end
        table.sort(xs)
        table.sort(ys)
        local mid = math.floor(#xs / 2) + 1
        local mx, my = xs[mid], ys[mid]

        local da, db = {}, {}
        for i, x in ipairs(xs) do da[i] = math.abs(x - mx) end
        for i, y in ipairs(ys) do db[i] = math.abs(y - my) end
        table.sort(da)
        table.sort(db)
        local ma = math.max(da[mid], 5)
        local mb = math.max(db[mid], 5)
        local tx, ty = ma * 5, mb * 5

        local nb = {}
        for _, e in pairs(es) do
            if math.abs(e.position.x - mx) <= tx and math.abs(e.position.y - my) <= ty then
                nb[#nb + 1] = e
            end
        end
        if #nb == 0 then nb = es end

        local x1, y1, x2, y2 = math.huge, math.huge, -math.huge, -math.huge
        for _, e in pairs(nb) do
            local b = e.bounding_box
            if b.left_top.x < x1 then x1 = b.left_top.x end
            if b.left_top.y < y1 then y1 = b.left_top.y end
            if b.right_bottom.x > x2 then x2 = b.right_bottom.x end
            if b.right_bottom.y > y2 then y2 = b.right_bottom.y end
        end
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        local w = x2 - x1 + 6
        local h = y2 - y1 + 6
        zoom = math.min(1920 / (w * 32), 1080 / (h * 32), 2)
        zoom = math.max(zoom, 0.125)
    end

    game.forces["player"].chart(s, {{cx - 200, cy - 200}, {cx + 200, cy + 200}})
    s.always_day = true
    s.daytime = 0
    s.freeze_daytime = true
    rendering.clear()

    game.take_screenshot{
        surface = s,
        position = {cx, cy},
        resolution = {1920, 1080},
        zoom = zoom,
        path = "factory.png",
        show_entity_info = true,
        show_gui = false,
        force_render = true,
    }
end

local function capture_once()
    local ok, err = pcall(take_factory_screenshot)
    log("FLE_SCREENSHOT config_changed ok=" .. tostring(ok) .. " err=" .. tostring(err))
end

script.on_configuration_changed(capture_once)
"""


def _is_valid_save_zip(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0 and zipfile.is_zipfile(path)


def _copy_server_mods_to_dir(container: str, mods_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["docker", "cp", f"{container}:/opt/factorio/mods/.", str(mods_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        print(f"  Warning: failed to copy server mods ({exc})")
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            detail = detail[-200:]
            print(f"  Warning: failed to copy server mods ({detail})")
        else:
            print("  Warning: failed to copy server mods")
        return False
    return True


def _load_module_registry_text() -> str:
    if FLE_MODULE_REGISTRY_TEXT:
        return FLE_MODULE_REGISTRY_TEXT.replace("\\n", "\n")
    if FLE_MODULE_REGISTRY_FILE:
        path = Path(FLE_MODULE_REGISTRY_FILE)
        if not path.is_file():
            sys.exit(
                f"ERROR: FLE_MODULE_REGISTRY_FILE does not exist: {path}"
            )
        return path.read_text()
    return DEFAULT_MODULE_REGISTRY


def _orchestrator_overlay(module_registry_text: str) -> str:
    return (
        "## Orchestrator Operating Mode (Fix + Connect + Delegate)\n"
        "Primary role:\n"
        "- You are the factory orchestrator.\n"
        "- You should mainly fix broken flows, connect modules, route power/belts/pipes, and keep production stable.\n\n"
        "Direct build policy:\n"
        "- You may directly build when you judge it is useful, except mining operations.\n"
        "- There is no hard cap for direct builds right now; decide pragmatically.\n\n"
        "When to delegate to build mode:\n"
        "- Delegate for reusable/scalable module construction.\n"
        "- Delegate when strict zone/interface contracts are required.\n"
        "- Delegate when local module work should be isolated from global planning.\n\n"
        "## Build-Mode Tool Contract (Authoritative)\n"
        "Control channel is JSON-only.\n\n"
        "Role ownership (strict):\n"
        "- Orchestrator mode may emit only BUILD_MODE_REQUEST.\n"
        "- Build mode may emit only BUILD_MODE_DONE or BUILD_MODE_GIVE_UP.\n"
        "- Orchestrator must never emit BUILD_MODE_DONE or BUILD_MODE_GIVE_UP.\n"
        "- Build mode must never emit BUILD_MODE_REQUEST.\n\n"
        "Delegation call format (current runtime):\n"
        "- For a delegation step, output exactly one JSON object.\n"
        "- Do not output Python, comments, markdown fences, or extra text in that step.\n"
        "- The JSON object must match the BUILD_MODE_REQUEST schema below.\n"
        "- A delegation step is control-plane only and performs no world action.\n\n"
        "Canonical BUILD_MODE_REQUEST schema (all keys required):\n"
        "```json\n"
        "{\n"
        "  \"version\": 1,\n"
        "  \"request_type\": \"BUILD_MODE_REQUEST\",\n"
        "  \"request_id\": \"string\",\n"
        "  \"module_type\": \"iron_mine_electric | smelter_coal\",\n"
        "  \"zone\": {\"x_min\": number, \"x_max\": number, \"y_min\": number, \"y_max\": number},\n"
        "  \"interfaces\": {\n"
        "    \"inputs\": [\n"
        "      {\n"
        "        \"name\": \"string\",\n"
        "        \"required\": boolean,\n"
        "        \"item\": \"string\",\n"
        "        \"position\": {\"x\": number, \"y\": number},\n"
        "        \"interface_type\": \"belt_handoff | drill_output | chest_handoff\",\n"
        "        \"belt_direction_into_zone\": \"north | east | south | west\",\n"
        "        \"lane_side\": \"left | right | both\"\n"
      "      }\n"
        "    ],\n"
        "    \"outputs\": [\n"
        "      {\n"
        "        \"name\": \"string\",\n"
        "        \"required\": boolean,\n"
        "        \"item\": \"string\",\n"
        "        \"position\": {\"x\": number, \"y\": number},\n"
        "        \"output_type\": \"belt | chest\",\n"
        "        \"belt_direction\": \"north | east | south | west\",\n"
        "        \"lane_side\": \"left | right | both\"\n"
        "      }\n"
        "    ]\n"
        "  },\n"
        "  \"power\": {\n"
        "    \"required\": boolean,\n"
        "    \"anchors\": [\n"
        "      {\"position\": {\"x\": number, \"y\": number}, \"entity_type\": \"string\"}\n"
        "    ]\n"
        "  },\n"
        "  \"constraints\": {\n"
        "    \"inside_zone_only\": boolean,\n"
        "    \"reject_if_required_interface_missing\": boolean,\n"
        "    \"allow_remove_existing_entities\": boolean\n"
        "  },\n"
        "  \"success_criteria\": {\n"
        "    \"must_have_power\": boolean,\n"
        "    \"must_consume_inputs\": [\"string\"],\n"
        "    \"must_output_item\": \"string\",\n"
        "    \"min_output_per_sec\": number,\n"
        "    \"consecutive_checks\": integer\n"
        "  },\n"
        "  \"module_spec\": {\n"
        "    \"module_spec_version\": 1,\n"
        "    \"data\": object\n"
        "  }\n"
        "}\n"
        "```\n"
        "Hard requirements:\n"
        "- module_type=iron_mine_electric: outputs must include name=ore_out; module_spec.data must include resource and build_target.\n"
        "- module_type=smelter_coal: inputs must include names ore_in and coal_in; outputs must include name=plate_out; module_spec.data must include recipe and build_target.\n"
        "Mining rule (mandatory, overrides direct build policy):\n"
        "- Any mining operation (new mine build or mining layout modification) MUST use BUILD_MODE_REQUEST with module_type=iron_mine_electric.\n"
        "- If the next action would place or reconfigure mining drills, issue BUILD_MODE_REQUEST first.\n"
        "- Do not construct mining directly in orchestrator mode.\n"
        "- Policies that directly place mining drills in orchestrator mode are rejected at runtime.\n"
        "- request_type must be exactly BUILD_MODE_REQUEST.\n"
        "- zone must satisfy x_min < x_max and y_min < y_max.\n"
        "- The request step counts as a normal step.\n"
        "- The next prompt switches to build mode only after request validation succeeds.\n\n"
        "Build mode return handling:\n"
        "- BUILD_MODE_DONE: integrate returned handoff/verification and continue orchestration.\n"
        "- BUILD_MODE_GIVE_UP: replan (materials/tech/zone/output contract) and issue a corrected request.\n\n"
        "Module registry rules:\n"
        "- Include only existing modules.\n"
        "- Include only verified facts.\n"
        "- Do not include placeholder values like unknown or UNCONFIRMED.\n"
        "- If critical info is missing, list it explicitly under missing_contracts.\n\n"
        "Planning priority:\n"
        "1. Keep power and currently-working production stable.\n"
        "2. Unblock module interfaces that are currently blocked or starved.\n"
        "3. Build or upgrade the next module needed for the goal.\n"
        "4. Route clean handoff interfaces between modules.\n\n"
        "Interface contract rules (strict):\n"
        "- For each module input/output belt, track item lane side explicitly: left | right | both.\n"
        "- Track handoff point coordinates and belt direction explicitly.\n\n"
        "### Module Registry (Existing Modules Only)\n"
        f"{module_registry_text.strip()}\n"
    )


BUILD_MODE_STRIP_LINES = {
    "- Long-horizon planning",
    "- DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off",
    "- Ensure that your factory is arranged in a grid",
    "- have at least 10 spaces between different factory sections",
}


def _strip_build_mode_base_prompt(base_system_prompt: str) -> str:
    filtered_lines: List[str] = []
    for line in base_system_prompt.splitlines():
        if line.strip() in BUILD_MODE_STRIP_LINES:
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).strip()


def _build_overlay(active_build_request: Optional[Dict[str, Any]]) -> str:
    if active_build_request:
        request_json = json.dumps(active_build_request, indent=2, sort_keys=True)
    else:
        request_json = json.dumps(
            {
                "version": 1,
                "request_type": "BUILD_MODE_REQUEST",
                "request_id": "req-preview",
                "module_type": "iron_mine_electric",
                "zone": {
                    "x_min": 0,
                    "x_max": 10,
                    "y_min": -10,
                    "y_max": 0,
                },
                "interfaces": {
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "ore_out",
                            "required": True,
                            "item": "iron-ore",
                            "position": {"x": 9, "y": -1},
                            "output_type": "belt",
                            "belt_direction": "east",
                            "lane_side": "both",
                        }
                    ],
                },
                "power": {
                    "required": True,
                    "anchors": [
                        {
                            "position": {"x": 0, "y": 0},
                            "entity_type": "electric-pole",
                        }
                    ],
                },
                "constraints": {
                    "inside_zone_only": True,
                    "reject_if_required_interface_missing": True,
                    "allow_remove_existing_entities": True,
                },
                "success_criteria": {
                    "must_have_power": True,
                    "must_consume_inputs": ["iron-ore"],
                    "must_output_item": "iron-ore",
                    "min_output_per_sec": 0.1,
                    "consecutive_checks": 3,
                },
                "module_spec": {
                    "module_spec_version": 1,
                    "data": {
                        "resource": "iron-ore",
                        "build_target": {"drills": 4},
                    },
                },
            },
            indent=2,
            sort_keys=True,
        )
    return (
        "## Build Mode (Scoped Module Execution)\n"
        "You are in BUILD MODE for exactly one scoped module.\n\n"
        "You must:\n"
        "- Build only the requested module.\n"
        "- Respect zone, interfaces, and power contract.\n"
        "- Produce clean, deterministic layout.\n"
        "- Prefer deliberate geometry over speed.\n\n"
        "You must NOT:\n"
        "- Use opportunistic placement (for example, exact=False for structural entities).\n"
        "- Use nearest() without validating it stays inside zone.\n"
        "- Place drills or belts without validating orientation and resource correctness.\n\n"
        "Core Build Philosophy:\n"
        "- The builder is not rewarded for quick success.\n"
        "- The builder is rewarded for correct, structured layout that satisfies contract deterministically.\n"
        "- Before placing entities, identify output axis from interfaces.outputs.belt_direction.\n"
        "- Define a primary trunk line aligned to that axis and passing through the required output position.\n"
        "- Compute exact integer coordinates for drill positions, trunk line, merge points, and power pole chain before placement.\n"
        "- If coordinates are not explicitly reasoned in PLANNING, do not build yet.\n\n"
        "Active build request:\n"
        "```json\n"
        f"{request_json}\n"
        "```\n\n"
        "Layout Invariants (Direction-Agnostic):\n"
        "1. Trunk-First Rule: Build the main output belt trunk first. It must align with belt_direction, pass through required output position, and match contract direction at the handoff tile.\n"
        "2. Drill Line Rule: Drills must mine only requested resource, align consistently, stay on integer grid, and use exact=True for structural placement. After each drill placement validate resource, zone inclusion, and drop-position feed logic. If validation fails, remove and retry at corrected coordinate.\n"
        "3. Feeder Rule: Connect drill drops to trunk with short perpendicular feeders. No unnecessary meandering or diagonal drift.\n"
        "4. Power Rule: Connect from provided power anchor with minimal straight chain. Avoid zig-zag unless required.\n"
        "5. Zone Rule: Verify zone inclusion before placing structural entities.\n\n"
        "Deterministic Placement Rules:\n"
        "- All core entities (drills, trunk belts, poles) must use exact=True.\n"
        "- Never rely on nearest() for placement decisions without validating position.\n"
        "- Prefer coordinates from get_resource_patch().bounding_box and trunk alignment.\n"
        "- Snap coordinates to integer tiles unless the API requires half-tile placement.\n\n"
        "Verification Discipline:\n"
        "- After each meaningful step, verify drills (resource correctness, powered, producing).\n"
        "- After each meaningful step, verify belts (orientation matches trunk axis and output handoff tile direction).\n"
        "- After each meaningful step, verify output (ore appears near output tile and rate trends toward minimum after warmup).\n"
        "- Do not wait until the end to validate everything.\n\n"
        "Important: Planning Stage Requirements\n"
        "- In PLANNING explicitly state: trunk axis, trunk coordinate, drill coordinates, merge strategy, and power routing plan.\n"
        "- If these are not explicit, design is incomplete.\n\n"
        "Build Completion Rules:\n"
        "- For normal build-progress steps, output Python actions.\n"
        "- To finish, output exactly one JSON object (no Python/comments/fences):\n"
        "  {\"version\":1,\"request_type\":\"BUILD_MODE_DONE\",\"request_id\":\"req-...\",\"status\":\"success|partial|failed\",\"verification\":{},\"handoff\":{},\"notes\":\"...\"}\n"
        "- If impossible, output exactly one JSON object (no Python/comments/fences):\n"
        "  {\"version\":1,\"request_type\":\"BUILD_MODE_GIVE_UP\",\"request_id\":\"req-...\",\"status\":\"impossible\",\"reason\":\"...\",\"evidence\":{},\"recommended_orchestrator_action\":\"...\"}\n"
    )


def _compose_prompt(
    base_system_prompt: str,
    mode: str,
    module_registry_text: str,
    active_build_request: Optional[Dict[str, Any]] = None,
) -> str:
    if mode == "default":
        return base_system_prompt
    if mode == "orchestrator":
        return base_system_prompt.rstrip() + "\n\n" + _orchestrator_overlay(
            module_registry_text
        )
    if mode == "build":
        build_base = _strip_build_mode_base_prompt(base_system_prompt)
        return build_base.rstrip() + "\n\n" + _build_overlay(active_build_request)
    raise ValueError(f"Unsupported prompt mode: {mode}")


def _switch_agent_prompt_mode(
    *,
    agent: GymAgent,
    task,
    agent_idx: int,
    raw_prompt: str,
    reset_to_recent_observation: bool,
) -> None:
    from fle.commons.models.conversation import Conversation

    updated_system_prompt = agent._get_instructions(raw_prompt, task, agent_idx)
    last_user_message = None
    if reset_to_recent_observation:
        for msg in reversed(agent.conversation.messages):
            if msg.role == "user":
                last_user_message = msg
                break
        agent.conversation = Conversation(messages=[])
    agent.system_prompt = updated_system_prompt
    agent.conversation.set_system_message(updated_system_prompt)
    if last_user_message:
        metadata = last_user_message.metadata or {}
        agent.conversation.add_user_message(last_user_message.content, **metadata)


MODE_COMMAND_RE = re.compile(
    r"^#\s*(BUILD_MODE_REQUEST|BUILD_MODE_DONE|BUILD_MODE_GIVE_UP)\s+(\{.*\})\s*$"
)
MODE_COMMAND_NAMES = {"BUILD_MODE_REQUEST", "BUILD_MODE_DONE", "BUILD_MODE_GIVE_UP"}
DIRECT_MINING_PLACEMENT_RE = re.compile(
    r"\bplace_entity(?:_next_to)?\s*\(\s*Prototype\.(?:ElectricMiningDrill|BurnerMiningDrill)\b"
)

DIRECTION_TO_FACTORIO = {
    "north": 0,
    "east": 2,
    "south": 4,
    "west": 6,
}

MODULE_TYPES = {"iron_mine_electric", "smelter_coal"}


def _lua_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_mode_event(event_type: str, payload: Dict[str, Any]) -> str:
    return f"{event_type} {json.dumps(payload, sort_keys=True)}"


def _parse_mode_command(policy_code: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return stripped

    stripped_policy = _strip_code_fence(policy_code)
    if not stripped_policy:
        return None, None, None

    first_non_empty = None
    for line in stripped_policy.splitlines():
        stripped = line.strip()
        if stripped:
            first_non_empty = stripped
            break
    if first_non_empty:
        legacy_match = MODE_COMMAND_RE.match(first_non_empty)
        if legacy_match:
            cmd = legacy_match.group(1)
            payload_raw = legacy_match.group(2)
            try:
                payload = json.loads(payload_raw)
            except Exception as exc:
                return (
                    cmd,
                    None,
                    f"legacy comment command format is not supported; emit raw JSON only ({exc})",
                )
            return (
                cmd,
                payload if isinstance(payload, dict) else None,
                "legacy comment command format is not supported; emit raw JSON only",
            )

    decoder = json.JSONDecoder()
    try:
        payload, idx = decoder.raw_decode(stripped_policy)
    except Exception:
        return None, None, None

    if not isinstance(payload, dict):
        return "BUILD_MODE_REQUEST", None, "control payload must be a JSON object"

    request_type = payload.get("request_type")
    if not isinstance(request_type, str) or not request_type.strip():
        return "BUILD_MODE_REQUEST", payload, "request_type missing from control JSON"
    if request_type not in MODE_COMMAND_NAMES:
        return request_type, payload, f"unsupported request_type: {request_type}"

    trailing = stripped_policy[idx:].strip()
    if trailing:
        return (
            request_type,
            payload,
            "control JSON must be the only content in the response",
        )
    return request_type, payload, None


def _validate_zone(zone: Any, prefix: str, errors: List[str]) -> None:
    if not isinstance(zone, dict):
        errors.append(f"{prefix} must be an object")
        return
    for key in ("x_min", "x_max", "y_min", "y_max"):
        if key not in zone:
            errors.append(f"{prefix}.{key} missing")
            continue
        if not isinstance(zone[key], (int, float)):
            errors.append(f"{prefix}.{key} must be numeric")
    if all(k in zone and isinstance(zone[k], (int, float)) for k in ("x_min", "x_max", "y_min", "y_max")):
        if zone["x_min"] >= zone["x_max"]:
            errors.append(f"{prefix}.x_min must be < x_max")
        if zone["y_min"] >= zone["y_max"]:
            errors.append(f"{prefix}.y_min must be < y_max")


def _validate_position(position: Any, prefix: str, errors: List[str]) -> None:
    if not isinstance(position, dict):
        errors.append(f"{prefix} must be an object")
        return
    for key in ("x", "y"):
        if key not in position:
            errors.append(f"{prefix}.{key} missing")
            continue
        if not isinstance(position[key], (int, float)):
            errors.append(f"{prefix}.{key} must be numeric")


def _validate_build_mode_request_schema(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required_top = {
        "version",
        "request_type",
        "request_id",
        "module_type",
        "zone",
        "interfaces",
        "power",
        "constraints",
        "success_criteria",
        "module_spec",
    }
    for key in sorted(required_top):
        if key not in payload:
            errors.append(f"{key} missing")

    if "version" in payload and not isinstance(payload["version"], int):
        errors.append("version must be an integer")
    if payload.get("request_type") != "BUILD_MODE_REQUEST":
        errors.append("request_type must be BUILD_MODE_REQUEST")
    if not isinstance(payload.get("request_id"), str) or not payload.get("request_id", "").strip():
        errors.append("request_id must be non-empty string")

    module_type = payload.get("module_type")
    if module_type not in MODULE_TYPES:
        errors.append(
            f"module_type must be one of {sorted(MODULE_TYPES)}"
        )

    _validate_zone(payload.get("zone"), "zone", errors)

    interfaces = payload.get("interfaces")
    if not isinstance(interfaces, dict):
        errors.append("interfaces must be an object")
    else:
        inputs = interfaces.get("inputs")
        outputs = interfaces.get("outputs")
        if not isinstance(inputs, list):
            errors.append("interfaces.inputs must be a list")
        if not isinstance(outputs, list):
            errors.append("interfaces.outputs must be a list")

        for bucket_name, bucket in (("inputs", inputs), ("outputs", outputs)):
            if not isinstance(bucket, list):
                continue
            for idx, iface in enumerate(bucket):
                iface_prefix = f"interfaces.{bucket_name}[{idx}]"
                if not isinstance(iface, dict):
                    errors.append(f"{iface_prefix} must be an object")
                    continue
                if not isinstance(iface.get("name"), str) or not iface.get("name", "").strip():
                    errors.append(f"{iface_prefix}.name must be non-empty string")
                if not isinstance(iface.get("required"), bool):
                    errors.append(f"{iface_prefix}.required must be boolean")
                if not isinstance(iface.get("item"), str) or not iface.get("item", "").strip():
                    errors.append(f"{iface_prefix}.item must be non-empty string")
                _validate_position(iface.get("position"), f"{iface_prefix}.position", errors)

                if bucket_name == "inputs":
                    iface_type = iface.get("interface_type")
                    if iface_type not in {"belt_handoff", "drill_output", "chest_handoff"}:
                        errors.append(
                            f"{iface_prefix}.interface_type must be belt_handoff|drill_output|chest_handoff"
                        )
                    direction = iface.get("belt_direction_into_zone")
                    if direction not in DIRECTION_TO_FACTORIO:
                        errors.append(
                            f"{iface_prefix}.belt_direction_into_zone must be one of {sorted(DIRECTION_TO_FACTORIO.keys())}"
                        )
                    lane_side = iface.get("lane_side")
                    if lane_side not in {"left", "right", "both"}:
                        errors.append(
                            f"{iface_prefix}.lane_side must be left|right|both"
                        )
                else:
                    output_type = iface.get("output_type")
                    if output_type not in {"belt", "chest"}:
                        errors.append(
                            f"{iface_prefix}.output_type must be belt|chest"
                        )
                    if output_type == "belt":
                        direction = iface.get("belt_direction")
                        if direction not in DIRECTION_TO_FACTORIO:
                            errors.append(
                                f"{iface_prefix}.belt_direction must be one of {sorted(DIRECTION_TO_FACTORIO.keys())}"
                            )
                        lane_side = iface.get("lane_side")
                        if lane_side not in {"left", "right", "both"}:
                            errors.append(
                                f"{iface_prefix}.lane_side must be left|right|both"
                            )

    power = payload.get("power")
    if not isinstance(power, dict):
        errors.append("power must be an object")
    else:
        if not isinstance(power.get("required"), bool):
            errors.append("power.required must be boolean")
        anchors = power.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            errors.append("power.anchors must be a non-empty list")
        else:
            for idx, anchor in enumerate(anchors):
                ap = f"power.anchors[{idx}]"
                if not isinstance(anchor, dict):
                    errors.append(f"{ap} must be an object")
                    continue
                _validate_position(anchor.get("position"), f"{ap}.position", errors)
                if not isinstance(anchor.get("entity_type"), str) or not anchor.get(
                    "entity_type", ""
                ).strip():
                    errors.append(f"{ap}.entity_type must be non-empty string")

    constraints = payload.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("constraints must be an object")
    else:
        for key in (
            "inside_zone_only",
            "reject_if_required_interface_missing",
            "allow_remove_existing_entities",
        ):
            if not isinstance(constraints.get(key), bool):
                errors.append(f"constraints.{key} must be boolean")

    success = payload.get("success_criteria")
    if not isinstance(success, dict):
        errors.append("success_criteria must be an object")
    else:
        if not isinstance(success.get("must_have_power"), bool):
            errors.append("success_criteria.must_have_power must be boolean")
        if not isinstance(success.get("must_output_item"), str) or not success.get(
            "must_output_item", ""
        ).strip():
            errors.append("success_criteria.must_output_item must be non-empty string")
        if not isinstance(success.get("min_output_per_sec"), (int, float)):
            errors.append("success_criteria.min_output_per_sec must be numeric")
        if not isinstance(success.get("consecutive_checks"), int):
            errors.append("success_criteria.consecutive_checks must be integer")
        if not isinstance(success.get("must_consume_inputs"), list):
            errors.append("success_criteria.must_consume_inputs must be list")

    module_spec = payload.get("module_spec")
    if not isinstance(module_spec, dict):
        errors.append("module_spec must be an object")
    else:
        if not isinstance(module_spec.get("module_spec_version"), int):
            errors.append("module_spec.module_spec_version must be integer")
        if not isinstance(module_spec.get("data"), dict):
            errors.append("module_spec.data must be an object")

    if errors:
        return errors

    # Module-type specific requirements
    inputs = {item["name"]: item for item in payload["interfaces"]["inputs"]}
    outputs = {item["name"]: item for item in payload["interfaces"]["outputs"]}
    spec_data = payload["module_spec"]["data"]

    if module_type == "iron_mine_electric":
        if "ore_out" not in outputs:
            errors.append("interfaces.outputs must include required output name ore_out")
        if "resource" not in spec_data:
            errors.append("module_spec.data.resource missing for iron_mine_electric")
        if "build_target" not in spec_data:
            errors.append("module_spec.data.build_target missing for iron_mine_electric")

    if module_type == "smelter_coal":
        for req_name in ("ore_in", "coal_in"):
            if req_name not in inputs:
                errors.append(
                    f"interfaces.inputs must include required input name {req_name}"
                )
        if "plate_out" not in outputs:
            errors.append("interfaces.outputs must include required output name plate_out")
        if "recipe" not in spec_data:
            errors.append("module_spec.data.recipe missing for smelter_coal")
        if "build_target" not in spec_data:
            errors.append("module_spec.data.build_target missing for smelter_coal")

    return errors


def _rcon_entities_at_position(rcon_client, x: float, y: float) -> List[Dict[str, Any]]:
    cmd = (
        "/sc "
        f"local x={x:.6f}; local y={y:.6f}; "
        "local s=game.surfaces[1]; "
        "local ents=s.find_entities_filtered{position={x,y}}; "
        "local out={}; "
        "for _,e in pairs(ents) do "
        "  table.insert(out, "
        "    e.name..';'..e.type..';'..tostring(e.direction or -1)..';'.."
        "    string.format('%.6f', e.position.x)..';'..string.format('%.6f', e.position.y)"
        "  ); "
        "end; "
        "rcon.print(table.concat(out,'|'))"
    )
    raw = rcon_client.send_command(cmd) or ""
    entities: List[Dict[str, Any]] = []
    for part in raw.split("|"):
        if not part:
            continue
        cols = part.split(";")
        if len(cols) < 5:
            continue
        try:
            direction = int(cols[2])
        except Exception:
            direction = -1
        try:
            ent_x = float(cols[3])
            ent_y = float(cols[4])
        except Exception:
            continue
        entities.append(
            {
                "name": cols[0],
                "type": cols[1],
                "direction": direction,
                "x": ent_x,
                "y": ent_y,
            }
        )
    return entities


def _entities_exact_at(
    entities: List[Dict[str, Any]], x: float, y: float, *, epsilon: float = 1e-6
) -> List[Dict[str, Any]]:
    return [
        ent
        for ent in entities
        if abs(float(ent.get("x", 999999.0)) - x) <= epsilon
        and abs(float(ent.get("y", 999999.0)) - y) <= epsilon
    ]


def _check_belt_interface_exact(
    rcon_client,
    *,
    item: str,
    x: float,
    y: float,
    direction: str,
    lane_side: str,
    label: str,
) -> Optional[str]:
    if direction not in DIRECTION_TO_FACTORIO:
        return f"{label}: invalid direction {direction}"
    if lane_side not in {"left", "right", "both"}:
        return f"{label}: invalid lane_side {lane_side}"
    expected_dir = DIRECTION_TO_FACTORIO[direction]
    cmd = (
        "/sc "
        f"local x={x:.6f}; local y={y:.6f}; "
        f"local expected_dir={expected_dir}; "
        f"local lane={_lua_str(lane_side)}; "
        f"local item={_lua_str(item)}; "
        "local s=game.surfaces[1]; "
        "local ents=s.find_entities_filtered{position={x,y}}; "
        "local belt=nil; "
        "for _,e in pairs(ents) do "
        "  if (e.type=='transport-belt' or e.type=='underground-belt' or e.type=='splitter') "
        "     and math.abs(e.position.x-x)<=0.000001 and math.abs(e.position.y-y)<=0.000001 then "
        "    belt=e; break; "
        "  end "
        "end; "
        "if belt==nil then rcon.print('ERR:no_exact_belt') return end; "
        "if belt.direction~=expected_dir then rcon.print('ERR:direction:'..tostring(belt.direction)) return end; "
        "local c1=0; local c2=0; "
        "local l1=belt.get_transport_line(1); "
        "local l2=belt.get_transport_line(2); "
        "if l1 then local v=l1.get_contents()[item]; if v then c1=v end end; "
        "if l2 then local v=l2.get_contents()[item]; if v then c2=v end end; "
        "if lane=='left' and c1<=0 then rcon.print('ERR:lane_left_empty') return end; "
        "if lane=='right' and c2<=0 then rcon.print('ERR:lane_right_empty') return end; "
        "if lane=='both' and (c1<=0 or c2<=0) then rcon.print('ERR:lane_both_not_filled') return end; "
        "rcon.print('OK')"
    )
    raw = (rcon_client.send_command(cmd) or "").strip()
    if raw == "OK":
        return None
    if raw.startswith("ERR:"):
        return f"{label}: {raw[4:]}"
    return f"{label}: belt interface check failed"


def _check_drill_drop_exact(rcon_client, *, x: float, y: float, label: str) -> Optional[str]:
    cmd = (
        "/sc "
        f"local x={x:.6f}; local y={y:.6f}; "
        "local s=game.surfaces[1]; "
        "local found=false; "
        "local drills=s.find_entities_filtered{type='mining-drill'}; "
        "for _,e in pairs(drills) do "
        "  local d=e.drop_position; "
        "  if math.abs(d.x-x)<0.0001 and math.abs(d.y-y)<0.0001 then found=true; break end "
        "end; "
        "if found then rcon.print('OK') else rcon.print('ERR:no_drill_drop') end"
    )
    raw = (rcon_client.send_command(cmd) or "").strip()
    if raw == "OK":
        return None
    return f"{label}: no drill drop at exact position"


def _check_power_anchor_exact(
    rcon_client, *, x: float, y: float, entity_type: str, label: str
) -> Optional[str]:
    entities = _entities_exact_at(_rcon_entities_at_position(rcon_client, x, y), x, y)
    for ent in entities:
        if ent["type"] == "electric-pole":
            if entity_type and entity_type != ent["name"]:
                continue
            return None
    return f"{label}: required electric pole not found at exact position"


def _check_output_interface_exact(
    rcon_client, iface: Dict[str, Any], label: str
) -> Optional[str]:
    position = iface["position"]
    x = float(position["x"])
    y = float(position["y"])
    entities = _entities_exact_at(_rcon_entities_at_position(rcon_client, x, y), x, y)
    output_type = iface.get("output_type")

    if output_type == "belt":
        belt_like = {"transport-belt", "underground-belt", "splitter"}
        if entities and all(ent["type"] not in belt_like for ent in entities):
            return f"{label}: output position blocked by non-belt entity"
        belt_entities = [ent for ent in entities if ent["type"] in belt_like]
        if belt_entities:
            expected_dir = DIRECTION_TO_FACTORIO[iface["belt_direction"]]
            if all(ent["direction"] != expected_dir for ent in belt_entities):
                return f"{label}: existing belt direction mismatch"
        else:
            expected_dir = DIRECTION_TO_FACTORIO[iface["belt_direction"]]
            cmd = (
                "/sc "
                f"local x={x:.6f}; local y={y:.6f}; local d={expected_dir}; "
                "local s=game.surfaces[1]; local f=game.forces.player; "
                "local ok=s.can_place_entity{"
                "name='transport-belt', position={x,y}, direction=d, force=f, "
                "build_check_type=defines.build_check_type.manual}; "
                "if ok then rcon.print('OK') else rcon.print('ERR:not_buildable_exact') end"
            )
            raw = (rcon_client.send_command(cmd) or "").strip()
            if raw != "OK":
                return (
                    f"{label}: exact output coordinate is not buildable for belt output"
                )
        return None

    if output_type == "chest":
        if not entities:
            cmd = (
                "/sc "
                f"local x={x:.6f}; local y={y:.6f}; "
                "local s=game.surfaces[1]; local f=game.forces.player; "
                "local ok=s.can_place_entity{"
                "name='iron-chest', position={x,y}, force=f, "
                "build_check_type=defines.build_check_type.manual}; "
                "if ok then rcon.print('OK') else rcon.print('ERR:not_buildable_exact') end"
            )
            raw = (rcon_client.send_command(cmd) or "").strip()
            if raw != "OK":
                return (
                    f"{label}: exact output coordinate is not buildable for chest output"
                )
            return None
        chest_ok = any(
            ent["type"] in {"container", "logistic-container"} or ent["name"].endswith("-chest")
            for ent in entities
        )
        if chest_ok:
            return None
        return f"{label}: output chest position blocked by non-chest entity"

    return f"{label}: unsupported output_type {output_type}"


def _validate_build_request_world_state(payload: Dict[str, Any], rcon_client) -> List[str]:
    errors: List[str] = []
    zone = payload["zone"]
    interfaces = payload["interfaces"]
    constraints = payload.get("constraints") or {}
    reject_missing = bool(constraints.get("reject_if_required_interface_missing", True))

    def _position_in_zone(position: Dict[str, Any]) -> bool:
        return (
            zone["x_min"] <= position["x"] <= zone["x_max"]
            and zone["y_min"] <= position["y"] <= zone["y_max"]
        )

    def _is_missing_interface_error(msg: str) -> bool:
        lowered = msg.lower()
        missing_tokens = (
            "missing",
            "not found",
            "no drill drop",
            "no_exact",
            "not buildable",
        )
        return any(token in lowered for token in missing_tokens)

    def _append_interface_error(err: Optional[str]) -> None:
        if not err:
            return
        if not reject_missing and _is_missing_interface_error(err):
            return
        errors.append(err)

    for idx, iface in enumerate(interfaces.get("inputs", [])):
        if not iface.get("required", False):
            continue
        label = f"inputs[{idx}]/{iface.get('name', '?')}"
        pos = iface["position"]
        if not _position_in_zone(pos):
            errors.append(f"{label}: position is outside requested zone (exact checks require inside-zone placement)")
            continue
        iface_type = iface["interface_type"]
        if iface_type == "belt_handoff":
            err = _check_belt_interface_exact(
                rcon_client,
                item=iface["item"],
                x=float(pos["x"]),
                y=float(pos["y"]),
                direction=iface["belt_direction_into_zone"],
                lane_side=iface["lane_side"],
                label=label,
            )
            _append_interface_error(err)
        elif iface_type == "drill_output":
            err = _check_drill_drop_exact(
                rcon_client, x=float(pos["x"]), y=float(pos["y"]), label=label
            )
            _append_interface_error(err)
        elif iface_type == "chest_handoff":
            entities = _entities_exact_at(
                _rcon_entities_at_position(
                    rcon_client, float(pos["x"]), float(pos["y"])
                ),
                float(pos["x"]),
                float(pos["y"]),
            )
            chest_ok = any(
                ent["type"] in {"container", "logistic-container"}
                or ent["name"].endswith("-chest")
                for ent in entities
            )
            if not chest_ok:
                _append_interface_error(
                    f"{label}: required chest handoff missing at exact position"
                )

    for idx, anchor in enumerate(payload["power"]["anchors"]):
        label = f"power.anchors[{idx}]"
        pos = anchor["position"]
        if not _position_in_zone(pos):
            errors.append(f"{label}: position is outside requested zone")
            continue
        err = _check_power_anchor_exact(
            rcon_client,
            x=float(pos["x"]),
            y=float(pos["y"]),
            entity_type=anchor["entity_type"],
            label=label,
        )
        _append_interface_error(err)

    for idx, iface in enumerate(interfaces.get("outputs", [])):
        if not iface.get("required", False):
            continue
        label = f"outputs[{idx}]/{iface.get('name', '?')}"
        pos = iface["position"]
        if not _position_in_zone(pos):
            errors.append(f"{label}: position is outside requested zone")
            continue
        err = _check_output_interface_exact(rcon_client, iface, label)
        _append_interface_error(err)

    return errors


def _validate_build_done(payload: Dict[str, Any], active_request_id: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload.get("version"), int):
        errors.append("version must be integer")
    if payload.get("request_type") != "BUILD_MODE_DONE":
        errors.append("request_type must be BUILD_MODE_DONE")
    if payload.get("request_id") != active_request_id:
        errors.append("request_id does not match active build request")
    status = payload.get("status")
    if status not in {"success", "partial", "failed"}:
        errors.append("status must be success|partial|failed")
    return errors


def _validate_build_give_up(payload: Dict[str, Any], active_request_id: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload.get("version"), int):
        errors.append("version must be integer")
    if payload.get("request_type") != "BUILD_MODE_GIVE_UP":
        errors.append("request_type must be BUILD_MODE_GIVE_UP")
    if payload.get("request_id") != active_request_id:
        errors.append("request_id does not match active build request")
    if payload.get("status") != "impossible":
        errors.append("status must be impossible")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("reason must be non-empty string")
    return errors


def _ensure_tool_action_loaded(instance, action_name: str) -> None:
    check_cmd = (
        "/sc "
        f"if global.actions and global.actions.{action_name} then "
        "rcon.print('OK') else rcon.print('MISSING') end"
    )
    status = (instance.rcon_client.send_command(check_cmd) or "").strip()
    if status == "OK":
        return
    instance.lua_script_manager.load_tool_into_game(action_name, force=True)
    status_after = (instance.rcon_client.send_command(check_cmd) or "").strip()
    if status_after != "OK":
        sys.exit(f"ERROR: failed to load required tool action '{action_name}'")


def _find_factorio_container_for_tcp_port(tcp_port: int) -> str:
    """Return running Factorio container that maps host tcp_port, else None."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        for name in names:
            if "factorio" not in name.lower():
                continue

            inspect = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.returncode != 0 or not inspect.stdout.strip():
                continue

            info = json.loads(inspect.stdout)[0]
            ports = info.get("NetworkSettings", {}).get("Ports", {})
            for port_spec, bindings in ports.items():
                if not port_spec.endswith("/tcp") or not bindings:
                    continue
                for binding in bindings:
                    host_port = binding.get("HostPort")
                    if host_port and int(host_port) == int(tcp_port):
                        return name
    except Exception:
        return None

    return None



def probe_world_signature(rcon_client, resource_radius: int, water_radius: int) -> Tuple[str, Dict[str, str]]:
    """Read-only world probe used to reject wrong maps before a run."""
    probe_cmd = (
        "/sc "
        "local p=game.players[1]; local s=game.surfaces[1]; "
        "local x,y=0,0; if p then x,y=p.position.x,p.position.y end; "
        f"local res_radius={resource_radius}; local water_radius={water_radius}; "
        "local names={'iron-ore','copper-ore','coal','stone','crude-oil'}; "
        "local out={'player@'..string.format('%.1f',x)..','..string.format('%.1f',y)}; "
        "for _,name in pairs(names) do "
        "  local ents=s.find_entities_filtered{position={x,y}, radius=res_radius, name=name}; "
        "  local best=nil; local bd=1e18; "
        "  for _,e in pairs(ents) do "
        "    local dx=e.position.x-x; local dy=e.position.y-y; local d=dx*dx+dy*dy; "
        "    if d<bd then bd=d; best=e end "
        "  end; "
        "  if best then "
        "    table.insert(out, name..'@'..string.format('%.1f',best.position.x)..','..string.format('%.1f',best.position.y)..':'..string.format('%.1f', math.sqrt(bd))) "
        "  else "
        "    table.insert(out, name..'@none') "
        "  end "
        "end; "
        "local wt=s.find_tiles_filtered{"
        "  area={{x-water_radius,y-water_radius},{x+water_radius,y+water_radius}}, "
        "  name={'water','deepwater','water-green','deepwater-green','water-shallow'}, "
        "  limit=1"
        "}; "
        "if #wt>0 then "
        "  local wp=wt[1].position; table.insert(out, 'water_tile@'..string.format('%.1f',wp.x)..','..string.format('%.1f',wp.y)) "
        "else "
        "  table.insert(out, 'water_tile@none') "
        "end; "
        "rcon.print(table.concat(out,'|'))"
    )

    raw = rcon_client.send_command(probe_cmd) or ""
    parsed: Dict[str, str] = {}
    for token in raw.split("|"):
        if "@" not in token:
            continue
        key, value = token.split("@", 1)
        parsed[key.strip()] = value.strip()
    return raw, parsed



def save_game_state(rcon_client, step_num: int, version: int) -> str:
    """Save game state via RCON and return the save name."""
    save_name = f"fle_run_v{version}_step_{step_num:03d}"
    rcon_client.send_command(f'/sc game.auto_save("{save_name}")')
    time.sleep(0.3)
    return save_name



def append_unique_save(
    save_names: List[str], seen: Set[str], save_name: str
) -> Optional[int]:
    if save_name in seen:
        return None
    seen.add(save_name)
    save_names.append(save_name)
    return len(save_names) - 1


def _parse_starter_inventory_spec(spec: str) -> Dict[str, int]:
    items: Dict[str, int] = {}
    if not spec:
        return items
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        if "=" not in part:
            sys.exit(
                f"ERROR: invalid FLE_STARTER_INVENTORY_SPEC token '{part}' "
                "(expected item=count)"
            )
        item, count_raw = part.split("=", 1)
        item = item.strip()
        count_raw = count_raw.strip()
        if not item:
            sys.exit(
                f"ERROR: invalid FLE_STARTER_INVENTORY_SPEC token '{part}' "
                "(empty item name)"
            )
        try:
            count = int(count_raw)
        except ValueError:
            sys.exit(
                f"ERROR: invalid count for item '{item}' in "
                f"FLE_STARTER_INVENTORY_SPEC: '{count_raw}'"
            )
        if count < 0:
            sys.exit(
                f"ERROR: invalid negative count for item '{item}' in "
                "FLE_STARTER_INVENTORY_SPEC"
            )
        items[item] = count
    return items


def _ensure_starter_inventory_if_empty(
    rcon_client,
    starter_items: Dict[str, int],
) -> Tuple[bool, str]:
    if not starter_items:
        return False, "starter inventory spec empty"

    item_tokens = []
    for item_name, item_count in starter_items.items():
        item_tokens.append(
            "{name="
            + _lua_str(item_name)
            + ",count="
            + str(int(item_count))
            + "}"
        )
    lua_items = "{" + ",".join(item_tokens) + "}"

    cmd = (
        "/sc "
        "local p=(global.agent_characters and global.agent_characters[1]) or nil; "
        "if not p or not p.valid then rcon.print('ERR:no_agent_character') return end; "
        "local inv=p.get_main_inventory(); "
        "if not inv then rcon.print('ERR:no_inventory') return end; "
        "local total_before=0; "
        "for _,c in pairs(inv.get_contents()) do total_before=total_before+c end; "
        "if total_before>0 then rcon.print('SKIP:non_empty:'..tostring(total_before)) return end; "
        f"local items={lua_items}; "
        "for _,entry in ipairs(items) do "
        "  if entry.count>0 then inv.insert{name=entry.name, count=entry.count} end "
        "end; "
        "local total_after=0; local kinds=0; "
        "for _,c in pairs(inv.get_contents()) do total_after=total_after+c; kinds=kinds+1 end; "
        "rcon.print('SET:'..tostring(kinds)..':'..tostring(total_after))"
    )
    raw = (rcon_client.send_command(cmd) or "").strip()
    if raw.startswith("SET:"):
        return True, raw
    if raw.startswith("SKIP:"):
        return False, raw
    return False, raw or "UNKNOWN"



def copy_save_from_docker(
    container: str,
    save_name: str,
    dest_dir: Path,
    use_existing: bool = True,
) -> Optional[Path]:
    """Copy one autosave from docker; returns local path or None."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    docker_path = f"{container}:/opt/factorio/saves/_autosave-{save_name}.zip"
    local_path = dest_dir / f"{save_name}.zip"
    if use_existing and _is_valid_save_zip(local_path):
        return local_path
    if local_path.exists() and not _is_valid_save_zip(local_path):
        local_path.unlink(missing_ok=True)
    temp_path = dest_dir / f".{save_name}.{uuid4().hex}.tmp.zip"
    result = subprocess.run(
        ["docker", "cp", docker_path, str(temp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not _is_valid_save_zip(temp_path):
        temp_path.unlink(missing_ok=True)
        print(f"  Warning: failed to copy save {save_name}")
        return None
    temp_path.replace(local_path)
    return local_path


def render_screenshot(
    container: str,
    save_zip: Path,
    output_png: Path,
    timeout_s: int,
    retries: int,
    ticks: int,
) -> bool:
    """Render a single PNG from a save zip using benchmark mode."""
    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        tmpdir = tempfile.mkdtemp(prefix="fle_live_render_")
        try:
            mods_root = Path(tmpdir) / "mods"
            mods_root.mkdir(parents=True, exist_ok=True)
            if attempt > 1:
                _copy_server_mods_to_dir(container, mods_root)

            mod_dir = mods_root / "fle_screenshot"
            mod_dir.mkdir(parents=True, exist_ok=True)
            (mod_dir / "info.json").write_text(_SCREENSHOT_MOD_INFO)
            (mod_dir / "control.lua").write_text(_SCREENSHOT_MOD_CONTROL)

            config_ini = Path(tmpdir) / "config.ini"
            script_output = Path(tmpdir) / "script-output"
            script_output.mkdir(parents=True, exist_ok=True)
            config_ini.write_text(
                f"[path]\n"
                f"read-data={FACTORIO_DATA}\n"
                f"write-data={tmpdir}\n"
            )

            cmd = [
                "xvfb-run",
                "-a",
                "-s",
                "-screen 0 1920x1080x24",
                str(FACTORIO_BINARY),
                "--benchmark-graphics",
                str(save_zip),
                "--benchmark-ticks",
                str(ticks),
                "--benchmark-ignore-paused",
                "--mod-directory",
                str(mods_root),
                "-c",
                str(config_ini),
                "--disable-audio",
                "--disable-migration-window",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )

            screenshot = script_output / "factory.png"
            if screenshot.exists() and screenshot.stat().st_size > 0:
                output_png.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(screenshot, output_png)
                return True

            if attempt < attempts:
                print(
                    f"  Live-render retry {attempt}/{attempts - 1} for {save_zip.name} "
                    f"(no screenshot, exit={result.returncode})"
                )
            else:
                print(
                    f"  Warning: live render missing screenshot for "
                    f"{save_zip.name} (exit={result.returncode})"
                )
        except Exception as exc:
            if attempt < attempts:
                print(
                    f"  Live-render retry {attempt}/{attempts - 1} for "
                    f"{save_zip.name} (error: {exc})"
                )
            else:
                print(f"  Error live-rendering {save_zip.name}: {exc}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    return False


def render_step_from_docker(
    container: str,
    save_name: str,
    step_idx: int,
    save_dir: Path,
    screenshot_dir: Path,
    timeout_s: int,
    retries: int,
    ticks: int,
) -> bool:
    """Copy one save from Docker and render it to step_<idx>.png."""
    save_zip = copy_save_from_docker(
        container,
        save_name,
        save_dir,
        use_existing=True,
    )
    if not save_zip:
        return False
    output_png = screenshot_dir / f"step_{step_idx:03d}.png"
    if output_png.exists() and output_png.stat().st_size > 0:
        return True
    return render_screenshot(
        container=container,
        save_zip=save_zip,
        output_png=output_png,
        timeout_s=timeout_s,
        retries=retries,
        ticks=ticks,
    )


def copy_saves_from_docker(container: str, save_names: List[str], dest_dir: Path) -> None:
    """Copy all unique save files from docker to local filesystem."""
    for name in save_names:
        copy_save_from_docker(container, name, dest_dir, use_existing=False)



def run_catchup_renderer(container: str, save_dir: Path, screenshot_dir: Path) -> None:
    """Run standalone renderer on all copied saves."""
    render_script = Path(__file__).parent / "render_saves.py"
    cmd = [
        sys.executable,
        str(render_script),
        str(save_dir),
        str(screenshot_dir),
        "--skip-existing",
        "--no-clear",
    ]

    print(
        "\nLaunching catch-up renderer: "
        f"python {render_script} {save_dir} {screenshot_dir} --skip-existing --no-clear"
    )

    result = subprocess.run(
        cmd,
        timeout=CATCHUP_PHASE_TIMEOUT,
        env={
            **os.environ,
            "RENDER_MAX_PARALLEL": str(CATCHUP_RENDER_PARALLEL),
            "RENDER_TIMEOUT": str(CATCHUP_RENDER_TIMEOUT),
            "RENDER_RETRIES": str(CATCHUP_RENDER_RETRIES),
            "RENDER_TICKS": str(CATCHUP_RENDER_TICKS),
            "RENDER_CONTAINER": container,
        },
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: catch-up renderer exited with code {result.returncode}")


async def main():
    print(f"=== FLE Run: {MODEL} on {ENV_ID}, {MAX_STEPS} steps ===")
    print("    Save per step + screenshot backend: benchmark")
    print(
        "    World profile: "
        f"{WORLD_PROFILE} "
        f"(required={','.join(WORLD_REQUIRED_RESOURCES)}, "
        f"resource_radius={WORLD_RESOURCE_RADIUS}, water_radius={WORLD_WATER_RADIUS})\n"
    )

    if not FACTORIO_BINARY.is_file():
        sys.exit(f"ERROR: Factorio binary not found at {FACTORIO_BINARY}")
    if not shutil.which("ffmpeg"):
        sys.exit("ERROR: ffmpeg not found (install ffmpeg)")
    if not shutil.which("xvfb-run"):
        sys.exit("ERROR: xvfb-run not found (install xvfb)")

    # Setup
    db_client = await create_db_client()
    env_info = get_environment_info(ENV_ID)
    task = TaskFactory.create_task(env_info["task_config_path"])
    object.__setattr__(task, "trajectory_length", MAX_STEPS)

    gym_env = gym.make(ENV_ID, run_idx=0)
    instance = gym_env.unwrapped.instance
    _ensure_tool_action_loaded(instance, "inspect_inventory")
    server_tcp_port = int(getattr(instance, "tcp_port", 0))
    if server_tcp_port <= 0:
        sys.exit(f"ERROR: invalid tcp port from environment instance: {server_tcp_port}")

    container = _find_factorio_container_for_tcp_port(server_tcp_port)
    if not container:
        sys.exit(
            "ERROR: could not resolve Factorio container for "
            f"tcp/{server_tcp_port}; refusing cross-world fallback."
        )

    print(f"Factorio server: 127.0.0.1:{server_tcp_port}")
    print(f"Docker container: {container}")

    if not SKIP_WORLD_CHECK:
        raw_probe, parsed_probe = probe_world_signature(
            instance.rcon_client,
            resource_radius=WORLD_RESOURCE_RADIUS,
            water_radius=WORLD_WATER_RADIUS,
        )
        print(f"World probe: {raw_probe}")

        missing_resources = [
            resource
            for resource in WORLD_REQUIRED_RESOURCES
            if parsed_probe.get(resource, "none").startswith("none")
        ]
        if parsed_probe.get("water_tile", "none").startswith("none"):
            missing_resources.append("water_tile")

        if missing_resources:
            sys.exit(
                "ERROR: Wrong world signature detected for profile "
                + f"{WORLD_PROFILE}. Missing resources in probe: "
                + ", ".join(missing_resources)
                + f" (required={','.join(WORLD_REQUIRED_RESOURCES)}, "
                + f"radius={WORLD_RESOURCE_RADIUS}, water_radius={WORLD_WATER_RADIUS}). "
                + "Set SKIP_WORLD_CHECK=1 to bypass."
            )
    else:
        print(f"World probe skipped (SKIP_WORLD_CHECK=1) for profile={WORLD_PROFILE}")

    generator = SystemPromptGenerator(str(importlib.resources.files("fle") / "env"))
    base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
    module_registry_text = _load_module_registry_text()
    current_prompt_mode = FLE_PROMPT_MODE
    active_build_request: Optional[Dict[str, Any]] = None

    def _prompt_for_mode(
        mode: str, active_request: Optional[Dict[str, Any]] = None
    ) -> str:
        return _compose_prompt(
            base_system_prompt,
            mode,
            module_registry_text,
            active_build_request=active_request,
        )

    system_prompt = _prompt_for_mode(current_prompt_mode, active_build_request)

    agent = GymAgent(
        model=MODEL,
        system_prompt=system_prompt,
        task=task,
        agent_idx=0,
        observation_formatter=BasicObservationFormatter(
            include_research=False,
            include_entities=FLE_INCLUDE_ENTITIES,
        ),
        system_prompt_formatter=SystemPromptFormatter(),
    )

    version = await get_next_version()
    config = GymEvalConfig(
        agents=[agent],
        version=version,
        version_description=f"model:{MODEL}\ntype:{task.task_key}\nnum_agents:1",
        task=task,
        agent_cards=[agent.get_agent_card()],
        env_id=ENV_ID,
    )

    log_dir = os.path.join(".fle", "trajectory_logs", f"v{version}")

    screenshot_dir = SCREENSHOT_BASE / f"v{version}"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    for old_png in screenshot_dir.glob("step_*.png"):
        old_png.unlink()

    save_dir = SAVES_DIR / f"v{version}"
    save_dir.mkdir(parents=True, exist_ok=True)
    for old_zip in save_dir.glob("*.zip"):
        old_zip.unlink()

    print(f"Version: {version}")
    print(f"Logs: {log_dir}")
    print(f"Screenshots: {screenshot_dir}")
    print(f"Saves: {save_dir}")
    print(f"World profile: {WORLD_PROFILE}")
    print(f"Include entities in prompt: {FLE_INCLUDE_ENTITIES}")
    print(f"Prompt mode: {current_prompt_mode}")
    print(f"Command mode switching: {FLE_ENABLE_COMMAND_MODE_SWITCH}")
    print(f"Ensure starter inventory: {FLE_ENSURE_STARTER_INVENTORY}")
    print(
        "Live render: "
        f"workers={LIVE_RENDER_PARALLEL} timeout={LIVE_RENDER_TIMEOUT} "
        f"retries={LIVE_RENDER_RETRIES} ticks={LIVE_RENDER_TICKS}"
    )
    print()

    save_names: List[str] = []
    seen_save_names: Set[str] = set()
    live_render_executor: Optional[ThreadPoolExecutor] = None
    live_render_jobs: List[Tuple[int, str, Future[bool]]] = []
    if LIVE_RENDER_PARALLEL > 0:
        live_render_executor = ThreadPoolExecutor(max_workers=LIVE_RENDER_PARALLEL)

    def submit_live_render(step_idx: int, save_name: str) -> None:
        if not live_render_executor:
            return
        future = live_render_executor.submit(
            render_step_from_docker,
            container,
            save_name,
            step_idx,
            save_dir,
            screenshot_dir,
            LIVE_RENDER_TIMEOUT,
            LIVE_RENDER_RETRIES,
            LIVE_RENDER_TICKS,
        )
        live_render_jobs.append((step_idx, save_name, future))

    starter_inventory = _parse_starter_inventory_spec(FLE_STARTER_INVENTORY_SPEC)
    if FLE_ENSURE_STARTER_INVENTORY and starter_inventory:
        # Ensure env.reset() starts with intended inventory, not empty default.
        instance.initial_inventory = starter_inventory

    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        db_client=db_client,
        log_dir=log_dir,
        process_id=0,
    )

    current_state, agent_steps = await runner._initialize_trajectory_state()
    _ = current_state

    if FLE_ENSURE_STARTER_INVENTORY:
        changed, detail = _ensure_starter_inventory_if_empty(
            instance.rcon_client, starter_inventory
        )
        status = "applied" if changed else "skipped"
        print(f"Starter inventory ensure: {status} ({detail})")
    else:
        print("Starter inventory ensure: disabled")

    initial_save = save_game_state(instance.rcon_client, 0, version)
    initial_idx = append_unique_save(save_names, seen_save_names, initial_save)
    if initial_idx is not None:
        submit_live_render(initial_idx, initial_save)
    print(f"Saved initial state: {initial_save}")

    for idx, configured_agent in enumerate(runner.agents):
        runner.logger.save_system_prompt(configured_agent, idx)

    from itertools import product as iprod

    from fle.env.gym_env.action import Action
    from fle.env.gym_env.observation import Observation
    from fle.agents import CompletionReason, CompletionResult

    step_count = 0
    done = False
    mode_events: List[Dict[str, Any]] = []
    mode_events_path = Path(log_dir) / "mode_events.jsonl"
    mode_events_path.parent.mkdir(parents=True, exist_ok=True)
    if mode_events_path.exists():
        mode_events_path.unlink()
    mode_events_path.touch()

    def _record_mode_event(
        event_type: str,
        payload: Dict[str, Any],
        *,
        errors: Optional[List[str]] = None,
    ) -> None:
        event = {
            "version": version,
            "event_type": event_type,
            "step": step_count,
            "mode": current_prompt_mode,
            "timestamp": time.time(),
            "payload": payload,
        }
        if isinstance(payload, dict) and payload.get("request_id") is not None:
            event["request_id"] = payload.get("request_id")
        if errors:
            event["errors"] = errors
        mode_events.append(event)
        with mode_events_path.open("a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    def _save_mode_prompt_snapshot(
        configured_agent: GymAgent, configured_agent_idx: int, mode: str
    ) -> None:
        if not runner.logger.log_dir:
            return
        prompt_file = (
            Path(runner.logger.log_dir)
            / f"agent{configured_agent_idx}_system_prompt_{mode}_step{step_count:03d}.txt"
        )
        formatted_prompt = configured_agent.system_prompt_formatter.format(
            configured_agent.task, configured_agent.system_prompt
        )
        prompt_file.write_text(formatted_prompt)

    def _switch_mode(
        configured_agent: GymAgent,
        configured_agent_idx: int,
        next_mode: str,
        next_active_request: Optional[Dict[str, Any]],
        reason: str,
    ) -> None:
        nonlocal current_prompt_mode, active_build_request
        reset_to_recent = (
            FLE_BUILD_MODE_RESET_CONTEXT
            if next_mode == "build"
            else FLE_BUILD_RETURN_RESET_CONTEXT
        )
        _switch_agent_prompt_mode(
            agent=configured_agent,
            task=task,
            agent_idx=configured_agent_idx,
            raw_prompt=_prompt_for_mode(next_mode, next_active_request),
            reset_to_recent_observation=reset_to_recent,
        )
        current_prompt_mode = next_mode
        active_build_request = next_active_request
        _save_mode_prompt_snapshot(configured_agent, configured_agent_idx, next_mode)
        _record_mode_event(
            "MODE_SWITCH",
            {
                "reason": reason,
                "next_mode": next_mode,
                "active_request_id": (
                    next_active_request.get("request_id")
                    if next_active_request
                    else None
                ),
            },
        )

    for _, agent_idx in iprod(range(MAX_STEPS), range(len(runner.agents))):
        agent_r = runner.agents[agent_idx]
        iteration_start = time.time()

        try:
            while agent_steps[agent_idx] < MAX_STEPS:
                policy = await agent_r.generate_policy()
                agent_steps[agent_idx] += 1
                step_count += 1

                if not policy:
                    print(f"[step {step_count}] Policy generation failed, skipping")
                    break

                pending_mode_switch: Optional[str] = None
                pending_active_request: Optional[Dict[str, Any]] = None
                mode_event_messages: List[str] = []
                action_code = policy.code

                command_name, command_payload, command_parse_error = _parse_mode_command(
                    policy.code
                )
                if FLE_ENABLE_COMMAND_MODE_SWITCH and command_name:
                    # Command responses are always control-plane only (no world action).
                    action_code = "pass"
                    if command_parse_error:
                        request_id = None
                        if isinstance(command_payload, dict):
                            request_id = command_payload.get("request_id")
                        errors = [command_parse_error]
                        rejection = {"request_id": request_id, "errors": errors}
                        mode_event_messages.append(
                            _format_mode_event("BUILD_MODE_REJECTED", rejection)
                        )
                        _record_mode_event("BUILD_MODE_REJECTED", rejection, errors=errors)
                    elif command_name == "BUILD_MODE_REQUEST":
                        request_id = command_payload.get("request_id")
                        if current_prompt_mode != "orchestrator":
                            errors = [
                                "BUILD_MODE_REQUEST is only valid in orchestrator mode"
                            ]
                        else:
                            schema_errors = _validate_build_mode_request_schema(
                                command_payload
                            )
                            world_errors = []
                            if not schema_errors:
                                world_errors = _validate_build_request_world_state(
                                    command_payload, instance.rcon_client
                                )
                            errors = schema_errors + world_errors

                        if errors:
                            rejection = {"request_id": request_id, "errors": errors}
                            mode_event_messages.append(
                                _format_mode_event("BUILD_MODE_REJECTED", rejection)
                            )
                            _record_mode_event(
                                "BUILD_MODE_REJECTED", rejection, errors=errors
                            )
                        else:
                            accepted = {
                                "request_id": command_payload["request_id"],
                                "module_type": command_payload["module_type"],
                                "zone": command_payload["zone"],
                            }
                            mode_event_messages.append(
                                _format_mode_event(
                                    "BUILD_MODE_REQUEST_ACCEPTED", accepted
                                )
                            )
                            _record_mode_event("BUILD_MODE_REQUEST_ACCEPTED", accepted)
                            pending_mode_switch = "build"
                            pending_active_request = command_payload

                    elif command_name == "BUILD_MODE_DONE":
                        request_id = command_payload.get("request_id")
                        if current_prompt_mode != "build" or not active_build_request:
                            errors = [
                                "BUILD_MODE_DONE is only valid in build mode with an active request"
                            ]
                        else:
                            errors = _validate_build_done(
                                command_payload, active_build_request["request_id"]
                            )

                        if errors:
                            rejection = {"request_id": request_id, "errors": errors}
                            mode_event_messages.append(
                                _format_mode_event("BUILD_MODE_REJECTED", rejection)
                            )
                            _record_mode_event(
                                "BUILD_MODE_REJECTED", rejection, errors=errors
                            )
                        else:
                            done_payload = {
                                "request_id": request_id,
                                "status": command_payload["status"],
                                "verification": command_payload.get("verification", {}),
                                "handoff": command_payload.get("handoff", {}),
                            }
                            mode_event_messages.append(
                                _format_mode_event("BUILD_MODE_DONE", done_payload)
                            )
                            _record_mode_event("BUILD_MODE_DONE", done_payload)
                            pending_mode_switch = "orchestrator"
                            pending_active_request = None

                    elif command_name == "BUILD_MODE_GIVE_UP":
                        request_id = command_payload.get("request_id")
                        if current_prompt_mode != "build" or not active_build_request:
                            errors = [
                                "BUILD_MODE_GIVE_UP is only valid in build mode with an active request"
                            ]
                        else:
                            errors = _validate_build_give_up(
                                command_payload, active_build_request["request_id"]
                            )

                        if errors:
                            rejection = {"request_id": request_id, "errors": errors}
                            mode_event_messages.append(
                                _format_mode_event("BUILD_MODE_REJECTED", rejection)
                            )
                            _record_mode_event(
                                "BUILD_MODE_REJECTED", rejection, errors=errors
                            )
                        else:
                            give_up_payload = {
                                "request_id": request_id,
                                "status": "impossible",
                                "reason": command_payload["reason"],
                            }
                            mode_event_messages.append(
                                _format_mode_event("BUILD_MODE_GIVE_UP", give_up_payload)
                            )
                            _record_mode_event("BUILD_MODE_GIVE_UP", give_up_payload)
                            pending_mode_switch = "orchestrator"
                            pending_active_request = None

                    else:
                        errors = [f"unsupported control command: {command_name}"]
                        rejection = {"request_id": None, "errors": errors}
                        mode_event_messages.append(
                            _format_mode_event("BUILD_MODE_REJECTED", rejection)
                        )
                        _record_mode_event("BUILD_MODE_REJECTED", rejection, errors=errors)
                elif (
                    FLE_ENABLE_COMMAND_MODE_SWITCH
                    and current_prompt_mode == "orchestrator"
                    and DIRECT_MINING_PLACEMENT_RE.search(policy.code)
                ):
                    action_code = "pass"
                    errors = [
                        "Direct mining drill placement is forbidden in orchestrator mode; emit BUILD_MODE_REQUEST JSON first"
                    ]
                    rejection = {"request_id": None, "errors": errors}
                    mode_event_messages.append(
                        _format_mode_event("BUILD_MODE_REJECTED", rejection)
                    )
                    _record_mode_event("BUILD_MODE_REJECTED", rejection, errors=errors)

                action = Action(code=action_code, agent_idx=agent_idx, game_state=None)
                obs_dict, reward, terminated, truncated, info = runner.gym_env.step(action)
                if mode_event_messages:
                    raw_text = (obs_dict.get("raw_text") or "").strip()
                    merged = "\n".join(mode_event_messages)
                    obs_dict["raw_text"] = f"{raw_text}\n{merged}".strip()
                observation = Observation.from_dict(obs_dict)
                production_score = info["production_score"]
                done = terminated or truncated

                program = await runner.create_program_from_policy(
                    policy=policy,
                    agent_idx=agent_idx,
                    reward=reward,
                    response=obs_dict["raw_text"],
                    error_occurred=info["error_occurred"],
                    achievements=info["achievements"],
                    game_state=info["output_game_state"],
                    production_score=production_score,
                )

                await agent_r.update_conversation(observation, previous_program=program)
                if pending_mode_switch:
                    _switch_mode(
                        configured_agent=agent_r,
                        configured_agent_idx=agent_idx,
                        next_mode=pending_mode_switch,
                        next_active_request=pending_active_request,
                        reason=command_name or "command",
                    )
                    print(
                        f"[prompt] switched mode to {pending_mode_switch} "
                        f"at completed_step_count={step_count}"
                    )

                runner._log_trajectory_state(
                    iteration_start,
                    agent_r,
                    agent_idx,
                    agent_steps[agent_idx],
                    production_score,
                    program,
                    observation,
                )

                elapsed = time.time() - iteration_start
                print(
                    f"[step {step_count:2d}/{MAX_STEPS}] "
                    f"reward={reward:.2f} score={production_score:.2f} "
                    f"err={info['error_occurred']} ({elapsed:.1f}s)"
                )

                save_name = save_game_state(instance.rcon_client, step_count, version)
                save_idx = append_unique_save(save_names, seen_save_names, save_name)
                if save_idx is not None:
                    submit_live_render(save_idx, save_name)

                if done:
                    print(f"\n*** TASK COMPLETED at step {step_count}! ***")
                    for configured_agent in runner.agents:
                        await configured_agent.end(
                            CompletionResult(
                                step=agent_steps[agent_idx],
                                reason=CompletionReason.SUCCESS,
                            )
                        )
                    break

            if done:
                break

        except Exception as exc:
            print(f"[step {step_count}] Error: {exc}")
            import traceback

            traceback.print_exc()

            # Keep a snapshot for post-mortem, but dedupe names so counts stay stable.
            snapshot_step = max(step_count, 0)
            save_name = save_game_state(instance.rcon_client, snapshot_step, version)
            save_idx = append_unique_save(save_names, seen_save_names, save_name)
            if save_idx is not None:
                submit_live_render(save_idx, save_name)
            continue

        if done:
            break

    if live_render_executor:
        total_live_jobs = len(live_render_jobs)
        print(f"\nWaiting for {total_live_jobs} live render jobs...")
        live_success = 0
        for step_idx, save_name, future in live_render_jobs:
            try:
                if future.result():
                    live_success += 1
            except Exception as exc:
                print(
                    f"  Live render job failed for step_{step_idx:03d} "
                    f"({save_name}): {exc}"
                )
        live_render_executor.shutdown(wait=True)
        print(f"Live render complete: {live_success}/{total_live_jobs}")
    else:
        print("\nLive rendering disabled (LIVE_RENDER_PARALLEL=0)")

    await db_client.cleanup()

    print(f"\nCopying {len(save_names)} saves from Docker...")
    copy_saves_from_docker(container, save_names, save_dir)

    run_catchup_renderer(container, save_dir, screenshot_dir)

    screenshot_count = len(list(screenshot_dir.glob("step_*.png")))
    expected_screenshots = len(save_names)
    if screenshot_count != expected_screenshots:
        sys.exit(
            f"ERROR: expected {expected_screenshots} screenshots, got {screenshot_count}."
        )

    print(f"\n{'=' * 60}")
    print(f"Run complete: {step_count} steps, {screenshot_count} screenshots")
    print(f"{'=' * 60}")

    print("\n=== ALL OUTPUTS ===")
    print(f"  Video:       {(screenshot_dir / 'run.mp4').resolve()}")
    print(f"  Screenshots: {screenshot_dir.resolve()}/step_*.png")
    print(f"  Logs:        {Path(log_dir).resolve()}/")
    print(f"  DB:          .fle/data.db (version {version})")


if __name__ == "__main__":
    asyncio.run(main())
