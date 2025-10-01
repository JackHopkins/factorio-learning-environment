"""
End-to-end pipeline for replay → cinematics.

This mirrors `run_to_mp4.py` but replaces "take screenshots after each
program" logic with event-driven shot generation via the Cinematographer.

Usage (CLI):

    python -m fle.eval.analysis.runtime_to_cinema VERSION --output-dir vids

It will:
    1. Fetch programs for the requested version from Postgres.
    2. Replay them in a gym environment.
    3. Feed action/world deltas into `Cinematographer.observe`.
    4. Submit the resulting plan to the admin Cutscene tool.
    5. Optionally wait for completion and fetch the shot report.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from dotenv import load_dotenv

from fle.env import FactorioInstance
from fle.env.tools.admin.cutscene.client import Cutscene
from fle.eval.analysis.cinematographer import ShotLib, ShotPolicy, ShotTemplate, Var, new_plan
from fle.eval.analysis.ast_actions import parse_actions
from fle.commons.models.program import Program
from fle.eval.tasks.task_factory import TaskFactory

# Import Cinematographer and related classes
from fle.eval.analysis.cinematographer import Cinematographer, CameraPrefs, GameClock


load_dotenv()


# --- Module-level defaults -------------------------------------------------

# Default shot policy for runtime cinema generation
POLICY = ShotPolicy()  # use defaults


# --- DB helpers ------------------------------------------------------------


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )


def get_program_chain(conn, version: int) -> List[tuple[int, Any]]:
    query = """
        SELECT id, created_at FROM programs
        WHERE version = %s
        AND state_json IS NOT NULL
        ORDER BY created_at ASC
        LIMIT 3000
    """
    with conn.cursor() as cur:
        cur.execute(query, (version,))
        return cur.fetchall()


def get_program_state(conn, program_id: int) -> Optional[Program]:
    query = "SELECT * FROM programs WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(query, (program_id,))
        row = cur.fetchone()
        if not row:
            return None
        col_names = [desc[0] for desc in cur.description]
        return Program.from_row(dict(zip(col_names, row)))


# --- Environment / Replay -------------------------------------------------


def create_instance_and_task(
    version: int, address: str, tcp_port: int
) -> tuple[FactorioInstance, Any]:
    conn = get_db_connection()
    try:
        query = """
            SELECT meta FROM programs
            WHERE version = %s
            AND meta IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
        """
        with conn.cursor() as cur:
            cur.execute(query, (version,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No programs found for version {version}")

            meta = result[0]
            description = meta.get("version_description", "")
            task_key = None
            if "type:" in description:
                task_key = description.split("type:")[1].split("\n")[0].strip()

            task = TaskFactory.create_task(task_key or "iron_plate_throughput")

            instance = FactorioInstance(
                address=address,
                tcp_port=tcp_port,
                fast=True,
                cache_scripts=True,
                peaceful=True,
                enable_admin_tools_in_runtime=True,
            )
            instance.set_speed_and_unpause(1.0)
            task.setup(instance)
            return instance, task
    finally:
        conn.close()


# --- Cinematography -------------------------------------------------------


def build_runtime_prelude() -> str:
    """Build the runtime prelude code that sets up cinema infrastructure."""
    return r'''
# === CINEMA PRELUDE (auto-injected) ===
# Note: This code runs in the Factorio namespace context where variables are available directly
if "_cinema_shots" not in globals():
    _cinema_shots = []

def _cinema_emit(intent):
    # Intent must already match server.lua schema
    _cinema_shots.append(intent)

def _bbox_two_points(p1, p2, pad):
    if not p1 or not p2: 
        return [[player_location.x-20, player_location.y-20],
                [player_location.x+20, player_location.y+20]]
    x1,y1 = p1[0], p1[1]
    x2,y2 = p2[0], p2[1]
    lo_x, hi_x = (x1 if x1<x2 else x2) - pad, (x2 if x2>x1 else x1) + pad
    lo_y, hi_y = (y1 if y1<y2 else y2) - pad, (y2 if y2>y1 else y1) + pad
    return [[lo_x, lo_y], [hi_x, hi_y]]

def _resolve_entity_pos(e):
    try:
        if hasattr(e, "position"):
            return [e.position.x, e.position.y]
        # group-like fallbacks (best-effort)
        if hasattr(e, "poles") and e.poles:
            return [e.poles[0].position.x, e.poles[0].position.y]
        if hasattr(e, "pipes") and e.pipes:
            return [e.pipes[0].position.x, e.pipes[0].position.y]
        if hasattr(e, "drop_position"):
            return [e.drop_position.x, e.drop_position.y]
    except Exception:
        pass
    return [player_location.x, player_location.y]

def _emit_focus_pos(pos, pan_ms, dwell_ms, zoom, id_prefix, tick=None, tags=None):
    t = _get_elapsed_ticks() if tick is None else tick
    intent = {
        "id": f"{id_prefix}-{t}",
        "pri": 10,
        "when": {"start_tick": t},
        "kind": {"type": "focus_position", "pos": pos},
        "pan_ms": pan_ms, "dwell_ms": dwell_ms
    }
    if zoom is not None:
        intent["zoom"] = zoom
    if tags:
        intent["tags"] = tags
    _cinema_emit(intent)

def _emit_zoom_to_fit_bbox(bbox, pan_ms, dwell_ms, zoom, id_prefix, tick=None, tags=None):
    t = _get_elapsed_ticks() if tick is None else tick
    intent = {
        "id": f"{id_prefix}-{t}",
        "pri": 8,
        "when": {"start_tick": t},
        "kind": {"type": "zoom_to_fit", "bbox": bbox},
        "pan_ms": pan_ms, "dwell_ms": dwell_ms
    }
    if zoom is not None:
        intent["zoom"] = zoom
    if tags:
        intent["tags"] = tags
    _cinema_emit(intent)
# === /CINEMA PRELUDE ===
'''


def build_runtime_trailer() -> str:
    """Build the runtime trailer code that flushes cinema shots."""
    return r'''
# === CINEMA FLUSH (auto-injected) ===
if "_cinema_shots" in globals() and _cinema_shots:
    _cutscene({"player": 1, "shots": _cinema_shots})
    _cinema_shots = []
# === /CINEMA FLUSH ===
'''


def render_pre_snippets_for_site(site, policy: ShotPolicy) -> list[str]:
    """
    Return a list of Python code strings to inject BEFORE the action line.
    MVP: only PRE snippets (no POST, no movement debouncer yet).
    """
    pre = []
    # MOVE_TO: pre-arrival cut (if enabled)
    if site.kind == "move_to" and policy.pre_arrival_cut:
        tpl = ShotLib.cut_to_pos(zoom=0.9)
        # pos_expr_src: new field provided by ast_actions for the first arg (string as it appears in code)
        pos_src = site.args.get("pos_src")  # e.g., "coords.center" or "Position(x=15, y=-3)"
        # Use template constants with our runtime helper
        pre.append(
            f'''_emit_focus_pos({pos_src}, {tpl.pan_ms}, {tpl.dwell_ms}, {tpl.zoom if tpl.zoom is not None else 'None'}, "cut")'''
        )

    # CONNECT_ENTITIES: pre zoom-to-fit on endpoints
    if site.kind == "connect_entities":
        tpl_pre, tpl_post = ShotLib.connection_two_point(padding=policy.connection_padding_tiles)
        a_src = site.args.get("a_src")  # identifier/expr text from AST
        b_src = site.args.get("b_src")
        # runtime compute positions + bbox, then emit zoom-to-fit using template timings/zoom
        pre.append(
            f'''_emit_zoom_to_fit_bbox(_bbox_two_points(_resolve_entity_pos({a_src}), _resolve_entity_pos({b_src}), {policy.connection_padding_tiles}), {tpl_pre.pan_ms}, {tpl_pre.dwell_ms}, {tpl_pre.zoom if tpl_pre.zoom is not None else 'None'}, "conn-pre")'''
        )

    # PLACE_ENTITY: simple pre reveal is usually unnecessary; skip in MVP.
    return pre


def build_runtime_prelude() -> str:
    """Build the runtime prelude code that sets up cinema infrastructure."""
    return r'''
# === CINEMA PRELUDE (auto-injected) ===
# Note: This code runs in the Factorio namespace context where variables are available directly
if "_cinema_shots" not in globals():
    _cinema_shots = []

def _cinema_emit(intent):
    # Intent must already match server.lua schema
    _cinema_shots.append(intent)

def _bbox_two_points(p1, p2, pad):
    if not p1 or not p2: 
        return [[player_location.x-20, player_location.y-20],
                [player_location.x+20, player_location.y+20]]
    x1,y1 = p1[0], p1[1]
    x2,y2 = p2[0], p2[1]
    lo_x, hi_x = (x1 if x1<x2 else x2) - pad, (x2 if x2>x1 else x1) + pad
    lo_y, hi_y = (y1 if y1<y2 else y2) - pad, (y2 if y2>y1 else y1) + pad
    return [[lo_x, lo_y], [hi_x, hi_y]]

def _resolve_entity_pos(e):
    try:
        if hasattr(e, "position"):
            return [e.position.x, e.position.y]
        # group-like fallbacks (best-effort)
        if hasattr(e, "poles") and e.poles:
            return [e.poles[0].position.x, e.poles[0].position.y]
        if hasattr(e, "pipes") and e.pipes:
            return [e.pipes[0].position.x, e.pipes[0].position.y]
        if hasattr(e, "drop_position"):
            return [e.drop_position.x, e.drop_position.y]
    except Exception:
        pass
    return [player_location.x, player_location.y]

def _emit_focus_pos(pos, pan_ms, dwell_ms, zoom, id_prefix, tick=None, tags=None):
    t = _get_elapsed_ticks() if tick is None else tick
    intent = {
        "id": f"{id_prefix}-{t}",
        "pri": 10,
        "when": {"start_tick": t},
        "kind": {"type": "focus_position", "pos": pos},
        "pan_ms": pan_ms, "dwell_ms": dwell_ms
    }
    if zoom is not None:
        intent["zoom"] = zoom
    if tags:
        intent["tags"] = tags
    _cinema_emit(intent)

def _emit_zoom_to_fit_bbox(bbox, pan_ms, dwell_ms, zoom, id_prefix, tick=None, tags=None):
    t = _get_elapsed_ticks() if tick is None else tick
    intent = {
        "id": f"{id_prefix}-{t}",
        "pri": 8,
        "when": {"start_tick": t},
        "kind": {"type": "zoom_to_fit", "bbox": bbox},
        "pan_ms": pan_ms, "dwell_ms": dwell_ms
    }
    if zoom is not None:
        intent["zoom"] = zoom
    if tags:
        intent["tags"] = tags
    _cinema_emit(intent)
# === /CINEMA PRELUDE ===
'''


def build_runtime_trailer() -> str:
    """Build the runtime trailer code that flushes cinema shots."""
    return r'''
# === CINEMA FLUSH (auto-injected) ===
if "_cinema_shots" in globals() and _cinema_shots:
    _cutscene({"player": 1, "shots": _cinema_shots})
    _cinema_shots = []
# === /CINEMA FLUSH ===
'''


def render_pre_snippets_for_site(site, policy: ShotPolicy) -> list[str]:
    """
    Return a list of Python code strings to inject BEFORE the action line.
    MVP: only PRE snippets (no POST, no movement debouncer yet).
    """
    pre = []
    # MOVE_TO: pre-arrival cut (if enabled)
    if site.kind == "move_to" and policy.pre_arrival_cut:
        tpl = ShotLib.cut_to_pos(zoom=0.9)
        # pos_expr_src: new field provided by ast_actions for the first arg (string as it appears in code)
        pos_src = site.args.get("pos_src")  # e.g., "coords.center" or "Position(x=15, y=-3)"
        # Use template constants with our runtime helper
        pre.append(
            f'''_emit_focus_pos({pos_src}, {tpl.pan_ms}, {tpl.dwell_ms}, {tpl.zoom if tpl.zoom is not None else 'None'}, "cut")'''
        )

    # CONNECT_ENTITIES: pre zoom-to-fit on endpoints
    if site.kind == "connect_entities":
        tpl_pre, tpl_post = ShotLib.connection_two_point(padding=policy.connection_padding_tiles)
        a_src = site.args.get("a_src")  # identifier/expr text from AST
        b_src = site.args.get("b_src")
        # runtime compute positions + bbox, then emit zoom-to-fit using template timings/zoom
        pre.append(
            f'''_emit_zoom_to_fit_bbox(_bbox_two_points(_resolve_entity_pos({a_src}), _resolve_entity_pos({b_src}), {policy.connection_padding_tiles}), {tpl_pre.pan_ms}, {tpl_pre.dwell_ms}, {tpl_pre.zoom if tpl_pre.zoom is not None else 'None'}, "conn-pre")'''
        )

    # PLACE_ENTITY: simple pre reveal is usually unnecessary; skip in MVP.
    return pre


def parse_program_actions(code: str) -> List[Dict[str, Any]]:
    """Parse a program's code to extract Factorio actions using AST.

    Returns:
        List of action dictionaries with type, args, and line_no.
    """
    # Keep signature for callers like debug tool
    return [  # normalize ActionSite -> dict for pretty-print
        {"type": s.kind, "args": s.args, "line_span": s.line_span}
        for s in parse_actions(code)
    ]


# Removed old manual implementations - now using AST-based template system
def splice_cinema_code(original_code: str, action_sites: list, policy: ShotPolicy = POLICY) -> str:
    """Splice cinema code between actions in the original program using AST integration."""
    lines = original_code.splitlines()
    insertions_before: dict[int, list[str]] = {}

    for site in action_sites:
        pre_snips = render_pre_snippets_for_site(site, policy)
        if pre_snips:
            # use site.line_span[0] as 1-based start line; convert to 0-based index
            idx0 = max(0, (site.line_span[0]-1))
            insertions_before.setdefault(idx0, []).extend(pre_snips)

    out = []
    injected_prelude = False
    for i, line in enumerate(lines):
        if not injected_prelude:
            out.append(build_runtime_prelude())
            injected_prelude = True
        if i in insertions_before:
            out.extend(insertions_before[i])
        out.append(line)

    out.append(build_runtime_trailer())
    return "\n".join(out)


def detect_game_events(
    instance: FactorioInstance,
    program: Any,
    response: tuple,
    previous_state: Dict[str, Any],
) -> List[tuple[str, Dict[str, Any]]]:
    """Detect game events by analyzing program actions and game state changes.

    Returns:
        List of (event_type, delta) tuples for multiple detected events.
    """
    current_tick = instance.get_elapsed_ticks()
    namespace_pos = (
        instance.namespace.player_location if hasattr(instance, "namespace") else None
    )
    pos = (
        [namespace_pos.x, namespace_pos.y]
        if namespace_pos and hasattr(namespace_pos, "x")
        else [0, 0]
    )

    events = []
    seen_events = set()  # Track seen events to prevent duplicates

    # Parse actions from the program code (just to identify what actions exist)
    actions = parse_program_actions(program.code) if program and program.code else []

    # Get current game state
    current_state = {
        "tick": current_tick,
        "position": pos,
        "prints": response[1] or "",
        "errors": response[2] or "",
        "actions": actions,
    }

    # 1. DETECT MOVEMENT EVENTS based on actual position changes
    if previous_state and "position" in previous_state:
        prev_pos = previous_state["position"]
        distance = ((pos[0] - prev_pos[0]) ** 2 + (pos[1] - prev_pos[1]) ** 2) ** 0.5

        # Only create significant movement events (more than 10 tiles)
        if distance >= 10:
            event_type = "player_movement"
            delta = {
                "position": pos,
                "movement_distance": distance,
                "from_position": prev_pos,
                "to_position": pos,
            }

            # Create a bounding box around the movement path
            center_x = (pos[0] + prev_pos[0]) / 2
            center_y = (pos[1] + prev_pos[1]) / 2
            padding = max(distance / 2, 15)  # Dynamic padding based on distance

            delta["movement_bbox"] = [
                [center_x - padding, center_y - padding],
                [center_x + padding, center_y + padding],
            ]
            delta["movement_center"] = [center_x, center_y]

            event_key = f"player_movement_{current_tick}_{pos}"
            if event_key not in seen_events:
                seen_events.add(event_key)
                events.append((event_type, delta))

    # 2. DETECT CONNECT_ENTITIES EVENTS based on action detection + game state
    has_connect_actions = any(
        action["type"] == "connect_entities" for action in actions
    )
    if has_connect_actions:
        event_type = "infrastructure_connection"
        delta = {"position": pos}

        # Try to get entities around the player position to find what was connected
        try:
            # Get entities in a reasonable radius around the player
            entities = instance.first_namespace.get_entities(
                position=pos,
                radius=50,  # Look in a 50-tile radius
                limit=100,
            )

            if entities and len(entities) >= 2:
                # Find the most recent entities (assuming they were just placed)
                recent_entities = sorted(
                    entities, key=lambda e: getattr(e, "tick", 0), reverse=True
                )[:2]

                if len(recent_entities) >= 2:
                    # Calculate bounding box that encompasses both entities with padding
                    positions = []
                    for entity in recent_entities:
                        if hasattr(entity, "position"):
                            positions.append([entity.position.x, entity.position.y])

                    if len(positions) >= 2:
                        # Calculate min/max coordinates
                        min_x = min(pos[0] for pos in positions)
                        max_x = max(pos[0] for pos in positions)
                        min_y = min(pos[1] for pos in positions)
                        max_y = max(pos[1] for pos in positions)

                        # Add padding (20 tiles)
                        padding = 20
                        delta["connection_bbox"] = [
                            [min_x - padding, min_y - padding],
                            [max_x + padding, max_y + padding],
                        ]
                        delta["center_position"] = [
                            (min_x + max_x) / 2,
                            (min_y + max_y) / 2,
                        ]
                        delta["entity_count"] = len(recent_entities)

                        # Determine connection type based on entity types
                        entity_types = [getattr(e, "name", "") for e in recent_entities]
                        if any("belt" in et for et in entity_types):
                            event_type = "belt_connection"
                        elif any("pole" in et for et in entity_types):
                            event_type = "power_connection"
                        elif any("pipe" in et for et in entity_types):
                            event_type = "fluid_connection"
                        else:
                            event_type = "infrastructure_connection"

            # Fallback to player position if we can't find entities
            if "connection_bbox" not in delta:
                delta["factory_bbox"] = [
                    [pos[0] - 30, pos[1] - 30],
                    [pos[0] + 30, pos[1] + 30],
                ]

        except Exception:
            # Fallback if entity detection fails
            delta["factory_bbox"] = [
                [pos[0] - 30, pos[1] - 30],
                [pos[0] + 30, pos[1] + 30],
            ]

        event_key = f"{event_type}_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append((event_type, delta))

    # 3. DETECT PLACE_ENTITY EVENTS based on action detection + game state
    for action in actions:
        if action["type"] == "place_entity":
            entity_type = action.get("args", {}).get("prototype") or ""
            entity_type = entity_type.lower() if entity_type else ""

            # Only create events if we have a valid entity type
            if entity_type:
                event_type = None
                delta = {"position": pos, "entity_type": entity_type}

                # Classify entity placements
                if entity_type in [
                    "boiler",
                    "steam_engine",
                    "offshorepump",
                    "offshore_pump",
                ]:
                    event_type = "power_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 15, pos[1] - 15],
                        [pos[0] + 15, pos[1] + 15],
                    ]
                elif entity_type in [
                    "burner_mining_drill",
                    "electric_mining_drill",
                    "burnerminingdrill",
                    "electricminingdrill",
                ]:
                    event_type = "mining_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 10, pos[1] - 10],
                        [pos[0] + 10, pos[1] + 10],
                    ]
                elif entity_type in [
                    "stone_furnace",
                    "steel_furnace",
                    "electric_furnace",
                    "stonefurnace",
                    "steelfurnace",
                    "electricfurnace",
                ]:
                    event_type = "smelting_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 8, pos[1] - 8],
                        [pos[0] + 8, pos[1] + 8],
                    ]
                elif entity_type in [
                    "assembly_machine_1",
                    "assembly_machine_2",
                    "assembly_machine_3",
                    "assemblymachine1",
                    "assemblymachine2",
                    "assemblymachine3",
                ]:
                    event_type = "assembly_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 12, pos[1] - 12],
                        [pos[0] + 12, pos[1] + 12],
                    ]
                elif entity_type in ["lab"]:
                    event_type = "research_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 8, pos[1] - 8],
                        [pos[0] + 8, pos[1] + 8],
                    ]
                else:
                    event_type = "building_placed"
                    delta["factory_bbox"] = [
                        [pos[0] - 5, pos[1] - 5],
                        [pos[0] + 5, pos[1] + 5],
                    ]

                if event_type:
                    event_key = f"{event_type}_{current_tick}_{entity_type}_{pos}"
                    if event_key not in seen_events:
                        seen_events.add(event_key)
                        events.append((event_type, delta))

    # Also check for events based on game output
    prints_lower = current_state["prints"].lower()

    # Check for fuel inserter events
    if "inserter" in prints_lower and "fuel" in prints_lower:
        event_key = f"fuel_inserter_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append(("fuel_inserter", {"position": pos}))

    # Check for power/electricity events
    if any(
        keyword in prints_lower for keyword in ["power", "electric", "steam", "boiler"]
    ):
        if any(
            keyword in prints_lower for keyword in ["online", "connected", "working"]
        ):
            event_key = f"power_online_{current_tick}_{pos}"
            if event_key not in seen_events:
                seen_events.add(event_key)
                events.append(
                    (
                        "power_online",
                        {
                            "position": pos,
                            "factory_bbox": [
                                [pos[0] - 25, pos[1] - 25],
                                [pos[0] + 25, pos[1] + 25],
                            ],
                        },
                    )
                )

    # Check for production/completion events
    if any(
        keyword in prints_lower for keyword in ["completed", "finished", "production"]
    ):
        event_key = f"production_milestone_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append(
                (
                    "production_milestone",
                    {
                        "position": pos,
                        "factory_bbox": [
                            [pos[0] - 30, pos[1] - 30],
                            [pos[0] + 30, pos[1] + 30],
                        ],
                    },
                )
            )

    return events


def process_programs(
    version: int,
    cin: Cinematographer,
    instance: FactorioInstance,
    programs: Iterable[tuple[int, Any]],
    conn,
    max_steps: int,
) -> Dict[str, Any]:
    # Note: cutscene tool is now available directly in the runtime namespace
    # No need for external cutscene_tool instance

    print(
        f"Processing version {version} with {len(list(programs))} programs (max {max_steps} steps)"
    )
    programs = list(programs)  # Convert back to list after len() call

    instance.reset()
    print("Environment reset complete")

    screenshot_sequences: List[Dict[str, Any]] = []

    # Track game state for event detection
    previous_state = None
    total_events_detected = 0

    for idx, (program_id, created_at) in enumerate(programs):
        if idx >= max_steps:
            print(f"Reached maximum steps limit ({max_steps}), stopping")
            break

        print(f"\n--- Processing program {idx + 1}/{len(programs)}: {program_id} ---")

        program = get_program_state(conn, program_id)
        if not program or not program.code:
            print(f"Skipping program {program_id} - no code available")
            continue

        print(f"Code preview: {program.code[:100]}...")

        if program.state:
            print("Resetting environment with program state")
            instance.reset(program.state)

        # Parse actions and splice cinema code
        action_sites = parse_actions(program.code) if program.code else []
        cinema_code = splice_cinema_code(program.code, action_sites, POLICY)

        print("Executing program with cinema code...")
        print(f"Original code length: {len(program.code)}")
        print(f"Cinema-spliced code length: {len(cinema_code)}")

        # Enable admin tools in the namespace for cinema functionality
        instance.first_namespace.enable_admin_tools_in_runtime(True)

        response = instance.eval(cinema_code)
        
        # Disable admin tools after execution to maintain security
        instance.first_namespace.enable_admin_tools_in_runtime(False)

        # Log execution results
        if response[2]:  # errors
            print(f"Execution errors: {response[2]}")
        if response[1]:  # prints
            print(f"Program output: {response[1]}")

        screenshot_sequences.append(
            {
                "program_id": program_id,
                "code": program.code,
                "cinema_code": cinema_code,
                "actions": parse_program_actions(program.code),
                "prints": response[1],
                "errors": response[2],
                "created_at": str(created_at),
            }
        )

        # Detect multiple game events from this program execution
        events = detect_game_events(instance, program, response, previous_state)

        current_tick = instance.get_elapsed_ticks()
        namespace_pos = (
            instance.namespace.player_location
            if hasattr(instance, "namespace")
            else None
        )
        pos = (
            [namespace_pos.x, namespace_pos.y]
            if namespace_pos and hasattr(namespace_pos, "x")
            else [0, 0]
        )

        print(f"Current game state: tick={current_tick}, position={pos}")
        print(f"Detected {len(events)} events from program execution")

        # Process each detected event
        for event_type, delta in events:
            total_events_detected += 1
            event = {
                "tick": current_tick,
                "event": event_type,
                "position": delta.get("position", pos),
            }

            # Observe the event with cinematographer
            cin.observe(event, delta)

            print(
                f"  Event {total_events_detected}: '{event_type}' at {event['position']}"
            )
            if delta.get("factory_bbox"):
                print(f"    Factory bbox: {delta['factory_bbox']}")
            if delta.get("entity_type"):
                print(f"    Entity type: {delta['entity_type']}")

        # Update previous state for next iteration
        previous_state = {
            "tick": current_tick,
            "position": pos,
            "prints": response[1] or "",
        }

        # Note: Cutscenes are now handled directly in the spliced code
        # No need for external cutscene management here

    # Note: All cutscenes are now handled directly in the spliced code
    # No need for external cutscene plan management

    print("\nProcessing complete:")
    print(f"  - Total programs processed: {min(len(programs), max_steps)}")
    print(f"  - Total events detected: {total_events_detected}")
    print("  - Cutscenes handled directly in runtime context")

    return {
        "programs": screenshot_sequences,
        "stats": {
            "programs_processed": min(len(programs), max_steps),
            "events_detected": total_events_detected,
            "cutscenes_in_runtime": True,
        },
    }


# --- CLI -----------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Replay programs with cinematics")
    parser.add_argument("versions", nargs="+", type=int)
    parser.add_argument("--output-dir", "-o", default="cinema_runs")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument(
        "--address", default=os.getenv("FACTORIO_SERVER_ADDRESS", "localhost")
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=int(os.getenv("FACTORIO_SERVER_PORT", "27000")),
    )
    args = parser.parse_args()

    output_base = Path(args.output_dir)
    output_base.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        for version in args.versions:
            programs = get_program_chain(conn, version)
            if not programs:
                print(f"No programs for version {version}")
                continue

            instance, task = create_instance_and_task(
                version, args.address, args.tcp_port
            )
            instance.set_speed_and_unpause(1.0)
            cin = Cinematographer(CameraPrefs(), GameClock())
            report = process_programs(
                version, cin, instance, programs, conn, args.max_steps
            )

            out_dir = output_base / str(version)
            out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "plan.json").open("w", encoding="utf-8") as fh:
            json.dump(report["plan"], fh, indent=2)
        with (out_dir / "enqueue.json").open("w", encoding="utf-8") as fh:
            json.dump(report["enqueue"], fh, indent=2)
        with (out_dir / "programs.json").open("w", encoding="utf-8") as fh:
            json.dump(report["programs"], fh, indent=2)

            print(f"Version {version}: plan written to {out_dir}")
            instance.cleanup()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
