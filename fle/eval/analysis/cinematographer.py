"""Phase 3 cinematographer heuristics.

This module listens to replay events and emits ShotIntent dictionaries that the
admin cutscene tool understands.  The first revision focuses on a minimal set of
heuristics: "firsts" (first fuel, first electricity, first lab online) and
factory-scale changes.  Later iterations can build on this scaffolding with more
advanced scoring or shot budgeting.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ShotIntent / plan schemas -------------------------------------------------

ShotIntent = Dict[str, Any]


def new_plan(player: int = 1, plan_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new plan dictionary with sensible defaults."""

    return {
        "plan_id": plan_id or f"auto-{uuid.uuid4().hex[:8]}",
        "player": player,
        "start_zoom": 1.05,
        "shots": [],
    }


# Camera heuristics ---------------------------------------------------------


@dataclass
class CameraPrefs:
    """Collection of tunable preferences for the cinematographer."""

    focus_pan_ms: int = 1600
    focus_dwell_ms: int = 900
    zoom_pan_ms: int = 2200
    zoom_dwell_ms: int = 1600
    follow_duration_ms: int = 5000
    follow_dwell_ms: int = 1200
    default_zoom: float = 1.0
    overview_zoom: float = 0.6


@dataclass
class GameClock:
    """Adaptor over replay ticks to typed fields."""

    tick: int = 0

    def advance(self, by: int) -> None:
        self.tick += by


# World observation ---------------------------------------------------------


@dataclass
class EventBookmark:
    tick: int
    position: Optional[tuple] = None
    entity_name: Optional[str] = None
    label: str = ""


@dataclass
class FirstsTracker:
    seen_fuel: bool = False
    seen_electricity: bool = False
    seen_lab_online: bool = False


@dataclass
class Cinematographer:
    prefs: CameraPrefs
    clock: GameClock
    events: List[ShotIntent] = field(default_factory=list)
    firsts: FirstsTracker = field(default_factory=FirstsTracker)

    def observe(self, event: Dict[str, Any], delta: Dict[str, Any]) -> None:
        """Consume replay event + world delta.

        The exact schema will depend on the replay pipeline; for now we rely on
        a few well-known keys and gracefully ignore the rest.
        """

        tick = event.get("tick", self.clock.tick)
        self.clock.tick = tick

        kind = event.get("event") or event.get("type")

        # Handle power-related events (first time detection)
        if kind == "power_setup" and not self.firsts.seen_electricity:
            self.firsts.seen_electricity = True
            shot = self._zoom_to_fit(delta, label="first-power-setup")
            self.events.append(shot)
            print(f"  Created first-power-setup shot at tick {tick}")
        elif kind == "power_online" and not self.firsts.seen_electricity:
            self.firsts.seen_electricity = True
            shot = self._zoom_to_fit(delta, label="first-electricity")
            self.events.append(shot)
            print(f"  Created first-electricity shot at tick {tick}")

        # Handle fuel-related events
        elif kind == "fuel_inserter" and not self.firsts.seen_fuel:
            self.firsts.seen_fuel = True
            shot = self._focus(event, label="first-fuel")
            self.events.append(shot)
            print(f"  Created first-fuel shot at tick {tick}")

        # Handle research/lab events
        elif kind == "research_setup" and not self.firsts.seen_lab_online:
            self.firsts.seen_lab_online = True
            shot = self._zoom_to_fit(delta, label="first-research-setup")
            self.events.append(shot)
            print(f"  Created first-research-setup shot at tick {tick}")
        elif kind == "lab_online" and not self.firsts.seen_lab_online:
            self.firsts.seen_lab_online = True
            shot = self._focus(event, label="first-lab")
            self.events.append(shot)
            print(f"  Created first-lab shot at tick {tick}")

        # Handle mining operations
        elif kind == "mining_setup":
            shot = self._focus(event, label="mining-setup")
            self.events.append(shot)
            print(f"  Created mining-setup shot at tick {tick}")
        elif kind == "mining_started":
            shot = self._focus(event, label="mining")
            self.events.append(shot)
            print(f"  Created mining shot at tick {tick}")

        # Handle smelting operations
        elif kind == "smelting_setup":
            shot = self._zoom_to_fit(delta, label="smelting-setup")
            self.events.append(shot)
            print(f"  Created smelting-setup shot at tick {tick}")

        # Handle assembly operations
        elif kind == "assembly_setup":
            shot = self._zoom_to_fit(delta, label="assembly-setup")
            self.events.append(shot)
            print(f"  Created assembly-setup shot at tick {tick}")

        # Handle infrastructure connections
        elif kind == "infrastructure_connection":
            shot = self._zoom_to_fit(delta, label="infrastructure")
            self.events.append(shot)
            print(f"  Created infrastructure shot at tick {tick}")

        # Handle specific connection types with better framing
        elif kind == "belt_connection":
            # For belt connections, use connection_bbox if available, otherwise factory_bbox
            bbox = delta.get("connection_bbox") or delta.get("factory_bbox")
            if bbox:
                shot = self._zoom_to_fit(delta, label="belt-connection", bbox=bbox)
                self.events.append(shot)
                print(f"  Created belt-connection shot at tick {tick}")

        elif kind == "power_connection":
            # For power connections, show the full connection with padding
            bbox = delta.get("connection_bbox") or delta.get("factory_bbox")
            if bbox:
                shot = self._zoom_to_fit(delta, label="power-connection", bbox=bbox)
                self.events.append(shot)
                print(f"  Created power-connection shot at tick {tick}")

        elif kind == "fluid_connection":
            # For fluid connections, show the full pipe network
            bbox = delta.get("connection_bbox") or delta.get("factory_bbox")
            if bbox:
                shot = self._zoom_to_fit(delta, label="fluid-connection", bbox=bbox)
                self.events.append(shot)
                print(f"  Created fluid-connection shot at tick {tick}")

        # Handle production milestones
        elif kind == "production_milestone":
            shot = self._zoom_to_fit(delta, label="production-milestone")
            self.events.append(shot)
            print(f"  Created production-milestone shot at tick {tick}")

        # Handle general building placement
        elif kind == "building_placed":
            bbox = delta.get("factory_bbox")
            if bbox:
                shot = self._zoom_to_fit(delta, label="building")
                self.events.append(shot)
                print(f"  Created building shot at tick {tick}")

        # Handle player movement (only for significant moves)
        elif kind == "player_movement":
            # Create shots for significant player movements
            current_pos = event.get("position", [0, 0])
            movement_distance = delta.get("movement_distance", 0)

            # Ensure current_pos is a list/tuple with at least 2 elements
            if current_pos and len(current_pos) >= 2:
                # Use movement_bbox if available for better framing
                if "movement_bbox" in delta:
                    shot = self._zoom_to_fit(
                        delta, label="player-movement", bbox=delta["movement_bbox"]
                    )
                    shot["zoom"] = 0.9  # Slightly zoomed out to show movement context
                    shot["pan_ms"] = 2000  # Slower pan for movement shots
                    shot["dwell_ms"] = 1500  # Shorter dwell for movement
                else:
                    shot = self._focus(event, label="player-movement")

                self.events.append(shot)
                print(
                    f"  Created player-movement shot at tick {tick} (distance: {movement_distance:.1f})"
                )
                self._last_movement_pos = current_pos

        # Handle legacy events for backwards compatibility
        elif kind == "large_factory_change":
            bbox = delta.get("factory_bbox")
            if bbox:
                shot = self._zoom_to_fit(delta, label="factory-scale")
                self.events.append(shot)
                print(f"  Created factory-scale shot at tick {tick}")
        elif kind == "crafting_started":
            shot = self._focus(event, label="crafting")
            self.events.append(shot)
            print(f"  Created crafting shot at tick {tick}")
        elif kind == "print":
            # For debugging - create a simple focus shot
            shot = self._focus(event, label="debug")
            self.events.append(shot)
            print(f"  Created debug shot at tick {tick}")

    # --- shot constructors -------------------------------------------------
    def _focus(self, event: Dict[str, Any], label: str) -> ShotIntent:
        position = event.get("position") or (0, 0)
        if isinstance(position, dict):
            pos = [position.get("x", 0), position.get("y", 0)]
        else:
            pos = list(position)

        return {
            "id": f"focus-{label}-{self.clock.tick}",
            "pri": 10,
            "when": {"start_tick": self.clock.tick},
            "kind": {"type": "focus_position", "pos": pos},
            "pan_ms": self.prefs.focus_pan_ms,
            "dwell_ms": self.prefs.focus_dwell_ms,
            "zoom": self.prefs.default_zoom,
            "tags": [label],
        }

    def _zoom_to_fit(
        self,
        delta: Dict[str, Any],
        label: str,
        bbox: Optional[List[List[float]]] = None,
    ) -> ShotIntent:
        # Use provided bbox, or fall back to factory_bbox, or default
        if bbox is None:
            bbox = (
                delta.get("factory_bbox")
                or delta.get("connection_bbox")
                or [[-40, -40], [40, 40]]
            )

        return {
            "id": f"zoom-{label}-{self.clock.tick}",
            "pri": 8,
            "when": {"start_tick": self.clock.tick + 30},
            "kind": {
                "type": "zoom_to_fit",
                "bbox": bbox,
            },
            "pan_ms": self.prefs.zoom_pan_ms,
            "dwell_ms": self.prefs.zoom_dwell_ms,
            "zoom": self.prefs.overview_zoom,
            "tags": [label, "overview"],
        }

    # --- output ------------------------------------------------------------
    def flush(self) -> List[ShotIntent]:
        shots = self.events
        self.events = []
        return shots

    def build_plan(self, player: int = 1) -> Dict[str, Any]:
        plan = new_plan(player)
        plan["shots"] = self.flush()
        return plan


__all__ = [
    "ShotIntent",
    "CameraPrefs",
    "GameClock",
    "Cinematographer",
    "new_plan",
]
