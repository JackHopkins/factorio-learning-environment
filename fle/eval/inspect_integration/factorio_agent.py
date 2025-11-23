"""Custom Inspect Agent that wraps FLE GymAgent for full trajectory execution."""

import asyncio
import logging
import time
import traceback

from inspect_ai.agent import Agent, agent, AgentState
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    ModelOutput,
    get_model,
    ContentImage,
    ContentText,
)
# Remove store_as import since it was causing issues

from fle.agents.gym_agent import GymAgent
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.gym_env.registry import get_environment_info
from fle.eval.tasks import TaskFactory
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)

from fle.eval.inspect_integration.simple_server_pool import get_simple_server_pool
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.agents.llm.parsing import parse_response
from fle.eval.inspect_integration.image_utils import rendered_image_to_data_url

import importlib.resources
import gym

logger = logging.getLogger(__name__)


@agent
def factorio_trajectory_agent() -> Agent:
    """Custom Inspect Agent that runs full Factorio trajectory with step-by-step logging"""

    async def execute(state: AgentState) -> AgentState:
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

            logger.info(f"🚀 Starting Factorio trajectory agent for {env_id}")
            logger.info(
                f"🎯 Target: {trajectory_length} steps using model {model_name}"
            )

            # Use simple store access instead of typed store
            # store = store_as(state, FactorioStore)  # This was causing the callable error

            # Get server allocation
            pool = await get_simple_server_pool()
            run_idx = await pool.get_run_idx()
            logger.info(f"📡 Allocated server factorio_{run_idx}")

            # Create gym environment
            gym_env = gym.make(env_id, run_idx=run_idx)
            gym_env.reset()
            logger.info("🎮 Connected to Factorio server")

            # Get task configuration
            env_info = get_environment_info(env_id)
            if not env_info:
                raise ValueError(f"No environment info for {env_id}")

            task = TaskFactory.create_task(env_info["task_config_path"])

            # Generate system prompt
            generator = SystemPromptGenerator(
                str(importlib.resources.files("fle") / "env")
            )
            system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)

            # Create GymAgent
            gym_agent = GymAgent(
                model=model_name,
                system_prompt=system_prompt,
                task=task,
                agent_idx=0,
                observation_formatter=BasicObservationFormatter(include_research=False),
                system_prompt_formatter=SystemPromptFormatter(),
            )

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
- Ensure continuous operation without manual intervention

## IMPORTANT NOTES
- You have {trajectory_length} steps to complete this task
- Each step should make meaningful progress toward the goal
- Focus on essential infrastructure first (mining, smelting, power)
- Then build the specific production chain required
- YOU MUST WRITE PYTHON CODE ENCLOSED IN ``` BLOCKS!
"""
            else:
                goal_description = (
                    f"Create an automatic {env_id.replace('_', '-')} factory"
                )
                task_instructions = f"## TASK OBJECTIVE\n{goal_description}"

            # Combine base instructions with task-specific instructions
            full_system_prompt = f"""{system_prompt}

{task_instructions}

Now begin working toward this objective step by step."""

            # Initialize conversation with proper system prompt
            # Replace any existing messages with our structured conversation
            original_user_message = (
                state.messages[0]
                if state.messages
                else ChatMessageUser(content=f"Begin task: {goal_description}")
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
            logger.info(
                f"💬 Conversation initialized with {len(state.messages)} messages"
            )

            logger.info(f"📋 System prompt: {len(full_system_prompt)} chars")
            logger.info(f"🎯 Task: {goal_description}")
            logger.info(f"📊 Quota: {quota} items per 60 seconds")

            # Run agentic trajectory loop using Inspect's proper agent protocol
            production_scores = []
            step_results = []
            step = 0

            logger.info(f"🎯 Starting {trajectory_length}-step agentic trajectory...")

            # Main agentic loop - using while loop as recommended by Inspect docs
            while step < trajectory_length:
                step_start = time.time()

                try:
                    # Get current observation from Factorio
                    observation: Observation = gym_env.get_observation()

                    obs_formatted = gym_agent.observation_formatter.format(observation)

                    # Create user message with current game state including visual
                    current_score = production_scores[-1] if production_scores else 0
                    step_text_content = f"""## Step {step + 1}/{trajectory_length} - Game State Analysis

Current production score: {current_score:.1f}/{quota}
Progress: {(step / trajectory_length) * 100:.1f}% complete

**Current Game State:**
{obs_formatted.raw_str.replace("\\n", "\n")}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to progress toward the production goal. Focus on one specific improvement or setup task."""

                    # Try to get rendered image
                    image_data_url = get_rendered_image(gym_env)

                    # Create message content with both image and text
                    if image_data_url:
                        step_message = ChatMessageUser(
                            content=[
                                ContentImage(image=image_data_url),
                                ContentText(text=step_text_content),
                            ]
                        )
                        logger.info(
                            f"🖼️  Step {step + 1}: Including rendered image in conversation"
                        )
                    else:
                        step_message = ChatMessageUser(content=step_text_content)
                        logger.info(
                            f"📝 Step {step + 1}: Text-only message (no image available)"
                        )

                    state.messages.append(step_message)

                    # Generate response using Inspect's model
                    state.output = await get_model().generate(
                        input=state.messages,
                        config={"max_tokens": 1500, "temperature": 0.1},
                    )

                    # Add model response to conversation
                    state.messages.append(state.output.message)

                    # Extract Python program from the model response using FLE parsing
                    program = parse_response(state.output)

                    logger.info(
                        f"📝 Step {step + 1}: Generated {len(program.code)} char program"
                    )

                    # Execute action in Factorio
                    action = Action(agent_idx=0, code=program.code)
                    obs, reward, terminated, truncated, info = gym_env.step(action)

                    # Log execution info for debugging
                    logger.info(
                        f"🎮 Step {step + 1}: reward={reward}, terminated={terminated}, info_keys={list(info.keys()) if info else 'None'}"
                    )

                    # Get the new observation after the action to show the agent what happened
                    post_action_observation: Observation = gym_env.get_observation()
                    post_action_formatted = gym_agent.observation_formatter.format(
                        post_action_observation
                    )

                    # Extract the program execution output (STDOUT/STDERR)
                    # program_output = post_action_observation.raw_text if hasattr(post_action_observation, 'raw_text') else "No output captured"
                    program_output = info["result"]
                    # Calculate production score
                    production_score = calculate_production_score(gym_env, task)
                    production_scores.append(production_score)

                    # Add comprehensive feedback showing program execution results with updated image
                    feedback_text_content = f"""## Step {step + 1} Execution Results
**Program Output (STDOUT/STDERR):**
```
{program_output}
```

**Performance Results:**
- Production score: {production_score:.1f} (was {current_score:.1f})  
- Score change: {production_score - current_score:+.1f}

**Updated Game State:**
{post_action_formatted.raw_str.replace("\\n", "\n") if hasattr(post_action_formatted, "raw_str") else str(post_action_formatted)}

Analyze these results and plan your next action to improve the factory."""

                    # Get updated rendered image after the action
                    updated_image_data_url = (
                        post_action_observation.map_image
                    )  # get_rendered_image(gym_env)

                    # Create feedback message with both image and text
                    if updated_image_data_url:
                        feedback_message = ChatMessageUser(
                            content=[
                                ContentImage(image=updated_image_data_url),
                                ContentText(text=feedback_text_content),
                            ]
                        )
                        logger.info(f"🖼️  Step {step + 1}:")
                    else:
                        feedback_message = ChatMessageUser(
                            content=feedback_text_content
                        )
                        logger.info(f"📝 Step {step + 1}:")

                    state.messages.append(feedback_message)

                    step_time = time.time() - step_start
                    step += 1

                    step_result = {
                        "step": step,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "program_content": program.code[:200] + "..."
                        if len(program.code) > 200
                        else program.code,
                    }
                    step_results.append(step_result)

                    logger.info(
                        f"✅ Step {step}/{trajectory_length}: Score={production_score:.1f}, Time={step_time:.1f}s"
                    )

                    # Store intermediate progress in Inspect store
                    # Store intermediate progress in Inspect store
                    if hasattr(state, "store"):
                        state.store.set("production_score", production_score)
                        state.store.set(
                            "trajectory_data",
                            {
                                "steps": step_results,
                                "total_steps": step,
                                "current_score": production_score,
                            },
                        )

                except asyncio.TimeoutError:
                    logger.error(f"❌ Step {step + 1} timed out")
                    break

                except Exception as step_error:
                    logger.error(
                        f"❌ Step {step + 1} error: {step_error}\n{traceback.format_exc()}"
                    )
                    step += 1  # Continue to next step
                    if step >= trajectory_length:
                        break

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0
            achievements = (
                gym_env.get_achievements()
                if hasattr(gym_env, "get_achievements")
                else {}
            )

            # Store final results in Inspect store
            if hasattr(state, "store"):
                state.store.set("production_score", final_score)
                state.store.set("achievements", achievements)
                state.store.set(
                    "trajectory_data",
                    {
                        "steps": step_results,
                        "total_steps": len(step_results),
                        "final_score": final_score,
                        "scores": production_scores,
                    },
                )

            # Set final model output
            state.output = ModelOutput(
                completion=f"Trajectory completed: {len(step_results)} steps, final score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                f"🎉 Trajectory complete: {final_score:.1f} score after {len(step_results)} steps"
            )

        except Exception as e:
            error_msg = f"Trajectory agent error: {str(e)}"
            logger.error(error_msg)

            if hasattr(state, "store"):
                state.store.set("error", error_msg)
                state.store.set("production_score", 0.0)

            state.output = ModelOutput(
                completion=f"Error in trajectory: {error_msg}",
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

    return execute


def get_rendered_image(gym_env: FactorioGymEnv) -> str:
    """Get rendered image as data URL from gym environment"""
    try:
        # Get the current game state as a blueprint-like structure
        # if hasattr(gym_env, 'namespace') and hasattr(gym_env.namespace, '_render'):
        #     # Get entities for rendering
        #     entities = []
        #     if hasattr(gym_env, 'get_entities'):
        #         entities = gym_env.get_entities()
        #     elif hasattr(gym_env, 'get_observation'):
        #         obs = gym_env.get_observation()
        #         if hasattr(obs, 'entities'):
        #             entities = obs.entities
        #
        #     # Create a minimal blueprint structure for rendering
        #     #blueprint = {"entities": entities} if entities else {}
        #
        # Render the image
        rendered_image = gym_env.namespaces._render()

        # Convert to data URL
        return rendered_image_to_data_url(rendered_image)
    except Exception as e:
        logger.warning(f"Could not render image: {e}")
        return None

    return None


def calculate_production_score(gym_env: FactorioGymEnv, task) -> float:
    """Calculate production score from gym environment"""
    try:
        # Use existing scoring logic
        if hasattr(gym_env, "get_production_score"):
            return gym_env.get_production_score()

        # Last resort
        return 0.0

    except Exception as e:
        logger.error(f"Error calculating production score: {e}")
        return 0.0
