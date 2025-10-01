"""Clean templating system for Factorio cinematography.

This module provides a template-based system for creating cinematic shots that can be
rendered with concrete values from AST-extracted variables. The system is designed to
work with the new AST parser and runtime detection pipeline.

Key components:
- Var: Placeholder class for symbolic fields
- ShotTemplate: Template for shots with Var placeholders
- ShotLib: Library of common shot templates
- ShotPolicy: Tunable defaults for shot behavior
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


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
    pre_arrival_cut: bool = True


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
            tags=["cut", "position"]
        )
    
    @staticmethod
    def focus_pos(pan_ms: int = 1600, dwell_ms: int = 900, zoom: float = 1.0) -> ShotTemplate:
        """Smooth pan to focus on a position."""
        return ShotTemplate(
            id_prefix="focus-pos",
            kind={"type": "focus_position", "pos": Var("pos")},
            pan_ms=pan_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["focus", "position"]
        )
    
    @staticmethod
    def zoom_to_bbox(pan_ms: int = 2200, dwell_ms: int = 1600, zoom: Optional[float] = None) -> ShotTemplate:
        """Zoom to fit a bounding box with optional zoom level."""
        return ShotTemplate(
            id_prefix="zoom-bbox",
            kind={"type": "zoom_to_fit", "bbox": Var("bbox")},
            pan_ms=pan_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["zoom", "bbox", "overview"]
        )
    
    @staticmethod
    def follow_entity(duration_ms: int, dwell_ms: int = 1200, zoom: float = 1.0) -> ShotTemplate:
        """Follow an entity for a specified duration."""
        return ShotTemplate(
            id_prefix="follow-entity",
            kind={"type": "follow_entity", "entity_uid": Var("entity_uid")},
            pan_ms=duration_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["follow", "entity"]
        )
    
    @staticmethod
    def orbit_entity(duration_ms: int, radius_tiles: int, degrees: int, dwell_ms: int, zoom: float) -> ShotTemplate:
        """Orbit around an entity with specified parameters."""
        return ShotTemplate(
            id_prefix="orbit-entity",
            kind={
                "type": "orbit_entity",
                "entity_uid": Var("entity_uid"),
                "radius_tiles": radius_tiles,
                "degrees": degrees
            },
            pan_ms=duration_ms,
            dwell_ms=dwell_ms,
            zoom=zoom,
            tags=["orbit", "entity"]
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
            tags=["connection", "pre", "overview"]
        )
        
        # Post-shot: focus on the connection point
        post_template = ShotTemplate(
            id_prefix="connection-post",
            kind={"type": "focus_position", "pos": Var("center")},
            pan_ms=1600,
            dwell_ms=1200,
            zoom=1.0,
            tags=["connection", "post", "focus"]
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


class Cinematographer:
    """Placeholder for cinematographer class."""
    
    def __init__(self, camera_prefs: CameraPrefs, game_clock: GameClock):
        self.camera_prefs = camera_prefs
        self.game_clock = game_clock
        self.events = []
    
    def observe(self, event: dict, delta: dict):
        """Placeholder for event observation."""
        self.events.append((event, delta))
    
    def build_plan(self, player: int = 1) -> dict:
        """Placeholder for plan building."""
        return {
            "player": player,
            "start_zoom": 1.0,
            "shots": []
        }


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
