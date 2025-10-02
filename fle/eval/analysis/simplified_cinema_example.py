"""
Example usage of the simplified camera tracking system.

This module demonstrates how to use the simplified camera tracker
with real agent actions and movements.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from fle.env.tools.admin.cutscene.client import Cutscene
from fle.eval.analysis.simplified_cinema_integration import (
    create_simplified_cinema_integration,
)


class SimplifiedCinemaExample:
    """
    Example implementation showing how to use the simplified camera tracker.

    This class demonstrates the key principles:
    1. Camera stays fixed where action is happening
    2. Only move camera when agent moves out of bounds
    3. Special handling for Connect Entities
    4. Simple, clean API
    """

    def __init__(self, cutscene_tool: Cutscene, player: int = 1):
        self.cinema = create_simplified_cinema_integration(cutscene_tool, player)
        self.player = player

    def process_agent_program(
        self,
        program_id: str,
        actions: List[Dict[str, Any]],
        world_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process an agent program with simplified camera tracking.

        This is the main entry point that demonstrates the simplified approach.
        """

        print(f"\n=== Processing Program {program_id} ===")

        # Start tracking
        self.cinema.start_tracking()

        # Get initial player position
        player_pos = world_context.get("player_position", [0, 0])
        current_position = (float(player_pos[0]), float(player_pos[1]))

        print(f"Initial position: {current_position}")

        # Track initial position
        self.cinema.track_agent_position(current_position, program_id)

        # Process each action
        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            print(f"\nAction {i + 1}: {action_type}")

            # Extract position from action
            action_pos = self._extract_action_position(action, world_context)
            if action_pos:
                current_position = action_pos
                print(f"  Position: {action_pos}")

                # Check if this is a Connect Entities action
                if action_type == "connect_entities":
                    bounding_box = self._calculate_connect_entities_bbox(
                        action, world_context
                    )
                    print(f"  Connect Entities bbox: {bounding_box}")

                    # Track with special Connect Entities handling
                    result = self.cinema.track_agent_action(
                        program_id=program_id,
                        action_type=action_type,
                        position=current_position,
                        entities=self._extract_entities(action, world_context),
                        bounding_box=bounding_box,
                        world_context=world_context,
                    )
                else:
                    # Regular action tracking
                    result = self.cinema.track_agent_action(
                        program_id=program_id,
                        action_type=action_type,
                        position=current_position,
                        entities=self._extract_entities(action, world_context),
                        world_context=world_context,
                    )

                if result:
                    print(f"  Camera repositioned: {result.get('plan_id', 'unknown')}")
                else:
                    print("  Camera stays in current position")
            else:
                print("  No position found for action")

        # Stop tracking
        self.cinema.stop_tracking()

        # Get final stats
        stats = self.cinema.get_stats()
        print(f"\nFinal stats: {stats}")

        return {
            "program_id": program_id,
            "actions_processed": len(actions),
            "camera_stats": stats,
        }

    def _extract_action_position(
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

    def _extract_entities(
        self, action: Dict[str, Any], world_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract entities involved in the action."""
        # This is a simplified implementation
        # In practice, you'd extract actual entity information from the action
        return []

    def _calculate_connect_entities_bbox(
        self, action: Dict[str, Any], world_context: Dict[str, Any]
    ) -> Optional[List[List[float]]]:
        """Calculate bounding box for Connect Entities action."""

        args = action.get("args", {})
        a_expr = args.get("a_expr")
        b_expr = args.get("b_expr")

        if not a_expr or not b_expr:
            return None

        resolve_pos = world_context.get("resolve_position")
        if not callable(resolve_pos):
            return None

        try:
            pos_a = resolve_pos(a_expr)
            pos_b = resolve_pos(b_expr)

            if (
                isinstance(pos_a, (list, tuple))
                and len(pos_a) >= 2
                and isinstance(pos_b, (list, tuple))
                and len(pos_b) >= 2
            ):
                # Create bounding box around both entities
                padding = 10.0  # Add some padding
                min_x = min(pos_a[0], pos_b[0]) - padding
                max_x = max(pos_a[0], pos_b[0]) + padding
                min_y = min(pos_a[1], pos_b[1]) - padding
                max_y = max(pos_a[1], pos_b[1]) + padding

                return [[min_x, min_y], [max_x, max_y]]
        except Exception:
            pass

        return None


def create_simplified_cinema_example(
    cutscene_tool: Cutscene, player: int = 1
) -> SimplifiedCinemaExample:
    """Create a new simplified cinema example instance."""
    return SimplifiedCinemaExample(cutscene_tool, player)
