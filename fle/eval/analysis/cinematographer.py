"""Clean templating system for Factorio cinematography.

This module provides a template-based system for creating cinematic shots that can be
rendered with concrete values from AST-extracted variables. The system is designed to
work with the new AST parser and runtime detection pipeline.

SINGLE SOURCE OF TRUTH: This module is the ONLY place where shot decisions are made.
All other modules (ast_actions, runtime_to_cinema, spliced helpers) are stateless
utilities that provide data or execute plans. Only the Cinematographer maps actions
to shots and owns all shot policy decisions.

Key components:
- Var: Placeholder class for symbolic fields
- ShotTemplate: Template for shots with Var placeholders
- ShotLib: Library of common shot templates
- ShotPolicy: Tunable defaults for shot behavior
- Cinematographer: The single brain that maps actions → shots
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --- Shot ordering policy --------------------------------------------------


def _priority_for_shot(shot: ShotIntent) -> int:
    tags = set(shot.get("tags", []))
    kind = shot.get("kind", {}).get("type", "")
    # Highest priority: connection pre overview, then endpoints, then post focus
    if {"connection", "pre"}.issubset(tags):
        return 0
    if {"connection", "endpoints"}.issubset(tags):
        return 5
    if {"connection", "post"}.issubset(tags):
        return 15
    # System setups
    if tags & {"mining", "power", "smelting", "assembly"}:
        return 20
    # Generic building beats
    if "building" in tags:
        return 30
    # Inserts and misc.
    if "insert" in tags:
        return 40
    # Fallback by kind type
    if kind == "zoom_to_fit":
        return 25
    if kind == "focus_position":
        return 35
    return 50


# Core types ----------------------------------------------------------------

ShotIntent = Dict[str, Any]


class Var:
    """Placeholder class for symbolic fields in shot templates.

    Used to mark fields that should be replaced with concrete values during rendering.
    The name attribute is used as the key in the context dictionary.
    """

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"Var('{self.name}')"


@dataclass
class ShotTemplate:
    """Template for creating shots with symbolic placeholders.

    Contains Var placeholders that get replaced with concrete values during rendering.
    The render method produces a ShotIntent dict ready for server.lua.
    """

    id_prefix: str
    kind: Dict[str, Any]
    pan_ticks: int
    dwell_ticks: int
    zoom: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def render(self, seq: int, **ctx) -> ShotIntent:
        """Replace Var placeholders with concrete values from context.

        Args:
            seq: Sequence number for shot ordering
            **ctx: Context dictionary with values for Var placeholders

        Returns:
            ShotIntent dict ready for server.lua
        """
        # Create a copy of the kind dict to avoid modifying the template
        rendered_kind = {}
        for key, value in self.kind.items():
            if isinstance(value, Var):
                rendered_kind[key] = ctx[value.name]
            else:
                rendered_kind[key] = value

        # Generate unique shot ID
        shot_id = f"{self.id_prefix}-{seq}"

        return {
            "id": shot_id,
            "seq": seq,
            "kind": rendered_kind,
            "pan_ticks": self.pan_ticks,
            "dwell_ticks": self.dwell_ticks,
            "zoom": self.zoom,
            "tags": self.tags.copy(),
        }


@dataclass
class ShotPolicy:
    """Tunable defaults for shot behavior and timing."""

    movement_min_distance_tiles: float = 15
    movement_window_n: int = 3
    connection_padding_tiles: float = 25
    pre_arrival_cut: bool = False
    establish_before_move: bool = False
    # Connection dwell/pan policy (used for connect_entities)
    connection_pan_ticks: int = 90  # ~1.5s @60 tps
    connection_min_dwell_ticks: int = 240  # ~4s linger
    connection_dwell_per_tile: float = 1.5  # add dwell proportional to span

    def build_move_establishments(
        self, action_stream: List[dict], world_context: dict
    ) -> List[ShotIntent]:
        """Return establishing shots for move_to actions only (does not mutate state)."""
        shots: List[ShotIntent] = []
        if not self.establish_before_move:
            return shots
        # Use sequence numbers for ordering instead of ticks
        seq = 0
        for action in action_stream:
            if action.get("type") != "move_to":
                continue
            args = action.get("args", {})
            dest = args.get("destination") or args.get("pos_src")
            # Resolve destination using world resolvers or fallback
            player_pos = world_context.get("player_position", [0, 0])
            resolve_pos = world_context.get("resolve_position")
            pos = resolve_pos(dest) if callable(resolve_pos) else player_pos
            tpl = ShotLib.focus_pos(pan_ticks=84, dwell_ticks=42, zoom=1.0)
            shot = tpl.render(seq=seq, pos=pos)
            shot["tags"] = ["movement", "establish"]
            shots.append(shot)
            seq += 1
        return shots


# Shot library --------------------------------------------------------------


class ShotLib:
    """Library of common shot templates with Var placeholders."""

    @staticmethod
    def cut_to_pos(zoom: float = 0.9) -> ShotTemplate:
        """Instant cut to a position with optional zoom."""
        return ShotTemplate(
            id_prefix="cut-pos",
            kind={"type": "focus_position", "pos": Var("pos")},
            pan_ticks=0,  # Instant cut
            dwell_ticks=0,
            zoom=zoom,
            tags=["cut", "position"],
        )

    @staticmethod
    def focus_pos(
        pan_ticks: int = 96, dwell_ticks: int = 54, zoom: float = 1.0
    ) -> ShotTemplate:
        """Smooth pan to focus on a position."""
        return ShotTemplate(
            id_prefix="focus-pos",
            kind={"type": "focus_position", "pos": Var("pos")},
            pan_ticks=pan_ticks,
            dwell_ticks=dwell_ticks,
            zoom=zoom,
            tags=["focus", "position"],
        )

    @staticmethod
    def zoom_to_bbox(
        pan_ticks: int = 132, dwell_ticks: int = 96, zoom: Optional[float] = None
    ) -> ShotTemplate:
        """Zoom to fit a bounding box with optional zoom level."""
        return ShotTemplate(
            id_prefix="zoom-bbox",
            kind={"type": "zoom_to_fit", "bbox": Var("bbox")},
            pan_ticks=pan_ticks,
            dwell_ticks=dwell_ticks,
            zoom=zoom,
            tags=["zoom", "bbox", "overview"],
        )

    @staticmethod
    def follow_entity(
        duration_ticks: int, dwell_ticks: int = 72, zoom: float = 1.0
    ) -> ShotTemplate:
        """Follow an entity for a specified duration."""
        return ShotTemplate(
            id_prefix="follow-entity",
            kind={"type": "follow_entity", "entity_uid": Var("entity_uid")},
            pan_ticks=duration_ticks,
            dwell_ticks=dwell_ticks,
            zoom=zoom,
            tags=["follow", "entity"],
        )

    @staticmethod
    def orbit_entity(
        duration_ticks: int,
        radius_tiles: int,
        degrees: int,
        dwell_ticks: int,
        zoom: float,
    ) -> ShotTemplate:
        """Orbit around an entity with specified parameters."""
        return ShotTemplate(
            id_prefix="orbit-entity",
            kind={
                "type": "orbit_entity",
                "entity_uid": Var("entity_uid"),
                "radius_tiles": radius_tiles,
                "degrees": degrees,
            },
            pan_ticks=duration_ticks,
            dwell_ticks=dwell_ticks,
            zoom=zoom,
            tags=["orbit", "entity"],
        )

    @staticmethod
    def connection_two_point(padding: int = 25) -> List[ShotTemplate]:
        """Create a two-shot sequence for connecting two points.

        Returns a list with [pre_zoom_to_fit_template, post_focus_template].
        """
        # Pre-shot: zoom to fit both points with padding
        pre_template = ShotTemplate(
            id_prefix="connection-pre",
            kind={"type": "zoom_to_fit", "bbox": Var("connection_bbox")},
            pan_ticks=132,
            dwell_ticks=48,
            zoom=0.7,
            tags=["connection", "pre", "overview"],
        )

        # Post-shot: focus on the connection point
        post_template = ShotTemplate(
            id_prefix="connection-post",
            kind={"type": "focus_position", "pos": Var("center")},
            pan_ticks=96,
            dwell_ticks=72,
            zoom=1.0,
            tags=["connection", "post", "focus"],
        )

        return [pre_template, post_template]


# Utility functions ---------------------------------------------------------


def new_plan(player: int = 1, plan_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new plan dictionary with sensible defaults."""
    return {
        "plan_id": plan_id or f"auto-{uuid.uuid4().hex[:8]}",
        "player": player,
        "start_zoom": 1.05,
        "shots": [],
    }


# Placeholder classes for runtime_to_cinema.py compatibility -----------------


@dataclass
class CameraPrefs:
    """Placeholder for camera preferences."""

    pass


@dataclass
class GameClock:
    """Placeholder for game clock."""

    pass


# 60 ticks per second in Factorio
TICKS_PER_SECOND = 60


def ms_to_ticks(ms: int) -> int:
    try:
        return max(0, int(round((ms or 0) * TICKS_PER_SECOND / 1000.0)))
    except Exception:
        return 0


class Cinematographer:
    """The single source of truth for shot mapping and policy decisions.

    This class is the ONLY place where actions are mapped to shots. It receives
    normalized ActionStream data and world context, then produces shot plans.
    """

    def __init__(
        self,
        camera_prefs: CameraPrefs,
        game_clock: GameClock,
        policy: Optional[ShotPolicy] = None,
    ):
        self.camera_prefs = camera_prefs
        self.game_clock = game_clock
        self.policy = policy or ShotPolicy()
        self.events = []
        self.shots = []
        self.action_stream = []
        self.world_context = {}
        # Per-program connection shot budget and connect_entities detection
        self._program_has_connect: Dict[Any, bool] = {}
        self._program_connect_emitted: Dict[Any, bool] = {}
        self._program_last_conn_center: Dict[Any, List[float]] = {}

    def observe_action_stream(self, action_stream: List[dict], world_context: dict):
        """Observe a stream of normalized actions and generate appropriate shots.

        Args:
            action_stream: List of normalized action events from ast_actions
            world_context: Lightweight world facts (player pos, current tick, etc.)
        """
        self.action_stream.extend(action_stream)
        self.world_context.update(world_context)

        # Per-program connect_entities policy and reset for new program_id
        pid = world_context.get("program_id")
        if pid is not None:
            if pid not in self._program_has_connect:
                self._program_has_connect[pid] = any(
                    a.get("type") == "connect_entities" for a in action_stream
                )
            # reset per-program connection emitted state for fresh action batches of the same program id
            self._program_connect_emitted.setdefault(pid, False)

        # Process each action in the stream
        for action in action_stream:
            self._map_action_to_shots(action)

    def _bbox_center(self, bbox: list) -> List[float]:
        (x1, y1), (x2, y2) = bbox[0], bbox[1]
        return [(x1 + x2) / 2.0, (y1 + y2) / 2.0]

    def observe_game_event(self, event: dict, delta: dict):
        """Observe a game event and generate appropriate shots.

        This is kept for backward compatibility with existing event-based detection.
        """
        self.events.append((event, delta))

        # Generate shots based on event type
        event_type = event.get("event")
        position = event.get("position", [0, 0])

        if event_type == "power_setup":
            # Focus on power generation setup
            bbox = delta.get(
                "factory_bbox",
                [
                    [position[0] - 15, position[1] - 15],
                    [position[0] + 15, position[1] + 15],
                ],
            )
            shot = ShotLib.zoom_to_bbox(pan_ticks=120, dwell_ticks=90, zoom=0.8).render(
                seq=len(self.shots), bbox=bbox
            )
            shot["tags"] = ["power", "setup"]
            self.shots.append(shot)

        elif event_type == "mining_setup":
            # Focus on mining setup
            bbox = delta.get(
                "factory_bbox",
                [
                    [position[0] - 10, position[1] - 10],
                    [position[0] + 10, position[1] + 10],
                ],
            )
            shot = ShotLib.zoom_to_bbox(pan_ticks=108, dwell_ticks=72, zoom=0.9).render(
                seq=len(self.shots), bbox=bbox
            )
            shot["tags"] = ["mining", "setup"]
            self.shots.append(shot)

        elif event_type == "building_placed":
            # Quick cut to building placement
            entity_type = delta.get("entity_type", "building")
            shot = ShotLib.cut_to_pos(zoom=1.0).render(
                seq=len(self.shots), pos=position
            )
            shot["tags"] = ["building", entity_type]
            self.shots.append(shot)

        elif event_type == "infrastructure_connection":
            # Show connection overview
            bbox = delta.get(
                "factory_bbox",
                [
                    [position[0] - 30, position[1] - 30],
                    [position[0] + 30, position[1] + 30],
                ],
            )
            shot = ShotLib.zoom_to_bbox(pan_ticks=132, dwell_ticks=60, zoom=0.7).render(
                seq=len(self.shots), bbox=bbox
            )
            shot["tags"] = ["connection", "infrastructure"]
            self.shots.append(shot)

        elif event_type == "player_movement":
            # Follow player movement
            movement_bbox = delta.get(
                "movement_bbox",
                [
                    [position[0] - 20, position[1] - 20],
                    [position[0] + 20, position[1] + 20],
                ],
            )
            shot = ShotLib.zoom_to_bbox(pan_ticks=90, dwell_ticks=48, zoom=0.8).render(
                seq=len(self.shots), bbox=movement_bbox
            )
            shot["tags"] = ["movement", "player"]
            self.shots.append(shot)

    def _map_action_to_shots(self, action: dict):
        """Map a single action to appropriate shots using shot policies.

        This is where all the "what camera move should this action produce?" rules live.
        """
        action_type = action.get("type")
        args = action.get("args", {})
        # Use sequence number for ordering instead of current tick
        seq = len(self.shots)
        player_pos = self.world_context.get("player_position", [0, 0])

        if action_type == "move_to":
            self._handle_move_to_action(action, args, seq, player_pos)
        elif action_type == "place_entity":
            self._handle_place_entity_action(action, args, seq, player_pos)
        elif action_type == "place_entity_next_to":
            self._handle_place_entity_next_to_action(action, args, seq, player_pos)
        elif action_type == "connect_entities":
            self._handle_connect_entities_action(action, args, seq, player_pos)
        elif action_type == "insert_item":
            self._handle_insert_item_action(action, args, seq, player_pos)

    def _handle_move_to_action(
        self, action: dict, args: dict, seq: int, player_pos: list
    ):
        """Handle move_to actions - usually ignored unless policy says otherwise."""
        if not self.policy.pre_arrival_cut:
            return

        # Only create pre-arrival cuts for significant movements
        destination = args.get("destination", "")
        if destination and destination != str(player_pos):
            # Resolve destination position
            dest_pos = self._resolve_position(destination, player_pos)
            shot = ShotLib.cut_to_pos(zoom=0.9).render(seq=seq, pos=dest_pos)
            shot["tags"] = ["movement", "pre_arrival"]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

    def _handle_place_entity_action(
        self, action: dict, args: dict, seq: int, player_pos: list
    ):
        """Handle place_entity actions based on entity type."""
        prototype = args.get("prototype", "").lower()
        position = self._resolve_position(args.get("position", player_pos), player_pos)

        # Map entity types to shot policies
        if prototype in ["boiler", "steam_engine", "offshore_pump"]:
            # Power setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 15)
            shot = ShotLib.zoom_to_bbox(pan_ticks=120, dwell_ticks=90, zoom=0.8).render(
                seq=seq, bbox=bbox
            )
            shot["tags"] = ["power", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

        elif prototype in ["burner_mining_drill", "electric_mining_drill"]:
            # Mining setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 10)
            shot = ShotLib.zoom_to_bbox(pan_ticks=108, dwell_ticks=72, zoom=0.9).render(
                seq=seq, bbox=bbox
            )
            shot["tags"] = ["mining", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

        elif prototype in ["stone_furnace", "steel_furnace", "electric_furnace"]:
            # Smelting setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 8)
            shot = ShotLib.zoom_to_bbox(pan_ticks=108, dwell_ticks=72, zoom=0.9).render(
                seq=seq, bbox=bbox
            )
            shot["tags"] = ["smelting", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

        elif prototype in [
            "assembly_machine_1",
            "assembly_machine_2",
            "assembly_machine_3",
        ]:
            # Assembly setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 12)
            shot = ShotLib.zoom_to_bbox(pan_ticks=108, dwell_ticks=72, zoom=0.9).render(
                seq=seq, bbox=bbox
            )
            shot["tags"] = ["assembly", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

        else:
            # Generic building - quick cut
            shot = ShotLib.cut_to_pos(zoom=1.0).render(seq=seq, pos=position)
            shot["tags"] = ["building", "placed", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
            )

    def _handle_place_entity_next_to_action(
        self, action: dict, args: dict, seq: int, player_pos: list
    ):
        """Handle place_entity_next_to actions - emit a single connection bird's-eye shot."""
        pid = self.world_context.get("program_id")
        # Suppress connection-like shots if the program has any connect_entities
        if self._program_has_connect.get(pid, False):
            return
        prototype = args.get("prototype", "").lower()
        target = args.get("target", "")
        position_expr = args.get("position", player_pos)

        resolve_pos = self.world_context.get("resolve_position")
        bbox_fn = self.world_context.get("bbox_two_points")

        # Resolve concrete positions
        pos = (
            resolve_pos(position_expr)
            if callable(resolve_pos)
            else self._resolve_position(position_expr, player_pos)
        )
        # tgt = (
        #     resolve_pos(target)
        #     if callable(resolve_pos)
        #     else self._resolve_position(target, player_pos)
        # )

        # Compute bbox covering both endpoints
        if callable(bbox_fn):
            bbox = bbox_fn(
                target, position_expr, pad=self.policy.connection_padding_tiles
            )
        else:
            # fallback to padding around placed position
            bbox = self._create_bbox_around_position(
                pos, self.policy.connection_padding_tiles
            )

        # Apply per-program connection shot budget: only one unless far away
        if pid is not None:
            if self._program_connect_emitted.get(pid, False):
                prev = self._program_last_conn_center.get(pid)
                cur = self._bbox_center(bbox)
                if prev is not None:
                    dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                    if (dx * dx + dy * dy) ** 0.5 <= 60.0:
                        return
                # otherwise allow and update
                self._program_last_conn_center[pid] = cur
            else:
                self._program_connect_emitted[pid] = True
                self._program_last_conn_center[pid] = self._bbox_center(bbox)

        # Emit a single zoom_to_fit shot with connection tags
        tpl = ShotLib.zoom_to_bbox(pan_ticks=132, dwell_ticks=96, zoom=None)
        shot = tpl.render(seq=seq, bbox=bbox)
        shot["tags"] = ["connection", "endpoints", prototype]
        self.shots.append(shot)
        print(
            f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} bbox={bbox} seq={shot.get('seq')}"
        )

    def _handle_connect_entities_action(
        self, action: dict, args: dict, seq: int, player_pos: list
    ):
        """Handle connect_entities actions - always zoom to bbox of endpoints."""
        pid = self.world_context.get("program_id")
        # If a pre-connect establishing shot already ran for this program, skip post-action shot.
        if self.world_context.get("pre_connect_done", False):
            return
        a_expr = args.get("a_expr", "")
        b_expr = args.get("b_expr", "")
        proto_name = args.get("proto_name", "")

        # Always compute bbox from the two endpoints' positions
        bbox_fn = self.world_context.get("bbox_two_points")
        resolve_pos = self.world_context.get("resolve_position")
        if callable(bbox_fn):
            bbox = bbox_fn(a_expr, b_expr, pad=self.policy.connection_padding_tiles)
        else:
            # Manual fallback: resolve both positions and build bbox
            a = (
                resolve_pos(a_expr)
                if callable(resolve_pos)
                else self._resolve_position(a_expr, player_pos)
            )
            b = (
                resolve_pos(b_expr)
                if callable(resolve_pos)
                else self._resolve_position(b_expr, player_pos)
            )
            x1, y1 = a
            x2, y2 = b
            pad = self.policy.connection_padding_tiles
            left, right = min(x1, x2) - pad, max(x1, x2) + pad
            top, bottom = min(y1, y2) - pad, max(y1, y2) + pad
            bbox = [[left, top], [right, bottom]]

        # Apply per-program connection shot budget: only one unless far away
        if pid is not None:
            if self._program_connect_emitted.get(pid, False):
                prev = self._program_last_conn_center.get(pid)
                cur = self._bbox_center(bbox)
                if prev is not None:
                    dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                    if (dx * dx + dy * dy) ** 0.5 <= 60.0:
                        return
                self._program_last_conn_center[pid] = cur
            else:
                self._program_connect_emitted[pid] = True
                self._program_last_conn_center[pid] = self._bbox_center(bbox)

        # Simple bird's-eye with a sensible dwell
        tpl = ShotLib.zoom_to_bbox(pan_ticks=132, dwell_ticks=96, zoom=None)
        shot = tpl.render(seq=seq, bbox=bbox)
        shot["tags"] = ["connection", "endpoints", proto_name]
        self.shots.append(shot)
        print(
            f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} bbox={bbox} seq={shot.get('seq')}"
        )

    def _handle_insert_item_action(
        self, action: dict, args: dict, seq: int, player_pos: list
    ):
        """Handle insert_item actions - restrict to meaningful inserts and resolve with world context."""
        prototype = (args.get("prototype", "") or "").lower()
        resolve_pos = self.world_context.get("resolve_position")
        raw_pos = args.get("position", player_pos)
        position = (
            resolve_pos(raw_pos)
            if callable(resolve_pos)
            else self._resolve_position(raw_pos, player_pos)
        )

        # Minimal taste filter: only surface obviously meaningful inserts (e.g., fueling)
        meaningful = prototype in {"coal"}  # extend as needed with more heuristics
        if not meaningful:
            return

        shot = ShotLib.cut_to_pos(zoom=1.0).render(seq=seq, pos=position)
        shot["tags"] = ["insert", "item", prototype]
        self.shots.append(shot)
        print(
            f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} seq={shot.get('seq')}"
        )

    def _resolve_position(self, position, fallback: list) -> list:
        """Resolve position from various formats to [x, y] list."""
        if isinstance(position, list) and len(position) >= 2:
            # Already a list
            return [float(position[0]), float(position[1])]
        elif isinstance(position, str):
            # Try to parse string representations like "Position(x=15, y=-3)"
            import re

            # Look for x=number, y=number pattern
            match = re.search(
                r"x=([+-]?\d+(?:\.\d+)?).*?y=([+-]?\d+(?:\.\d+)?)", position
            )
            if match:
                return [float(match.group(1)), float(match.group(2))]
            # Look for [x, y] pattern
            match = re.search(
                r"\[([+-]?\d+(?:\.\d+)?),\s*([+-]?\d+(?:\.\d+)?)\]", position
            )
            if match:
                return [float(match.group(1)), float(match.group(2))]
        # Fallback to provided fallback position
        return fallback

    def _create_bbox_around_position(self, position: list, padding: float) -> list:
        """Create a bounding box around a position with padding."""
        if not position or len(position) < 2:
            return [[0, 0], [10, 10]]

        x, y = position[0], position[1]
        return [[x - padding, y - padding], [x + padding, y + padding]]

    def build_plan(self, player: int = 1) -> dict:
        """Build a complete shot plan from observed events and actions.

        This applies prioritization, deduplication, and narrative timing policies.
        """
        # Attach sequence numbers for stability
        for idx, s in enumerate(self.shots):
            s.setdefault("seq", idx)
            s["pri"] = _priority_for_shot(s)

        # Sort by (priority, sequence) to get a clean order - no tick-based sorting
        ordered = sorted(
            self.shots,
            key=lambda s: (
                s.get("pri", 50),
                s.get("seq", 0),
            ),
        )

        # Apply deduplication and merging policies
        deduplicated_shots = self._apply_deduplication(ordered)

        # Clear per-program caches for the current program_id after building the plan
        pid = self.world_context.get("program_id")
        if pid in self._program_connect_emitted:
            del self._program_connect_emitted[pid]
            self._program_has_connect.pop(pid, None)
            self._program_last_conn_center.pop(pid, None)

        return {"player": player, "start_zoom": 1.0, "shots": deduplicated_shots}

    def _apply_deduplication(self, shots: list) -> list:
        """Apply spatial deduplication to reduce déjà vu."""
        if not shots:
            return shots
        deduped = []
        # Keep a spatial footprint cache: (type, cx, cy, sx, sy) -> seen
        seen = set()

        def _bbox_center_span(s):
            k = s.get("kind", {})
            if k.get("type") == "zoom_to_fit" and "bbox" in k:
                (x1, y1), (x2, y2) = k["bbox"][0], k["bbox"][1]
                cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                sx, sy = abs(x2 - x1), abs(y2 - y1)
                return cx, cy, sx, sy
            if k.get("type") == "focus_position" and "pos" in k:
                x, y = k["pos"][0], k["pos"][1]
                return x, y, 0.0, 0.0
            return None

        for s in shots:
            ktype = s.get("kind", {}).get("type", "")
            key_tuple = _bbox_center_span(s)
            if key_tuple is None:
                # No spatial info; keep all shots
                deduped.append(s)
                continue
            # Round to tile-ish precision to group near-identical frames
            cx, cy, sx, sy = key_tuple
            fp = (
                ktype,
                round(cx, 1 if ktype == "focus_position" else 0),
                round(cy, 1 if ktype == "focus_position" else 0),
                round(sx, 0),
                round(sy, 0),
            )
            if fp not in seen:
                deduped.append(s)
                seen.add(fp)
            else:
                # Skip duplicate shot
                continue
        return deduped


# Module exports ------------------------------------------------------------

__all__ = [
    "ShotIntent",
    "Var",
    "ShotTemplate",
    "ShotLib",
    "ShotPolicy",
    "new_plan",
    "Cinematographer",
    "CameraPrefs",
    "GameClock",
]
