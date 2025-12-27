"""Optimized solver variants for Factorio trajectory execution.

These solvers implement different context management strategies to improve
speed while maintaining performance. Each variant trades off context richness
for faster inference.

Variants:
1. factorio_no_image_history_solver: Strips images from history, only shows latest
2. factorio_aggressive_trim_solver: Keeps fewer messages (8 instead of 16)
3. factorio_text_only_solver: No images at all, text observations only
4. factorio_minimal_context_solver: Minimal observations, aggressive trimming
5. factorio_hud_solver: Fixed 3-message context (system/assistant/user HUD)
6. factorio_reasoning_only_solver: Keeps only reasoning blocks, strips code from history
"""

import logging
import os
import time
import traceback
from typing import List, Optional

from inspect_ai._util.content import ContentReasoning
from inspect_ai.scorer import score
from inspect_ai.log import transcript
from inspect_ai.solver import solver
from inspect_ai.agent import AgentState
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    ChatMessageAssistant,
    ModelOutput,
    get_model,
    ContentImage,
    ContentText,
    CachePolicy,
)
from inspect_ai.util import store_as

from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import TreeObservationFormatter
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)

from fle.eval.inspect_integration.simple_server_pool import (
    get_simple_server_pool,
)
from fle.eval.inspect_integration.solver_utils import (
    TrajectoryData,
    render_vision_image,
    render_multi_zoom_images,
    format_saved_variables,
    build_diary_content,
    trim_messages,
    build_hud_user_message,
    log_latency_summary,
    get_base_system_prompt,
)
from fle.agents.llm.parsing import parse_response
from fle.env.tools.agent.sleep.client import Sleep

import importlib.resources
import gym


logger = logging.getLogger(__name__)


def extract_reasoning_from_response(output) -> Optional[str]:
    """Extract reasoning/thinking content from a model response.

    Inspect AI normalizes reasoning into ContentReasoning blocks.
    This function extracts those blocks to build the reasoning diary.

    Args:
        output: ModelOutput from Inspect AI

    Returns:
        Extracted reasoning text, or None if no reasoning found
    """
    if not hasattr(output, "message") or not hasattr(output.message, "content"):
        return None

    content = output.message.content

    # Handle list of content blocks (ContentReasoning, ContentText, etc.)
    if isinstance(content, list):
        reasoning_parts = []
        for block in content:
            # Check for ContentReasoning blocks (Inspect AI's normalized format)
            if hasattr(block, "type") and block.type == "reasoning":
                if hasattr(block, "content"):
                    reasoning_parts.append(block.content)
                elif hasattr(block, "text"):
                    reasoning_parts.append(block.text)
            # Also check class name for ContentReasoning
            elif type(block).__name__ == "ContentReasoning":
                if hasattr(block, "content"):
                    reasoning_parts.append(block.content)
                elif hasattr(block, "text"):
                    reasoning_parts.append(block.text)

        if reasoning_parts:
            return "\n\n".join(reasoning_parts)

    # Handle string content - look for <thinking> tags
    if isinstance(content, str):
        import re

        thinking_pattern = r"<thinking>(.*?)</thinking>"
        matches = re.findall(thinking_pattern, content, re.DOTALL)
        if matches:
            return "\n\n".join(match.strip() for match in matches)

    return None


async def _base_solver_loop(
    state: AgentState,
    config: dict,
) -> AgentState:
    """Base solver loop with configurable context management.

    Args:
        state: Agent state
        config: Configuration dict with keys:
            - strip_images_from_history: bool
            - max_messages: int
            - trim_to: int
            - include_entities: bool
            - text_only: bool (no images at all)
            - use_hud_mode: bool (fixed 3-message context)

    Returns:
        Updated agent state
    """
    run_idx = None
    gym_env = None

    # Extract config
    strip_images_from_history = config.get("strip_images_from_history", False)
    max_messages = config.get("max_messages", 25)
    trim_to = config.get("trim_to", 16)
    include_entities = config.get("include_entities", True)
    text_only = config.get("text_only", False)
    use_hud_mode = config.get("use_hud_mode", False)
    solver_name = config.get("solver_name", "optimized")

    try:
        # Get configuration from metadata
        metadata = getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
        env_id = metadata.get("env_id", "open_play_production")
        gym_env_id = "open_play"
        model_name = metadata.get("model", "openai/gpt-4o-mini")
        trajectory_length = metadata.get("trajectory_length", 5000)
        goal_description = metadata.get(
            "goal_description",
            "Achieve the highest automatic production score rate",
        )

        vision_enabled = (
            os.environ.get("FLE_VISION", "").lower() == "true" and not text_only
        )
        if vision_enabled:
            logger.info("👁️  Vision mode enabled - rendering images after each step")

        logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
        logger.info(f"🎯 Target: {trajectory_length} steps using model {model_name}")

        # Get server allocation
        pool = await get_simple_server_pool()
        allocation = await pool.get_server_allocation()
        run_idx = allocation.run_idx
        if allocation.api_key:
            logger.warning(
                f"📡 Allocated server factorio_{run_idx} with API key index {allocation.api_key_index}"
            )
        else:
            logger.warning(f"📡 Allocated server factorio_{run_idx}")

        # Create gym environment
        gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
        gym_env.reset()

        logger.info("Connected to Factorio server")

        # Generate system prompt
        generator = SystemPromptGenerator(str(importlib.resources.files("fle") / "env"))
        base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
        task_instructions = get_base_system_prompt(goal_description, trajectory_length)

        full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin building your factory step by step."""

        # Initialize conversation
        original_user_message = (
            state.messages[0].content
            if state.messages
            else f"Begin task: {goal_description}"
        )

        state.messages = [
            ChatMessageSystem(content=full_system_prompt),
            ChatMessageUser(
                content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
            ),
        ]

        logger.info(f"📋 Initialized system prompt: {len(full_system_prompt)} chars")
        logger.info(f"🎯 Task: {goal_description}")
        logger.info(f"📈 Starting {trajectory_length}-step {solver_name} execution...")

        # Trajectory tracking
        production_scores = []
        step_results = []
        game_ticks = []
        game_states = []

        # Achievement tracking - unique item types produced
        produced_item_types_set: set = set()
        # Research tracking - technologies researched during trajectory
        researched_technologies_set: set = set()

        # For HUD mode
        reasoning_diary: List[str] = []
        last_program_code: Optional[str] = None
        last_program_output: Optional[str] = None
        last_flow_str: Optional[str] = None

        # Latency tracking
        inference_latencies = []
        env_execution_latencies = []
        policy_execution_latencies = []
        sleep_durations = []
        total_step_latencies = []

        for step in range(trajectory_length):
            step_start = time.time()
            Sleep.reset_step_sleep_duration()

            try:
                try:
                    gym_env.clear_enemies()
                except Exception as ee:
                    logger.warning(f"Environment error: Clearing enemies: {ee}")
                    raise Exception(f"Clearing enemies: {ee}") from ee

                # Get current observation
                observation: Observation = gym_env.get_observation()
                obs_formatted = TreeObservationFormatter(
                    include_research=False,
                    include_flows=False,
                    include_entities=include_entities,
                ).format(observation)

                current_score = production_scores[-1] if production_scores else 0

                if use_hud_mode:
                    # HUD mode: rebuild context each step
                    namespace = gym_env.instance.namespaces[0]
                    saved_vars_str = format_saved_variables(namespace)

                    hud_content = build_hud_user_message(
                        step=step,
                        trajectory_length=trajectory_length,
                        current_score=current_score,
                        obs_formatted=obs_formatted.raw_str.replace("\\n", "\n"),
                        saved_vars_str=saved_vars_str,
                        last_program_code=last_program_code,
                        last_program_output=last_program_output,
                        flow_str=last_flow_str,
                    )

                    diary_content = build_diary_content(
                        reasoning_diary, max_tokens=8000
                    )

                    # Fixed 3-message format
                    messages = [
                        ChatMessageSystem(content=full_system_prompt),
                    ]
                    if diary_content:
                        messages.append(
                            ChatMessageAssistant(
                                content=f"## Previous Reasoning\n\n{diary_content}"
                            )
                        )

                    # HUD mode can include a visual render if not text_only
                    if not text_only:
                        hud_image_url = None
                        if vision_enabled:
                            hud_image_url, viewport_info = render_vision_image(gym_env)
                            if viewport_info:
                                hud_content += f"\n\n{viewport_info}"
                        else:
                            # Get map image from observation
                            obs_dict = observation.to_dict()
                            if obs_dict.get("map_image"):
                                hud_image_url = obs_dict["map_image"]

                        if hud_image_url:
                            messages.append(
                                ChatMessageUser(
                                    content=[
                                        ContentImage(image=hud_image_url),
                                        ContentText(text=hud_content),
                                    ]
                                )
                            )
                        else:
                            messages.append(ChatMessageUser(content=hud_content))
                    else:
                        messages.append(ChatMessageUser(content=hud_content))

                else:
                    # Standard mode: append to message history
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}"""

                    step_message = ChatMessageUser(content=step_content)
                    state.messages.append(step_message)
                    messages = state.messages

                # Generate response
                generation_config = {
                    "reasoning_tokens": 1024 * 4,
                    "cache": CachePolicy(per_epoch=False),
                }
                _model = get_model()
                if "openrouter" in _model.name:
                    generation_config["transforms"] = ["middle-out"]

                inference_start = time.time()
                output = await _model.generate(
                    input=messages,
                    config=generation_config,
                )
                inference_time = int(time.time() - inference_start)
                inference_latencies.append(inference_time)

                if hasattr(output, "usage") and hasattr(
                    output.usage, "reasoning_tokens"
                ):
                    logger.info(
                        f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                    )

                if use_hud_mode:
                    # Extract reasoning blocks for diary (not the code output)
                    reasoning_text = extract_reasoning_from_response(output)
                    if reasoning_text:
                        reasoning_diary.append(reasoning_text)
                else:
                    state.messages.append(output.message)
                    state.output = output

                # Extract program
                program = parse_response(output)

                if not program:
                    raise Exception(
                        "Could not parse program from model response. "
                        "Be sure to wrap your code in ``` blocks."
                    )

                logger.info(
                    f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                )

                # Execute action
                action = Action(agent_idx=0, code=program.code)
                try:
                    env_start = time.time()
                    obs, reward, terminated, truncated, info = gym_env.step(action)
                    env_time = time.time() - env_start
                    env_execution_latencies.append(env_time)

                    game_states.append(info["output_game_state"])

                    policy_time = info.get("policy_execution_time", 0.0)
                    if policy_time:
                        policy_execution_latencies.append(float(policy_time))

                    step_sleep_duration = Sleep.get_step_sleep_duration()
                    sleep_durations.append(step_sleep_duration)
                except Exception as ee:
                    logger.warning(f"Environment error: {ee}")
                    if use_hud_mode:
                        last_program_code = program.code
                        last_program_output = f"ERROR: {ee}"
                        last_flow_str = None
                    else:
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )

                    if not game_states:
                        raise Exception(f"Environment error: {ee}") from ee

                    gym_env.reset({"game_state": game_states.pop()})
                    continue

                logger.info(
                    f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}, "
                    f"inference={inference_time}s, env={env_time:.1f}s"
                )

                # Get program output
                program_output = (
                    info.get("result", "No output captured")
                    if info
                    else "No info available"
                )

                flow = obs["flows"]
                production_score = info.get("production_score", 0)
                production_scores.append(production_score)

                # Extract unique item types from flows
                # flow is obs["flows"] dict with harvested/output as lists of dicts
                # Format: [{"type": "coal", "amount": 50.0}, ...]
                if "harvested" in flow:
                    for item in flow["harvested"]:
                        if isinstance(item, dict) and "type" in item:
                            produced_item_types_set.add(item["type"])
                if "output" in flow:
                    for item in flow["output"]:
                        if isinstance(item, dict) and "type" in item:
                            produced_item_types_set.add(item["type"])
                if "crafted" in flow:
                    for craft in flow["crafted"]:
                        if isinstance(craft, dict) and "outputs" in craft:
                            produced_item_types_set.update(
                                list(craft["outputs"].keys())
                            )

                # Extract researched technologies from observation
                try:
                    for (
                        tech_name,
                        tech_state,
                    ) in observation.research.technologies.items():
                        if tech_state.researched:
                            researched_technologies_set.add(tech_name)
                except Exception as research_err:
                    logger.debug(f"Could not extract research state: {research_err}")

                # Record game ticks and calculate cost
                try:
                    current_ticks = gym_env.instance.get_elapsed_ticks()
                    previous_ticks = game_ticks[-1] if game_ticks else 0
                    ticks_cost = current_ticks - previous_ticks
                    game_ticks.append(current_ticks)
                except Exception:
                    current_ticks = 0
                    ticks_cost = 0
                    game_ticks.append(0)

                # Format elapsed time from ticks (60 ticks per second)
                total_seconds = current_ticks // 60
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                if not program_output:
                    program_output = "None" if program.code else "No code submitted."

                if use_hud_mode:
                    # Store for next HUD
                    last_program_code = program.code
                    last_program_output = program_output
                    last_flow_str = TreeObservationFormatter.format_flows_compact(flow)
                else:
                    # Create feedback message
                    feedback_content = f"""

**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

                    # Handle image
                    image_data_url = None
                    viewport_info = None

                    if not text_only:
                        if vision_enabled:
                            image_data_url, viewport_info = render_vision_image(gym_env)
                            if viewport_info:
                                feedback_content += f"\n\n{viewport_info}"
                        else:
                            image_data_url = obs.get("map_image")

                    # Trim messages
                    state.messages = trim_messages(
                        state.messages,
                        max_messages=max_messages,
                        trim_to=trim_to,
                        strip_images=strip_images_from_history,
                    )

                    # Create feedback message
                    if image_data_url and not text_only:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)

                    state.messages.append(feedback_message)

                step_time = time.time() - step_start
                total_step_latencies.append(step_time)

                step_result = {
                    "step": step + 1,
                    "production_score": production_score,
                    "program_length": len(program.code),
                    "execution_time": step_time,
                    "program_content": program.code[:200] + "..."
                    if len(program.code) > 200
                    else program.code,
                    "program_output": program_output[:200] + "..."
                    if len(str(program_output)) > 200
                    else str(program_output),
                    "inference_latency": inference_time,
                    "env_execution_latency": env_time if "env_time" in locals() else 0,
                    "policy_execution_latency": policy_time
                    if "policy_time" in locals()
                    else 0,
                    "sleep_duration": step_sleep_duration
                    if "step_sleep_duration" in locals()
                    else 0,
                }
                step_results.append(step_result)

                logger.info(
                    f"✅ Step {step + 1}/{trajectory_length}: "
                    f"Score={production_score:.1f}, Time={step_time:.1f}s"
                )

                # Store progress
                trajectory_data = store_as(TrajectoryData)
                trajectory_data.production_score = production_score
                trajectory_data.current_score = production_score
                trajectory_data.total_steps = step + 1
                trajectory_data.steps = step_results
                trajectory_data.scores = production_scores
                trajectory_data.ticks = game_ticks
                trajectory_data.produced_item_types = list(produced_item_types_set)
                trajectory_data.researched_technologies = list(
                    researched_technologies_set
                )
                trajectory_data.inference_latencies = inference_latencies
                trajectory_data.env_execution_latencies = env_execution_latencies
                trajectory_data.policy_execution_latencies = policy_execution_latencies
                trajectory_data.sleep_durations = sleep_durations
                trajectory_data.total_step_latencies = total_step_latencies

                await score(state)

                if terminated or truncated:
                    logger.info(
                        f"⚠️ Episode ended at step {step + 1}: "
                        f"terminated={terminated}, truncated={truncated}"
                    )
                    state.complete = True
                    break

            except Exception as step_error:
                logger.error(f"❌ Step {step + 1} error: {step_error}")
                if use_hud_mode:
                    if "program" in locals() and program:
                        last_program_code = program.code
                        last_program_output = f"ERROR: {step_error}"
                        last_flow_str = None
                else:
                    state.messages.append(
                        ChatMessageUser(
                            content=f"❌ Step {step + 1} error: {step_error}"
                        )
                    )

        # Final results
        final_score = production_scores[-1] if production_scores else 0.0

        trajectory_data = store_as(TrajectoryData)
        trajectory_data.production_score = final_score
        trajectory_data.final_score = final_score
        trajectory_data.total_steps = len(step_results)
        trajectory_data.steps = step_results
        trajectory_data.scores = production_scores
        trajectory_data.ticks = game_ticks
        trajectory_data.produced_item_types = list(produced_item_types_set)
        trajectory_data.researched_technologies = list(researched_technologies_set)
        trajectory_data.inference_latencies = inference_latencies
        trajectory_data.env_execution_latencies = env_execution_latencies
        trajectory_data.policy_execution_latencies = policy_execution_latencies
        trajectory_data.sleep_durations = sleep_durations
        trajectory_data.total_step_latencies = total_step_latencies

        log_latency_summary(
            total_step_latencies,
            inference_latencies,
            env_execution_latencies,
            policy_execution_latencies,
            sleep_durations,
        )

        state.output = ModelOutput(
            completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
            f"with final production score: {final_score:.1f}",
            model=model_name,
        )

        logger.info(
            f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
            f"score after {len(step_results)} steps"
        )
        transcript().info(
            f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
            f"score after {len(step_results)} steps"
        )

    except Exception as e:
        error_msg = f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)

        trajectory_data = store_as(TrajectoryData)
        trajectory_data.error = error_msg
        trajectory_data.production_score = 0.0
        trajectory_data.final_score = 0.0

        state.output = ModelOutput(
            completion=f"Error in {solver_name} trajectory: {error_msg}",
            model=metadata.get("model", "unknown")
            if "metadata" in locals()
            else "unknown",
        )

    finally:
        if run_idx is not None:
            try:
                pool = await get_simple_server_pool()
                await pool.release_run_idx(run_idx)
                logger.info(f"🧹 Released server factorio_{run_idx}")
            except Exception as e:
                logger.error(f"Error releasing server: {e}")

    return state


# =============================================================================
# SOLVER VARIANTS
# =============================================================================


@solver
def factorio_no_image_history_solver():
    """Solver that strips images from message history.

    Only the LATEST image is shown - older images are converted to text-only.
    This significantly reduces context size while still providing visual feedback.

    Optimization: ~50-70% context reduction for image-heavy trajectories
    Trade-off: Model can't reference older images for comparison
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "no-image-history",
                "strip_images_from_history": True,
                "max_messages": 25,
                "trim_to": 16,
                "include_entities": True,
                "text_only": False,
            },
        )

    return solve


@solver
def factorio_aggressive_trim_solver():
    """Solver with aggressive message trimming.

    Keeps only 8 recent messages instead of 16, triggers trimming at 12.
    Images are kept but history is much shorter.

    Optimization: ~50% reduction in message history
    Trade-off: Less context about earlier steps
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "aggressive-trim",
                "strip_images_from_history": False,
                "max_messages": 12,
                "trim_to": 8,
                "include_entities": True,
                "text_only": False,
            },
        )

    return solve


@solver
def factorio_text_only_solver():
    """Solver with no images at all - pure text observations.

    Completely disables image generation and rendering.
    Fastest possible inference due to minimal context.

    Optimization: Maximum speed, minimal token usage
    Trade-off: No visual feedback, harder spatial reasoning
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "text-only",
                "strip_images_from_history": True,
                "max_messages": 25,
                "trim_to": 16,
                "include_entities": True,
                "text_only": True,
            },
        )

    return solve


@solver
def factorio_minimal_context_solver():
    """Solver with minimal context - no entities, aggressive trim, no images.

    Strips entities from observations, uses aggressive trimming, and no images.
    Most aggressive optimization for maximum speed.

    Optimization: Maximum context reduction
    Trade-off: Limited situational awareness
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "minimal-context",
                "strip_images_from_history": True,
                "max_messages": 12,
                "trim_to": 6,
                "include_entities": False,
                "text_only": True,
            },
        )

    return solve


@solver
def factorio_hud_solver():
    """Solver with fixed HUD-style context (no growing history) + visual rendering.

    Uses a fixed 3-message format each step:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with current state, saved vars, last code/output + rendered image

    Optimization: Bounded context regardless of trajectory length
    Trade-off: Model must rely on diary and saved vars for continuity
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "hud",
                "use_hud_mode": True,
                "strip_images_from_history": True,
                "max_messages": 3,
                "trim_to": 3,
                "include_entities": True,
                "text_only": False,  # Include visual rendering
            },
        )

    return solve


@solver
def factorio_hud_text_only_solver():
    """Solver with fixed HUD-style context, text only (no images).

    Uses a fixed 3-message format each step:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with current state, saved vars, last code/output (no image)

    Optimization: Maximum context reduction with bounded history
    Trade-off: No visual feedback, relies entirely on text observations
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "hud-text-only",
                "use_hud_mode": True,
                "strip_images_from_history": True,
                "max_messages": 3,
                "trim_to": 3,
                "include_entities": True,
                "text_only": True,
            },
        )

    return solve


@solver
def factorio_fat_hud_solver():
    """Solver with fixed HUD-style context and 3 images at different zoom levels.

    Uses a fixed message format each step with multiple visual perspectives:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with 3 images at zoom levels 16, 32, 64 (close, medium, far)
            plus current state, saved vars, last code/output

    The three zoom levels provide:
    - Zoom 16: Close-up view (32x32 tiles) - detailed view of nearby entities
    - Zoom 32: Medium view (64x64 tiles) - factory overview
    - Zoom 64: Far view (128x128 tiles) - large-scale factory layout

    All images have the same pixel dimensions but show different amounts of the world.

    Optimization: Rich multi-scale visual feedback with bounded context
    Trade-off: Higher token usage per step due to 3 images, but enables better
               spatial reasoning across different scales
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )

            solver_name = "fat-hud"

            logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            if allocation.api_key:
                logger.warning(
                    f"📡 Allocated server factorio_{run_idx} with API key index {allocation.api_key_index}"
                )
            else:
                logger.warning(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
            task_instructions = get_base_system_prompt(
                goal_description, trajectory_length
            )

            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

## VISUAL FEEDBACK
You will receive 3 images at different zoom levels each step:
- **Zoom 16 (Close)**: Detailed view of immediate surroundings (32x32 tiles)
- **Zoom 32 (Medium)**: Factory overview (64x64 tiles)
- **Zoom 64 (Far)**: Large-scale layout view (128x128 tiles)

Use these multi-scale views to:
- Plan detailed placement with the close-up view
- Check factory organization with the medium view
- Understand overall layout and expansion direction with the far view

Now begin building your factory step by step."""

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
                ChatMessageUser(
                    content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
                ),
            ]

            logger.info(
                f"📋 Initialized system prompt: {len(full_system_prompt)} chars"
            )
            logger.info(f"🎯 Task: {goal_description}")
            logger.info(
                f"📈 Starting {trajectory_length}-step {solver_name} execution..."
            )

            # Trajectory tracking
            production_scores = []
            step_results = []
            game_ticks = []
            game_states = []

            # For HUD mode
            reasoning_diary: List[str] = []
            last_program_code: Optional[str] = None
            last_program_output: Optional[str] = None
            last_flow_str: Optional[str] = None

            # Latency tracking
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            for step in range(trajectory_length):
                step_start = time.time()
                Sleep.reset_step_sleep_duration()

                try:
                    try:
                        gym_env.clear_enemies()
                    except Exception as ee:
                        logger.warning(f"Environment error: Clearing enemies: {ee}")
                        raise Exception(f"Clearing enemies: {ee}") from ee

                    # Get current observation
                    observation: Observation = gym_env.get_observation()
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                        include_entities=True,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0

                    # Build HUD content
                    namespace = gym_env.instance.namespaces[0]
                    saved_vars_str = format_saved_variables(namespace)

                    hud_content = build_hud_user_message(
                        step=step,
                        trajectory_length=trajectory_length,
                        current_score=current_score,
                        obs_formatted=obs_formatted.raw_str.replace("\\n", "\n"),
                        saved_vars_str=saved_vars_str,
                        last_program_code=last_program_code,
                        last_program_output=last_program_output,
                        flow_str=last_flow_str,
                    )

                    diary_content = build_diary_content(
                        reasoning_diary, max_tokens=8000
                    )

                    # Build messages with multi-zoom images
                    messages = [
                        ChatMessageSystem(content=full_system_prompt),
                    ]
                    if diary_content:
                        messages.append(
                            ChatMessageAssistant(
                                content=f"## Previous Reasoning\n\n{diary_content}"
                            )
                        )

                    # Render multi-zoom images
                    zoom_images = render_multi_zoom_images(
                        gym_env, zoom_levels=[16, 32, 64]
                    )

                    # Build user message content with images and viewport info
                    user_content = []

                    # Add images with labels
                    if zoom_images:
                        viewport_info_text = (
                            "\n\n---\n### Multi-Scale Viewport Information\n"
                        )
                        for zoom_img in zoom_images:
                            user_content.append(
                                ContentImage(image=zoom_img.image_data_url)
                            )
                            viewport_info_text += f"\n{zoom_img.viewport_info}\n"

                        # Add all viewport info after images
                        hud_content += viewport_info_text

                    user_content.append(ContentText(text=hud_content))

                    if user_content:
                        messages.append(ChatMessageUser(content=user_content))
                    else:
                        messages.append(ChatMessageUser(content=hud_content))

                    # Generate response
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    if "openrouter" in _model.name:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    output = await _model.generate(
                        input=messages,
                        config=generation_config,
                    )
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    if hasattr(output, "usage") and hasattr(
                        output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Extract reasoning blocks for diary
                    reasoning_text = extract_reasoning_from_response(output)
                    if reasoning_text:
                        reasoning_diary.append(reasoning_text)

                    # Extract program
                    program = parse_response(output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            policy_execution_latencies.append(float(policy_time))

                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        last_program_code = program.code
                        last_program_output = f"ERROR: {ee}"
                        last_flow_str = None

                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee

                        gym_env.reset({"game_state": game_states.pop()})
                        continue

                    logger.info(
                        f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}, "
                        f"inference={inference_time}s, env={env_time:.1f}s"
                    )

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )

                    flow = obs["flows"]
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Record game ticks
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        game_ticks.append(current_ticks)
                    except Exception:
                        game_ticks.append(0)

                    if not program_output:
                        program_output = (
                            "None" if program.code else "No code submitted."
                        )

                    # Store for next HUD
                    last_program_code = program.code
                    last_program_output = program_output
                    last_flow_str = TreeObservationFormatter.format_flows_compact(flow)

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "program_content": program.code[:200] + "..."
                        if len(program.code) > 200
                        else program.code,
                        "program_output": program_output[:200] + "..."
                        if len(str(program_output)) > 200
                        else str(program_output),
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time
                        if "env_time" in locals()
                        else 0,
                        "policy_execution_latency": policy_time
                        if "policy_time" in locals()
                        else 0,
                        "sleep_duration": step_sleep_duration
                        if "step_sleep_duration" in locals()
                        else 0,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: "
                        f"Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    await score(state)

                    if terminated or truncated:
                        logger.info(
                            f"⚠️ Episode ended at step {step + 1}: "
                            f"terminated={terminated}, truncated={truncated}"
                        )
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    if "program" in locals() and program:
                        last_program_code = program.code
                        last_program_output = f"ERROR: {step_error}"
                        last_flow_str = None

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            log_latency_summary(
                total_step_latencies,
                inference_latencies,
                env_execution_latencies,
                policy_execution_latencies,
                sleep_durations,
            )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
                f"with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = (
                f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in {solver_name} trajectory: {error_msg}",
                model=metadata.get("model", "unknown")
                if "metadata" in locals()
                else "unknown",
            )

        finally:
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve


@solver
def factorio_balanced_solver():
    """Balanced solver - moderate optimizations for good speed/performance.

    Strips images from history but keeps recent ones.
    Moderate trimming (12 messages).
    Keeps entities for situational awareness.

    Optimization: Good balance of speed and context
    Trade-off: Moderate compromise on both
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "balanced",
                "strip_images_from_history": True,
                "max_messages": 16,
                "trim_to": 12,
                "include_entities": True,
                "text_only": False,
            },
        )

    return solve


def extract_reasoning_from_message(message: ChatMessageAssistant) -> Optional[str]:
    """Extract reasoning text from a message, stripping code blocks.

    The reasoning conveys the agent's intent and understanding,
    which is sufficient context for what the code should do.
    """
    content = message.content
    if isinstance(content, list):
        # Handle content blocks
        text_parts = []
        for block in content:
            if isinstance(block, ContentReasoning):
                if hasattr(block, "reasoning"):
                    text_parts.append(block.reasoning)
                else:
                    text_parts.append(block.summary)
            elif hasattr(block, "text"):
                text_parts.append(block.text)
            elif isinstance(block, str):
                text_parts.append(block)
        content = "\n".join(text_parts)

    if not isinstance(content, str):
        return None

    # Remove code blocks (```...```) to keep only reasoning
    import re

    # Remove fenced code blocks
    content = re.sub(r"```[\s\S]*?```", "[code executed]", content)
    # Remove inline code
    content = re.sub(r"`[^`]+`", "", content)

    # Clean up excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = content.strip()

    return content if content else None


def convert_messages_to_reasoning_only(messages: list) -> list:
    """Convert message history to reasoning-only format.

    Keeps system message intact, strips code from assistant messages,
    keeps user messages but removes code blocks if present.
    """
    converted = []
    for msg in messages:
        if msg.role == "system":
            converted.append(msg)
        elif msg.role == "assistant":
            reasoning = extract_reasoning_from_message(msg)
            if reasoning:
                converted.append(ChatMessageAssistant(content=reasoning))
        elif msg.role == "user":
            # Keep user messages but strip any code blocks
            reasoning = extract_reasoning_from_message(msg)
            if reasoning:
                converted.append(ChatMessageUser(content=reasoning))
            else:
                converted.append(msg)
        else:
            converted.append(msg)

    return converted


@solver
def factorio_reasoning_only_solver():
    """Solver that keeps only reasoning blocks from history, stripping code.

    The key insight: the reasoning/thinking conveys what the code should do,
    so we don't need to keep the actual code in history. This dramatically
    reduces context size while maintaining the agent's understanding of
    what was attempted and why.

    Message format:
    - System: Full system prompt (cached)
    - History: Reasoning-only messages (code stripped)
    - Latest user: Full current observation

    Optimization: ~60-80% context reduction vs full history
    Trade-off: Model can't see exact code from previous steps
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )

            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            solver_name = "reasoning-only"

            logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            logger.warning(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
            task_instructions = get_base_system_prompt(
                goal_description, trajectory_length
            )

            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin building your factory step by step."""

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
                ChatMessageUser(
                    content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
                ),
            ]

            logger.info(
                f"📋 Initialized system prompt: {len(full_system_prompt)} chars"
            )

            # Trajectory tracking
            production_scores = []
            step_results = []
            game_ticks = []
            game_states = []

            # Achievement tracking - unique item types produced
            produced_item_types_set: set = set()
            # Research tracking - technologies researched during trajectory
            researched_technologies_set: set = set()

            # Latency tracking
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            for step in range(trajectory_length):
                step_start = time.time()
                Sleep.reset_step_sleep_duration()

                try:
                    gym_env.clear_enemies()

                    # Get current observation
                    observation: Observation = gym_env.get_observation()
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                        include_entities=True,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0

                    # Create step message with full observation (only current step gets full context)
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to expand and improve your factory."""

                    # Convert history to reasoning-only (except system and current message)
                    # Keep system message, convert history, then add current observation
                    if len(state.messages) > 2:
                        reasoning_messages = convert_messages_to_reasoning_only(
                            state.messages[:-1]
                        )
                        messages = reasoning_messages + [
                            ChatMessageUser(content=step_content)
                        ]
                    else:
                        messages = state.messages[:-1] + [
                            ChatMessageUser(content=step_content)
                        ]

                    # Generate response
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    if "openrouter" in _model.name:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    output = await _model.generate(
                        input=messages,
                        config=generation_config,
                    )
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    if hasattr(output, "usage") and hasattr(
                        output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add full response to state (will be converted to reasoning-only next iteration)
                    # state.messages.append(ChatMessageUser(content=step_content))
                    state.messages.append(output.message)
                    state.output = output

                    # Extract program
                    program = parse_response(output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            policy_execution_latencies.append(float(policy_time))

                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee
                        gym_env.reset({"game_state": game_states.pop()})
                        continue

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )
                    flow = obs["flows"]
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Extract unique item types from flows
                    # flow is obs["flows"] dict with harvested/output as lists of dicts
                    # Format: [{"type": "coal", "amount": 50.0}, ...]
                    if "harvested" in flow:
                        for item in flow["harvested"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "output" in flow:
                        for item in flow["output"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "crafted" in flow:
                        for craft in flow["crafted"]:
                            if isinstance(craft, dict) and "outputs" in craft:
                                produced_item_types_set.update(craft["outputs"].keys())

                    # Extract researched technologies from observation
                    try:
                        for (
                            tech_name,
                            tech_state,
                        ) in observation.research.technologies.items():
                            if tech_state.researched:
                                researched_technologies_set.add(tech_name)
                    except Exception as research_err:
                        logger.debug(
                            f"Could not extract research state: {research_err}"
                        )

                    # Record game ticks and calculate cost
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        previous_ticks = game_ticks[-1] if game_ticks else 0
                        ticks_cost = current_ticks - previous_ticks
                        game_ticks.append(current_ticks)
                    except Exception:
                        current_ticks = 0
                        ticks_cost = 0
                        game_ticks.append(0)

                    # Format elapsed time from ticks (60 ticks per second)
                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "None" if program.code else "No code submitted."
                        )

                    # Create feedback message
                    feedback_content = f"""
**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

                    # Handle image (only for current step)
                    image_data_url = None
                    if vision_enabled:
                        image_data_url, viewport_info = render_vision_image(gym_env)
                        if viewport_info:
                            feedback_content += f"\n\n{viewport_info}"
                    else:
                        image_data_url = obs.get("map_image")

                    if image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)

                    state.messages.append(feedback_message)

                    # Trim messages (reasoning-only conversion happens at next iteration)
                    if len(state.messages) > 25:
                        if state.messages[0].role == "system":
                            system_message = state.messages[0]
                            recent_messages = state.messages[-16:]
                            state.messages = [system_message] + recent_messages

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: "
                        f"Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.produced_item_types = list(produced_item_types_set)
                    trajectory_data.researched_technologies = list(
                        researched_technologies_set
                    )
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    await score(state)

                    if terminated or truncated:
                        logger.info(f"⚠️ Episode ended at step {step + 1}")
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    state.messages.append(
                        ChatMessageUser(
                            content=f"❌ Step {step + 1} error: {step_error}"
                        )
                    )

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.produced_item_types = list(produced_item_types_set)
            trajectory_data.researched_technologies = list(researched_technologies_set)
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            log_latency_summary(
                total_step_latencies,
                inference_latencies,
                env_execution_latencies,
                policy_execution_latencies,
                sleep_durations,
            )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
                f"with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = (
                f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in {solver_name} trajectory: {error_msg}",
                model=metadata.get("model", "unknown")
                if "metadata" in locals()
                else "unknown",
            )

        finally:
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve


# =============================================================================
# PRUNED GAMESTATE SOLVER
# =============================================================================


def prune_user_message_to_program_output(content) -> str:
    """Extract only program output from a user message, omitting game state.

    This function takes user message content (which may contain game state,
    program output, flows, viewport info, etc.) and returns only the program
    output section, replacing everything else with [omitted].

    Args:
        content: Message content (string or list of content blocks)

    Returns:
        Pruned message with only program output preserved
    """
    import re

    # Extract text content if it's a list of content blocks
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif isinstance(block, str):
                text_parts.append(block)
        text = "\n".join(text_parts)
    else:
        text = str(content)

    # Extract program output section using regex
    # Pattern matches: **Program Output (STDOUT/STDERR):**\n```\n...\n```
    program_output_pattern = (
        r"\*\*Program Output \(STDOUT/STDERR\):\*\*\s*```\s*(.*?)\s*```"
    )
    match = re.search(program_output_pattern, text, re.DOTALL)

    if match:
        program_output = match.group(1).strip()
        return f"""[Game state omitted]

**Program Output (STDOUT/STDERR):**
```
{program_output}
```

[Other fields omitted]"""
    else:
        # If no program output found, check if this is a step message (observation)
        # or an error message
        if "Step" in text and "Game State" in text:
            return "[Game state observation omitted]"
        elif "error" in text.lower():
            # Keep error messages intact
            return text
        else:
            return "[Message content omitted]"


def prune_historical_messages(messages: list) -> list:
    """Prune historical messages to only keep program output.

    Keeps system message and latest user message intact.
    For all other user messages, strips game state and keeps only program output.
    Assistant messages are kept intact (they contain the model's reasoning/code).

    Args:
        messages: List of chat messages

    Returns:
        Pruned message list
    """
    if len(messages) <= 2:
        return messages

    pruned = []
    for i, msg in enumerate(messages):
        is_last_user_message = (i == len(messages) - 1 and msg.role == "user") or (
            i == len(messages) - 2
            and messages[-1].role == "assistant"
            and msg.role == "user"
        )

        if msg.role == "system":
            # Keep system message intact
            pruned.append(msg)
        elif msg.role == "assistant":
            # Keep assistant messages (model's code/reasoning)
            pruned.append(msg)
        elif msg.role == "user":
            if is_last_user_message or i == len(messages) - 1:
                # Keep latest user message intact (current game state)
                pruned.append(msg)
            else:
                # Prune historical user messages to only program output
                pruned_content = prune_user_message_to_program_output(msg.content)
                pruned.append(ChatMessageUser(content=pruned_content))
        else:
            pruned.append(msg)

    return pruned


@solver
def factorio_pruned_gamestate_solver():
    """Solver that prunes historical user messages to only keep program output.

    This solver removes all game state observations from historical messages,
    keeping only:
    - System prompt (full)
    - Assistant messages (full - contains reasoning and code)
    - Historical user messages: Only program output (stdout/stderr)
    - Latest user message: Full game state observation

    The key insight: Program output tells the model what happened (success/error),
    while the current game state tells it what to do next. Historical game states
    are largely redundant since the current state reflects cumulative changes.

    Optimization: ~40-60% context reduction on user messages
    Trade-off: Model can't reference exact historical game states
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )

            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            solver_name = "pruned-gamestate"

            logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            logger.warning(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
            task_instructions = get_base_system_prompt(
                goal_description, trajectory_length
            )

            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin building your factory step by step."""

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
                ChatMessageUser(
                    content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
                ),
            ]

            logger.info(
                f"📋 Initialized system prompt: {len(full_system_prompt)} chars"
            )

            # Trajectory tracking
            production_scores = []
            step_results = []
            game_ticks = []
            game_states = []

            # Achievement tracking - unique item types produced
            produced_item_types_set: set = set()
            # Research tracking - technologies researched during trajectory
            researched_technologies_set: set = set()

            # Latency tracking
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            for step in range(trajectory_length):
                step_start = time.time()
                Sleep.reset_step_sleep_duration()

                try:
                    gym_env.clear_enemies()

                    # Get current observation
                    observation: Observation = gym_env.get_observation()
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                        include_entities=True,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0

                    # Create step message with full observation
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to expand and improve your factory."""

                    # PRUNE historical messages before adding new one
                    state.messages = prune_historical_messages(state.messages)

                    # Add current step message (will be kept intact as latest)
                    state.messages.append(ChatMessageUser(content=step_content))

                    # Generate response
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    if "openrouter" in _model.name:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    output = await _model.generate(
                        input=state.messages,
                        config=generation_config,
                    )
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    if hasattr(output, "usage") and hasattr(
                        output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add response to state
                    state.messages.append(output.message)
                    state.output = output

                    # Extract program
                    program = parse_response(output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            policy_execution_latencies.append(float(policy_time))

                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee
                        gym_env.reset({"game_state": game_states.pop()})
                        continue

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )
                    flow = obs["flows"]
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Extract unique item types from flows
                    # flow is obs["flows"] dict with harvested/output as lists of dicts
                    # Format: [{"type": "coal", "amount": 50.0}, ...]
                    if "harvested" in flow:
                        for item in flow["harvested"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "output" in flow:
                        for item in flow["output"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "crafted" in flow:
                        for craft in flow["crafted"]:
                            if isinstance(craft, dict) and "outputs" in craft:
                                produced_item_types_set.update(craft["outputs"].keys())

                    # Extract researched technologies from observation
                    try:
                        for (
                            tech_name,
                            tech_state,
                        ) in observation.research.technologies.items():
                            if tech_state.researched:
                                researched_technologies_set.add(tech_name)
                    except Exception as research_err:
                        logger.debug(
                            f"Could not extract research state: {research_err}"
                        )

                    # Record game ticks and calculate cost
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        previous_ticks = game_ticks[-1] if game_ticks else 0
                        ticks_cost = current_ticks - previous_ticks
                        game_ticks.append(current_ticks)
                    except Exception:
                        current_ticks = 0
                        ticks_cost = 0
                        game_ticks.append(0)

                    # Format elapsed time from ticks (60 ticks per second)
                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "None" if program.code else "No code submitted."
                        )

                    # Create feedback message (will be pruned next iteration)
                    feedback_content = f"""
**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

                    # Handle image
                    image_data_url = None
                    if vision_enabled:
                        image_data_url, viewport_info = render_vision_image(gym_env)
                        if viewport_info:
                            feedback_content += f"\n\n{viewport_info}"
                    else:
                        image_data_url = obs.get("map_image")

                    if image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)

                    state.messages.append(feedback_message)

                    # Trim messages if too long (standard trimming on top of pruning)
                    if len(state.messages) > 25:
                        if state.messages[0].role == "system":
                            system_message = state.messages[0]
                            recent_messages = state.messages[-16:]
                            state.messages = [system_message] + recent_messages

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: "
                        f"Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.produced_item_types = list(produced_item_types_set)
                    trajectory_data.researched_technologies = list(
                        researched_technologies_set
                    )
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    await score(state)

                    if terminated or truncated:
                        logger.info(f"⚠️ Episode ended at step {step + 1}")
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    state.messages.append(
                        ChatMessageUser(
                            content=f"❌ Step {step + 1} error: {step_error}"
                        )
                    )

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.produced_item_types = list(produced_item_types_set)
            trajectory_data.researched_technologies = list(researched_technologies_set)
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            log_latency_summary(
                total_step_latencies,
                inference_latencies,
                env_execution_latencies,
                policy_execution_latencies,
                sleep_durations,
            )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
                f"with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = (
                f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in {solver_name} trajectory: {error_msg}",
                model=metadata.get("model", "unknown")
                if "metadata" in locals()
                else "unknown",
            )

        finally:
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve


# =============================================================================
# CONDENSED PROMPT SOLVER
# =============================================================================


@solver
def factorio_full_prompt_solver():
    """Control solver using the full system prompt with all images.

    This is the baseline solver for comparison against context reduction variants.
    Uses the full ~28k token system prompt and keeps all images in history.

    Configuration:
    - Full system prompt (~28k tokens)
    - All images kept in history
    - Standard message trimming (25 -> 16 messages)
    - Full entity observations
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "full-prompt",
                "strip_images_from_history": False,
                "max_messages": 25,
                "trim_to": 16,
                "include_entities": True,
                "text_only": False,
            },
        )

    return solve


@solver
def factorio_full_prompt_latest_image_solver():
    """Full system prompt with only the latest image (history images stripped).

    Uses the full ~28k token system prompt but strips images from message history,
    keeping only the most recent image. This is the same as factorio_no_image_history_solver
    but with an explicit name for the experiment.

    Configuration:
    - Full system prompt (~28k tokens)
    - Images stripped from history, only latest shown
    - Standard message trimming (25 -> 16 messages)
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        return await _base_solver_loop(
            state,
            config={
                "solver_name": "full-prompt-latest-image",
                "strip_images_from_history": True,
                "max_messages": 25,
                "trim_to": 16,
                "include_entities": True,
                "text_only": False,
            },
        )

    return solve


@solver
def factorio_condensed_prompt_latest_image_solver():
    """Condensed system prompt with only the latest image.

    Combines two context reduction strategies:
    1. Condensed system prompt (~10k tokens vs ~28k)
    2. Image history stripping (only latest image shown)

    This provides maximum context reduction while still having visual feedback.

    Configuration:
    - Condensed system prompt (~10k tokens)
    - Images stripped from history, only latest shown
    - Standard message trimming (25 -> 16 messages)
    """
    from fle.eval.inspect_integration.condensed_prompts import (
        get_condensed_system_prompt,
    )

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )

            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            solver_name = "condensed-prompt-latest-image"

            logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            logger.warning(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # USE CONDENSED SYSTEM PROMPT
            full_system_prompt = get_condensed_system_prompt(
                goal_description=goal_description,
                trajectory_length=trajectory_length,
            )

            logger.info(
                f"📋 Using CONDENSED system prompt: {len(full_system_prompt)} chars "
                f"(~{len(full_system_prompt) // 4} tokens)"
            )

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
                ChatMessageUser(
                    content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
                ),
            ]

            # Trajectory tracking
            production_scores = []
            step_results = []
            game_ticks = []
            game_states = []

            # Achievement tracking - unique item types produced
            produced_item_types_set: set = set()
            # Research tracking - technologies researched during trajectory
            researched_technologies_set: set = set()

            # Latency tracking
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            for step in range(trajectory_length):
                step_start = time.time()
                Sleep.reset_step_sleep_duration()

                try:
                    gym_env.clear_enemies()

                    # Get current observation
                    observation: Observation = gym_env.get_observation()
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                        include_entities=True,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0

                    # Create step message
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to expand and improve your factory."""

                    state.messages.append(ChatMessageUser(content=step_content))

                    # Generate response
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    if "openrouter" in _model.name:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    output = await _model.generate(
                        input=state.messages,
                        config=generation_config,
                    )
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    if hasattr(output, "usage") and hasattr(
                        output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add response to state
                    state.messages.append(output.message)
                    state.output = output

                    # Extract program
                    program = parse_response(output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            policy_execution_latencies.append(float(policy_time))

                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee
                        gym_env.reset({"game_state": game_states.pop()})
                        continue

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )
                    flow = obs["flows"]
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Extract unique item types from flows
                    # flow is obs["flows"] dict with harvested/output as lists of dicts
                    # Format: [{"type": "coal", "amount": 50.0}, ...]
                    if "harvested" in flow:
                        for item in flow["harvested"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "output" in flow:
                        for item in flow["output"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "crafted" in flow:
                        for craft in flow["crafted"]:
                            if isinstance(craft, dict) and "outputs" in craft:
                                produced_item_types_set.update(craft["outputs"].keys())

                    # Extract researched technologies from observation
                    try:
                        for (
                            tech_name,
                            tech_state,
                        ) in observation.research.technologies.items():
                            if tech_state.researched:
                                researched_technologies_set.add(tech_name)
                    except Exception as research_err:
                        logger.debug(
                            f"Could not extract research state: {research_err}"
                        )

                    # Record game ticks and calculate cost
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        previous_ticks = game_ticks[-1] if game_ticks else 0
                        ticks_cost = current_ticks - previous_ticks
                        game_ticks.append(current_ticks)
                    except Exception:
                        current_ticks = 0
                        ticks_cost = 0
                        game_ticks.append(0)

                    # Format elapsed time from ticks (60 ticks per second)
                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "None" if program.code else "No code submitted."
                        )

                    # Create feedback message
                    feedback_content = f"""
**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

                    # Handle image
                    image_data_url = None
                    if vision_enabled:
                        image_data_url, viewport_info = render_vision_image(gym_env)
                        if viewport_info:
                            feedback_content += f"\n\n{viewport_info}"
                    else:
                        image_data_url = obs.get("map_image")

                    # STRIP IMAGES FROM HISTORY before adding new feedback
                    state.messages = trim_messages(
                        state.messages,
                        max_messages=25,
                        trim_to=16,
                        strip_images=True,  # Strip images from history
                    )

                    if image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)

                    state.messages.append(feedback_message)

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: "
                        f"Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.produced_item_types = list(produced_item_types_set)
                    trajectory_data.researched_technologies = list(
                        researched_technologies_set
                    )
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    await score(state)

                    if terminated or truncated:
                        logger.info(f"⚠️ Episode ended at step {step + 1}")
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    state.messages.append(
                        ChatMessageUser(
                            content=f"❌ Step {step + 1} error: {step_error}"
                        )
                    )

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.produced_item_types = list(produced_item_types_set)
            trajectory_data.researched_technologies = list(researched_technologies_set)
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            log_latency_summary(
                total_step_latencies,
                inference_latencies,
                env_execution_latencies,
                policy_execution_latencies,
                sleep_durations,
            )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
                f"with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = (
                f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in {solver_name} trajectory: {error_msg}",
                model=metadata.get("model", "unknown")
                if "metadata" in locals()
                else "unknown",
            )

        finally:
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve


@solver
def factorio_condensed_prompt_solver():
    """Solver using a condensed system prompt (~10k tokens vs ~28k).

    This solver uses a pre-condensed version of the system prompt generated
    by Claude Opus 4.5. The condensed prompt preserves all essential API
    semantics while reducing token count by ~65%.

    Key differences from full prompt:
    - Types section: Compact notation, essential attributes only
    - Methods section: Concise signatures with key parameters
    - Manual: Core concepts only, no verbose examples
    - Task instructions: Streamlined strategy guidance

    Benefits:
    - ~65% reduction in system prompt tokens (28k -> 10k)
    - Faster time-to-first-token
    - Lower cost per step
    - More headroom for context growth

    Trade-offs:
    - Less verbose explanations
    - Fewer examples in documentation
    - Model must infer from concise descriptions
    """
    from fle.eval.inspect_integration.condensed_prompts import (
        get_condensed_system_prompt,
    )

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )

            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            solver_name = "condensed-prompt"

            logger.info(f"🚀 Starting {solver_name} trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            logger.warning(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # USE CONDENSED SYSTEM PROMPT
            full_system_prompt = get_condensed_system_prompt(
                goal_description=goal_description,
                trajectory_length=trajectory_length,
            )

            logger.info(
                f"📋 Using CONDENSED system prompt: {len(full_system_prompt)} chars "
                f"(~{len(full_system_prompt) // 4} tokens)"
            )

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
                ChatMessageUser(
                    content=f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
                ),
            ]

            # Trajectory tracking
            production_scores = []
            step_results = []
            game_ticks = []
            game_states = []

            # Achievement tracking - unique item types produced
            produced_item_types_set: set = set()
            # Research tracking - technologies researched during trajectory
            researched_technologies_set: set = set()

            # Latency tracking
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            for step in range(trajectory_length):
                step_start = time.time()
                Sleep.reset_step_sleep_duration()

                try:
                    gym_env.clear_enemies()

                    # Get current observation
                    observation: Observation = gym_env.get_observation()
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                        include_entities=True,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0

                    # Create step message
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to expand and improve your factory."""

                    state.messages.append(ChatMessageUser(content=step_content))

                    # Generate response
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    if "openrouter" in _model.name:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    output = await _model.generate(
                        input=state.messages,
                        config=generation_config,
                    )
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    if hasattr(output, "usage") and hasattr(
                        output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add response to state
                    state.messages.append(output.message)
                    state.output = output

                    # Extract program
                    program = parse_response(output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            policy_execution_latencies.append(float(policy_time))

                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee
                        gym_env.reset({"game_state": game_states.pop()})
                        continue

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )
                    flow = obs["flows"]
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Extract unique item types from flows
                    # flow is obs["flows"] dict with harvested/output as lists of dicts
                    # Format: [{"type": "coal", "amount": 50.0}, ...]
                    if "harvested" in flow:
                        for item in flow["harvested"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "output" in flow:
                        for item in flow["output"]:
                            if isinstance(item, dict) and "type" in item:
                                produced_item_types_set.add(item["type"])
                    if "crafted" in flow:
                        for craft in flow["crafted"]:
                            if isinstance(craft, dict) and "outputs" in craft:
                                produced_item_types_set.update(craft["outputs"].keys())

                    # Extract researched technologies from observation
                    try:
                        for (
                            tech_name,
                            tech_state,
                        ) in observation.research.technologies.items():
                            if tech_state.researched:
                                researched_technologies_set.add(tech_name)
                    except Exception as research_err:
                        logger.debug(
                            f"Could not extract research state: {research_err}"
                        )

                    # Record game ticks and calculate cost
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        previous_ticks = game_ticks[-1] if game_ticks else 0
                        ticks_cost = current_ticks - previous_ticks
                        game_ticks.append(current_ticks)
                    except Exception:
                        current_ticks = 0
                        ticks_cost = 0
                        game_ticks.append(0)

                    # Format elapsed time from ticks (60 ticks per second)
                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "None" if program.code else "No code submitted."
                        )

                    # Create feedback message
                    feedback_content = f"""
**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""

                    # Handle image
                    image_data_url = None
                    if vision_enabled:
                        image_data_url, viewport_info = render_vision_image(gym_env)
                        if viewport_info:
                            feedback_content += f"\n\n{viewport_info}"
                    else:
                        image_data_url = obs.get("map_image")

                    if image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)

                    state.messages.append(feedback_message)

                    # Standard message trimming
                    if len(state.messages) > 25:
                        if state.messages[0].role == "system":
                            system_message = state.messages[0]
                            recent_messages = state.messages[-16:]
                            state.messages = [system_message] + recent_messages

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: "
                        f"Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.produced_item_types = list(produced_item_types_set)
                    trajectory_data.researched_technologies = list(
                        researched_technologies_set
                    )
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    await score(state)

                    if terminated or truncated:
                        logger.info(f"⚠️ Episode ended at step {step + 1}")
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    state.messages.append(
                        ChatMessageUser(
                            content=f"❌ Step {step + 1} error: {step_error}"
                        )
                    )

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.produced_item_types = list(produced_item_types_set)
            trajectory_data.researched_technologies = list(researched_technologies_set)
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            log_latency_summary(
                total_step_latencies,
                inference_latencies,
                env_execution_latencies,
                policy_execution_latencies,
                sleep_durations,
            )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step {solver_name} trajectory "
                f"with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 {solver_name} trajectory complete: {final_score:.1f} production "
                f"score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = (
                f"{solver_name} solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in {solver_name} trajectory: {error_msg}",
                model=metadata.get("model", "unknown")
                if "metadata" in locals()
                else "unknown",
            )

        finally:
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve
