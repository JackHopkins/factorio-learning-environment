"""
SubtitleTracker - Captures tool execution events and generates WebVTT subtitles.

This module provides real-time tracking of Factorio tool executions during
cinema recording sessions, capturing precise tick-based timing for each action
and generating synchronized WebVTT subtitle files.

Architecture:
- Hooks into tool pre/post execution via LuaScriptManager
- Captures start/end ticks for each action
- Generates WebVTT files with styled cues
- Handles speed multipliers and timestamp conversion

Integration:
- Works with CinematicInstance for automatic hook registration
- Synchronizes with rollout_to_videos rendering pipeline
- Outputs .vtt files alongside .mp4 videos
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fle.env.lua_manager import LuaScriptManager


@dataclass
class ToolExecutionEvent:
    """Event representing a single tool execution with timing information."""

    program_id: int
    tool_name: str
    start_tick: int
    end_tick: int
    args: Dict[str, Any]
    position: Optional[Tuple[float, float]] = None
    result: Optional[Any] = None

    def to_vtt_timestamp(self, tick: int, speed: float = 4.0) -> str:
        """
        Convert game tick to WebVTT timestamp format.

        Args:
            tick: Game tick number
            speed: Video speed multiplier (default 4.0x)

        Returns:
            Formatted timestamp string (HH:MM:SS.mmm)

        Formula:
            video_seconds = tick / (18 ticks/frame × 24 fps × speed)
        """
        # 18 ticks per frame, 24 fps input, speed multiplier
        video_seconds = tick / (18 * 24 * speed)

        hours = int(video_seconds // 3600)
        minutes = int((video_seconds % 3600) // 60)
        seconds = video_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    def get_duration_ticks(self) -> int:
        """Get the duration of this event in ticks."""
        return self.end_tick - self.start_tick

    def get_duration_seconds(self) -> float:
        """Get the duration of this event in game seconds."""
        return self.get_duration_ticks() / 60.0

    def format_subtitle_text(self, styled: bool = True) -> str:
        """
        Generate human-readable subtitle text for this event.

        Args:
            styled: If True, include WebVTT styling tags

        Returns:
            Formatted subtitle text
        """
        if styled:
            return self._format_styled_text()
        else:
            return self._format_plain_text()

    def _format_plain_text(self) -> str:
        """Format as plain text without styling."""
        arg_parts = []
        for key, value in self.args.items():
            formatted_value = self._format_value(key, value)
            arg_parts.append(f"{key}={formatted_value}")

        arg_str = ", ".join(arg_parts)
        return f"{self.tool_name}({arg_str})"

    def _format_styled_text(self) -> str:
        """Format with WebVTT styling tags."""
        parts = [f"<c.tool>{self.tool_name}</c>("]

        arg_items = list(self.args.items())
        for i, (key, value) in enumerate(arg_items):
            if i > 0:
                parts.append(", ")

            parts.append(f"<c.arg-key>{key}</c>=")

            formatted_value = self._format_value_styled(key, value)
            parts.append(formatted_value)

        parts.append(")")
        return "".join(parts)

    def _format_value(self, key: str, value: Any) -> str:
        """Format a value for plain text display."""
        if key == "position" and isinstance(value, (tuple, list)) and len(value) >= 2:
            return f"({value[0]:.1f}, {value[1]:.1f})"
        elif hasattr(value, "__name__"):  # Enum or class
            return value.__name__
        elif hasattr(value, "name"):  # Object with name attribute
            return str(value.name)
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return str(value)

    def _format_value_styled(self, key: str, value: Any) -> str:
        """Format a value with WebVTT styling tags."""
        if key == "position" and isinstance(value, (tuple, list)) and len(value) >= 2:
            return f"<c.position>({value[0]:.1f}, {value[1]:.1f})</c>"
        elif hasattr(value, "__name__"):
            return f"<c.arg-value>{value.__name__}</c>"
        elif hasattr(value, "name"):
            return f"<c.arg-value>{value.name}</c>"
        elif isinstance(value, str):
            return f'<c.arg-value>"{value}"</c>'
        else:
            return f"<c.arg-value>{value}</c>"


@dataclass
class ProgramExecutionEvent:
    """Event representing a complete program execution."""

    program_id: int
    start_tick: int
    end_tick: int
    code_preview: str
    num_actions: int


class SubtitleTracker:
    """
    Tracks tool executions and generates WebVTT subtitle files.

    This class integrates with CinematicInstance to capture tool execution
    events in real-time using pre/post hooks, then generates synchronized
    WebVTT subtitle files for the rendered videos.

    Usage:
        tracker = SubtitleTracker(cinematic_instance, speed=4.0)
        tracker.register_hooks()
        tracker.start_program(program_id=4701)
        # ... program executes, events captured automatically ...
        tracker.generate_webvtt(output_path)
    """

    def __init__(self, cinematic_instance, speed: float = 4.0):
        """
        Initialize subtitle tracker.

        Args:
            cinematic_instance: CinematicInstance to track
            speed: Video speed multiplier for timestamp conversion
        """
        self.instance = cinematic_instance
        self.speed = speed
        self.events: List[ToolExecutionEvent] = []
        self.program_events: List[ProgramExecutionEvent] = []

        # Session-level tick tracking (absolute ticks across resets)
        self.session_start_tick: Optional[int] = None
        self.session_tick_offset: int = 0  # Cumulative offset across resets

        # Current program tracking
        self.current_program_id: Optional[int] = None
        self.current_program_start_tick: Optional[int] = None
        self.current_program_action_count: int = 0

        # Pending event for pre/post hook coordination
        self._pending_event: Optional[Dict[str, Any]] = None

        # Hooks registered flag
        self._hooks_registered = False

    def _get_current_tick(self) -> int:
        """
        Get current game tick from Factorio (session-absolute).

        Returns:
            Absolute tick number accounting for resets
        """
        try:
            result = self.instance.rcon_client.send_command(
                "/c rcon.print(global.elapsed_ticks or 0)"
            )
            relative_tick = int(result.strip()) if result else 0

            # Return absolute tick by adding session offset
            return self.session_tick_offset + relative_tick
        except Exception as e:
            print(f"Warning: Could not get current tick: {e}")
            return self.session_tick_offset

    def mark_reset(self):
        """
        Mark that instance.reset() is about to be called.

        This captures the current tick before reset and updates the offset.
        Call this BEFORE instance.reset().
        """
        current_absolute = self._get_current_tick()
        # Update offset to maintain absolute tick continuity
        self.session_tick_offset = current_absolute

    def start_program(self, program_id: int, code_preview: Optional[str] = None):
        """
        Mark the start of a new program execution.

        Args:
            program_id: Unique identifier for the program
            code_preview: Optional preview of the program code
        """
        self.current_program_id = program_id
        self.current_program_start_tick = self._get_current_tick()
        self.current_program_action_count = 0

        # Initialize session start tick on first program
        if self.session_start_tick is None:
            self.session_start_tick = self.current_program_start_tick
            print(
                f"[SubtitleTracker] Session started at tick {self.session_start_tick}"
            )

        if code_preview:
            # Truncate long code
            if len(code_preview) > 100:
                code_preview = code_preview[:97] + "..."

        print(
            f"[SubtitleTracker] Started tracking program {program_id} at absolute tick {self.current_program_start_tick} (offset: {self.session_tick_offset})"
        )

    def end_program(self):
        """Mark the end of the current program execution."""
        if self.current_program_id is None:
            return

        end_tick = self._get_current_tick()

        # Create program event
        program_event = ProgramExecutionEvent(
            program_id=self.current_program_id,
            start_tick=self.current_program_start_tick or 0,
            end_tick=end_tick,
            code_preview="",
            num_actions=self.current_program_action_count,
        )
        self.program_events.append(program_event)

        print(
            f"[SubtitleTracker] Ended program {self.current_program_id}: {self.current_program_action_count} actions, {end_tick - (self.current_program_start_tick or 0)} ticks"
        )

        # Reset current program tracking
        self.current_program_id = None
        self.current_program_start_tick = None
        self.current_program_action_count = 0

    def _extract_position(
        self, tool_name: str, args: tuple, kwargs: dict
    ) -> Optional[Tuple[float, float]]:
        """
        Extract position from tool arguments.

        Args:
            tool_name: Name of the tool being executed
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Position tuple (x, y) or None
        """
        # Try keyword args first
        pos = kwargs.get("position")
        if pos:
            return self._normalize_position(pos)

        # Tool-specific position extraction
        if tool_name in ["place_entity", "place_entity_next_to"]:
            # Position is usually 2nd or 3rd arg, or 'position' kwarg
            if len(args) >= 2:
                pos = args[1]
                return self._normalize_position(pos)

        elif tool_name == "move_to":
            # Destination is first arg
            if len(args) >= 1:
                pos = args[0]
                return self._normalize_position(pos)
            pos = kwargs.get("destination")
            if pos:
                return self._normalize_position(pos)

        elif tool_name == "insert_item":
            # Position is usually target entity position
            target = kwargs.get("target") or (args[1] if len(args) >= 2 else None)
            if target and hasattr(target, "position"):
                return self._normalize_position(target.position)

        elif tool_name == "connect_entities":
            # Could extract midpoint between entities
            entity_a = kwargs.get("entity_a") or (args[0] if len(args) >= 1 else None)
            entity_b = kwargs.get("entity_b") or (args[1] if len(args) >= 2 else None)

            if entity_a and entity_b:
                pos_a = self._normalize_position(getattr(entity_a, "position", None))
                pos_b = self._normalize_position(getattr(entity_b, "position", None))

                if pos_a and pos_b:
                    # Return midpoint
                    return ((pos_a[0] + pos_b[0]) / 2, (pos_a[1] + pos_b[1]) / 2)

        return None

    def _normalize_position(self, pos: Any) -> Optional[Tuple[float, float]]:
        """
        Normalize various position representations to (x, y) tuple.

        Args:
            pos: Position in various formats (tuple, list, object with x/y)

        Returns:
            Normalized (x, y) tuple or None
        """
        if pos is None:
            return None

        if isinstance(pos, (tuple, list)) and len(pos) >= 2:
            return (float(pos[0]), float(pos[1]))

        if hasattr(pos, "x") and hasattr(pos, "y"):
            return (float(pos.x), float(pos.y))

        return None

    def _create_pre_hook(self, tool_name: str):
        """
        Create a pre-hook function for a specific tool.

        Args:
            tool_name: Name of the tool to hook

        Returns:
            Hook function that captures event start
        """

        def _pre_hook(tool_instance, *args, **kwargs):
            try:
                # Capture start tick
                start_tick = self._get_current_tick()

                # Extract position
                position = self._extract_position(tool_name, args, kwargs)

                # Store pending event for post-hook
                self._pending_event = {
                    "tool_name": tool_name,
                    "start_tick": start_tick,
                    "args": kwargs.copy(),  # Store kwargs only for cleaner display
                    "position": position,
                }

            except Exception as e:
                print(f"Warning: Error in subtitle pre-hook for {tool_name}: {e}")

        return _pre_hook

    def _create_post_hook(self, tool_name: str):
        """
        Create a post-hook function for a specific tool.

        Args:
            tool_name: Name of the tool to hook

        Returns:
            Hook function that captures event end
        """

        def _post_hook(tool_instance, result):
            try:
                # Capture end tick
                end_tick = self._get_current_tick()

                # Retrieve pending event
                if self._pending_event is None:
                    return

                pending = self._pending_event

                # Create full event
                event = ToolExecutionEvent(
                    program_id=self.current_program_id or 0,
                    tool_name=pending["tool_name"],
                    start_tick=pending["start_tick"],
                    end_tick=end_tick,
                    args=pending["args"],
                    position=pending["position"],
                    result=result,
                )

                self.events.append(event)
                self.current_program_action_count += 1

                # Clear pending event
                self._pending_event = None

            except Exception as e:
                print(f"Warning: Error in subtitle post-hook for {tool_name}: {e}")

        return _post_hook

    def register_hooks(self, tools: Optional[List[str]] = None):
        """
        Register subtitle tracking hooks for specified tools.

        Args:
            tools: List of tool names to track. If None, uses default set.
        """
        if self._hooks_registered:
            print("[SubtitleTracker] Hooks already registered, skipping")
            return

        if tools is None:
            # Default set of tools to track
            tools = [
                "place_entity",
                "place_entity_next_to",
                "connect_entities",
                "move_to",
                "insert_item",
                "craft_item",
                "harvest_resource",
                "pickup_entity",
                "rotate_entity",
            ]

        for tool in tools:
            # Register pre-hook
            LuaScriptManager.register_pre_tool_hook(
                self.instance, tool, self._create_pre_hook(tool)
            )

            # Register post-hook
            LuaScriptManager.register_post_tool_hook(
                self.instance, tool, self._create_post_hook(tool)
            )

        self._hooks_registered = True
        print(
            f"[SubtitleTracker] Registered hooks for {len(tools)} tools: {', '.join(tools)}"
        )

    def generate_webvtt(
        self, output_path: Path, include_programs: bool = False
    ) -> None:
        """
        Generate WebVTT subtitle file from captured events.

        Args:
            output_path: Path to write .vtt file
            include_programs: If True, include program-level cues
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # Write WebVTT header
            f.write("WEBVTT\n\n")

            # Write styling
            f.write(self._generate_style_block())
            f.write("\n")

            # Write cues for each event
            for event in self.events:
                f.write(self._generate_cue(event))
                f.write("\n")

        print(f"[SubtitleTracker] Generated WebVTT subtitle file: {output_path}")
        print(f"  Total events: {len(self.events)}")
        print(f"  Total programs: {len(self.program_events)}")

    def _generate_style_block(self) -> str:
        """
        Generate WebVTT STYLE block with CSS for subtitle formatting.

        Returns:
            STYLE block as string
        """
        return """STYLE
::cue {
  background-color: rgba(0, 0, 0, 0.85);
  color: #FFFFFF;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 16px;
  line-height: 1.5;
  padding: 8px 12px;
  border-radius: 4px;
  text-align: left;
}

::cue(.tool) {
  color: #4CAF50;
  font-weight: bold;
}

::cue(.arg-key) {
  color: #90CAF9;
}

::cue(.arg-value) {
  color: #FFB74D;
}

::cue(.position) {
  color: #BA68C8;
}

::cue(.program) {
  background-color: rgba(33, 150, 243, 0.9);
  color: white;
  font-weight: bold;
}
"""

    def _generate_cue(self, event: ToolExecutionEvent) -> str:
        """
        Generate WebVTT cue for a single event.

        Args:
            event: Event to generate cue for

        Returns:
            Formatted cue as string
        """
        # Calculate timestamps
        start_ts = event.to_vtt_timestamp(event.start_tick, self.speed)
        end_ts = event.to_vtt_timestamp(event.end_tick, self.speed)

        # Format subtitle text with styling
        text = event.format_subtitle_text(styled=True)

        # Generate cue with metadata comment
        duration_ticks = event.get_duration_ticks()
        cue = f"NOTE Program {event.program_id}, {event.tool_name}, Ticks {event.start_tick}-{event.end_tick} ({duration_ticks} ticks)\n"
        cue += f"{start_ts} --> {end_ts}\n"
        cue += f"{text}\n"

        return cue

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about captured events.

        Returns:
            Dictionary with statistics
        """
        if not self.events:
            return {
                "total_events": 0,
                "total_programs": len(self.program_events),
            }

        # Calculate statistics
        tool_counts = {}
        total_duration_ticks = 0

        for event in self.events:
            tool_counts[event.tool_name] = tool_counts.get(event.tool_name, 0) + 1
            total_duration_ticks += event.get_duration_ticks()

        return {
            "total_events": len(self.events),
            "total_programs": len(self.program_events),
            "total_duration_ticks": total_duration_ticks,
            "total_duration_seconds": total_duration_ticks / 60.0,
            "tool_counts": tool_counts,
            "speed_multiplier": self.speed,
        }
