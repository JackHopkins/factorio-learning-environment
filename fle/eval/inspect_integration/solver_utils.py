"""Common utilities for Factorio solvers.

Extracts reusable functions from solver implementations to reduce code duplication
and enable easy creation of solver variants with different context management strategies.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pydantic import Field
from inspect_ai.util import StoreModel
from inspect_ai.model import (
    ChatMessageUser,
    ContentImage,
    ContentText,
)

from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.observation_formatter import TreeObservationFormatter

logger = logging.getLogger(__name__)


class StepResult(StoreModel):
    """Store model for individual step results"""

    step: int = Field(default=0)
    production_score: float = Field(default=0.0)
    program_length: int = Field(default=0)
    execution_time: float = Field(default=0.0)
    program_content: str = Field(default="")
    program_output: str = Field(default="")


class TrajectoryData(StoreModel):
    """Store model for trajectory tracking data"""

    production_score: float = Field(default=0.0)
    automated_production_score: float = Field(
        default=0.0
    )  # Score excluding harvested/crafted
    total_steps: int = Field(default=0)
    current_score: float = Field(default=0.0)
    final_score: float = Field(default=0.0)
    final_automated_score: float = Field(default=0.0)  # Final automated score
    scores: List[float] = Field(default_factory=list)
    automated_scores: List[float] = Field(
        default_factory=list
    )  # Automated scores per step
    steps: List[dict] = Field(default_factory=list)
    error: str = Field(default="")
    ticks: List[int] = Field(default_factory=list)

    # Achievement tracking - unique item types produced
    produced_item_types: List[str] = Field(
        default_factory=list
    )  # List of unique item type names produced during trajectory

    # Research tracking - technologies researched during trajectory
    researched_technologies: List[str] = Field(
        default_factory=list
    )  # List of technology names that have been researched

    # Latency tracking fields
    inference_latencies: List[float] = Field(default_factory=list)
    env_execution_latencies: List[float] = Field(default_factory=list)
    policy_execution_latencies: List[float] = Field(default_factory=list)
    sleep_durations: List[float] = Field(default_factory=list)
    total_step_latencies: List[float] = Field(default_factory=list)


@dataclass
class SolverConfig:
    """Configuration for solver behavior."""

    # Context management
    include_images_in_history: bool = True  # Whether to keep images in message history
    max_messages: int = 25  # Max messages before trimming
    trim_to: int = 16  # Number of recent messages to keep when trimming

    # Observation formatting
    include_entities: bool = True  # Include entity list in observations
    include_research: bool = False  # Include research state
    include_flows: bool = False  # Include production flows in pre-step obs

    # Code history management
    max_code_history: int = -1  # -1 = unlimited, else max chars of code per message
    summarize_old_code: bool = False  # Replace old code with summaries

    # Vision
    vision_enabled: bool = False  # Use full sprite renderer

    # Fixed context mode (HUD style)
    use_fixed_context: bool = False  # Rebuild context each step (no growing history)
    max_diary_tokens: int = 8000  # Max tokens for reasoning diary in fixed context mode


def render_vision_image(gym_env: FactorioGymEnv) -> Tuple[Optional[str], Optional[str]]:
    """Render an image centered on the player using the full sprite renderer.

    Returns:
        Tuple of (base64_image_data_url, viewport_info_string)
        Returns (None, None) if rendering fails
    """
    try:
        namespace = gym_env.instance.namespaces[0]
        player_pos = namespace.player_location
        vis_logger = logging.getLogger(__name__)
        vis_logger.info(
            f"👁️ Vision render: player at ({player_pos.x:.1f}, {player_pos.y:.1f})"
        )

        result = namespace._render(
            radius=64,
            max_render_radius=32,
            position=player_pos,
            include_status=True,
        )

        base64_data = result.to_base64()
        image_data_url = f"data:image/png;base64,{base64_data}"

        viewport = result.viewport
        vis_logger.info(
            f"👁️ Vision render: viewport center ({viewport.center_x:.1f}, {viewport.center_y:.1f}), "
            f"size {viewport.width_tiles:.0f}x{viewport.height_tiles:.0f} tiles, "
            f"image {viewport.image_width}x{viewport.image_height}px"
        )

        viewport_info = f"""**Viewport Information:**
- Center: ({viewport.center_x:.1f}, {viewport.center_y:.1f})
- World bounds: ({viewport.world_min_x:.1f}, {viewport.world_min_y:.1f}) to ({viewport.world_max_x:.1f}, {viewport.world_max_y:.1f})
- Size: {viewport.width_tiles:.0f} x {viewport.height_tiles:.0f} tiles
- Image: {viewport.image_width} x {viewport.image_height} pixels
- Scale: {viewport.scaling:.1f} pixels/tile"""

        return image_data_url, viewport_info
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to render vision image: {e}", exc_info=True
        )
        return None, None


@dataclass
class ZoomLevelImage:
    """Container for a single zoom level image with metadata."""

    image_data_url: str
    zoom_level: int
    viewport_info: str


def render_multi_zoom_images(
    gym_env: FactorioGymEnv,
    zoom_levels: List[int] = None,
) -> List[ZoomLevelImage]:
    """Render multiple images at different zoom levels, all with the same dimensions.

    Each zoom level corresponds to max_render_radius, which determines how many
    tiles are visible. Lower values = more zoomed in (fewer tiles visible),
    higher values = more zoomed out (more tiles visible).

    Args:
        gym_env: The Factorio gym environment
        zoom_levels: List of zoom levels (max_render_radius values).
                     Default: [16, 32, 64] for close, medium, far views.

    Returns:
        List of ZoomLevelImage objects, one for each zoom level.
        Returns empty list if all renders fail.
    """
    if zoom_levels is None:
        zoom_levels = [16, 32, 64]  # Close, medium, far

    results = []
    vis_logger = logging.getLogger(__name__)

    try:
        namespace = gym_env.instance.namespaces[0]
        player_pos = namespace.player_location
        vis_logger.info(
            f"👁️ Multi-zoom render: player at ({player_pos.x:.1f}, {player_pos.y:.1f})"
        )

        for zoom in zoom_levels:
            try:
                # Use radius = zoom * 2 to ensure we capture enough data
                # max_render_radius controls what portion gets rendered
                result = namespace._render(
                    radius=zoom * 2,
                    max_render_radius=zoom,
                    position=player_pos,
                    include_status=True,
                )

                base64_data = result.to_base64()
                image_data_url = f"data:image/png;base64,{base64_data}"

                viewport = result.viewport
                vis_logger.info(
                    f"👁️ Zoom {zoom}: viewport size {viewport.width_tiles:.0f}x{viewport.height_tiles:.0f} tiles, "
                    f"image {viewport.image_width}x{viewport.image_height}px"
                )

                # Create viewport info string
                viewport_info = f"""**Zoom Level {zoom} Viewport:**
- Zoom: {zoom} (max_render_radius)
- Center: ({viewport.center_x:.1f}, {viewport.center_y:.1f})
- World bounds: ({viewport.world_min_x:.1f}, {viewport.world_min_y:.1f}) to ({viewport.world_max_x:.1f}, {viewport.world_max_y:.1f})
- Visible area: {viewport.width_tiles:.0f} x {viewport.height_tiles:.0f} tiles
- Image: {viewport.image_width} x {viewport.image_height} pixels
- Scale: {viewport.scaling:.1f} pixels/tile"""

                results.append(
                    ZoomLevelImage(
                        image_data_url=image_data_url,
                        zoom_level=zoom,
                        viewport_info=viewport_info,
                    )
                )

            except Exception as zoom_error:
                vis_logger.warning(
                    f"Failed to render at zoom level {zoom}: {zoom_error}"
                )
                continue

    except Exception as e:
        vis_logger.warning(f"Failed to render multi-zoom images: {e}", exc_info=True)

    return results


def format_saved_variables(namespace) -> str:
    """Format saved variables from namespace's persistent_vars.

    Args:
        namespace: FactorioNamespace instance

    Returns:
        Formatted string showing saved variables
    """
    if not hasattr(namespace, "persistent_vars"):
        return "No saved variables."

    # Filter out builtins, functions, and internal attributes
    skip_types = (type, type(lambda: None), type(print))
    skip_names = {
        # Builtins
        "print",
        "len",
        "range",
        "int",
        "str",
        "float",
        "bool",
        "list",
        "dict",
        "tuple",
        "set",
        "sum",
        "min",
        "max",
        "enumerate",
        "zip",
        "map",
        "filter",
        "any",
        "all",
        "sorted",
        "reversed",
        "round",
        "abs",
        "isinstance",
        "type",
        "assert",
        # Type hints
        "Optional",
        "Union",
        "List",
        "Dict",
        "Tuple",
        "Set",
        # Math
        "sqrt",
        "sin",
        "cos",
        "tan",
        "pi",
        "floor",
        "ceil",
        "pow",
        # Directions
        "UP",
        "ABOVE",
        "TOP",
        "RIGHT",
        "EAST",
        "LEFT",
        "WEST",
        "DOWN",
        "BELOW",
        "BOTTOM",
        # Game types
        "Prototype",
        "Resource",
        "Direction",
        "Position",
        "EntityStatus",
        "BoundingBox",
        "BuildingBox",
        "BeltGroup",
        "Technology",
        "Recipe",
        "PipeGroup",
        "ElectricityGroup",
        "Pipe",
        "RecipeName",
        "prototype_by_name",
        # Entity classes
        "Entity",
        "Inserter",
        "BurnerInserter",
        "TransportBelt",
        "BurnerMiningDrill",
        "ElectricMiningDrill",
        "StoneFurnace",
        "SteelFurnace",
        "AssemblingMachine1",
        "AssemblingMachine2",
        "AssemblingMachine3",
        "Chest",
        "WoodenChest",
        "IronChest",
        "SteelChest",
        "Boiler",
        "SteamEngine",
        "OffshorePump",
        "SmallElectricPole",
        "MediumElectricPole",
        "BigElectricPole",
        "Lab",
        "Radar",
        "Wall",
        "Gun",
        "Splitter",
        "UndergroundBelt",
        "Inventory",
    }

    saved_vars = []
    for name, value in namespace.persistent_vars.items():
        if name.startswith("_"):
            continue
        if name in skip_names:
            continue
        if isinstance(value, skip_types):
            continue
        if callable(value):
            continue
        if isinstance(value, type):
            continue

        try:
            value_repr = repr(value)
            if len(value_repr) > 500:
                value_repr = value_repr[:500] + "..."
            saved_vars.append(f"  {name} = {value_repr}")
        except Exception:
            saved_vars.append(f"  {name} = <unable to repr>")

    if not saved_vars:
        return "No saved variables."

    return "**Saved Variables (from previous steps):**\n" + "\n".join(saved_vars)


def build_diary_content(reasoning_blocks: List[str], max_tokens: int = 8000) -> str:
    """Build the concatenated diary from reasoning blocks.

    Args:
        reasoning_blocks: List of reasoning text blocks from previous steps
        max_tokens: Approximate max characters (rough token estimate)

    Returns:
        Concatenated diary string, potentially truncated from the beginning
    """
    if not reasoning_blocks:
        return ""

    diary_parts = []
    for i, block in enumerate(reasoning_blocks, 1):
        if block.strip():
            diary_parts.append(f"[Step {i}]\n{block.strip()}")

    full_diary = "\n\n".join(diary_parts)

    if len(full_diary) > max_tokens:
        truncated = full_diary[-max_tokens:]
        step_marker_idx = truncated.find("[Step ")
        if step_marker_idx > 0:
            truncated = truncated[step_marker_idx:]
        full_diary = "...(earlier reasoning truncated)...\n\n" + truncated

    return full_diary


def create_feedback_message(
    step: int,
    program_output: str,
    reward: float,
    production_score: float,
    current_score: float,
    flow: dict,
    image_data_url: Optional[str] = None,
    viewport_info: Optional[str] = None,
    include_image: bool = True,
    current_ticks: int = 0,
    ticks_cost: int = 0,
) -> ChatMessageUser:
    """Create a feedback message after step execution.

    Args:
        step: Current step number (0-indexed)
        program_output: Output from program execution
        reward: Reward for this step
        production_score: New production score
        current_score: Previous production score
        flow: Production flows dict
        image_data_url: Optional base64 image data URL
        viewport_info: Optional viewport info string
        include_image: Whether to include image in message
        current_ticks: Current game ticks (60 ticks per second)
        ticks_cost: Ticks consumed this step

    Returns:
        ChatMessageUser with feedback content
    """
    # Format elapsed time from ticks (60 ticks per second)
    total_seconds = current_ticks // 60
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

    feedback_content = f"""

**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Execution Info:**
- Reward this step: {reward}

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

    if viewport_info:
        feedback_content += f"\n\n{viewport_info}"

    if include_image and image_data_url:
        return ChatMessageUser(
            content=[
                ContentImage(image=image_data_url),
                ContentText(text=feedback_content),
            ]
        )
    else:
        return ChatMessageUser(content=feedback_content)


def strip_images_from_messages(messages: list) -> list:
    """Remove images from message history, keeping only text.

    Args:
        messages: List of chat messages

    Returns:
        Messages with images stripped (text only)
    """
    stripped = []
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg.content, list):
            # Extract only text content
            text_parts = []
            for part in msg.content:
                if hasattr(part, "text"):
                    text_parts.append(part.text)
                elif isinstance(part, str):
                    text_parts.append(part)

            if text_parts:
                # Create new message with text only
                new_msg = type(msg)(content="\n".join(text_parts))
                stripped.append(new_msg)
            else:
                stripped.append(msg)
        else:
            stripped.append(msg)

    return stripped


def trim_messages(
    messages: list,
    max_messages: int = 25,
    trim_to: int = 16,
    strip_images: bool = False,
) -> list:
    """Trim message history while preserving system message.

    Args:
        messages: List of chat messages
        max_messages: Max messages before trimming
        trim_to: Number of recent messages to keep
        strip_images: Whether to also strip images from history

    Returns:
        Trimmed message list
    """
    if len(messages) <= max_messages:
        if strip_images:
            return strip_images_from_messages(messages)
        return messages

    # Preserve system message
    if len(messages) > 0 and messages[0].role == "system":
        system_message = messages[0]
        recent_messages = messages[-trim_to:]
        result = [system_message] + recent_messages
    else:
        result = messages[-trim_to:]

    if strip_images:
        result = strip_images_from_messages(result)

    logger.info(f"🧹 Trimmed conversation to {len(result)} messages")
    return result


def summarize_code_block(code: str, max_length: int = 200) -> str:
    """Summarize a code block to reduce context size.

    Args:
        code: Full code string
        max_length: Max length for summary

    Returns:
        Summarized code or original if short enough
    """
    if len(code) <= max_length:
        return code

    # Extract key information
    lines = code.split("\n")
    summary_parts = []

    # Get function/class definitions
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            summary_parts.append(stripped.split("(")[0] + "(...)")
        elif stripped.startswith("#") and "TODO" in stripped.upper():
            summary_parts.append(stripped)

    if summary_parts:
        return f"[Code summary: {len(lines)} lines]\n" + "\n".join(summary_parts[:5])
    else:
        return f"[Code: {len(lines)} lines, {len(code)} chars]"


def build_hud_user_message(
    step: int,
    trajectory_length: int,
    current_score: float,
    obs_formatted: str,
    saved_vars_str: str,
    last_program_code: Optional[str] = None,
    last_program_output: Optional[str] = None,
    flow_str: Optional[str] = None,
) -> str:
    """Build the HUD-style user message for fixed context mode.

    Args:
        step: Current step number (0-indexed)
        trajectory_length: Total trajectory length
        current_score: Current production score
        obs_formatted: Formatted observation string
        saved_vars_str: Formatted saved variables string
        last_program_code: Code from the previous step
        last_program_output: Output from the previous step
        flow_str: Optional flow information from last step

    Returns:
        Formatted HUD string
    """
    lines = []

    # Header
    lines.append(f"## Step {step + 1}/{trajectory_length} - Factory HUD")
    lines.append("")
    lines.append(f"**Production Score:** {current_score:.1f} (maximize this!)")
    lines.append(
        f"**Progress:** {(step / trajectory_length) * 100:.1f}% of trajectory complete"
    )
    lines.append("")

    # Last step results (if not first step)
    if last_program_code is not None:
        lines.append("---")
        lines.append("### Previous Step Results")
        lines.append("")
        lines.append("**Last Program Code:**")
        lines.append("```python")
        code_display = last_program_code
        if len(code_display) > 2000:
            code_display = code_display[:2000] + "\n# ... (truncated)"
        lines.append(code_display)
        lines.append("```")
        lines.append("")
        lines.append("**Program Output (STDOUT/STDERR):**")
        lines.append("```")
        output_display = last_program_output or "No output"
        if len(output_display) > 1500:
            output_display = output_display[:1500] + "\n... (truncated)"
        lines.append(output_display)
        lines.append("```")

        if flow_str:
            lines.append("")
            lines.append("**Production Flows (from last step):**")
            lines.append(flow_str)

        lines.append("")

    # Current game state
    lines.append("---")
    lines.append("### Current Game State")
    lines.append("")
    lines.append(obs_formatted)
    lines.append("")

    # Saved variables
    lines.append("---")
    lines.append("### Variable Namespace")
    lines.append("")
    lines.append(saved_vars_str)
    lines.append("")

    # Action prompt
    lines.append("---")
    lines.append("### Next Action Required")
    lines.append(
        "Analyze the current state and write a Python program using the FLE API "
        "to expand and improve your factory. Focus on actions that will increase "
        "your production score."
    )

    return "\n".join(lines)


def log_latency_summary(
    total_step_latencies: List[float],
    inference_latencies: List[float],
    env_execution_latencies: List[float],
    policy_execution_latencies: List[float],
    sleep_durations: List[float],
) -> None:
    """Log a summary of latency metrics."""
    if not total_step_latencies:
        return

    avg_total = sum(total_step_latencies) / len(total_step_latencies)
    avg_inference = (
        sum(inference_latencies) / len(inference_latencies)
        if inference_latencies
        else 0
    )
    avg_env = (
        sum(env_execution_latencies) / len(env_execution_latencies)
        if env_execution_latencies
        else 0
    )
    avg_policy = (
        sum(policy_execution_latencies) / len(policy_execution_latencies)
        if policy_execution_latencies
        else 0
    )
    total_sleep = sum(sleep_durations)

    logger.info(
        f"⏱️ Latency summary: avg_total={avg_total:.2f}s, avg_inference={avg_inference:.2f}s, "
        f"avg_env={avg_env:.2f}s, avg_policy={avg_policy:.2f}s, total_sleep={total_sleep:.2f}s"
    )


def get_base_system_prompt(goal_description: str, trajectory_length: int) -> str:
    """Generate the task-specific portion of the system prompt.

    Args:
        goal_description: Description of the task goal
        trajectory_length: Number of steps in trajectory

    Returns:
        Task instructions string
    """
    return f"""
## TASK OBJECTIVE
{goal_description}

## SUCCESS CRITERIA
- There is NO specific quota or target - your goal is to maximize total production
- Build the largest, most productive factory possible
- The "Production Score" measures the total economic value of everything produced
- Higher production score = better performance

## STRATEGY GUIDANCE
- Start with basic resource extraction (iron, copper, coal)
- Establish power generation early
- Scale up production chains progressively
- Automate everything - manual work doesn't scale
- Consider efficiency: more complex items have higher value
- Balance between expanding production and optimizing existing systems

## IMPORTANT NOTES
- You have {trajectory_length} steps - use them wisely
- Each step should make meaningful progress
- Think long-term: early investments in infrastructure pay off later
- The production score is cumulative - it grows as your factory produces items
"""
