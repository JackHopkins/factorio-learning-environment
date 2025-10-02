"""
CinematicInstance - A Factorio instance that integrates cutscene actions with program execution hooks.

This module provides a CinematicInstance that combines:
- Hook system from screenshots_from_run.py for capturing after actions
- Cinematographer logic for generating camera shots
- Cutscene action integration for precise camera control
- Buffering system for managing shots across action calls

The instance allows for specific cutscene hooks to actions while maintaining
the ability to buffer and manage shots across multiple action calls.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum

from fle.env.instance import FactorioInstance


class ShotState(Enum):
    """Simple states for camera placement."""

    ESTABLISHING = "establishing"  # Wide overview shot
    FOCUS = "focus"  # Focused shot on specific area
    FOLLOW = "follow"  # Following shot
    REACTION = "reaction"  # Reaction shot showing results


@dataclass
class CinematicShot:
    """Represents a cinematic shot with position, timing, and metadata."""

    id: str
    state: ShotState
    kind: Dict[str, Any]  # Camera instruction (focus_position, zoom_to_fit, etc.)
    pan_ticks: int = 60  # Time to move to position (1 second default)
    dwell_ticks: int = 180  # Time to stay at position (3 seconds default)
    zoom: Optional[float] = None  # Zoom level (None = auto-calculate)
    tags: List[str] = field(default_factory=list)
    action_id: Optional[str] = None  # Associated action ID
    program_id: Optional[str] = None
    # Spatial information for reference
    spatial_center: Optional[Tuple[float, float]] = None
    spatial_radius: float = 0.0
    # Timing information
    start_tick: Optional[int] = None
    end_tick: Optional[int] = None


@dataclass
class ActionContext:
    """Context for a single action's execution."""

    action_id: str
    action_type: str
    args: Dict[str, Any]
    position: Optional[Tuple[float, float]] = None
    world_context: Dict[str, Any] = field(default_factory=dict)
    program_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ShotBuffer:
    """Manages buffering of shots across action calls."""

    def __init__(self, max_buffer_size: int = 10):
        self.shots: List[CinematicShot] = []
        self.max_buffer_size = max_buffer_size
        self.current_tick = 0

    def add_shot(self, shot: CinematicShot) -> None:
        """Add a shot to the buffer."""
        shot.start_tick = self.current_tick
        shot.end_tick = self.current_tick + shot.pan_ticks + shot.dwell_ticks
        self.shots.append(shot)

        # Trim buffer if it gets too large
        if len(self.shots) > self.max_buffer_size:
            self.shots = self.shots[-self.max_buffer_size :]

    def get_pending_shots(self) -> List[CinematicShot]:
        """Get shots that are ready to be executed."""
        return [shot for shot in self.shots if shot.start_tick <= self.current_tick]

    def advance_tick(self, ticks: int = 1) -> None:
        """Advance the current tick."""
        self.current_tick += ticks

    def clear_completed_shots(self) -> None:
        """Remove shots that have completed."""
        self.shots = [shot for shot in self.shots if shot.end_tick > self.current_tick]

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about the buffer."""
        return {
            "buffer_size": len(self.shots),
            "current_tick": self.current_tick,
            "pending_shots": len(self.get_pending_shots()),
            "completed_shots": len(
                [s for s in self.shots if s.end_tick <= self.current_tick]
            ),
        }


class CinematicInstance(FactorioInstance):
    """
    A Factorio instance that integrates cutscene actions with program execution hooks.

    This instance provides:
    - Hook system for capturing after actions
    - Cinematographer logic for generating camera shots
    - Cutscene action integration for precise camera control
    - Buffering system for managing shots across action calls
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Shot management
        self.shot_buffer = ShotBuffer()
        self.active_shots: List[CinematicShot] = []
        self.shot_counter = 0

        # Hook management
        self.pre_action_hooks: Dict[str, List[Callable]] = {}
        self.post_action_hooks: Dict[str, List[Callable]] = {}
        self.action_contexts: Dict[str, ActionContext] = {}

        # Cinematographer settings
        self.player = kwargs.get("player", 1)
        self.capture_enabled = True
        self.capture_dir = "cinema_seq"

        # Timing configuration
        self.establishment_duration = 180  # 3 seconds
        self.focus_duration = 120  # 2 seconds
        self.follow_duration = 150  # 2.5 seconds
        self.reaction_duration = 120  # 2 seconds
        self.pan_duration = 60  # 1 second

        # Initialize cutscene system
        self._initialize_cutscene_system()

    def _initialize_cutscene_system(self) -> None:
        """Initialize the cutscene system in Factorio."""
        # Clear any existing camera
        self.rcon_client.send_command("/c global.camera = nil")

        # Initialize cutscene system
        self.rcon_client.send_command("/c global.cutscene_system = {}")
        self.rcon_client.send_command("/c global.cutscene_system.shots = {}")
        self.rcon_client.send_command("/c global.cutscene_system.current_shot = nil")
        self.rcon_client.send_command(
            "/c global.cutscene_system.capture_enabled = true"
        )

    def register_pre_action_hook(self, action_type: str, hook_func: Callable) -> None:
        """Register a hook to be called before an action is executed."""
        if action_type not in self.pre_action_hooks:
            self.pre_action_hooks[action_type] = []
        self.pre_action_hooks[action_type].append(hook_func)

    def register_post_action_hook(self, action_type: str, hook_func: Callable) -> None:
        """Register a hook to be called after an action is executed."""
        if action_type not in self.post_action_hooks:
            self.post_action_hooks[action_type] = []
        self.post_action_hooks[action_type].append(hook_func)

    def _create_action_context(
        self, action_type: str, args: Dict[str, Any], program_id: Optional[str] = None
    ) -> ActionContext:
        """Create an action context for the given action."""
        action_id = f"{action_type}_{uuid.uuid4().hex[:8]}"

        # Extract position from action
        position = self._extract_position_from_action(action_type, args)

        # Create world context
        world_context = {
            "player_position": self._get_player_position(),
            "resolve_position": self._resolve_position,
        }

        return ActionContext(
            action_id=action_id,
            action_type=action_type,
            args=args,
            position=position,
            world_context=world_context,
            program_id=program_id,
        )

    def _extract_position_from_action(
        self, action_type: str, args: Dict[str, Any]
    ) -> Optional[Tuple[float, float]]:
        """Extract position from action arguments."""
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
                try:
                    pos_a = self._resolve_position(a_expr)
                    pos_b = self._resolve_position(b_expr)
                    if (
                        isinstance(pos_a, (list, tuple))
                        and len(pos_a) >= 2
                        and isinstance(pos_b, (list, tuple))
                        and len(pos_b) >= 2
                    ):
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

        try:
            resolved = self._resolve_position(pos_expr)
            if isinstance(resolved, (list, tuple)) and len(resolved) >= 2:
                return (float(resolved[0]), float(resolved[1]))
        except Exception:
            pass

        # Fallback to player position
        player_pos = self._get_player_position()
        return (float(player_pos[0]), float(player_pos[1]))

    def _resolve_position(self, pos_expr: Any) -> Any:
        """Resolve a position expression to actual coordinates."""
        # This would need to be implemented based on your position resolution logic
        # For now, return the expression as-is
        return pos_expr

    def _get_player_position(self) -> Tuple[float, float]:
        """Get the current player position."""
        try:
            # Get player position from Factorio
            self.rcon_client.send_command("/c game.players[1].position")
            # Parse the result and return coordinates
            # This is a simplified version - you'd need to parse the actual result
            return (0.0, 0.0)
        except Exception:
            return (0.0, 0.0)

    def _execute_pre_action_hooks(self, context: ActionContext) -> None:
        """Execute pre-action hooks for the given action context."""
        hooks = self.pre_action_hooks.get(context.action_type, [])
        for hook in hooks:
            try:
                hook(self, context)
            except Exception as e:
                print(f"Error in pre-action hook for {context.action_type}: {e}")

    def _execute_post_action_hooks(self, context: ActionContext) -> None:
        """Execute post-action hooks for the given action context."""
        hooks = self.post_action_hooks.get(context.action_type, [])
        for hook in hooks:
            try:
                hook(self, context)
            except Exception as e:
                print(f"Error in post-action hook for {context.action_type}: {e}")

    def _generate_cinematic_shots(self, context: ActionContext) -> List[CinematicShot]:
        """Generate cinematic shots for the given action context."""
        shots = []

        if not context.position:
            return shots

        # Determine shot strategy based on action type
        if context.action_type in ["place_entity", "place_entity_next_to"]:
            shots.extend(self._create_placement_shots(context))
        elif context.action_type == "connect_entities":
            shots.extend(self._create_connection_shots(context))
        elif context.action_type == "move_to":
            shots.extend(self._create_movement_shots(context))
        else:
            shots.extend(self._create_generic_shots(context))

        return shots

    def _create_placement_shots(self, context: ActionContext) -> List[CinematicShot]:
        """Create shots for entity placement actions."""
        shots = []

        # Focus shot on the placement location
        focus_shot = CinematicShot(
            id=f"focus_placement_{context.action_id}",
            state=ShotState.FOCUS,
            kind={"type": "focus_position", "pos": list(context.position)},
            pan_ticks=self.pan_duration,
            dwell_ticks=self.focus_duration,
            zoom=1.1,  # Medium zoom for entity placement
            tags=["placement", "focus", "entity_placement"],
            action_id=context.action_id,
            program_id=context.program_id,
            spatial_center=context.position,
            spatial_radius=8.0,
        )
        shots.append(focus_shot)

        return shots

    def _create_connection_shots(self, context: ActionContext) -> List[CinematicShot]:
        """Create shots for entity connection actions."""
        shots = []

        # Focus shot on the connection midpoint
        focus_shot = CinematicShot(
            id=f"focus_connection_{context.action_id}",
            state=ShotState.FOCUS,
            kind={"type": "focus_position", "pos": list(context.position)},
            pan_ticks=self.pan_duration,
            dwell_ticks=self.focus_duration,
            zoom=0.8,  # Zoom out to see both entities
            tags=["connection", "focus", "entity_connection"],
            action_id=context.action_id,
            program_id=context.program_id,
            spatial_center=context.position,
            spatial_radius=12.0,
        )
        shots.append(focus_shot)

        return shots

    def _create_movement_shots(self, context: ActionContext) -> List[CinematicShot]:
        """Create shots for movement actions."""
        shots = []

        # Focus shot on the destination
        focus_shot = CinematicShot(
            id=f"focus_movement_{context.action_id}",
            state=ShotState.FOCUS,
            kind={"type": "focus_position", "pos": list(context.position)},
            pan_ticks=self.pan_duration,
            dwell_ticks=self.focus_duration,
            zoom=0.9,  # Zoom out to see the path
            tags=["movement", "focus", "player_movement"],
            action_id=context.action_id,
            program_id=context.program_id,
            spatial_center=context.position,
            spatial_radius=10.0,
        )
        shots.append(focus_shot)

        return shots

    def _create_generic_shots(self, context: ActionContext) -> List[CinematicShot]:
        """Create generic shots for other actions."""
        shots = []

        # Simple focus shot
        focus_shot = CinematicShot(
            id=f"focus_generic_{context.action_id}",
            state=ShotState.FOCUS,
            kind={"type": "focus_position", "pos": list(context.position)},
            pan_ticks=self.pan_duration,
            dwell_ticks=self.focus_duration,
            zoom=1.0,  # Default zoom
            tags=["generic", "focus"],
            action_id=context.action_id,
            program_id=context.program_id,
            spatial_center=context.position,
            spatial_radius=8.0,
        )
        shots.append(focus_shot)

        return shots

    def _execute_cutscene_action(self, shot: CinematicShot) -> None:
        """Execute a cutscene action for the given shot."""
        try:
            # Build the cutscene command
            if shot.kind["type"] == "focus_position":
                pos = shot.kind["pos"]
                zoom_cmd = f", zoom={shot.zoom}" if shot.zoom else ""
                command = f"/c cutscene_focus_position({{x={pos[0]}, y={pos[1]}{zoom_cmd}}}, {shot.pan_ticks}, {shot.dwell_ticks})"
            elif shot.kind["type"] == "zoom_to_fit":
                bbox = shot.kind["bbox"]
                command = f"/c cutscene_zoom_to_fit({{x1={bbox[0][0]}, y1={bbox[0][1]}, x2={bbox[1][0]}, y2={bbox[1][1]}}}, {shot.pan_ticks}, {shot.dwell_ticks})"
            else:
                print(f"Unknown shot kind: {shot.kind['type']}")
                return

            # Execute the cutscene command
            self.rcon_client.send_command(command)

            # Add to active shots
            self.active_shots.append(shot)

            print(f"Executed cutscene action: {shot.id} ({shot.state.value})")

        except Exception as e:
            print(f"Error executing cutscene action {shot.id}: {e}")

    def _process_shot_buffer(self) -> None:
        """Process pending shots in the buffer."""
        pending_shots = self.shot_buffer.get_pending_shots()

        for shot in pending_shots:
            self._execute_cutscene_action(shot)

        # Advance tick and clear completed shots
        self.shot_buffer.advance_tick()
        self.shot_buffer.clear_completed_shots()

    def execute_action_with_cinema(
        self, action_type: str, args: Dict[str, Any], program_id: Optional[str] = None
    ) -> Any:
        """Execute an action with cinematic hooks."""
        # Create action context
        context = self._create_action_context(action_type, args, program_id)
        self.action_contexts[context.action_id] = context

        # Execute pre-action hooks
        self._execute_pre_action_hooks(context)

        # Generate cinematic shots
        shots = self._generate_cinematic_shots(context)

        # Add shots to buffer
        for shot in shots:
            self.shot_buffer.add_shot(shot)

        # Execute the actual action
        try:
            result = self.eval(f"{action_type}({self._args_to_lua_string(args)})")
        except Exception as e:
            print(f"Error executing action {action_type}: {e}")
            result = None

        # Execute post-action hooks
        self._execute_post_action_hooks(context)

        # Process shot buffer
        self._process_shot_buffer()

        return result

    def _args_to_lua_string(self, args: Dict[str, Any]) -> str:
        """Convert args dictionary to Lua string."""
        lua_args = []
        for key, value in args.items():
            if isinstance(value, str):
                lua_args.append(f"{key}='{value}'")
            elif isinstance(value, (list, tuple)):
                lua_args.append(f"{key}={{{', '.join(map(str, value))}}}")
            else:
                lua_args.append(f"{key}={value}")
        return ", ".join(lua_args)

    def register_cinematic_hooks(self) -> None:
        """Register cinematic hooks for common actions."""
        # Register hooks for entity placement
        self.register_post_action_hook("place_entity", self._cinematic_placement_hook)
        self.register_post_action_hook(
            "place_entity_next_to", self._cinematic_placement_hook
        )

        # Register hooks for connections
        self.register_post_action_hook(
            "connect_entities", self._cinematic_connection_hook
        )

        # Register hooks for movement
        self.register_post_action_hook("move_to", self._cinematic_movement_hook)

        # Register hooks for other actions
        self.register_post_action_hook("rotate_entity", self._cinematic_generic_hook)
        self.register_post_action_hook("shift_entity", self._cinematic_generic_hook)
        self.register_post_action_hook("harvest_resource", self._cinematic_generic_hook)

    def _cinematic_placement_hook(self, instance, context: ActionContext) -> None:
        """Cinematic hook for entity placement actions."""
        print(f"Executing cinematic placement hook for {context.action_id}")
        # Additional placement-specific cinematic logic can be added here

    def _cinematic_connection_hook(self, instance, context: ActionContext) -> None:
        """Cinematic hook for entity connection actions."""
        print(f"Executing cinematic connection hook for {context.action_id}")
        # Additional connection-specific cinematic logic can be added here

    def _cinematic_movement_hook(self, instance, context: ActionContext) -> None:
        """Cinematic hook for movement actions."""
        print(f"Executing cinematic movement hook for {context.action_id}")
        # Additional movement-specific cinematic logic can be added here

    def _cinematic_generic_hook(self, instance, context: ActionContext) -> None:
        """Cinematic hook for generic actions."""
        print(f"Executing cinematic generic hook for {context.action_id}")
        # Additional generic cinematic logic can be added here

    def get_cinematic_stats(self) -> Dict[str, Any]:
        """Get statistics about the cinematic system."""
        buffer_stats = self.shot_buffer.get_buffer_stats()

        return {
            "buffer_stats": buffer_stats,
            "active_shots": len(self.active_shots),
            "registered_pre_hooks": sum(
                len(hooks) for hooks in self.pre_action_hooks.values()
            ),
            "registered_post_hooks": sum(
                len(hooks) for hooks in self.post_action_hooks.values()
            ),
            "action_contexts": len(self.action_contexts),
            "capture_enabled": self.capture_enabled,
            "capture_dir": self.capture_dir,
        }

    def cleanup(self) -> None:
        """Clean up the cinematic instance."""
        # Clear cutscene system
        self.rcon_client.send_command("/c global.cutscene_system = nil")
        self.rcon_client.send_command("/c global.camera = nil")

        # Clear hooks and contexts
        self.pre_action_hooks.clear()
        self.post_action_hooks.clear()
        self.action_contexts.clear()

        # Clear shots
        self.shot_buffer.shots.clear()
        self.active_shots.clear()

        # Call parent cleanup
        super().cleanup()


# Convenience function for creating a cinematic instance
def create_cinematic_instance(*args, **kwargs) -> CinematicInstance:
    """Create a new cinematic instance with default settings."""
    instance = CinematicInstance(*args, **kwargs)
    instance.register_cinematic_hooks()
    return instance
