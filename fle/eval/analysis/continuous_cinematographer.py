"""
Continuous Cinematographer - A simplified camera placement system for Factorio.

This module focuses on placing the camera at key locations and lingering there,
similar to run_to_mp4.py but with camera logic managed by server.lua.

Key principles:
- Camera placement: Focus on getting the camera to the right places at the right time
- Simple shots: Each shot is just a camera position with timing
- No action management: Let server.lua handle screenshot capture automatically
- Program-level thinking: Generate shots based on program analysis
- Stability: Prioritize smooth camera movements and appropriate dwell times

The cinematographer generates simple shot plans that tell server.lua where to place
the camera and how long to stay there.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class ShotState(Enum):
    """Simple states for camera placement."""

    ESTABLISHING = "establishing"  # Wide overview shot
    FOCUS = "focus"  # Focused shot on specific area
    FOLLOW = "follow"  # Following shot
    REACTION = "reaction"  # Reaction shot showing results


@dataclass
class ContinuousShot:
    """Represents a simple camera shot with position and timing."""

    id: str
    state: ShotState
    kind: Dict[str, Any]  # Camera instruction (focus_position, zoom_to_fit, etc.)
    pan_ticks: int = 60  # Time to move to position (1 second default)
    dwell_ticks: int = 180  # Time to stay at position (3 seconds default)
    zoom: Optional[float] = None  # Zoom level (None = auto-calculate)
    tags: List[str] = field(default_factory=list)
    program_id: Optional[str] = None
    # Spatial information for reference
    spatial_center: Optional[Tuple[float, float]] = None
    spatial_radius: float = 0.0


@dataclass
class ProgramContext:
    """Context for a single program's execution."""

    program_id: str
    actions: List[Dict[str, Any]]
    world_context: Dict[str, Any]
    # Spatial bounds of program activity
    activity_bbox: Optional[List[List[float]]] = None
    # Current player position
    player_position: Tuple[float, float] = (0.0, 0.0)
    # Key positions to focus on
    key_positions: List[Tuple[float, float]] = field(default_factory=list)
    # Program type for shot strategy
    program_type: str = "generic"  # "placement", "connection", "movement", "generic"


class ContinuousCinematographer:
    """
    Prescient cinematographer that anticipates where action will happen.

    This cinematographer generates shot plans that position the camera WHERE THE ACTION
    WILL HAPPEN before it occurs, rather than reacting to it. The key insight is that
    with automatic screenshot capture, we need to be PRESCIENT - get the camera to
    the right place BEFORE the player/agent gets there.

    Philosophy:
    - Prescient positioning (anticipate where action will happen)
    - Stable framing (fewer, longer shots to avoid jarring movements)
    - Smart zoom levels (appropriate framing for the type of action)
    - Focus on the PRIMARY action location (where most work happens)
    """

    def __init__(self, player: int = 1):
        self.player = player
        self.shots: List[ContinuousShot] = []
        self.program_contexts: Dict[str, ProgramContext] = {}

        # Timing configuration focused on precision and smart positioning
        self.establishment_duration = 180  # 3 seconds for establishing shots
        self.focus_duration = (
            120  # 2 seconds for focus shots (enough to capture the action)
        )
        self.follow_duration = 150  # 2.5 seconds for follow shots
        self.reaction_duration = 120  # 2 seconds for reaction shots
        self.pan_duration = 60  # 1 second for camera movement (smooth transitions)

    def process_program(
        self,
        program_id: str,
        actions: List[Dict[str, Any]],
        world_context: Dict[str, Any],
    ) -> None:
        """Process a complete program and generate camera shots."""

        # Create program context
        context = ProgramContext(
            program_id=program_id,
            actions=actions,
            world_context=world_context,
            player_position=tuple(world_context.get("player_position", [0, 0])),
        )

        # Analyze program to determine key positions and type
        self._analyze_program(context)

        # Generate simple camera shots
        self._generate_camera_shots(context)

        # Store context for reference
        self.program_contexts[program_id] = context

    def _analyze_program(self, context: ProgramContext) -> None:
        """Analyze program to determine key positions and program type."""

        # Extract positions from actions
        positions = []
        action_types = set()

        for action in context.actions:
            action_type = action.get("type")
            action_types.add(action_type)

            # Extract position from action
            pos = self._extract_position_from_action(action, context.world_context)
            if pos:
                positions.append(pos)
                context.key_positions.append(pos)

        # Determine program type based on action types
        if "connect_entities" in action_types:
            context.program_type = "connection"
        elif any(t in action_types for t in ["place_entity", "place_entity_next_to"]):
            context.program_type = "placement"
        elif "move_to" in action_types:
            context.program_type = "movement"
        else:
            context.program_type = "generic"

        # Calculate activity bounding box
        if positions:
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            padding = 25.0
            context.activity_bbox = [
                [min(xs) - padding, min(ys) - padding],
                [max(xs) + padding, max(ys) + padding],
            ]

        # For prescient positioning, try to predict where action will actually happen
        # by looking at existing entities in the world
        self._enhance_positions_with_world_context(context)

    def _enhance_positions_with_world_context(self, context: ProgramContext) -> None:
        """Enhance position predictions using world context for better prescient positioning."""
        # This is where we could use world context to better predict where action will happen
        # For now, we'll keep the existing logic but this is where we could add:
        # - Entity existence checks
        # - Path prediction for movement
        # - Better positioning for connections

        # Future enhancement: Use world context to validate/refine positions
        # For example, if we're connecting entities, check if they actually exist
        # and adjust positioning accordingly
        pass

    def _extract_position_from_action(
        self, action: Dict[str, Any], world_context: Dict[str, Any]
    ) -> Optional[Tuple[float, float]]:
        """Extract position from action using world context resolvers."""

        action_type = action.get("type")
        args = action.get("args", {})

        # Try to resolve position based on action type
        if action_type == "move_to":
            pos_expr = args.get("destination") or args.get("pos_src")
        elif action_type in ["place_entity", "place_entity_next_to"]:
            pos_expr = args.get("position")
        elif action_type == "insert_item":
            pos_expr = args.get("position")
        elif action_type == "connect_entities":
            # For connect_entities, return the midpoint of the two entities
            a_expr = args.get("a_expr")
            b_expr = args.get("b_expr")
            if a_expr and b_expr:
                resolve_pos = world_context.get("resolve_position")
                if callable(resolve_pos):
                    try:
                        pos_a = resolve_pos(a_expr)
                        pos_b = resolve_pos(b_expr)
                        if (
                            isinstance(pos_a, (list, tuple))
                            and len(pos_a) >= 2
                            and isinstance(pos_b, (list, tuple))
                            and len(pos_b) >= 2
                        ):
                            # Return midpoint of the two positions
                            mid_x = (float(pos_a[0]) + float(pos_b[0])) / 2
                            mid_y = (float(pos_a[1]) + float(pos_b[1])) / 2
                            return (mid_x, mid_y)
                    except Exception:
                        pass
            return None
        else:
            return None

        if not pos_expr:
            return None

        # Use world context resolver
        resolve_pos = world_context.get("resolve_position")
        if callable(resolve_pos):
            try:
                resolved = resolve_pos(pos_expr)
                if isinstance(resolved, (list, tuple)) and len(resolved) >= 2:
                    return (float(resolved[0]), float(resolved[1]))
            except Exception:
                pass

        # Fallback to player position
        player_pos = world_context.get("player_position", [0, 0])
        return (float(player_pos[0]), float(player_pos[1]))

    def _generate_camera_shots(self, context: ProgramContext) -> None:
        """Generate prescient camera shots that anticipate where action will happen."""

        if not context.actions:
            return

        # Strategy: Prescient positioning - get camera to action location BEFORE it happens
        # 1. One establishing shot to show the area (if we have a bbox)
        if context.activity_bbox:
            self._create_establishing_shot(context)

        # 2. One focused shot on the PRIMARY action location (where most work happens)
        if context.key_positions:
            primary_pos = self._choose_primary_action_location(context)
            self._create_focus_shot(context, primary_pos, 0)

        # 3. Only add reaction shot if there are multiple distinct action areas
        if len(context.key_positions) > 1 and self._has_distinct_action_areas(context):
            self._create_reaction_shot(context)

    def _choose_primary_action_location(
        self, context: ProgramContext
    ) -> Tuple[float, float]:
        """Choose the primary location where most action will happen."""
        if not context.key_positions:
            return context.player_position

        # For connection programs, choose the midpoint to see both entities
        if context.program_type == "connection":
            xs = [p[0] for p in context.key_positions]
            ys = [p[1] for p in context.key_positions]
            return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

        # For placement programs, choose the first position (where building starts)
        elif context.program_type == "placement":
            return context.key_positions[0]

        # For movement programs, choose a position that shows the path
        elif context.program_type == "movement":
            # Choose a position that's between start and end
            if len(context.key_positions) >= 2:
                start = context.key_positions[0]
                end = context.key_positions[-1]
                return ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            else:
                return context.key_positions[0]

        # For other programs, choose the first position
        return context.key_positions[0]

    def _has_distinct_action_areas(self, context: ProgramContext) -> bool:
        """Check if there are multiple distinct areas where action happens."""
        if len(context.key_positions) < 2:
            return False

        # Check if positions are far enough apart to warrant separate shots
        min_distance = 20.0  # tiles
        for i, pos1 in enumerate(context.key_positions):
            for j, pos2 in enumerate(context.key_positions[i + 1 :], i + 1):
                distance = ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
                if distance > min_distance:
                    return True

        return False

    def _calculate_smart_zoom(
        self, context: ProgramContext, position: Tuple[float, float]
    ) -> float:
        """Calculate smart zoom level based on program type and position."""
        if context.program_type == "connection":
            # For connections, zoom out a bit to see both entities
            return 0.8
        elif context.program_type == "placement":
            # For placements, medium zoom to see the entity being placed
            return 1.1
        elif context.program_type == "movement":
            # For movement, zoom out to see the path
            return 0.9
        else:
            # Default zoom for other actions
            return 1.0

    def _create_establishing_shot(self, context: ProgramContext) -> None:
        """Create a precise establishing shot that frames the entire activity area."""
        if context.activity_bbox:
            establishing_shot = ContinuousShot(
                id=f"establish-{context.program_id}",
                state=ShotState.ESTABLISHING,
                kind={"type": "zoom_to_fit", "bbox": context.activity_bbox},
                pan_ticks=self.pan_duration,  # Smooth transition
                dwell_ticks=self.establishment_duration,  # Enough time to see the setup
                zoom=None,  # Let server.lua calculate optimal zoom from bbox
                tags=["establishing", "overview", "precise_framing"],
                program_id=context.program_id,
                spatial_center=context.key_positions[0]
                if context.key_positions
                else None,
                spatial_radius=25.0,
            )
            self.shots.append(establishing_shot)

    def _create_focus_shot(
        self, context: ProgramContext, position: Tuple[float, float], index: int
    ) -> None:
        """Create a prescient focus shot that anticipates where action will happen."""
        # Calculate smart zoom based on program type
        zoom_level = self._calculate_smart_zoom(context, position)

        focus_shot = ContinuousShot(
            id=f"focus-{index}-{context.program_id}",
            state=ShotState.FOCUS,
            kind={"type": "focus_position", "pos": list(position)},
            pan_ticks=self.pan_duration,  # Smooth transition to action location
            dwell_ticks=self.focus_duration,  # Stay there to capture the work
            zoom=zoom_level,  # Smart zoom for optimal framing
            tags=[
                "focus",
                f"position_{index}",
                "prescient_positioning",
                "action_anticipation",
            ],
            program_id=context.program_id,
            spatial_center=position,
            spatial_radius=8.0,
        )
        self.shots.append(focus_shot)

    def _create_reaction_shot(self, context: ProgramContext) -> None:
        """Create a precise reaction shot that shows the results."""
        # Use the first key position as the reaction focus
        reaction_pos = context.key_positions[0]
        zoom_level = self._calculate_smart_zoom(context, reaction_pos)

        reaction_shot = ContinuousShot(
            id=f"reaction-{context.program_id}",
            state=ShotState.REACTION,
            kind={"type": "focus_position", "pos": list(reaction_pos)},
            pan_ticks=self.pan_duration,  # Smooth transition to exact position
            dwell_ticks=self.reaction_duration,  # Enough time to see results
            zoom=zoom_level,  # Smart zoom for optimal framing
            tags=["reaction", "result", "precise_positioning", "outcome"],
            program_id=context.program_id,
            spatial_center=reaction_pos,
            spatial_radius=12.0,
        )
        self.shots.append(reaction_shot)

    def build_plan(self) -> Dict[str, Any]:
        """Build the final shot plan for execution."""

        # Convert continuous shots to the expected format
        shot_plan = []
        for i, shot in enumerate(self.shots):
            shot_dict = {
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
            shot_plan.append(shot_dict)

        return {
            "player": self.player,
            "start_zoom": 1.0,
            "shots": shot_plan,
            "plan_id": f"continuous-{uuid.uuid4().hex[:8]}",
            "capture": True,  # Always enable capture
            "capture_dir": "cinema_seq",  # Default capture directory
        }

    def reset(self) -> None:
        """Reset the cinematographer for a new session."""
        self.shots.clear()
        self.program_contexts.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about generated shots."""
        if not self.shots:
            return {"total_shots": 0, "total_duration": 0}

        total_duration = sum(shot.pan_ticks + shot.dwell_ticks for shot in self.shots)
        state_counts = {}
        for shot in self.shots:
            state = shot.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "total_shots": len(self.shots),
            "total_duration": total_duration,
            "state_counts": state_counts,
            "programs_processed": len(self.program_contexts),
        }


# Convenience function for backward compatibility
def create_continuous_cinematographer(player: int = 1) -> ContinuousCinematographer:
    """Create a new continuous cinematographer instance."""
    return ContinuousCinematographer(player=player)
