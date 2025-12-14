"""Controlled solver that manages Factorio trajectory execution.

Contains two solvers:
- factorio_controlled_solver: For throughput tasks with specific quotas
- factorio_unbounded_solver: For open-play tasks tracking cumulative production score
"""

import logging
import os
import time
import traceback
from typing import List, Optional, Tuple

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

from fle.eval.inspect_integration.simple_server_pool import get_simple_server_pool
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.agents.llm.parsing import parse_response


import importlib.resources
import gym


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
    total_steps: int = Field(default=0)
    current_score: float = Field(default=0.0)
    final_score: float = Field(default=0.0)
    scores: List[float] = Field(default_factory=list)
    steps: List[dict] = Field(default_factory=list)  # Using dict for step data
    error: str = Field(default="")


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

            # Get server allocation
            pool = await get_simple_server_pool()
            run_idx = await pool.get_run_idx()
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

            # Initialize conversation with proper system prompt
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
                    step_content = f"""## Step {step + 1}/{trajectory_length} - Game State Analysis

Current production score: {current_score:.1f}/{quota}
Progress: {(step / trajectory_length) * 100:.1f}% complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to progress toward the production goal."""

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
                        gym_env.clear_enemies()
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
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

**Flows**
{flow}

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

                    # Create feedback message with both image and text
                    if updated_image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=updated_image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                        logger.info(
                            f"🖼️  Step {step + 1}: {'(vision mode)' if vision_enabled else ''}"
                        )
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)
                        logger.info(f"📝 Step {step + 1}:")

                    state.messages.append(feedback_message)

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
                    feedback_message = ChatMessageUser(
                        content=f"❌ Step {step + 1} error: {step_error}"
                    )
                    state.messages.append(feedback_message)

                    # Continue with next step rather than failing completely
                    step += 1

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
                "Build the biggest possible factory. Maximize automation, efficiency and scale.",
            )
            # Check if vision mode is enabled
            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"
            if vision_enabled:
                logger.info("👁️  Vision mode enabled - rendering images after each step")

            logger.info(f"🚀 Starting unbounded Factorio trajectory for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Get server allocation
            pool = await get_simple_server_pool()
            run_idx = await pool.get_run_idx()
            logger.info(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment - always use open_play for unbounded tasks
            # open_play uses DefaultTask which has no throughput requirements
            gym_env: FactorioGymEnv = gym.make(gym_env_id, run_idx=run_idx)
            gym_env.reset()

            logger.info("🎮 Connected to Factorio server")

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            base_system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)

            # Unbounded task instructions - no quota, maximize everything
            task_instructions = f"""
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

            # Combine base instructions with task-specific instructions
            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin building your factory step by step."""

            # Initialize conversation with proper system prompt
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
            logger.info(f"📈 Starting {trajectory_length}-step unbounded execution...")

            # Trajectory execution
            production_scores = []
            step_results = []

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
                    step_content = f"""## Step {step + 1}/{trajectory_length} - Game State Analysis

Current production score: {current_score:.1f} (maximize this!)
Progress: {(step / trajectory_length) * 100:.1f}% of trajectory complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to expand and improve your factory. Focus on actions that will increase your production score."""

                    step_message = ChatMessageUser(content=step_content)
                    state.messages.append(step_message)

                    # Generate response using Inspect's model
                    generation_config = {
                        "max_tokens": 4096,
                        "transforms": ["middle-out"],
                        # "reasoning_effort": "minimal",
                    }

                    state.output = await get_model().generate(
                        input=state.messages,
                        config=generation_config,
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
                        gym_env.clear_enemies()
                    except Exception as ee:
                        logger.warning(f"Environment error: {ee}")
                        state.messages.append(
                            ChatMessageUser(content=f"Environment error: {ee}")
                        )
                        continue

                    # Log execution details
                    logger.info(
                        f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}"
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
- Reward this step: {reward}

**Performance Results:**
- Total production score: {production_score:.1f} (was {current_score:.1f})
- Score increase: {production_score - current_score:+.1f}

**Flows**
{flow}

Continue to step {step + 2}."""

                    logger.debug(str(obs))

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

                    # Create feedback message with both image and text
                    if updated_image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=updated_image_data_url),
                                ContentText(text=feedback_content),
                            ]
                        )
                        logger.info(f"🖼️  Step {step + 1}:")
                    else:
                        feedback_message = ChatMessageUser(content=feedback_content)
                        logger.info(f"📝 Step {step + 1}:")

                    state.messages.append(feedback_message)

                    # Trim messages if we have too many (keep system prompt)
                    if len(state.messages) > 25:
                        if (
                            len(state.messages) > 0
                            and state.messages[0].role == "system"
                        ):
                            system_message = state.messages[0]
                            recent_messages = state.messages[-24:]
                            state.messages = [system_message] + recent_messages
                            logger.info(
                                f"🧹 Trimmed conversation to {len(state.messages)} messages"
                            )
                        else:
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

                    # Apply intermediate scoring for real-time metrics tracking
                    try:
                        from fle.eval.inspect_integration.scorers import (
                            apply_unbounded_intermediate_scoring,
                        )

                        await apply_unbounded_intermediate_scoring(
                            state=state,
                            step_num=step + 1,
                            production_score=production_score,
                            scores_history=production_scores,
                        )
                    except Exception as scoring_error:
                        logger.warning(
                            f"Intermediate scoring error at step {step + 1}: {scoring_error}"
                        )

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
                    feedback_message = ChatMessageUser(
                        content=f"❌ Step {step + 1} error: {step_error}"
                    )
                    state.messages.append(feedback_message)
                    # Continue with next step rather than failing completely

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            # Store final results using typed store
            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores

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
