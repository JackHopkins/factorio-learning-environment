"""Controlled solver that manages Factorio trajectory execution.

Contains two solvers:
- factorio_controlled_solver: For throughput tasks with specific quotas
- factorio_unbounded_solver: For open-play tasks tracking cumulative production score
"""

import logging
import math
import os
import time
import traceback
from typing import List, Optional, Tuple

from inspect_ai.scorer import score
from pydantic import Field
from inspect_ai.log import transcript
from inspect_ai.solver import solver
from inspect_ai.agent import AgentState
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    ModelOutput,
    get_model,
    ContentImage,
    ContentText,
    CachePolicy,
)
from inspect_ai.util import StoreModel, store_as

from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import TreeObservationFormatter
from fle.env.gym_env.registry import get_environment_info
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)

from fle.eval.inspect_integration.simple_server_pool import (
    get_simple_server_pool,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.agents.llm.parsing import parse_response
from fle.env.tools.agent.sleep.client import Sleep


import importlib.resources
from pathlib import Path
from jinja2 import Template
import gym


def _load_prompt_template(filename: str) -> Template:
    """Load a Jinja2 prompt template from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    return Template(prompt_path.read_text())


def render_vision_image(gym_env: FactorioGymEnv) -> Tuple[Optional[str], Optional[str]]:
    """Render an image centered on the player using the full sprite renderer.

    Returns:
        Tuple of (base64_image_data_url, viewport_info_string)
        Returns (None, None) if rendering fails
    """
    try:
        # Access the namespace to use the full _render method
        namespace = gym_env.instance.namespaces[0]

        # Get player position for debugging
        player_pos = namespace.player_location
        vis_logger = logging.getLogger(__name__)
        vis_logger.info(
            f"👁️ Vision render: player at ({player_pos.x:.1f}, {player_pos.y:.1f})"
        )

        # Render with default settings - centered on player
        # Pass position explicitly to ensure centering works
        result = namespace._render(
            radius=64,
            max_render_radius=32,
            position=player_pos,
            include_status=True,
        )

        # Get the base64 image with proper data URL prefix for ContentImage
        base64_data = result.to_base64()
        image_data_url = f"data:image/png;base64,{base64_data}"

        # Format viewport information
        viewport = result.viewport
        vis_logger.info(
            f"👁️ Vision render: viewport center ({viewport.center_x:.1f}, {viewport.center_y:.1f}), "
            f"size {viewport.width_tiles:.0f}x{viewport.height_tiles:.0f} tiles, "
            f"image {viewport.image_width}x{viewport.image_height}px"
        )

        # Check if the image might be empty (only grid) by sampling pixels
        # img = result.image
        # if img:
        #     # Sample some pixels to detect if image has content beyond just grid lines
        #     pixels = list(img.getdata())
        #     sample_size = min(1000, len(pixels))
        #     unique_colors = len(set(pixels[:sample_size]))
        #     if unique_colors <= 3:  # Only background and maybe grid lines
        #         vis_logger.warning(
        #             f"👁️ Vision render produced image with only {unique_colors} unique colors "
        #             f"(likely empty grid). Check if sprites are installed correctly. "
        #             f"Run 'fle sprites' to download sprites."
        #         )

        viewport_template = _load_prompt_template("vision_viewport.jinja2.md")
        viewport_info = viewport_template.render(
            center_x=f"{viewport.center_x:.1f}",
            center_y=f"{viewport.center_y:.1f}",
            world_min_x=f"{viewport.world_min_x:.1f}",
            world_min_y=f"{viewport.world_min_y:.1f}",
            world_max_x=f"{viewport.world_max_x:.1f}",
            world_max_y=f"{viewport.world_max_y:.1f}",
            width_tiles=f"{viewport.width_tiles:.0f}",
            height_tiles=f"{viewport.height_tiles:.0f}",
            image_width=viewport.image_width,
            image_height=viewport.image_height,
            scaling=f"{viewport.scaling:.1f}",
        )

        return image_data_url, viewport_info
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to render vision image: {e}", exc_info=True
        )
        return None, None


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
    steps: List[dict] = Field(default_factory=list)  # Using dict for step data
    error: str = Field(default="")
    ticks: List[int] = Field(default_factory=list)  # Game ticks at each step

    # Achievement tracking - unique item types produced
    produced_item_types: List[str] = Field(
        default_factory=list
    )  # List of unique item type names produced during trajectory

    # Research tracking - technologies researched during trajectory
    researched_technologies: List[str] = Field(
        default_factory=list
    )  # List of technology names that have been researched

    # Latency tracking fields
    inference_latencies: List[float] = Field(
        default_factory=list
    )  # Time for model generation (seconds)
    env_execution_latencies: List[float] = Field(
        default_factory=list
    )  # Time for gym_env.step() (seconds)
    policy_execution_latencies: List[float] = Field(
        default_factory=list
    )  # Time for Python code execution (seconds)
    sleep_durations: List[float] = Field(
        default_factory=list
    )  # Accumulated sleep time per step (seconds)
    total_step_latencies: List[float] = Field(
        default_factory=list
    )  # Total wall-clock time per step (seconds)

    # Full program codes for static analysis
    program_codes: List[str] = Field(
        default_factory=list
    )  # Full program code for each step


@solver
def factorio_controlled_solver():
    """Controlled solver that runs exactly 64 Factorio steps with full logging"""

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "iron_ore_throughput")
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get(
                "trajectory_length", 64
            )  # Full trajectory length

            logger.info(
                f"🚀 Starting controlled 64-step Factorio trajectory for {env_id}"
            )
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation with round-robin API key assignment
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            if allocation.api_key:
                logger.info(
                    f"📡 Allocated server factorio_{run_idx} with API key index {allocation.api_key_index}"
                )
            else:
                logger.info(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env: FactorioGymEnv = gym.make(env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("🎮 Connected to Factorio server")

            # Get task configuration
            env_info = get_environment_info(env_id)
            if not env_info:
                raise ValueError(f"No environment info for {env_id}")

            # task = TaskFactory.create_task(env_info["task_config_path"])

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)

            # Get task-specific instructions
            task_config = THROUGHPUT_TASKS.get(env_id)
            if task_config:
                goal_description = task_config.goal_description
                quota = task_config.quota
                task_instructions = f"""
## TASK OBJECTIVE
{goal_description}

## SUCCESS CRITERIA
- Produce at least {quota} {env_id.replace("_throughput", "").replace("_", "-")} per 60 in-game seconds
- Build a fully automated production system
- Complete the task within {trajectory_length} trajectory steps

## IMPORTANT NOTES
- You have {trajectory_length} steps to complete this task
- Each step should make meaningful progress toward the goal
- Focus on essential infrastructure first (mining, smelting, power)
- Then build the specific production chain required
"""
            else:
                goal_description = (
                    f"Create an automatic {env_id.replace('_', '-')} factory"
                )
                quota = 16
                task_instructions = f"## TASK OBJECTIVE\n{goal_description}"

            # Combine base instructions with task-specific instructions
            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin working toward this objective step by step."""

            # Initialize conversation with system prompt only
            # The first user message will be added in the step loop to avoid
            # contiguous user messages (initial + step 1)
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
            ]

            logger.info(
                f"📋 Initialized system prompt: {len(full_system_prompt)} chars"
            )
            logger.info(f"🎯 Task: {goal_description}")
            logger.info(f"📊 Quota: {quota} items per 60 seconds")
            logger.info(f"📈 Starting {trajectory_length}-step controlled execution...")
            logger.info(f"Trajectory length: {trajectory_length} steps")

            # Check if vision mode is enabled
            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            if vision_enabled:
                logger.info("👁️  Vision mode enabled - rendering images after each step")

            # Controlled trajectory execution - WE control the 64 steps
            production_scores = []
            step_results = []
            game_ticks = []  # Track game ticks at each step

            # Store previous step's feedback to combine with next step's prompt
            # This avoids contiguous user messages in the conversation
            # Initialize with the original user message so it gets combined with step 1
            previous_feedback_content = f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
            previous_feedback_image = None

            for step in range(trajectory_length):
                step_start = time.time()

                try:
                    # Get current observation from Factorio
                    observation: Observation = gym_env.get_observation()
                    # Don't include flows in pre-step observation since they're cumulative totals
                    # Flows are only meaningful after a step (showing delta production)
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                    ).format(observation)

                    # Create step message with current game state
                    current_score = production_scores[-1] if production_scores else 0
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Current production score: {current_score:.1f}/{quota}
Progress: {(step / trajectory_length) * 100:.1f}% complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to progress toward the production goal."""

                    # Combine previous feedback with current step content to avoid contiguous user messages
                    # This maintains proper user/assistant alternation in the conversation
                    if previous_feedback_content is not None:
                        combined_content = (
                            f"{previous_feedback_content}\n\n---\n\n{step_content}"
                        )
                        if previous_feedback_image is not None:
                            # Include image from previous feedback with combined text
                            step_message = ChatMessageUser(
                                content=[
                                    ContentImage(image=previous_feedback_image),
                                    ContentText(text=combined_content),
                                ]
                            )
                        else:
                            step_message = ChatMessageUser(content=combined_content)
                        # Reset for next iteration
                        previous_feedback_content = None
                        previous_feedback_image = None
                    else:
                        step_message = ChatMessageUser(content=step_content)

                    state.messages.append(step_message)

                    # Generate response using Inspect's model with reasoning support
                    generation_config = {
                        "max_tokens": 4096,  # More tokens for complex programs
                        "transforms": ["middle-out"],
                        "reasoning_effort": "minimal",
                        # "temperature": 0.1
                    }

                    state.output = await get_model().generate(
                        input=state.messages,
                        config=generation_config,
                        # transforms = ['middle-out']
                    )

                    # Log reasoning usage if available
                    if hasattr(state.output, "usage") and hasattr(
                        state.output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {state.output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add model response to conversation
                    state.messages.append(state.output.message)

                    # Extract Python program from the model response
                    program = parse_response(state.output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action in Factorio and capture results
                    action = Action(agent_idx=0, code=program.code)
                    try:
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        # Clear enemies after each step to prevent interference
                        gym_env.background_step()

                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        # Store error as feedback for next step instead of appending directly
                        # This avoids contiguous user messages
                        previous_feedback_content = f"Environment error: {ee}"
                        previous_feedback_image = None
                        continue

                    # Log execution details
                    logger.info(
                        f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}"
                    )

                    # Get post-execution observation and program output
                    # post_action_observation = gym_env.get_observation()
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )

                    # Calculate flows
                    flow = obs["flows"]
                    # Calculate production score
                    production_score = obs["score"] if obs["score"] else 0
                    production_scores.append(production_score)

                    # Record game ticks and calculate cost
                    try:
                        current_ticks = gym_env.instance.get_elapsed_ticks()
                        previous_ticks = game_ticks[-1] if game_ticks else 0
                        ticks_cost = current_ticks - previous_ticks
                        game_ticks.append(current_ticks)
                    except Exception as tick_err:
                        logger.debug(f"Could not get game ticks: {tick_err}")
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
                        if not program.code:
                            program_output = (
                                "No code was submitted. Write code in ``` blocks."
                            )
                        else:
                            program_output = "None"
                    # Create comprehensive feedback message
                    feedback_content = f"""## Step {step + 1} Execution Results

**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Execution Info:**
- Reward: {reward}

**Performance Results:**
- Production score: {production_score:.1f} (was {current_score:.1f})
- Score change: {production_score - current_score:+.1f}
- Elapsed time: {elapsed_time_str}
- Ticks: {current_ticks}
- Ticks cost: +{ticks_cost}

**Flows:**
{TreeObservationFormatter.format_flows_compact(flow)}

Continue to step {step + 2}."""
                    logger.debug(str(obs))

                    # Get rendered image - use vision mode if enabled
                    updated_image_data_url = None
                    viewport_info = None

                    if vision_enabled:
                        # Use full sprite renderer with viewport info
                        updated_image_data_url, viewport_info = render_vision_image(
                            gym_env
                        )
                        if viewport_info:
                            feedback_content += f"\n\n{viewport_info}"
                    else:
                        # Fall back to simple render from observation
                        updated_image_data_url = obs.get("map_image")

                    # Validate image is a proper data URL to avoid Inspect trying to load it as a file
                    if updated_image_data_url and not str(
                        updated_image_data_url
                    ).startswith("data:"):
                        logger.warning(
                            f"Invalid map_image format (expected data URL), skipping: {str(updated_image_data_url)[:100]}"
                        )
                        updated_image_data_url = None

                    # Store feedback for combining with next step's prompt
                    # This avoids contiguous user messages in the conversation
                    previous_feedback_content = feedback_content
                    previous_feedback_image = updated_image_data_url

                    if updated_image_data_url:
                        logger.info(
                            f"🖼️  Step {step + 1}: {'(vision mode)' if vision_enabled else ''}"
                        )
                    else:
                        logger.info(f"📝 Step {step + 1}:")

                    # Trim messages if we have too many user/assistant pairs (keep system prompt)
                    if (
                        len(state.messages) > 25
                    ):  # 1 system + 32 user/assistant messages = 33 total
                        # Defensively preserve system message - ensure it exists and is a system message
                        if (
                            len(state.messages) > 0
                            and state.messages[0].role == "system"
                        ):
                            system_message = state.messages[0]
                            recent_messages = state.messages[-24:]
                            state.messages = [system_message] + recent_messages
                            logger.info(
                                f"🧹 Trimmed conversation to {len(state.messages)} messages (kept system + last 32)"
                            )
                        else:
                            # Fallback: just keep last 32 messages if no valid system message found
                            state.messages = state.messages[-24:]
                            logger.warning(
                                f"⚠️ No valid system message found - kept last {len(state.messages)} messages only"
                            )

                    step_time = time.time() - step_start

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
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store intermediate progress using typed store
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks

                    # Apply intermediate scoring for real-time metrics tracking
                    try:
                        from fle.eval.inspect_integration.scorers import (
                            apply_intermediate_scoring,
                        )

                        await apply_intermediate_scoring(
                            state=state,
                            step_num=step + 1,
                            production_score=production_score,
                            expected_score=quota,
                            scores_history=production_scores,
                        )
                    except Exception as scoring_error:
                        logger.warning(
                            f"Intermediate scoring error at step {step + 1}: {scoring_error}"
                        )

                    # Check for early termination
                    if terminated or truncated:
                        logger.info(
                            f"⚠️ Episode ended early at step {step + 1}: terminated={terminated}, truncated={truncated}"
                        )
                        transcript().info(
                            f"⚠️ Episode ended early at step {step + 1}: terminated={terminated}, truncated={truncated}, score={production_score:.1f}, flows={flow}"
                        )

                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    # Store error as feedback for next step instead of appending directly
                    # This avoids contiguous user messages
                    previous_feedback_content = (
                        f"❌ Step {step + 1} error: {step_error}"
                    )
                    previous_feedback_image = None
                    # Continue with next step rather than failing completely

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0
            # achievements = gym_env.get_achievements() if hasattr(gym_env, "get_achievements") else {}

            # Store final results using typed store
            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks

            # Set final model output with summary
            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step trajectory with final score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 Controlled trajectory complete: {final_score:.1f} score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 Controlled trajectory complete: {final_score:.1f} score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = f"Controlled solver error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)

            # Store error information using typed store
            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in controlled trajectory: {error_msg}",
                model=metadata.get("model", "unknown") if metadata else "unknown",
            )

        finally:
            # Clean up resources
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
def factorio_unbounded_solver():
    """Unbounded solver for open-play tasks that tracks cumulative production score.

    Unlike the throughput solver, this solver:
    - Uses cumulative production score (total economic value of all production)
    - Has no quota or target - the goal is to maximize production
    - Designed for long trajectories (5000+ steps)
    - Never terminates early based on quota achievement
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None

        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            # For unbounded production tasks, always use the "open_play" gym environment
            # The env_id in metadata (e.g., "open_play_production") is just for task identification
            # The actual gym environment is "open_play" which uses DefaultTask
            env_id = metadata.get("env_id", "open_play_production")
            gym_env_id = "open_play"  # Always use open_play gym environment
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )
            # Check if vision mode is enabled
            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            if vision_enabled:
                logger.info("👁️  Vision mode enabled - rendering images after each step")

            logger.info(f"🚀 Starting unbounded Factorio trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation with round-robin API key assignment
            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            if allocation.api_key:
                logger.warning(
                    f"📡 Allocated server factorio_{run_idx} with API key index {allocation.api_key_index}"
                )
            else:
                logger.warning(f"📡 Allocated server factorio_{run_idx}")

            AGENT_ID = 0
            # Initial radius
            INITIAL_RADIUS = 5

            # Create gym environment - always use open_play for unbounded tasks
            # open_play uses DefaultTask which has no throughput requirements
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("Connected to Factorio server")

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(
                agent_idx=AGENT_ID, num_agents=1
            )

            # Combine base instructions with task-specific instructions
            system_template = _load_prompt_template("unbounded_system.jinja2.md")
            full_system_prompt = system_template.render(
                base_system_prompt=base_system_prompt
            )

            # Initialize conversation with system prompt only
            # The first user message will be added in the step loop to avoid
            # contiguous user messages (initial + step 1)
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )

            state.messages = [
                ChatMessageSystem(content=full_system_prompt),
            ]

            logger.info(
                f"📋 Initialized system prompt: {len(full_system_prompt)} chars"
            )
            logger.info(f"🎯 Task: {goal_description}")
            logger.info(f"📈 Starting {trajectory_length}-step unbounded execution...")

            # Trajectory execution
            production_scores = []
            automated_production_scores = []  # Automated production scores (excluding harvested/crafted)
            step_results = []
            game_ticks = []  # Track game ticks at each step
            game_states = []

            # Store previous step's feedback to combine with next step's prompt
            # This avoids contiguous user messages in the conversation
            # Initialize with the original user message so it gets combined with step 1
            previous_feedback_content = f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
            previous_feedback_image = None

            # Achievement tracking - unique item types produced
            produced_item_types_set: set = set()

            # Research tracking - technologies researched
            researched_technologies_set: set = set()

            # Latency tracking lists
            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []

            # Full program codes for static analysis
            program_codes = []

            for step in range(trajectory_length):
                step_start = time.time()

                # Reset sleep duration tracking for this step
                Sleep.reset_step_sleep_duration()

                try:
                    try:
                        # Clear enemies before each step to prevent interference
                        gym_env.background_step(step=step + INITIAL_RADIUS)
                    except Exception as ee:
                        logger.warning(f"Environment error: Clearing enemies: {ee}")
                        raise Exception(f"Clearing enemies: {ee}") from ee

                    # Get current observation from Factorio
                    observation: Observation = gym_env.get_observation()
                    # Don't include flows in pre-step observation since they're cumulative totals
                    # Flows are only meaningful after a step (showing delta production)
                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                    ).format(observation)

                    # Create step message with current game state
                    current_score = production_scores[-1] if production_scores else 0
                    step_template = _load_prompt_template("unbounded_step.jinja2.md")
                    step_content = step_template.render(
                        step=step + 1,
                        trajectory_length=trajectory_length,
                        progress=f"{(step / trajectory_length) * 100:.1f}",
                        game_state=obs_formatted.raw_str.replace("\\n", "\n"),
                    )

                    # Combine previous feedback with current step content to avoid contiguous user messages
                    # This maintains proper user/assistant alternation in the conversation
                    try:
                        if previous_feedback_content is not None:
                            combined_content = (
                                f"{previous_feedback_content}\n\n---\n\n{step_content}"
                            )
                            if previous_feedback_image is not None:
                                # Validate image before creating ContentImage
                                if not isinstance(
                                    previous_feedback_image, str
                                ) or not previous_feedback_image.startswith("data:"):
                                    logger.warning(
                                        f"Invalid previous_feedback_image, skipping: {type(previous_feedback_image)} - {str(previous_feedback_image)[:100] if previous_feedback_image else 'None'}"
                                    )
                                    step_message = ChatMessageUser(
                                        content=combined_content
                                    )
                                else:
                                    # Include image from previous feedback with combined text
                                    step_message = ChatMessageUser(
                                        content=[
                                            ContentImage(image=previous_feedback_image),
                                            ContentText(text=combined_content),
                                        ]
                                    )
                            else:
                                step_message = ChatMessageUser(content=combined_content)
                            # Reset for next iteration
                            previous_feedback_content = None
                            previous_feedback_image = None
                        else:
                            step_message = ChatMessageUser(content=step_content)
                    except Exception as msg_error:
                        logger.error(f"Error creating step message: {msg_error}")
                        logger.error(
                            f"previous_feedback_image type: {type(previous_feedback_image)}, value: {str(previous_feedback_image)[:200] if previous_feedback_image else 'None'}"
                        )
                        # Fall back to text-only message
                        step_message = ChatMessageUser(content=step_content)
                        previous_feedback_content = None
                        previous_feedback_image = None

                    try:
                        state.messages.append(step_message)
                    except Exception as append_error:
                        logger.error(f"Error appending step message: {append_error}")
                        raise

                    # Generate response using Inspect's model
                    generation_config = {
                        # "max_tokens": 4096,
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                        # "reasoning_effort": "minimal",
                    }
                    _model = get_model()
                    # Safely access model name - handle cases where get_model() returns unexpected types
                    model_name_str = (
                        getattr(_model, "name", "") if hasattr(_model, "name") else ""
                    )
                    if model_name_str and "openrouter" in model_name_str:
                        generation_config["transforms"] = ["middle-out"]

                    # Track inference latency
                    inference_start = time.time()
                    try:
                        state.output = await _model.generate(
                            input=state.messages,
                            config=generation_config,
                        )
                    except Exception as gen_error:
                        logger.error(f"Error during model generation: {gen_error}")
                        logger.error(f"Number of messages: {len(state.messages)}")
                        for i, msg in enumerate(state.messages):
                            content_type = type(msg.content).__name__
                            if isinstance(msg.content, list):
                                content_types = [type(c).__name__ for c in msg.content]
                                logger.error(
                                    f"  Message {i}: role={msg.role}, content types={content_types}"
                                )
                            else:
                                logger.error(
                                    f"  Message {i}: role={msg.role}, content type={content_type}"
                                )
                        raise
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    # Log reasoning usage if available
                    if hasattr(state.output, "usage") and hasattr(
                        state.output.usage, "reasoning_tokens"
                    ):
                        logger.info(
                            f"🧠 Step {step + 1}: Used {state.output.usage.reasoning_tokens} reasoning tokens"
                        )

                    # Add model response to conversation
                    state.messages.append(state.output.message)

                    # Extract Python program from the model response
                    program = parse_response(state.output)

                    if not program:
                        raise Exception(
                            "Could not parse program from model response. Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Store full program code for static analysis
                    program_codes.append(program.code)

                    # Execute action in Factorio and capture results
                    action = Action(
                        agent_idx=0, code=program.code
                    )  # , game_state=game_states[-1] if game_states else None
                    try:
                        # Track environment execution latency
                        env_start = time.time()
                        obs, reward, terminated, truncated, info = gym_env.step(action)
                        env_time = time.time() - env_start
                        env_execution_latencies.append(env_time)

                        game_states.append(info["output_game_state"])

                        # Get policy execution time from info (time for Python code execution)
                        policy_time = info.get("policy_execution_time", 0.0)
                        if policy_time:
                            logger.warning(
                                str(math.ceil(policy_time * 10) / 10)
                                + " seconds to execute policy"
                            )
                            policy_execution_latencies.append(float(policy_time))

                        # Get accumulated sleep duration for this step
                        step_sleep_duration = Sleep.get_step_sleep_duration()
                        sleep_durations.append(step_sleep_duration)
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee} - {type(gym_env)}")
                        # Store error as feedback for next step instead of appending directly
                        # This avoids contiguous user messages
                        previous_feedback_content = f"Environment error: {ee}"
                        previous_feedback_image = None
                        if not game_states:
                            raise Exception(f"Environment error: {ee}") from ee

                        gym_env.reset({"game_state": game_states.pop()})
                        logger.warning(
                            f"Resetting environment after error to previous game state: {ee}"
                        )
                        continue

                    # Log execution details with latency info
                    logger.info(
                        f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}, "
                        f"inference={inference_time}s, env={env_time}s, policy={policy_time}s, sleep={step_sleep_duration}s"
                    )

                    # Get program output
                    program_output = (
                        info.get("result", "No output captured")
                        if info
                        else "No info available"
                    )

                    # Calculate flows
                    flow = obs["flows"]

                    # For unbounded tasks, use the CUMULATIVE production score from info
                    # This is the true total economic value, not the per-step reward
                    production_score = info.get("production_score", 0)
                    production_scores.append(production_score)

                    # Track automated production score (excludes harvested/crafted items)
                    automated_score = info.get("automated_production_score", 0)
                    automated_production_scores.append(automated_score)

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
                    # observation.research.technologies is a dict of TechnologyState objects
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
                    except Exception as tick_err:
                        logger.debug(f"Could not get game ticks: {tick_err}")
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
                        if not program.code:
                            program_output = (
                                "No code was submitted. Write code in ``` blocks."
                            )
                        else:
                            program_output = "None"

                    # Create comprehensive feedback message
                    feedback_template = _load_prompt_template(
                        "unbounded_feedback.jinja2.md"
                    )
                    feedback_content = feedback_template.render(
                        program_output=program_output,
                        production_score=f"{production_score:.1f}",
                        previous_score=f"{current_score:.1f}",
                        score_change=f"{production_score - current_score:+.1f}",
                        elapsed_time=elapsed_time_str,
                        current_ticks=current_ticks,
                        ticks_cost=ticks_cost,
                        flows=TreeObservationFormatter.format_flows_compact(flow),
                        next_step=step + 2,
                    )

                    logger.debug(str(obs))

                    try:
                        if vision_enabled:
                            # Use full sprite renderer with viewport info
                            updated_image_data_url, viewport_info = render_vision_image(
                                gym_env
                            )
                            if viewport_info:
                                feedback_content += f"\n\n{viewport_info}"
                        else:
                            # Fall back to simple render from observation
                            updated_image_data_url = obs.get("map_image")
                    except Exception as e:
                        raise Exception(f"Vision rendering error: {e}") from e

                    # Store feedback for combining with next step's prompt
                    # This avoids contiguous user messages in the conversation
                    previous_feedback_content = feedback_content
                    previous_feedback_image = updated_image_data_url

                    # Trim messages if we have too many (keep system prompt)
                    if len(state.messages) > 25:
                        if (
                            len(state.messages) > 0
                            and state.messages[0].role == "system"
                        ):
                            system_message = state.messages[0]
                            recent_messages = state.messages[-16:]
                            state.messages = [system_message] + recent_messages
                            logger.info(
                                f"🧹 Trimmed conversation to {len(state.messages)} messages"
                            )
                        else:
                            state.messages = state.messages[-16:]
                            logger.warning(
                                f"⚠️ No valid system message found - kept last {len(state.messages)} messages only"
                            )

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
                        # Include latency breakdown in step result
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                        "policy_execution_latency": policy_time,
                        "sleep_duration": step_sleep_duration,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step + 1}/{trajectory_length}: Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store intermediate progress using typed store
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.automated_production_score = automated_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.automated_scores = automated_production_scores
                    trajectory_data.ticks = game_ticks
                    trajectory_data.produced_item_types = list(produced_item_types_set)
                    trajectory_data.researched_technologies = list(
                        researched_technologies_set
                    )

                    # Store latency data
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies

                    # Store program codes for static analysis
                    trajectory_data.program_codes = program_codes

                    # Apply scoring
                    await score(state)

                    # For unbounded tasks, we don't terminate early based on quota
                    # Only terminate if the environment says so (e.g., crash, error)
                    if terminated or truncated:
                        logger.info(
                            f"⚠️ Episode ended at step {step + 1}: terminated={terminated}, truncated={truncated}"
                        )
                        transcript().info(
                            f"⚠️ Episode ended at step {step + 1}: terminated={terminated}, truncated={truncated}, score={production_score:.1f}"
                        )
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error(f"❌ Step {step + 1} error: {step_error}")
                    # Store error as feedback for next step instead of appending directly
                    # This avoids contiguous user messages
                    previous_feedback_content = (
                        f"❌ Step {step + 1} error: {step_error}"
                    )
                    previous_feedback_image = None
                    # Continue with next step rather than failing completely

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0
            final_automated_score = (
                automated_production_scores[-1] if automated_production_scores else 0.0
            )

            # Store final results using typed store
            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.automated_production_score = final_automated_score
            trajectory_data.final_score = final_score
            trajectory_data.final_automated_score = final_automated_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.automated_scores = automated_production_scores
            trajectory_data.ticks = game_ticks
            trajectory_data.produced_item_types = list(produced_item_types_set)
            trajectory_data.researched_technologies = list(researched_technologies_set)

            # Store final latency data
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies

            # Store program codes for static analysis
            trajectory_data.program_codes = program_codes

            # Log latency summary
            if total_step_latencies:
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

            # Set final model output with summary
            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step unbounded trajectory with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 Unbounded trajectory complete: {final_score:.1f} production score after {len(step_results)} steps"
            )
            transcript().info(
                f"🎉 Unbounded trajectory complete: {final_score:.1f} production score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = f"Unbounded solver error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)

            # Store error information using typed store
            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in unbounded trajectory: {error_msg}",
                model=metadata.get("model", "unknown") if metadata else "unknown",
            )

        finally:
            # Clean up resources
            if run_idx is not None:
                try:
                    pool = await get_simple_server_pool()
                    await pool.release_run_idx(run_idx)
                    logger.info(f"🧹 Released server factorio_{run_idx}")
                except Exception as e:
                    logger.error(f"Error releasing server: {e}")

        return state

    return solve
