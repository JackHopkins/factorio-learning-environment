"""CLI helper to inspect expected cinema shots for recorded programs.

This utility reuses the cinematography pipeline orchestrated by
`runtime_to_cinema` but runs it in-process for already captured programs.
It is useful for quickly comparing the raw program code with the shots that
our current policies would generate, without replaying Factorio.

Example:

    uv run python -m fle.eval.analysis.compare_code_shots 4701 --limit 5

The script looks for `videos/<version>/programs.json` artefacts produced by
`runtime_to_cinema.py`. If present, it feeds each program's normalized action
stream into a Cinematographer instance and prints the resulting shot summary.
Positions are resolved heuristically so we only rely on shot metadata (tags,
kind) rather than precise world co-ordinates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict

from dotenv import load_dotenv
from fle.eval.analysis.cinematographer import (
    CameraPrefs,
    Cinematographer,
    GameClock,
    ShotIntent,
    ShotPolicy,
    ShotLib,
)
from fle.eval.analysis.runtime_to_cinema import (
    get_db_connection,
    parse_program_actions,
)

load_dotenv()

# Connection cache to avoid repeated connection overhead
_connection_cache = None


def _get_cached_connection():
    """Get a cached database connection to avoid connection overhead"""
    global _connection_cache
    if _connection_cache is None or _connection_cache.closed:
        _connection_cache = get_db_connection()
    return _connection_cache


def _close_cached_connection():
    """Close the cached connection"""
    global _connection_cache
    if _connection_cache and not _connection_cache.closed:
        _connection_cache.close()
        _connection_cache = None


# Matplotlib gets pulled in indirectly by some optional dependencies; ensure it
# can build its font cache inside the workspace sandbox to avoid long delays.
_mpl_dir = Path(".mplconfig")
_mpl_dir.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(_mpl_dir)
os.environ.setdefault("MPLBACKEND", "Agg")
_cache_dir = Path(".cache")
_cache_dir.mkdir(exist_ok=True)
os.environ["XDG_CACHE_HOME"] = str(_cache_dir)


@dataclass
class ProgramSummary:
    program_id: int
    first_line: str
    shots: List[ShotIntent]
    action_to_shot_mapping: Dict[
        int, List[ShotIntent]
    ]  # Maps action index to generated shots


def _load_programs(path: Path) -> list:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _fetch_programs_from_db(version: int, limit: int = None) -> list:
    """Fetch programs from database and convert to the same format as programs.json"""
    import time

    start_time = time.time()

    conn_start = time.time()
    conn = _get_cached_connection()
    conn_time = time.time() - conn_start
    print(
        f"[db] Connection {'reused' if conn_time < 0.1 else 'established'} in {conn_time:.2f}s"
    )

    # Optimized query - only fetch essential columns, add limit early
    query = """
        SELECT id, created_at, code
        FROM programs
        WHERE version = %s
        AND code IS NOT NULL
        AND LENGTH(code) > 10
        ORDER BY created_at ASC
    """
    if limit:
        query += f" LIMIT {limit}"

    print(f"[db] Executing query for version {version}...")
    query_start = time.time()

    with conn.cursor() as cur:
        cur.execute(query, (version,))
        rows = cur.fetchall()

    query_time = time.time() - query_start
    print(f"[db] Query completed in {query_time:.2f}s, fetched {len(rows)} rows")

    # Process rows
    parse_start = time.time()
    result = []
    for i, row in enumerate(rows):
        program_id, created_at, code = row
        if code:
            # Convert to the same format as programs.json
            program_data = {
                "program_id": program_id,
                "code": code,
                "actions": parse_program_actions(code),
                "created_at": str(created_at),
            }
            result.append(program_data)

            # Progress indicator for large datasets
            if (i + 1) % 10 == 0:
                print(f"[db] Processed {i + 1}/{len(rows)} programs...")

    parse_time = time.time() - parse_start
    total_time = time.time() - start_time
    print(f"[db] Parsing completed in {parse_time:.2f}s, total time: {total_time:.2f}s")

    return result


def _first_non_empty_line(code: str) -> str:
    for raw in code.splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _extract_source_lines(code: str, line_span: List[int]) -> str:
    """Extract source code lines from the given line span."""
    if not line_span or len(line_span) < 2:
        return ""

    start_line, end_line = line_span[0], line_span[1]
    lines = code.splitlines()

    # Convert to 0-based indexing
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)

    if start_idx >= end_idx:
        return ""

    return "\n".join(lines[start_idx:end_idx])


def _find_unmapped_actions(
    actions: List[dict], action_to_shot_mapping: Dict[int, List[ShotIntent]]
) -> List[dict]:
    """Find actions that didn't generate any shots."""
    unmapped = []
    for i, action in enumerate(actions):
        if i not in action_to_shot_mapping:
            unmapped.append(action)
    return unmapped


def _suppress_cinema_logs():
    """Suppress [cinema] log output by redirecting stdout temporarily."""
    import io

    class SuppressCinemaLogs:
        def __init__(self):
            self.original_stdout = None
            self.captured_output = io.StringIO()

        def __enter__(self):
            self.original_stdout = sys.stdout
            sys.stdout = self.captured_output
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            sys.stdout = self.original_stdout

    return SuppressCinemaLogs()


def _make_stub_world_context(program_id: int) -> dict:
    """Return a minimal world context compatible with Cinematographer.

    We only care about tags/kinds for comparison, so a coarse resolver is fine.
    """

    def resolve_position(_expr):
        return [0.0, 0.0]

    def bbox_two_points(_a, _b, pad: float):
        return [[-pad, -pad], [pad, pad]]

    return {
        "program_id": program_id,
        "player_position": [0.0, 0.0],
        "resolve_position": resolve_position,
        "bbox_two_points": bbox_two_points,
    }


class TrackingCinematographer(Cinematographer):
    """Cinematographer that tracks which actions generate which shots."""

    def __init__(self, camera_prefs, game_clock, policy):
        super().__init__(camera_prefs, game_clock, policy)
        self.action_to_shot_mapping = {}
        self.current_action_index = 0

    def observe_action_stream(self, action_stream: List[dict], world_context: dict):
        """Override to track action-to-shot mapping."""
        self.action_stream.extend(action_stream)
        self.world_context.update(world_context)

        # Process each action individually to track mapping
        for i, action in enumerate(action_stream):
            self.current_action_index = i
            shots_before = len(self.plan.shots)
            self._map_action_to_shots(action)
            shots_after = len(self.plan.shots)

            # Record which shots were generated by this action
            if shots_after > shots_before:
                new_shots = self.plan.shots[shots_before:]
                self.action_to_shot_mapping[i] = new_shots.copy()

        # Add opening shot if no shots were generated
        if not self.plan.shots:
            player_pos = world_context.get("player_position")
            if player_pos:
                self.plan.add_template(
                    ShotLib.zoom_to_bbox(pan_ticks=90, dwell_ticks=60, zoom=1.05),
                    stage="opening",
                    tags=["opening", "overview"],
                    bbox=self._create_bbox_around_position(player_pos, 30),
                )


def _summarize_program(program: dict, suppress_logs: bool = True) -> ProgramSummary:
    cin = TrackingCinematographer(CameraPrefs(), GameClock(), ShotPolicy())
    action_stream = program.get("actions") or []

    if not isinstance(action_stream, list):
        action_stream = []

    world_context = _make_stub_world_context(program.get("program_id"))

    if suppress_logs:
        with _suppress_cinema_logs():
            cin.observe_action_stream(action_stream, world_context)
    else:
        cin.observe_action_stream(action_stream, world_context)

    plan = cin.build_plan(player=1)
    shots = plan.get("shots", [])

    return ProgramSummary(
        program_id=program.get("program_id"),
        first_line=_first_non_empty_line(program.get("code", "")),
        shots=shots,
        action_to_shot_mapping=cin.action_to_shot_mapping,
    )


def _format_shot(
    shot: ShotIntent,
    show_source: bool = False,
    source_code: str = "",
    action_index: int = -1,
    show_details: bool = False,
    line_span: List[int] = None,
) -> str:
    kind = shot.get("kind", {}).get("type", "?")
    tags = ", ".join(shot.get("tags", []))

    # Add line number information if available
    line_info = ""
    if line_span and len(line_span) >= 2:
        start_line = line_span[0]
        end_line = line_span[1]
        if start_line == end_line:
            line_info = f"ln{start_line} "
        else:
            line_info = f"ln{start_line}:{end_line} "

    result = f"{line_info}{kind}: [{tags}]"

    if show_details:
        # Add critical timing and spatial parameters
        pan_ticks = shot.get("pan_ticks", 0)
        dwell_ticks = shot.get("dwell_ticks", 0)
        zoom = shot.get("zoom")
        stage = shot.get("stage", "action")

        details = []
        details.append(f"pan={pan_ticks} ticks")
        details.append(f"dwell={dwell_ticks} ticks")
        if zoom is not None:
            details.append(f"zoom={zoom}")
        details.append(f"stage={stage}")

        # Add spatial parameters
        kind_obj = shot.get("kind", {})
        if kind_obj.get("type") == "zoom_to_fit" and "bbox" in kind_obj:
            bbox = kind_obj["bbox"]
            details.append(f"bbox={bbox}")
        elif kind_obj.get("type") == "focus_position" and "pos" in kind_obj:
            pos = kind_obj["pos"]
            details.append(f"pos={pos}")
        elif "entity_uid" in kind_obj:
            details.append(f"entity={kind_obj['entity_uid']}")

        result += f"\n    ({', '.join(details)})"

    if show_source and source_code.strip():
        result += f"\n```python\n{source_code}\n```"

    return result


def _iter_versions(args) -> Iterable[int]:
    for raw in args.versions:
        try:
            yield int(raw)
        except ValueError:
            raise SystemExit(f"Invalid version '{raw}' (expected integer)") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare recorded program code with the shots the cinematographer would "
            "emit for it."
        )
    )
    parser.add_argument(
        "versions",
        nargs="+",
        help="One or more version identifiers (e.g. 4701)",
    )
    parser.add_argument(
        "--root",
        default="videos",
        type=Path,
        help="Directory containing <version>/programs.json artefacts",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum programs to display per version (default: 5)",
    )
    parser.add_argument(
        "--show-source",
        action="store_true",
        default=True,
        help="Show source code lines that generate each shot (default: True)",
    )
    parser.add_argument(
        "--no-show-source",
        action="store_false",
        dest="show_source",
        help="Hide source code lines that generate each shot",
    )
    parser.add_argument(
        "--show-cinema-logs",
        action="store_true",
        help="Show [cinema] log output (default: suppressed)",
    )
    parser.add_argument(
        "--show-details",
        action="store_true",
        default=True,
        help="Show detailed shot parameters (timing, spatial, stage) (default: True)",
    )
    parser.add_argument(
        "--no-show-details",
        action="store_false",
        dest="show_details",
        help="Hide detailed shot parameters",
    )
    parser.add_argument(
        "--show-unmapped",
        action="store_true",
        help="Show code lines that didn't generate any shots",
    )

    parsed = parser.parse_args(argv)

    root: Path = parsed.root
    if not root.exists():
        raise SystemExit(f"Data root '{root}' does not exist")

    limit = parsed.limit if parsed.limit and parsed.limit > 0 else None

    for version in _iter_versions(parsed):
        programs_path = root / str(version) / "programs.json"

        if programs_path.exists():
            # Use local file if available
            programs = _load_programs(programs_path)
            print(
                f"\nVersion {version} — displaying up to {limit or len(programs)} programs (from local file)"
            )
        else:
            # Fetch from database if local file not available
            print(f"[info] {programs_path} not found; fetching from database...")
            try:
                programs = _fetch_programs_from_db(version, limit)
                if not programs:
                    print(
                        f"[warn] No programs found for version {version} in database; skipping"
                    )
                    continue
                print(
                    f"\nVersion {version} — displaying up to {len(programs)} programs (from database)"
                )
            except Exception as e:
                print(
                    f"[error] Failed to fetch programs from database for version {version}: {e}"
                )
                continue

        count = 0
        total_programs = len(programs)
        for program in programs:
            summary = _summarize_program(
                program, suppress_logs=not parsed.show_cinema_logs
            )
            print(
                f"\nProgram {count + 1}/{total_programs}, {summary.program_id}: {summary.first_line}"
            )
            if summary.shots:
                print(f"  Shots ({len(summary.shots)}):")

                # Create a mapping from shot to source code
                shot_to_source = {}
                code = program.get("code", "")
                actions = program.get("actions", [])

                for action_idx, action_shots in summary.action_to_shot_mapping.items():
                    if action_idx < len(actions):
                        action = actions[action_idx]
                        line_span = action.get("line_span", [])
                        source_lines = _extract_source_lines(code, line_span)

                        for shot in action_shots:
                            shot_id = shot.get("id", "")
                            shot_to_source[shot_id] = source_lines

                for idx, shot in enumerate(summary.shots, start=1):
                    shot_id = shot.get("id", "")
                    source_code = shot_to_source.get(shot_id, "")

                    # Find the line_span for this shot
                    shot_line_span = None
                    for (
                        action_idx,
                        action_shots,
                    ) in summary.action_to_shot_mapping.items():
                        if any(s.get("id") == shot_id for s in action_shots):
                            if action_idx < len(actions):
                                shot_line_span = actions[action_idx].get("line_span")
                            break

                    shot_text = _format_shot(
                        shot,
                        show_source=parsed.show_source,
                        source_code=source_code,
                        show_details=parsed.show_details,
                        line_span=shot_line_span,
                    )
                    print(f"    {idx:>2}. {shot_text}")
            else:
                print("  Shots: none (no qualifying actions)")

            # Show unmapped actions if requested
            if parsed.show_unmapped:
                unmapped_actions = _find_unmapped_actions(
                    actions, summary.action_to_shot_mapping
                )
                if unmapped_actions:
                    print(f"  Unmapped actions ({len(unmapped_actions)}):")
                    for action in unmapped_actions:
                        action_type = action.get("type", "?")
                        line_span = action.get("line_span", [])
                        source_lines = _extract_source_lines(code, line_span)
                        if source_lines.strip():
                            start_line = line_span[0] if line_span else "?"
                            end_line = (
                                line_span[1] if len(line_span) > 1 else start_line
                            )
                            if start_line == end_line:
                                line_info = f"ln{start_line}"
                            else:
                                line_info = f"ln{start_line}:{end_line}"
                            print(f"    - {line_info} {action_type}:")
                            print(f"      ```python\n{source_lines}\n      ```")
                        else:
                            print(f"    - {action_type} (no source available)")

            count += 1
            if limit is not None and count >= limit:
                break

    # Clean up cached connection
    _close_cached_connection()
    return 0


if __name__ == "__main__":
    sys.exit(main())
