"""
End-to-end pipeline for replay → cinematics.

This mirrors `run_to_mp4.py` but replaces "take screenshots after each
program" logic with action-driven shot generation via the Cinematographer.

ORCHESTRATOR ONLY: This module orchestrates the pipeline but does NOT emit shots.
Cinematographer receives an action stream + world resolvers (resolve_position, bbox_two_points) and is solely responsible for mapping to shot intents.
It calls ast_actions to extract normalized actions, provides world context to
Cinematographer, and executes the resulting plan. All shot decisions are made
by the Cinematographer module.

Usage (CLI):

    python -m fle.eval.analysis.runtime_to_cinema VERSION --output-dir vids

It will:
    1. Fetch programs for the requested version from Postgres.
    2. Replay them in a gym environment.
    3. Extract normalized actions using ast_actions.
    4. Feed actions + world context into Cinematographer.observe_action_stream.
    5. Submit the resulting plan to the admin Cutscene tool.
    6. Optionally wait for completion and fetch the shot report.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import time
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

from fle.env import FactorioInstance
from fle.eval.analysis.cinematographer import ShotPolicy
from fle.eval.analysis.ast_actions import parse_actions, create_action_stream
from fle.commons.models.program import Program
from fle.eval.tasks.task_factory import TaskFactory

# Import Cinematographer and related classes
from fle.eval.analysis.cinematographer import Cinematographer, CameraPrefs, GameClock


load_dotenv()


# --- Remote (RCON) helpers for screenshot capture --------------------------


def _lua_bool(b: bool) -> str:
    return "true" if b else "false"


def _start_frame_capture(
    instance: FactorioInstance,
    *,
    player_index: int = 1,
    nth: int = 6,
    dir_prefix: str = "cinema_seq",
    res: tuple[int, int] = (1920, 1080),
    quality: int = 100,
    show_gui: bool = False,
    subdir: str | None = None,
) -> None:
    """Tell the mod-side remote interface to start continuous capture on a rendering client.
    This captures the *player's current view* (cutscene camera), so we don't need to pass zoom/position.
    """
    w, h = res
    # Build directory path inside client's script-output. Factorio will create nested dirs.
    if subdir:
        full_dir = f"{dir_prefix}/{subdir}"
    else:
        full_dir = dir_prefix
    cmd = (
        'remote.call("cinema_capture","start", '
        f'{{player_index={player_index}, nth={nth}, dir="{full_dir}", res={{{w},{h}}}, quality={quality}, show_gui={_lua_bool(show_gui)}}})'
    )
    try:
        instance.rcon_client.send_command(f"/c {cmd}")
    except Exception as e:
        print(f"[capture] start failed: {e}")


def _stop_frame_capture(instance: FactorioInstance) -> None:
    cmd = 'remote.call("cinema_capture","stop")'
    try:
        instance.rcon_client.send_command(f"/c {cmd}")
    except Exception as e:
        print(f"[capture] stop failed: {e}")


# --- Module-level defaults -------------------------------------------------

# Note: connection shots now provide pan_ticks/dwell_ticks; Lua prefers tick timing when present.
POLICY = ShotPolicy()  # use defaults

# Environment toggle for pre-establish move shots
PRE_ESTABLISH_MOVES = os.getenv("PRE_ESTABLISH_MOVES", "1") in (
    "1",
    "true",
    "TRUE",
    "yes",
    "on",
)

# Pre-connection establishing shot toggle
PRE_CONNECT_ESTABLISH = os.getenv("PRE_CONNECT_ESTABLISH", "1") in (
    "1",
    "true",
    "TRUE",
    "yes",
    "on",
)

# Execute cutscene every N programs (override via env CINEMA_EVERY_N)
EXECUTE_EVERY_N = int(os.getenv("CINEMA_EVERY_N", "4"))


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
            instance.set_speed(1.0)
            task.setup(instance)
            return instance, task
    finally:
        conn.close()


# --- Cinematography -------------------------------------------------------


def build_world_context(instance: FactorioInstance, program: Any) -> dict:
    """Build lightweight world context for Cinematographer.

    This provides the minimal world facts that Cinematographer needs to make
    shot decisions. It does NOT emit shots or make camera decisions.
    """
    # No longer need current_tick for shot timing
    namespace_pos = (
        instance.namespace.player_location if hasattr(instance, "namespace") else None
    )
    player_position = (
        [namespace_pos.x, namespace_pos.y]
        if namespace_pos and hasattr(namespace_pos, "x")
        else [0, 0]
    )

    def _resolve_position(expr: Any) -> list:
        """Best-effort resolver for positions from strings/structured args."""
        # Already numeric list
        if isinstance(expr, (list, tuple)) and len(expr) >= 2:
            return [float(expr[0]), float(expr[1])]
        # String forms we already parse in Cinematographer
        if isinstance(expr, str):
            import re

            m = re.search(r"x=([+-]?\d+(?:\.\d+)?).*?y=([+-]?\d+(?:\.\d+)?)", expr)
            if m:
                return [float(m.group(1)), float(m.group(2))]
            # Try to resolve obj.attr chains like "foo.position"
            parts = expr.split(".")
            if len(parts) >= 2 and parts[-1] == "position":
                name = ".".join(parts[:-1])
                try:
                    # Try to fetch by last known entity name in namespace if available
                    ent = getattr(instance.first_namespace, name, None)
                    if ent and hasattr(ent, "position"):
                        p = ent.position
                        return (
                            [float(p[0]), float(p[1])]
                            if isinstance(p, (list, tuple))
                            else [float(p.x), float(p.y)]
                        )
                except Exception:
                    pass
            # Fallback: try resolving bare variable names on the namespace
            try:
                ent = getattr(instance.first_namespace, expr, None)
                if ent is not None:
                    # Entity-like object exposing .position or .x/.y
                    p = getattr(ent, "position", None)
                    if p is not None:
                        if isinstance(p, (list, tuple)):
                            return [float(p[0]), float(p[1])]
                        else:
                            return [float(p.x), float(p.y)]
                    px = getattr(ent, "x", None)
                    py = getattr(ent, "y", None)
                    if px is not None and py is not None:
                        return [float(px), float(py)]
            except Exception:
                pass
        # Fallback to current player position
        return player_position

    def _bbox_two_points(a_expr: Any, b_expr: Any, pad: float = 25.0) -> list:
        a = _resolve_position(a_expr)
        b = _resolve_position(b_expr)
        x1, y1 = a
        x2, y2 = b
        left, right = min(x1, x2) - pad, max(x1, x2) + pad
        top, bottom = min(y1, y2) - pad, max(y1, y2) + pad
        return [[left, top], [right, bottom]]

    def _resolve_bbox(expr: Any, pad: float = 0.0) -> list:
        # Try to resolve single position first
        try:
            pos = _resolve_position(expr)
            if pos is not None:
                x, y = pos
                return [[x - pad, y - pad], [x + pad, y + pad]]
        except Exception:
            pass
        # Try to look up an object by name on the namespace (groups, connection results)
        try:
            if isinstance(expr, str):
                obj = getattr(instance.first_namespace, expr, None)
                if obj is not None:
                    # If it has a bounding_box
                    bb = getattr(obj, "bounding_box", None)
                    if bb and hasattr(bb, "left"):
                        return [
                            [float(bb.left), float(bb.top)],
                            [float(bb.right), float(bb.bottom)],
                        ]
                    # If it exposes poles/pipes etc.
                    for attr in ("poles", "pipes", "entities", "items"):
                        coll = getattr(obj, attr, None)
                        if coll:
                            xs, ys = [], []
                            for it in coll:
                                p = getattr(it, "position", None) or getattr(
                                    it, "pos", None
                                )
                                if p is not None:
                                    if isinstance(p, (list, tuple)):
                                        xs.append(float(p[0]))
                                        ys.append(float(p[1]))
                                    else:
                                        xs.append(float(p.x))
                                        ys.append(float(p.y))
                            if xs and ys:
                                return [
                                    [min(xs) - pad, min(ys) - pad],
                                    [max(xs) + pad, max(ys) + pad],
                                ]
                    # If it looks like an (x,y) pair stored on the object
                    px = getattr(obj, "x", None)
                    py = getattr(obj, "y", None)
                    if px is not None and py is not None:
                        return [
                            [float(px) - pad, float(py) - pad],
                            [float(px) + pad, float(py) + pad],
                        ]
        except Exception:
            pass
        # Fallback to a tiny box around player
        return [
            [player_position[0] - pad, player_position[1] - pad],
            [player_position[0] + pad, player_position[1] + pad],
        ]

    def _bbox_from_exprs(a_expr: Any, b_expr: Any, pad_outer: float = 25.0) -> list:
        bb_a = _resolve_bbox(a_expr, 0.0)
        bb_b = _resolve_bbox(b_expr, 0.0)
        left = min(bb_a[0][0], bb_b[0][0]) - pad_outer
        top = min(bb_a[0][1], bb_b[0][1]) - pad_outer
        right = max(bb_a[1][0], bb_b[1][0]) + pad_outer
        bottom = max(bb_a[1][1], bb_b[1][1]) + pad_outer
        return [[left, top], [right, bottom]]

    # Debug hook: uncomment for noisy resolution tracing
    # print(f"[world] player={player_position}")
    return {
        "player_position": player_position,
        "program_id": getattr(program, "id", None) if program else None,
        "resolve_position": _resolve_position,
        "bbox_two_points": _bbox_two_points,
        "resolve_bbox": _resolve_bbox,
        "bbox_from_exprs": _bbox_from_exprs,
    }


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


# Removed detect_game_events function - we now use action-driven approach
# where Cinematographer maps actions directly to shots instead of detecting
# events from game state changes.


def process_programs(
    version: int,
    cin: Cinematographer,
    instance: FactorioInstance,
    programs: Iterable[tuple[int, Any]],
    conn,
    max_steps: int,
    capture_opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process programs and generate cinema shots using clean orchestration.

    This function orchestrates the pipeline but does NOT emit shots. It:
    1. Extracts normalized actions using ast_actions
    2. Provides world context to Cinematographer
    3. Executes the resulting plan
    Handles screenshot capture lifecycle if enabled via capture_opts.
    """

    print(
        f"Processing version {version} with {len(list(programs))} programs (max {max_steps} steps)"
    )
    programs = list(programs)  # Convert back to list after len() call

    instance.reset()
    print("Environment reset complete")
    instance.first_namespace.enable_admin_tools_in_runtime(True)

    capture_opts = capture_opts or {}
    cap_enabled = capture_opts.get("enabled", True)
    cap_player = int(capture_opts.get("player_index", 1))
    cap_nth = int(capture_opts.get("nth", 6))
    cap_dir_prefix = str(capture_opts.get("dir_prefix", "cinema_seq"))
    cap_res = tuple(capture_opts.get("res", (1920, 1080)))
    cap_quality = int(capture_opts.get("quality", 100))
    cap_show_gui = bool(capture_opts.get("show_gui", False))
    run_slug = datetime.now().strftime("%Y%m%d_%H%M%S")

    screenshot_sequences: List[Dict[str, Any]] = []
    total_actions_processed = 0

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

        # Extract normalized actions using ast_actions (stateless extractor)
        action_sites = (
            parse_actions(
                program.code,
                program_id=str(program_id),
                created_at=created_at.timestamp()
                if hasattr(created_at, "timestamp")
                else None,
            )
            if program.code
            else []
        )

        # Build a failure-aware filter based on runtime errors
        error_text = ""
        # try:
        #     if response and len(response) >= 3 and response[2]:
        #         error_text = "\n".join([str(e) for e in response[2]])
        # except Exception:
        #     pass

        def _should_keep(site) -> bool:
            k = getattr(site, "kind", "")
            if "Could not place" in error_text and k in {
                "place_entity",
                "place_entity_next_to",
            }:
                return False
            if "Did not find any valid connections" in error_text and k in {
                "connect_entities"
            }:
                return False
            return True

        if action_sites:
            action_sites = [s for s in action_sites if _should_keep(s)]

        print(f"Extracted {len(action_sites)} actions from program")

        # Debug: how many shots are currently queued before mapping this program
        print(f"[cinema] queued shots before mapping: {len(cin.shots)}")

        # --- Pre-connection establishing shot logic ---
        pre_connect_done = False
        has_connect = any(
            getattr(s, "kind", "") == "connect_entities" for s in action_sites
        )
        if has_connect and PRE_CONNECT_ESTABLISH:
            pre_world = build_world_context(instance, program)
            first_conn = next(
                (
                    s
                    for s in action_sites
                    if getattr(s, "kind", "") == "connect_entities"
                ),
                None,
            )
            if first_conn:
                a_expr = first_conn.args.get("a_expr")
                b_expr = first_conn.args.get("b_expr")
                if callable(pre_world.get("bbox_from_exprs")):
                    bbox = pre_world["bbox_from_exprs"](a_expr, b_expr, pad_outer=25.0)
                else:
                    bbox = pre_world["bbox_two_points"](a_expr, b_expr, pad=25.0)
                pre_plan = {
                    "player": 1,
                    "start_zoom": 1.0,
                    "shots": [
                        {
                            "id": f"pre-conn-{program_id}-0",
                            "seq": 0,
                            "kind": {"type": "zoom_to_fit", "bbox": bbox},
                            "pan_ticks": 84,
                            "dwell_ticks": 54,
                            "zoom": None,
                            "tags": ["connection", "pre_establish"],
                        }
                    ],
                }
                try:
                    instance.first_namespace.cutscene(pre_plan)
                except Exception as e:
                    print(f"[warn] pre-connect cutscene failed: {e}")
                pre_connect_done = True
        else:
            pre_connect_done = False

        # Optional: play establishing camera moves for move_to before executing the program
        if PRE_ESTABLISH_MOVES:
            pre_moves = cin.build_move_establishments(
                create_action_stream(action_sites),
                build_world_context(instance, program),
            )
            if pre_moves:
                pre_plan = {"player": 1, "start_zoom": 1.0, "shots": pre_moves}
                print(
                    f"\nExecuting pre-establish move plan with {len(pre_moves)} shots..."
                )
                try:
                    instance.first_namespace.cutscene(pre_plan)
                except Exception as e:
                    print(f"[warn] pre-establish cutscene failed: {e}")

        # Create normalized action stream and world context before execution
        action_stream = create_action_stream(action_sites)
        world_context = build_world_context(instance, program)
        world_context["pre_connect_done"] = pre_connect_done

        # Give the cinematographer a chance to stage pre-program opening shots
        cin.observe_action_stream(action_stream, world_context)

        if idx == 0 and cin.shots:
            opening_plan = cin.build_plan(player=1)
            if opening_plan.get("shots"):
                print(
                    f"\nExecuting opening shots ({len(opening_plan['shots'])}) before replay..."
                )
                try:
                    instance.first_namespace.cutscene(opening_plan)
                except Exception as e:
                    print(f"[warn] opening cutscene failed: {e}")
                cin.reset_plan()

        # Execute the original program (no cinema code injection)
        print("Executing program...")
        response = instance.eval(program.code)

        # Log execution results
        if response[2]:  # errors
            print(f"Execution errors: {response[2]}")
        if response[1]:  # prints
            print(f"Program output: {response[1]}")

        # Refresh world context (positions may have changed after execution)
        world_context = build_world_context(instance, program)
        world_context["pre_connect_done"] = pre_connect_done

        # Recreate normalized action stream (consistent with program results)
        action_stream = create_action_stream(action_sites)

        # Feed actions + world context to Cinematographer (the single brain)
        cin.observe_action_stream(action_stream, world_context)

        # Debug: how many shots were added by this program
        # Note: "added approx" is an estimate; deduplication may affect the true count.
        print(
            f"[cinema] queued shots after mapping: {len(cin.shots)} (added {len(cin.shots) - (total_actions_processed - len(action_stream))} approx)"
        )

        total_actions_processed += len(action_stream)

        screenshot_sequences.append(
            {
                "program_id": program_id,
                "code": program.code,
                "actions": parse_program_actions(program.code),
                "prints": response[1],
                "errors": response[2],
                "created_at": str(created_at),
            }
        )

        print(
            f"Processed {len(action_stream)} actions, total: {total_actions_processed}"
        )

        # Execute cutscene periodically (configurable cadence)
        if (idx + 1) % EXECUTE_EVERY_N == 0:
            if cin.shots:  # Only if we have shots to execute
                print(
                    f"\nExecuting cutscene after program {idx + 1} with {len(cin.shots)} shots (cadence={EXECUTE_EVERY_N})..."
                )
                plan = cin.build_plan(player=1)
                # Start client-side continuous capture bound to this cutscene lifecycle
                if cap_enabled:
                    subdir = f"v{version}/batch_{(idx + 1) // EXECUTE_EVERY_N:04d}_{run_slug}"
                    _start_frame_capture(
                        instance,
                        player_index=cap_player,
                        nth=cap_nth,
                        dir_prefix=cap_dir_prefix,
                        res=cap_res,
                        quality=cap_quality,
                        show_gui=cap_show_gui,
                        subdir=subdir,
                    )
                cutscene_result = instance.first_namespace.cutscene(plan)
                print(f"Cutscene execution result: {cutscene_result}")
                # Do not stop here; Lua auto-stops on on_cutscene_finished
                # Give the event loop a moment to flush any remaining frames
                time.sleep(0.5)

                # Clear shots after execution to avoid duplicates
                cin.reset_plan()

                # Small delay to make cutscenes more visible
                time.sleep(2)

    # Build final plan from cinematographer
    plan = cin.build_plan(player=1)

    # Execute cutscene if we have shots
    cutscene_result = None
    if plan.get("shots"):
        print(f"\nExecuting final cutscene with {len(plan['shots'])} shots...")
        try:
            if cap_enabled:
                subdir = f"v{version}/final_{run_slug}"
                _start_frame_capture(
                    instance,
                    player_index=cap_player,
                    nth=cap_nth,
                    dir_prefix=cap_dir_prefix,
                    res=cap_res,
                    quality=cap_quality,
                    show_gui=cap_show_gui,
                    subdir=subdir,
                )
            cutscene_result = instance.first_namespace.cutscene(plan)
            print(f"Cutscene execution result: {cutscene_result}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error executing cutscene: {e}")

    print("\nProcessing complete:")
    print(f"  - Total programs processed: {min(len(programs), max_steps)}")
    print(f"  - Total actions processed: {total_actions_processed}")
    print(f"  - Shots generated: {len(plan.get('shots', []))}")
    print(f"  - Cutscene executed: {cutscene_result is not None}")

    try:
        instance.first_namespace.enable_admin_tools_in_runtime(False)
    except Exception:
        pass

    return {
        "programs": screenshot_sequences,
        "plan": plan,
        "enqueue": {"player": 1, "shots": plan.get("shots", [])},
        "cutscene_result": cutscene_result,
        "stats": {
            "programs_processed": min(len(programs), max_steps),
            "actions_processed": total_actions_processed,
            "shots_generated": len(plan.get("shots", [])),
            "cutscene_executed": cutscene_result is not None,
        },
    }


# --- CLI -----------------------------------------------------------------


#
# --- Filesystem helpers ----------------------------------------------------


def _detect_script_output_dir(explicit: Optional[str] = None) -> Path:
    """Resolve the Factorio script-output directory cross-platform.
    Precedence: explicit CLI arg -> env FACTORIO_SCRIPT_OUTPUT -> platform default.
    macOS: ~/Library/Application Support/factorio/script-output
    Linux: ~/.factorio/script-output or ~/.local/share/factorio/script-output (try both)
    Windows: %APPDATA%/Factorio/script-output
    """
    if explicit:
        p = Path(explicit).expanduser()
        return p
    env_p = os.getenv("FACTORIO_SCRIPT_OUTPUT")
    if env_p:
        return Path(env_p).expanduser()

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "factorio"
            / "script-output"
        )
    if os.name == "nt":
        appdata = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Factorio" / "script-output"
    # Linux / other POSIX
    candidates = [
        Path.home() / ".factorio" / "script-output",
        Path.home() / ".local" / "share" / "factorio" / "script-output",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _move_png_tree(src_root: Path, dest_root: Path) -> dict:
    """Move all .png files from src_root (recursively) into dest_root preserving subtree.
    Returns a small report dict with counts.
    """
    moved = 0
    created_dirs = 0
    dest_root.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src_root):
        root_path = Path(root)
        rel = root_path.relative_to(src_root)
        for fname in files:
            if not fname.lower().endswith(".png"):
                continue
            src_f = root_path / fname
            dst_dir = dest_root / rel
            if not dst_dir.exists():
                dst_dir.mkdir(parents=True, exist_ok=True)
                created_dirs += 1
            shutil.move(str(src_f), str(dst_dir / fname))
            moved += 1
    return {"moved": moved, "dirs_created": created_dirs}


def _render_video_from_frames(
    frames_dir: Path,
    output_dir: Path,
    *,
    script: Optional[Path] = None,
    extra_args: Optional[List[str]] = None,
) -> dict:
    """Invoke the shell helper to turn a frame tree into MP4 artifacts."""

    if not frames_dir.exists():
        return {"ok": False, "error": f"frames dir {frames_dir} missing"}

    if not any(frames_dir.rglob("*.png")):
        return {"ok": False, "error": "no png frames"}

    script_path = (
        script or Path(__file__).resolve().parents[3] / "process_cinema_frames.sh"
    )
    if not script_path.exists():
        return {"ok": False, "error": f"script {script_path} not found"}

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["bash", str(script_path), "--output", str(output_dir)]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(str(frames_dir))

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "error": f"failed to invoke script: {exc}"}

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": cmd,
    }


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
    parser.add_argument(
        "--no-capture",
        action="store_true",
        help="Disable screenshot capture via remote interface",
    )
    parser.add_argument(
        "--capture-nth",
        type=int,
        default=int(os.getenv("CINEMA_CAPTURE_NTH", "6")),
        help="Capture every Nth tick (lower = more frames)",
    )
    parser.add_argument(
        "--capture-dir",
        default=os.getenv("CINEMA_CAPTURE_DIR", "cinema_seq"),
        help="Base directory under client's script-output for frames",
    )
    parser.add_argument(
        "--capture-width",
        type=int,
        default=int(os.getenv("CINEMA_CAPTURE_WIDTH", "1920")),
    )
    parser.add_argument(
        "--capture-height",
        type=int,
        default=int(os.getenv("CINEMA_CAPTURE_HEIGHT", "1080")),
    )
    parser.add_argument(
        "--capture-quality",
        type=int,
        default=int(os.getenv("CINEMA_CAPTURE_QUALITY", "100")),
    )
    parser.add_argument(
        "--capture-show-gui", action="store_true", help="Include GUI in captured frames"
    )
    parser.add_argument(
        "--script-output-dir",
        default=os.getenv("FACTORIO_SCRIPT_OUTPUT", None),
        help="Override Factorio script-output directory (defaults to OS-specific path)",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip running process_cinema_frames.sh after moving frames",
    )
    parser.add_argument(
        "--render-arg",
        action="append",
        default=[],
        help="Additional arguments to forward to process_cinema_frames.sh",
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
            instance.set_speed(1.0)
            cin = Cinematographer(CameraPrefs(), GameClock())
            capture_opts = {
                "enabled": not args.no_capture,
                "player_index": 1,
                "nth": args.capture_nth,
                "dir_prefix": args.capture_dir,
                "res": (args.capture_width, args.capture_height),
                "quality": args.capture_quality,
                "show_gui": args.capture_show_gui,
            }
            report = process_programs(
                version, cin, instance, programs, conn, args.max_steps, capture_opts
            )

            out_dir = output_base / str(version)
            out_dir.mkdir(parents=True, exist_ok=True)

            with (out_dir / "plan.json").open("w", encoding="utf-8") as fh:
                json.dump(report["plan"], fh, indent=2)
            with (out_dir / "enqueue.json").open("w", encoding="utf-8") as fh:
                json.dump(report["enqueue"], fh, indent=2)
            with (out_dir / "programs.json").open("w", encoding="utf-8") as fh:
                json.dump(report["programs"], fh, indent=2)
            if report.get("cutscene_result"):
                with (out_dir / "cutscene_result.json").open(
                    "w", encoding="utf-8"
                ) as fh:
                    json.dump(report["cutscene_result"], fh, indent=2)

            # --- Move captured PNGs to output frames and clean script-output ---
            script_output_dir = _detect_script_output_dir(args.script_output_dir)
            src_version_root = script_output_dir / args.capture_dir / f"v{version}"
            frames_out = out_dir / "frames"
            if src_version_root.exists():
                report_move = _move_png_tree(src_version_root, frames_out)
                try:
                    shutil.rmtree(src_version_root)
                except Exception as e:
                    print(f"[warn] failed to remove {src_version_root}: {e}")
                print(
                    f"Moved {report_move['moved']} PNGs into {frames_out} and removed {src_version_root}"
                )
                if not args.no_render:
                    videos_out = out_dir / "videos"
                    render_report = _render_video_from_frames(
                        frames_out, videos_out, extra_args=args.render_arg
                    )
                    if render_report.get("ok"):
                        print(
                            f"Rendered video(s) to {videos_out} using {render_report['command']}"
                        )
                    else:
                        print(
                            f"[warn] video render skipped/failed: {render_report.get('error', 'unknown')}"
                        )
                        stderr = render_report.get("stderr")
                        if stderr:
                            print(f"[render stderr]\n{stderr}")
            else:
                print(
                    f"[info] no frames found under {src_version_root} (nothing to move)"
                )

            print(f"Version {version}: plan written to {out_dir}")
            instance.cleanup()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
