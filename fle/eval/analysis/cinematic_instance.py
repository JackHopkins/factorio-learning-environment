"""
CinematicInstance - A Factorio instance that integrates cutscene actions with program execution hooks.

This module provides a CinematicInstance that combines:
- Hook system for capturing actions
- Cinematographer logic for generating camera shots
- Clean integration with the cutscene admin tool

State management is handled by the Lua cutscene system (server.lua).
Python side focuses on high-level shot generation and hook coordination.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable

from fle.env.instance import FactorioInstance


@dataclass
class ActionContext:
    """Context for a single action's execution."""

    action_id: str
    action_type: str
    args: Dict[str, Any]
    position: Optional[Tuple[float, float]] = None
    program_id: Optional[str] = None


class CinematicInstance(FactorioInstance):
    """
    A Factorio instance that integrates cutscene actions with program execution hooks.

    This instance provides:
    - Hook system for capturing after actions
    - Cinematographer logic for generating camera shots
    - Clean integration with cutscene admin tool via self.controllers["cutscene"]

    State management is delegated to Lua (server.lua) for simplicity.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hook management
        self.pre_action_hooks: Dict[str, List[Callable]] = {}
        self.post_action_hooks: Dict[str, List[Callable]] = {}
        self.action_contexts: Dict[str, ActionContext] = {}

        # Cinematographer settings
        self.player = kwargs.get("player", 1)
        self.capture_dir = kwargs.get("capture_dir", "cinema_seq")

        # Timing configuration (in ticks, 60 ticks = 1 second)
        self.focus_duration = 120  # 2 seconds
        self.pan_duration = 60  # 1 second

        # Hooks registered flag
        self._hooks_registered = False

    @property
    def cutscene(self):
        """Get the cutscene controller for clean API access."""
        return self.controllers.get("cutscene")

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

        return ActionContext(
            action_id=action_id,
            action_type=action_type,
            args=args,
            position=position,
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

    def _generate_shot_intent(self, context: ActionContext) -> Optional[Dict[str, Any]]:
        """Generate a shot intent for the given action context.

        Returns a shot intent dict ready for submission to the cutscene tool.
        """
        if not context.position:
            return None

        # Determine shot parameters based on action type
        if context.action_type in ["place_entity", "place_entity_next_to"]:
            zoom = 2.5
        elif context.action_type == "connect_entities":
            zoom = 2.0
        elif context.action_type == "move_to":
            zoom = 2.2
        else:
            zoom = 2.0

        # Build shot intent
        shot_intent = {
            "id": f"shot_{context.action_type}_{context.action_id}",
            "kind": {
                "type": "focus_position",
                "pos": list(context.position),
            },
            "pan_ticks": self.pan_duration,
            "dwell_ticks": self.focus_duration,
            "zoom": zoom,
        }

        return shot_intent

    def execute_action_with_cinema(
        self, action_type: str, args: Dict[str, Any], program_id: Optional[str] = None
    ) -> Any:
        """Execute an action with cinematic hooks and shot submission."""
        # Create action context
        context = self._create_action_context(action_type, args, program_id)
        self.action_contexts[context.action_id] = context

        # Execute pre-action hooks
        self._execute_pre_action_hooks(context)

        # Generate and submit shot intent
        shot_intent = self._generate_shot_intent(context)
        if shot_intent and self.cutscene:
            try:
                response = self.cutscene.submit_shot(
                    shot=shot_intent,
                    player=self.player,
                    capture_dir=self.capture_dir,
                )
                if not response.get("ok"):
                    print(f"Warning: Shot submission failed: {response.get('error')}")
            except Exception as e:
                print(f"Error submitting shot for {action_type}: {e}")

        # Execute the actual action
        try:
            result = self.eval(f"{action_type}({self._args_to_lua_string(args)})")
        except Exception as e:
            print(f"Error executing action {action_type}: {e}")
            result = None

        # Execute post-action hooks
        self._execute_post_action_hooks(context)

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

    def get_cinematic_stats(self) -> Dict[str, Any]:
        """Get statistics about the cinematic system."""
        # Get stats from Lua side
        lua_stats = {}
        if self.cutscene:
            try:
                lua_stats = self.cutscene.get_stats()
            except Exception as e:
                print(f"Error getting Lua stats: {e}")

        # Combine with Python-side stats
        return {
            "lua_stats": lua_stats,
            "registered_pre_hooks": sum(
                len(hooks) for hooks in self.pre_action_hooks.values()
            ),
            "registered_post_hooks": sum(
                len(hooks) for hooks in self.post_action_hooks.values()
            ),
            "action_contexts": len(self.action_contexts),
            "capture_dir": self.capture_dir,
        }

    def get_cutscene_status(self, player: Optional[int] = None) -> Dict[str, Any]:
        """Get the current cutscene status for a player."""
        player = player or self.player
        if self.cutscene:
            try:
                return self.cutscene.get_status(player)
            except Exception as e:
                print(f"Error getting cutscene status: {e}")
        return {"ok": False, "error": "cutscene controller not available"}

    def cancel_cutscene(self, player: Optional[int] = None) -> Dict[str, Any]:
        """Cancel the active cutscene for a player."""
        player = player or self.player
        if self.cutscene:
            try:
                return self.cutscene.cancel(player)
            except Exception as e:
                print(f"Error cancelling cutscene: {e}")
        return {"ok": False, "error": "cutscene controller not available"}

    def register_cinematic_hooks(self) -> None:
        """Register all cinematic hooks for automatic camera positioning during tool execution."""
        if self._hooks_registered:
            return

        from fle.env.lua_manager import LuaScriptManager
        import time

        def _create_cutscene_for_action(
            tool_name: str, zoom: float = 1.5, dwell_ticks: int = 96
        ):
            """Create a pre-hook that positions camera before action executes."""

            def _pre_hook(tool_instance, *args, **kwargs):
                try:
                    # Extract position based on tool type
                    pos = None

                    if tool_name in ["place_entity", "place_entity_next_to"]:
                        # Position is 3rd positional arg or keyword 'position'
                        pos = kwargs.get("position")
                        if pos is None and len(args) >= 3:
                            pos = args[2]
                    elif tool_name == "connect_entities":
                        # For connections, get midpoint of both entities
                        entity_a = kwargs.get("entity_a") or (
                            args[0] if len(args) > 0 else None
                        )
                        entity_b = kwargs.get("entity_b") or (
                            args[1] if len(args) > 1 else None
                        )
                        if entity_a and entity_b:
                            # Get positions and calculate midpoint
                            pos_a = getattr(entity_a, "position", None)
                            pos_b = getattr(entity_b, "position", None)
                            if pos_a and pos_b:
                                mid_x = (pos_a.x + pos_b.x) / 2
                                mid_y = (pos_a.y + pos_b.y) / 2
                                pos = (mid_x, mid_y)
                    elif tool_name == "move_to":
                        # Destination is first arg
                        pos = kwargs.get("destination") or (
                            args[0] if len(args) > 0 else None
                        )
                    elif tool_name == "insert_item":
                        # Position is 2nd positional arg or keyword 'position'
                        pos = kwargs.get("position")
                        if pos is None and len(args) >= 2:
                            pos = args[1]

                    if pos is None:
                        return

                    # Convert position to [x, y] list
                    if hasattr(pos, "x") and hasattr(pos, "y"):
                        x, y = float(pos.x), float(pos.y)
                    elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
                        x, y = float(pos[0]), float(pos[1])
                    else:
                        return

                    # Create cutscene plan to position camera
                    plan = {
                        "player": self.player,
                        "shots": [
                            {
                                "id": f"auto-{tool_name}-{int(time.time() * 1000)}",
                                "kind": {
                                    "type": "focus_position",
                                    "pos": [x, y],
                                },
                                "pan_ticks": self.pan_duration,
                                "dwell_ticks": dwell_ticks,
                                "zoom": zoom,
                            }
                        ],
                    }

                    # Submit cutscene plan to position camera
                    if self.cutscene:
                        result = self.cutscene(plan)
                        print(f"[DEBUG] Cutscene result for {tool_name}: {result}")
                        if isinstance(result, dict) and not result.get("ok", False):
                            print(
                                f"Warning: Cutscene hook for {tool_name} at ({x:.1f}, {y:.1f}) failed: {result.get('error', 'unknown')}"
                            )
                        elif not isinstance(result, dict):
                            print(
                                f"Warning: Cutscene returned non-dict: {type(result)} = {result}"
                            )

                except Exception as e:
                    # Don't fail the action if cutscene fails
                    print(f"Warning: Cutscene hook failed for {tool_name}: {e}")

            return _pre_hook

        # Register hooks for each action type with appropriate zoom/dwell
        LuaScriptManager.register_pre_tool_hook(
            self,
            "place_entity",
            _create_cutscene_for_action("place_entity", zoom=1.5, dwell_ticks=96),
        )
        LuaScriptManager.register_pre_tool_hook(
            self,
            "place_entity_next_to",
            _create_cutscene_for_action(
                "place_entity_next_to", zoom=1.5, dwell_ticks=96
            ),
        )
        LuaScriptManager.register_pre_tool_hook(
            self,
            "connect_entities",
            _create_cutscene_for_action("connect_entities", zoom=1.2, dwell_ticks=120),
        )
        LuaScriptManager.register_pre_tool_hook(
            self,
            "move_to",
            _create_cutscene_for_action("move_to", zoom=1.3, dwell_ticks=72),
        )
        LuaScriptManager.register_pre_tool_hook(
            self,
            "insert_item",
            _create_cutscene_for_action("insert_item", zoom=1.6, dwell_ticks=84),
        )

        self._hooks_registered = True
        print("Cinematic hooks registered for all action types")

    def cleanup(self) -> None:
        """Clean up the cinematic instance."""
        # NOTE: stop_recording is now called in rollout_to_videos._cleanup()
        # to avoid duplicate calls. Keeping this as fallback only.
        if self.cutscene:
            try:
                # Check if recording is still active
                stats = self.cutscene.get_stats()
                if stats.get("capture_active"):
                    self.cutscene.stop_recording()
            except Exception:
                pass

        # Clear hooks and contexts
        self.pre_action_hooks.clear()
        self.post_action_hooks.clear()
        self.action_contexts.clear()

        # Call parent cleanup
        super().cleanup()


# Convenience function for creating a cinematic instance
def create_cinematic_instance(*args, **kwargs) -> CinematicInstance:
    """Create a new cinematic instance with default settings."""
    return CinematicInstance(*args, **kwargs)
