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
    pan_ms: int
    dwell_ms: int
    zoom: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def render(self, tick: int, **ctx) -> ShotIntent:
        """Replace Var placeholders with concrete values from context.

        Args:
            tick: Game tick when shot should start
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
        shot_id = f"{self.id_prefix}-{tick}"

        return {
            "id": shot_id,
            "when": {"start_tick": tick},
            "kind": rendered_kind,
            "pan_ms": self.pan_ms,
            "dwell_ms": self.dwell_ms,
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


# Shot library --------------------------------------------------------------


class ShotLib:
    """Library of common shot templates with Var placeholders."""

    @staticmethod
    def cut_to_pos(zoom: float = 0.9) -> ShotTemplate:
        """Instant cut to a position with optional zoom."""
        return ShotTemplate(
            id_prefix="cut-pos",
            kind={"type": "focus_position", "pos": Var("pos")},
            pan_ms=0,  # Instant cut
            dwell_ms=0,
            zoom=zoom,
            tags=["cut", "position"],
        )

    @staticmethod
    def focus_pos(
        pan_ms: int = 1600, dwell_ms: int = 900, zoom: float = 1.0
    ) -> ShotTemplate:
        """Smooth pan to focus on a position."""
        return ShotTemplate(
            id_prefix="focus-pos",
            kind={"type": "focus_position", "pos": Var("pos")},
            pan_ms=pan_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["focus", "position"],
        )

    @staticmethod
    def zoom_to_bbox(
        pan_ms: int = 2200, dwell_ms: int = 1600, zoom: Optional[float] = None
    ) -> ShotTemplate:
        """Zoom to fit a bounding box with optional zoom level."""
        return ShotTemplate(
            id_prefix="zoom-bbox",
            kind={"type": "zoom_to_fit", "bbox": Var("bbox")},
            pan_ms=pan_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["zoom", "bbox", "overview"],
        )

    @staticmethod
    def follow_entity(
        duration_ms: int, dwell_ms: int = 1200, zoom: float = 1.0
    ) -> ShotTemplate:
        """Follow an entity for a specified duration."""
        return ShotTemplate(
            id_prefix="follow-entity",
            kind={"type": "follow_entity", "entity_uid": Var("entity_uid")},
            pan_ms=duration_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["follow", "entity"],
        )

    @staticmethod
    def orbit_entity(
        duration_ms: int, radius_tiles: int, degrees: int, dwell_ms: int, zoom: float
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
            pan_ms=duration_ms,
            dwell_ms=dwell_ms,
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
            pan_ms=2200,
            dwell_ms=800,
            zoom=0.7,
            tags=["connection", "pre", "overview"],
        )

        # Post-shot: focus on the connection point
        post_template = ShotTemplate(
            id_prefix="connection-post",
            kind={"type": "focus_position", "pos": Var("center")},
            pan_ms=1600,
            dwell_ms=1200,
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

    def observe_action_stream(self, action_stream: List[dict], world_context: dict):
        """Observe a stream of normalized actions and generate appropriate shots.

        Args:
            action_stream: List of normalized action events from ast_actions
            world_context: Lightweight world facts (player pos, current tick, etc.)
        """
        self.action_stream.extend(action_stream)
        self.world_context.update(world_context)

        # Process each action in the stream
        for action in action_stream:
            self._map_action_to_shots(action)

    def observe_game_event(self, event: dict, delta: dict):
        """Observe a game event and generate appropriate shots.

        This is kept for backward compatibility with existing event-based detection.
        """
        self.events.append((event, delta))

        # Generate shots based on event type
        event_type = event.get("event")
        tick = event.get("tick", 0)
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
            shot = ShotLib.zoom_to_bbox(pan_ms=2000, dwell_ms=1500, zoom=0.8).render(
                tick=tick, bbox=bbox
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
            shot = ShotLib.zoom_to_bbox(pan_ms=1800, dwell_ms=1200, zoom=0.9).render(
                tick=tick, bbox=bbox
            )
            shot["tags"] = ["mining", "setup"]
            self.shots.append(shot)

        elif event_type == "building_placed":
            # Quick cut to building placement
            entity_type = delta.get("entity_type", "building")
            shot = ShotLib.cut_to_pos(zoom=1.0).render(tick=tick, pos=position)
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
            shot = ShotLib.zoom_to_bbox(pan_ms=2200, dwell_ms=1000, zoom=0.7).render(
                tick=tick, bbox=bbox
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
            shot = ShotLib.zoom_to_bbox(pan_ms=1500, dwell_ms=800, zoom=0.8).render(
                tick=tick, bbox=movement_bbox
            )
            shot["tags"] = ["movement", "player"]
            self.shots.append(shot)

    def _map_action_to_shots(self, action: dict):
        """Map a single action to appropriate shots using shot policies.

        This is where all the "what camera move should this action produce?" rules live.
        """
        action_type = action.get("type")
        args = action.get("args", {})
        tick = self.world_context.get("current_tick", 0)
        player_pos = self.world_context.get("player_position", [0, 0])

        if action_type == "move_to":
            self._handle_move_to_action(action, args, tick, player_pos)
        elif action_type == "place_entity":
            self._handle_place_entity_action(action, args, tick, player_pos)
        elif action_type == "place_entity_next_to":
            self._handle_place_entity_next_to_action(action, args, tick, player_pos)
        elif action_type == "connect_entities":
            self._handle_connect_entities_action(action, args, tick, player_pos)
        elif action_type == "insert_item":
            self._handle_insert_item_action(action, args, tick, player_pos)

    def _handle_move_to_action(
        self, action: dict, args: dict, tick: int, player_pos: list
    ):
        """Handle move_to actions - usually ignored unless policy says otherwise."""
        if not self.policy.pre_arrival_cut:
            return

        # Only create pre-arrival cuts for significant movements
        destination = args.get("destination", "")
        if destination and destination != str(player_pos):
            # Resolve destination position
            dest_pos = self._resolve_position(destination, player_pos)
            shot = ShotLib.cut_to_pos(zoom=0.9).render(tick=tick, pos=dest_pos)
            shot["tags"] = ["movement", "pre_arrival"]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

    def _handle_place_entity_action(
        self, action: dict, args: dict, tick: int, player_pos: list
    ):
        """Handle place_entity actions based on entity type."""
        prototype = args.get("prototype", "").lower()
        position = self._resolve_position(args.get("position", player_pos), player_pos)

        # Map entity types to shot policies
        if prototype in ["boiler", "steam_engine", "offshore_pump"]:
            # Power setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 15)
            shot = ShotLib.zoom_to_bbox(pan_ms=2000, dwell_ms=1500, zoom=0.8).render(
                tick=tick, bbox=bbox
            )
            shot["tags"] = ["power", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

        elif prototype in ["burner_mining_drill", "electric_mining_drill"]:
            # Mining setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 10)
            shot = ShotLib.zoom_to_bbox(pan_ms=1800, dwell_ms=1200, zoom=0.9).render(
                tick=tick, bbox=bbox
            )
            shot["tags"] = ["mining", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

        elif prototype in ["stone_furnace", "steel_furnace", "electric_furnace"]:
            # Smelting setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 8)
            shot = ShotLib.zoom_to_bbox(pan_ms=1800, dwell_ms=1200, zoom=0.9).render(
                tick=tick, bbox=bbox
            )
            shot["tags"] = ["smelting", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

        elif prototype in [
            "assembly_machine_1",
            "assembly_machine_2",
            "assembly_machine_3",
        ]:
            # Assembly setup - zoom to bbox
            bbox = self._create_bbox_around_position(position, 12)
            shot = ShotLib.zoom_to_bbox(pan_ms=1800, dwell_ms=1200, zoom=0.9).render(
                tick=tick, bbox=bbox
            )
            shot["tags"] = ["assembly", "setup", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

        else:
            # Generic building - quick cut
            shot = ShotLib.cut_to_pos(zoom=1.0).render(tick=tick, pos=position)
            shot["tags"] = ["building", "placed", prototype]
            self.shots.append(shot)
            print(
                f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
            )

    def _handle_place_entity_next_to_action(
        self, action: dict, args: dict, tick: int, player_pos: list
    ):
        """Handle place_entity_next_to actions - two-point connection sequence."""
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
        tgt = (
            resolve_pos(target)
            if callable(resolve_pos)
            else self._resolve_position(target, player_pos)
        )

        # Two-shot sequence
        templates = ShotLib.connection_two_point(
            padding=self.policy.connection_padding_tiles
        )
        # Pre: fit both points
        if callable(bbox_fn):
            connection_bbox = bbox_fn(
                target, position_expr, pad=self.policy.connection_padding_tiles
            )
        else:
            # fallback to padding around placed position
            connection_bbox = self._create_bbox_around_position(
                pos, self.policy.connection_padding_tiles
            )
        pre_shot = templates[0].render(tick=tick, connection_bbox=connection_bbox)
        pre_shot["tags"] = ["connection", "pre", "overview", prototype]
        self.shots.append(pre_shot)
        print(
            f"[cinema] add shot: {pre_shot['kind']['type']} tags={pre_shot.get('tags')} tick={pre_shot.get('when', {}).get('start_tick')}"
        )

        # Post: focus midpoint (or placed position as fallback)
        center = [(tgt[0] + pos[0]) / 2.0, (tgt[1] + pos[1]) / 2.0]
        post_tick = tick + pre_shot["pan_ms"] + pre_shot["dwell_ms"]
        post_shot = templates[1].render(tick=post_tick, center=center)
        post_shot["tags"] = ["connection", "post", "focus", prototype]
        self.shots.append(post_shot)
        print(
            f"[cinema] add shot: {post_shot['kind']['type']} tags={post_shot.get('tags')} tick={post_shot.get('when', {}).get('start_tick')}"
        )

    def _handle_connect_entities_action(
        self, action: dict, args: dict, tick: int, player_pos: list
    ):
        """Handle connect_entities actions - connection overview."""
        a_expr = args.get("a_expr", "")
        b_expr = args.get("b_expr", "")
        proto_name = args.get("proto_name", "")

        bbox_fn = self.world_context.get("bbox_two_points")
        if callable(bbox_fn):
            bbox = bbox_fn(a_expr, b_expr, pad=self.policy.connection_padding_tiles)
        else:
            center = player_pos
            bbox = self._create_bbox_around_position(center, 30)

        shot = ShotLib.zoom_to_bbox(pan_ms=2200, dwell_ms=1000, zoom=0.7).render(
            tick=tick, bbox=bbox
        )
        shot["tags"] = ["connection", "infrastructure", proto_name]
        self.shots.append(shot)
        print(
            f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
        )

    def _handle_insert_item_action(
        self, action: dict, args: dict, tick: int, player_pos: list
    ):
        """Handle insert_item actions - usually just a quick cut."""
        prototype = args.get("prototype", "").lower()
        position = self._resolve_position(args.get("position", player_pos), player_pos)

        shot = ShotLib.cut_to_pos(zoom=1.0).render(tick=tick, pos=position)
        shot["tags"] = ["insert", "item", prototype]
        self.shots.append(shot)
        print(
            f"[cinema] add shot: {shot['kind']['type']} tags={shot.get('tags')} tick={shot.get('when', {}).get('start_tick')}"
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

        This applies deduplication, merging, and narrative timing policies.
        """
        # Sort shots by tick to ensure proper ordering
        sorted_shots = sorted(
            self.shots, key=lambda s: s.get("when", {}).get("start_tick", 0)
        )

        # Apply deduplication and merging policies
        deduplicated_shots = self._apply_deduplication(sorted_shots)

        # Retime shots to a monotonic narrative clock in ticks so batches don’t explode at once
        if deduplicated_shots:
            base_tick = self.world_context.get("current_tick", 0)
            t = base_tick
            retimed = []
            for s in deduplicated_shots:
                # Compute duration in ticks from ms fields, fall back to 30 ticks if unknown
                pan_ms = s.get("pan_ms", 0)
                dwell_ms = s.get("dwell_ms", 0)
                dur_ticks = ms_to_ticks(pan_ms) + ms_to_ticks(dwell_ms)
                if dur_ticks <= 0:
                    dur_ticks = 30  # half a second at 60 tps
                # Assign start_tick and advance timeline with a tiny gap
                s.setdefault("when", {})["start_tick"] = t
                retimed.append(s)
                t += dur_ticks + 10  # small spacer
            deduplicated_shots = retimed

        return {"player": player, "start_zoom": 1.0, "shots": deduplicated_shots}

    def _apply_deduplication(self, shots: list) -> list:
        """Apply temporal + spatial deduplication to reduce déjà vu."""
        if not shots:
            return shots
        deduped = []
        # Keep a small recent footprint cache: (type, cx, cy, sx, sy) -> last_tick
        recent = {}

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
            t = s.get("when", {}).get("start_tick", 0)
            ktype = s.get("kind", {}).get("type", "")
            key_tuple = _bbox_center_span(s)
            if key_tuple is None:
                # No spatial info; apply basic temporal spacing (>=100 ticks)
                if (
                    not deduped
                    or t - deduped[-1].get("when", {}).get("start_tick", 0) >= 100
                ):
                    deduped.append(s)
                continue
            # Round to tile-ish precision to group near-identical frames
            cx, cy, sx, sy = key_tuple
            fp = (ktype, round(cx, 1), round(cy, 1), round(sx, 1), round(sy, 1))
            last_t = recent.get(fp)
            if last_t is None or (t - last_t) >= 240:  # ~4 seconds at 60 tps
                deduped.append(s)
                recent[fp] = t
            else:
                # Skip near-duplicate shot
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
