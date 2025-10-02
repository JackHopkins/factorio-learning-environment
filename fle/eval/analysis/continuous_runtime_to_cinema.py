"""
Continuous version of runtime_to_cinema.py using the new Continuous Cinematographer.

This module integrates the new continuous cinematographer with the existing pipeline,
providing a drop-in replacement that emphasizes continuity and program-level storytelling.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime

from dotenv import load_dotenv

from fle.env import FactorioInstance
from fle.eval.analysis.continuous_cinematographer import ContinuousCinematographer
from fle.eval.analysis.ast_actions import parse_actions, create_action_stream

# Import the world context builder from the original module
from fle.eval.analysis.runtime_to_cinema import (
    get_db_connection,
    get_program_chain,
    get_program_state,
    create_instance_and_task,
    build_world_context,
    _detect_script_output_dir,
    _move_png_tree,
    _render_video_from_frames,
)

load_dotenv()


def process_programs_continuous(
    version: int,
    cinematographer: ContinuousCinematographer,
    instance: FactorioInstance,
    programs: Iterable[tuple[int, Any]],
    conn,
    max_steps: int,
    capture_opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process programs using the continuous cinematographer approach.

    This function interleaves cinematography with program execution to capture
    the story as it unfolds, not in retrospect.
    """

    print(f"Processing version {version} with continuous cinematography")
    programs = list(programs)
    print(f"Total programs: {len(programs)} (max {max_steps} steps)")

    instance.reset()
    print("Environment reset complete")
    instance.first_namespace.enable_admin_tools_in_runtime(True)

    # Capture options
    cap_enabled = capture_opts.get("enabled", True) if capture_opts else True
    cap_player = 1
    run_slug = datetime.now().strftime("%Y%m%d_%H%M%S")

    def play_cutscene(
        plan: Dict[str, Any],
        warn_label: str,
        *,
        subdir: Optional[str] = None,
        linger: float = 0.5,
    ):
        if not plan or not plan.get("shots"):
            return None

        label_source = None
        if subdir:
            label_source = str(subdir).strip("/").split("/")[-1]
        if not label_source:
            label_source = f"{warn_label}_{run_slug}"

        plan_id = plan.get("plan_id") or label_source
        plan["plan_id"] = plan_id
        plan.setdefault("player", cap_player)

        # Handle capture settings - ensure proper tick-based naming
        if cap_enabled:
            plan["capture"] = True
            # Use the capture_dir from the plan if provided, otherwise use version directory
            if not plan.get("capture_dir"):
                if subdir:
                    version_dir = subdir.split("/")[0]
                    plan["capture_dir"] = version_dir
                else:
                    plan["capture_dir"] = f"v{version}"
        else:
            plan.pop("capture", None)
            plan.pop("capture_dir", None)

        try:
            result = instance.first_namespace.cutscene(plan)
            if linger > 0:
                time.sleep(linger)
            return result
        except Exception as e:
            print(f"[warn] {warn_label} cutscene failed: {e}")
            return None

    screenshot_sequences: List[Dict[str, Any]] = []
    total_actions_processed = 0
    programs_processed = 0

    # Process programs individually with immediate cinematography
    for idx, (program_id, created_at) in enumerate(programs):
        if programs_processed >= max_steps:
            print(f"Reached maximum steps limit ({max_steps}), stopping")
            break

        print(f"\n--- Processing program {programs_processed + 1}: {program_id} ---")

        program = get_program_state(conn, program_id)
        if not program or not program.code:
            print(f"Skipping program {program_id} - no code available")
            continue

        print(f"Code preview: {program.code[:100]}...")

        if program.state:
            print("Resetting environment with program state")
            instance.reset(program.state)

        # STEP 1: Parse AST to understand what the program will do
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

        action_stream = create_action_stream(action_sites)
        print(f"Extracted {len(action_stream)} actions")

        # STEP 2: Execute the program first
        print("Executing program...")
        response = instance.eval(program.code)

        # Log execution results
        if response[2]:  # errors
            print(f"Execution errors: {response[2]}")
        if response[1]:  # prints
            print(f"Program output: {response[1]}")

        # STEP 3: Generate shots AFTER program execution (when entities exist)
        # Build world context after execution so entities are available
        world_context = build_world_context(instance, program)

        # Create cinematographer and process program with post-execution context
        cinematographer = ContinuousCinematographer(player=1)
        cinematographer.process_program(
            program_id=str(program_id),
            actions=action_stream,
            world_context=world_context,
        )

        # Execute all shots immediately after program execution
        if cinematographer.shots:
            # Group shots by type for better organization
            shot_groups = {}
            for shot in cinematographer.shots:
                shot_type = shot.state.value
                if shot_type not in shot_groups:
                    shot_groups[shot_type] = []
                shot_groups[shot_type].append(shot)

            # Execute each group of shots
            for shot_type, shots in shot_groups.items():
                shot_plan = {
                    "player": 1,
                    "start_zoom": 1.0,
                    "shots": [
                        {
                            "id": shot.id,
                            "seq": i,
                            "kind": shot.kind,
                            "pan_ticks": shot.pan_ticks,
                            "dwell_ticks": shot.dwell_ticks,
                            "zoom": shot.zoom,
                            "tags": shot.tags,
                            "stage": shot.state.value,
                            "order": i,
                        }
                        for i, shot in enumerate(shots)
                    ],
                    "plan_id": f"{shot_type}-{program_id}-{run_slug}",
                    "capture": True,
                    "capture_dir": f"v{version}",
                }

                # Debug: Print shot details
                for i, shot in enumerate(shots):
                    print(
                        f"  {shot_type} Shot {i}: zoom={shot.zoom}, dwell={shot.dwell_ticks}, pos={shot.kind.get('pos')}"
                    )
                    if shot.kind.get("bbox"):
                        bbox = shot.kind["bbox"]
                        width = abs(bbox[1][0] - bbox[0][0])
                        height = abs(bbox[1][1] - bbox[0][1])
                        print(f"    Bbox dimensions: {width:.1f} x {height:.1f} tiles")

                print(f"Executing {len(shots)} {shot_type} shots...")
                play_cutscene(
                    shot_plan,
                    shot_type,
                    subdir=f"v{version}/{shot_type}_{program_id:07d}_{run_slug}",
                    linger=0.2,  # Slightly longer transition
                )

        # Store program data
        screenshot_sequences.append(
            {
                "program_id": program_id,
                "code": program.code,
                "actions": action_stream,
                "prints": response[1],
                "errors": response[2],
                "created_at": str(created_at),
            }
        )

        total_actions_processed += len(action_stream)
        programs_processed += 1

        # Small delay between programs for visibility
        time.sleep(1)

    print("\nContinuous processing complete:")
    print(f"  - Total programs processed: {programs_processed}")
    print(f"  - Total actions processed: {total_actions_processed}")

    try:
        instance.first_namespace.enable_admin_tools_in_runtime(False)
    except Exception:
        pass

    return {
        "programs": screenshot_sequences,
        "plan": {
            "player": 1,
            "shots": [],
        },  # No final plan since we execute immediately
        "enqueue": {"player": 1, "shots": []},
        "cutscene_result": None,
        "stats": {
            "programs_processed": programs_processed,
            "actions_processed": total_actions_processed,
            "shots_generated": 0,  # Shots executed immediately
            "cutscene_executed": True,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Replay programs with continuous cinematics"
    )
    parser.add_argument("versions", nargs="+", type=int)
    parser.add_argument("--output-dir", "-o", default="continuous_cinema_runs")
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
        help="Disable server-driven screenshot capture",
    )
    parser.add_argument(
        "--script-output-dir",
        default=os.getenv("FACTORIO_SCRIPT_OUTPUT", None),
        help="Override Factorio script-output directory (defaults to OS-specific path)",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip running ffmpeg after moving frames",
    )
    parser.add_argument(
        "--render-fps",
        type=int,
        default=int(os.getenv("CINEMA_RENDER_FPS", "10")),
        help="Playback framerate for ffmpeg (controls final speed)",
    )
    parser.add_argument(
        "--render-crf",
        type=int,
        default=int(os.getenv("CINEMA_RENDER_CRF", "28")),
        help="FFmpeg CRF (lower = higher quality)",
    )
    parser.add_argument(
        "--render-preset",
        default=os.getenv("CINEMA_RENDER_PRESET", "ultrafast"),
        help="FFmpeg preset (e.g. ultrafast, fast, medium)",
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

            # Create continuous cinematographer
            cinematographer = ContinuousCinematographer(player=1)

            capture_opts = {
                "enabled": not args.no_capture,
            }
            script_output_dir = _detect_script_output_dir(args.script_output_dir)
            capture_root = script_output_dir / f"v{version}"

            if not args.no_capture:
                # Clean up any existing PNGs for this version in script-output
                try:
                    if capture_root.exists():
                        shutil.rmtree(capture_root)
                        print(f"Cleaned existing PNGs from {capture_root}")
                except Exception as exc:
                    print(f"[warn] failed to clean capture dir {capture_root}: {exc}")
                capture_root.mkdir(parents=True, exist_ok=True)

            report = process_programs_continuous(
                version,
                cinematographer,
                instance,
                programs,
                conn,
                args.max_steps,
                capture_opts,
            )

            out_dir = output_base / str(version)
            # Clean existing output directory to ensure fresh start
            if out_dir.exists():
                try:
                    shutil.rmtree(out_dir)
                    print(f"Cleaned existing output directory {out_dir}")
                except Exception as exc:
                    print(f"[warn] failed to clean output dir {out_dir}: {exc}")
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
            src_version_root = capture_root
            frames_out = out_dir / "frames"

            # Clean existing frames directory to ensure fresh start
            if frames_out.exists():
                try:
                    # Count existing files before cleanup
                    existing_files = list(frames_out.glob("*.png"))
                    print(
                        f"Found {len(existing_files)} existing PNG files in {frames_out}"
                    )
                    shutil.rmtree(frames_out)
                    print(f"Cleaned existing frames directory {frames_out}")
                except Exception as exc:
                    print(f"[warn] failed to clean frames dir {frames_out}: {exc}")

            if src_version_root.exists():
                # Count files before move
                src_files = list(src_version_root.glob("*.png"))
                print(f"Found {len(src_files)} PNG files in {src_version_root}")
                if src_files:
                    print(f"Sample files: {[f.name for f in src_files[:3]]}")

                report_move = _move_png_tree(src_version_root, frames_out)
                try:
                    shutil.rmtree(src_version_root)
                except Exception as e:
                    print(f"[warn] failed to remove {src_version_root}: {e}")
                print(
                    f"Moved {report_move['moved']} PNGs into {frames_out} and removed {src_version_root}"
                )

                # Verify files after move
                moved_files = list(frames_out.glob("*.png"))
                print(f"After move: {len(moved_files)} PNG files in {frames_out}")
                if moved_files:
                    print(f"Sample moved files: {[f.name for f in moved_files[:3]]}")
                if not args.no_render:
                    videos_out = out_dir / "videos"
                    # Clean existing videos directory to ensure fresh start
                    if videos_out.exists():
                        try:
                            shutil.rmtree(videos_out)
                            print(f"Cleaned existing videos directory {videos_out}")
                        except Exception as exc:
                            print(
                                f"[warn] failed to clean videos dir {videos_out}: {exc}"
                            )

                    render_report = _render_video_from_frames(
                        frames_out,
                        videos_out,
                        fps=args.render_fps,
                        crf=args.render_crf,
                        preset=args.render_preset,
                    )
                    if render_report.get("ok"):
                        print(
                            f"Rendered video to {render_report.get('output')} using {render_report['command']}"
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

            print(f"Version {version}: continuous plan written to {out_dir}")
            instance.cleanup()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
