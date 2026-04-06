"""Sandbox solvers that use Inspect's sandbox().exec() to run Factorio inside containers.

Contains two solvers:
- factorio_sandbox_controlled_solver: For throughput tasks with specific quotas
- factorio_sandbox_unbounded_solver: For open-play tasks tracking cumulative production score

Both communicate with the in-container bridge_service.py via bridge_client.py CLI.
"""

import json
import logging
import os
import time
import traceback
from pathlib import Path

from inspect_ai.scorer import score
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
from inspect_ai.util import store_as, sandbox

from jinja2 import Template

from fle.eval.inspect.integration.solver import (
    TrajectoryData,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.agents.llm.parsing import parse_response
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import TreeObservationFormatter

logger = logging.getLogger(__name__)

BRIDGE_CMD = ["python3", "/opt/fle/bridge_client.py"]


def _load_prompt_template(filename: str) -> Template:
    """Load a Jinja2 prompt template from the prompts directory."""
    prompt_path = Path(__file__).parent.parent / "integration" / "prompts" / filename
    return Template(prompt_path.read_text())


async def _bridge_exec(
    command: str,
    body: dict = None,
    timeout: int = 300,
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> dict:
    """Execute a bridge client command inside the sandbox container.

    Returns parsed JSON response. Retries with exponential backoff on
    "busy" errors (the bridge is single-threaded and rejects concurrent
    requests). Raises on non-retryable failures.
    """
    args = list(BRIDGE_CMD) + [command]
    if body is not None:
        args.append(json.dumps(body))

    last_error = None
    for attempt in range(max_retries + 1):
        result = await sandbox().exec(args, timeout=timeout)

        if result.success:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Bridge command '{command}' returned invalid JSON: {e}\n"
                    f"stdout={result.stdout[:500]}"
                )

        # Check if the failure is a "busy" error that's worth retrying
        stdout_lower = (result.stdout or "").lower()
        is_busy = "already busy" in stdout_lower or "busy with another" in stdout_lower

        if not is_busy or attempt == max_retries:
            raise RuntimeError(
                f"Bridge command '{command}' failed (rc={result.returncode}): "
                f"stdout={result.stdout[:500]}, stderr={result.stderr[:500]}"
            )

        delay = base_delay * (2 ** attempt)
        logger.warning(
            "Bridge busy on '%s' (attempt %d/%d), retrying in %.1fs...",
            command,
            attempt + 1,
            max_retries,
            delay,
        )
        last_error = result.stdout[:200]
        await _async_sleep(delay)


async def _wait_for_bridge(timeout: int = 180):
    """Wait for the bridge service to become ready."""
    logger.info("Waiting for bridge service readiness...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = await _bridge_exec("health", timeout=10)
            if resp.get("status") == "ok":
                logger.info("Bridge service is ready.")
                return
        except Exception:
            pass
        await _async_sleep(2)
    raise RuntimeError(f"Bridge service not ready after {timeout}s")


async def _async_sleep(seconds):
    """Async sleep helper."""
    import asyncio

    await asyncio.sleep(seconds)


# ===========================================================================
# Controlled solver (throughput tasks)
# ===========================================================================


@solver
def factorio_sandbox_controlled_solver():
    """Controlled solver using Inspect sandbox - runs exactly N steps for throughput tasks."""

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        try:
            # Get configuration from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "iron_ore_throughput")
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 64)

            logger.info(
                "Starting sandbox controlled solver for %s (%d steps)",
                env_id,
                trajectory_length,
            )

            # Wait for bridge to be ready
            await _wait_for_bridge()

            # Reset the environment
            await _bridge_exec("reset")

            # Get system prompt from container
            prompt_resp = await _bridge_exec("system-prompt")
            base_system_prompt = prompt_resp["system_prompt"]

            # Build task-specific instructions
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

            full_system_prompt = f"""{base_system_prompt}

{task_instructions}

Now begin working toward this objective step by step."""

            # Initialize conversation
            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )
            state.messages = [ChatMessageSystem(content=full_system_prompt)]

            logger.info("Task: %s, Quota: %s", goal_description, quota)

            # Vision mode
            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"

            # Step tracking
            production_scores = []
            step_results = []
            game_ticks = []
            previous_feedback_content = f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
            previous_feedback_image = None

            for step in range(trajectory_length):
                step_start = time.time()

                try:
                    # Get observation from container
                    obs_dict = await _bridge_exec("observe")
                    observation = Observation.from_dict(obs_dict)

                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                    ).format(observation)

                    # Build step message
                    current_score = production_scores[-1] if production_scores else 0
                    game_state_str = obs_formatted.raw_str.replace("\\n", "\n")
                    step_content = f"""\n\n## Step {step + 1}/{trajectory_length} - Game State Analysis

Current production score: {current_score:.1f}/{quota}
Progress: {(step / trajectory_length) * 100:.1f}% complete

**Current Game State:**
{game_state_str}

**Next Action Required:**
Analyze the current state and write a Python program using the FLE API to progress toward the production goal."""

                    # Combine previous feedback with current step content
                    if previous_feedback_content is not None:
                        combined_content = (
                            f"{previous_feedback_content}\n\n---\n\n{step_content}"
                        )
                        if (
                            previous_feedback_image
                            and isinstance(previous_feedback_image, str)
                            and previous_feedback_image.startswith("data:")
                        ):
                            step_message = ChatMessageUser(
                                content=[
                                    ContentImage(image=previous_feedback_image),
                                    ContentText(text=combined_content),
                                ]
                            )
                        else:
                            step_message = ChatMessageUser(content=combined_content)
                        previous_feedback_content = None
                        previous_feedback_image = None
                    else:
                        step_message = ChatMessageUser(content=step_content)

                    state.messages.append(step_message)

                    # Generate LLM response (host-side)
                    generation_config = {
                        "max_tokens": 4096,
                        "transforms": ["middle-out"],
                        "reasoning_effort": "minimal",
                    }
                    state.output = await get_model().generate(
                        input=state.messages,
                        config=generation_config,
                    )
                    state.messages.append(state.output.message)

                    # Parse program from response
                    program = parse_response(state.output)
                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        "Step %d: Generated %d char program",
                        step + 1,
                        len(program.code),
                    )

                    # Execute program INSIDE container
                    exec_result = await _bridge_exec(
                        "execute",
                        {"code": program.code, "agent_idx": 0},
                        timeout=180,
                    )

                    # Process execution results
                    program_output = exec_result.get("result", "No output captured")
                    production_score = exec_result.get("production_score", 0)
                    production_scores.append(production_score)
                    reward = exec_result.get("reward", 0)
                    terminated = exec_result.get("terminated", False)
                    truncated = exec_result.get("truncated", False)
                    flows_formatted = exec_result.get("flows_formatted", "")
                    current_ticks = exec_result.get("ticks", 0)

                    # Record game ticks
                    previous_ticks = game_ticks[-1] if game_ticks else 0
                    ticks_cost = current_ticks - previous_ticks
                    game_ticks.append(current_ticks)

                    # Format elapsed time
                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "No code was submitted. Write code in ``` blocks."
                            if not program.code
                            else "None"
                        )

                    # Build feedback message
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
{flows_formatted}

Continue to step {step + 2}."""

                    # Get screenshot if vision enabled
                    updated_image_data_url = None
                    if vision_enabled:
                        try:
                            screenshot_resp = await _bridge_exec(
                                "screenshot", timeout=30
                            )
                            updated_image_data_url = screenshot_resp.get("base64")
                        except Exception as img_err:
                            logger.warning("Screenshot failed: %s", img_err)

                    previous_feedback_content = feedback_content
                    previous_feedback_image = updated_image_data_url

                    # Trim messages
                    if len(state.messages) > 25:
                        if state.messages and state.messages[0].role == "system":
                            system_message = state.messages[0]
                            state.messages = [system_message] + state.messages[-24:]
                            logger.info(
                                "Trimmed conversation to %d messages",
                                len(state.messages),
                            )

                    step_time = time.time() - step_start
                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "program_content": (
                            program.code[:200] + "..."
                            if len(program.code) > 200
                            else program.code
                        ),
                        "program_output": (
                            str(program_output)[:200] + "..."
                            if len(str(program_output)) > 200
                            else str(program_output)
                        ),
                    }
                    step_results.append(step_result)

                    logger.info(
                        "Step %d/%d: Score=%.1f, Time=%.1fs",
                        step + 1,
                        trajectory_length,
                        production_score,
                        step_time,
                    )

                    # Store intermediate progress
                    trajectory_data = store_as(TrajectoryData)
                    trajectory_data.production_score = production_score
                    trajectory_data.current_score = production_score
                    trajectory_data.total_steps = step + 1
                    trajectory_data.steps = step_results
                    trajectory_data.scores = production_scores
                    trajectory_data.ticks = game_ticks

                    # Apply intermediate scoring
                    try:
                        from fle.eval.inspect.integration.scorers import (
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
                        logger.warning("Intermediate scoring error: %s", scoring_error)

                    if terminated or truncated:
                        logger.info("Episode ended at step %d", step + 1)
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error("Step %d error: %s", step + 1, step_error)
                    previous_feedback_content = f"Step {step + 1} error: {step_error}"
                    previous_feedback_image = None

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.production_score = final_score
            trajectory_data.final_score = final_score
            trajectory_data.total_steps = len(step_results)
            trajectory_data.steps = step_results
            trajectory_data.scores = production_scores
            trajectory_data.ticks = game_ticks

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step trajectory with final score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                "Controlled trajectory complete: %.1f score after %d steps",
                final_score,
                len(step_results),
            )

        except Exception as e:
            error_msg = (
                f"Sandbox controlled solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in controlled trajectory: {error_msg}",
                model=metadata.get("model", "unknown") if metadata else "unknown",
            )

        return state

    return solve


# ===========================================================================
# Unbounded solver (open-play tasks)
# ===========================================================================


@solver
def factorio_sandbox_unbounded_solver():
    """Unbounded sandbox solver for open-play tasks tracking cumulative production score.

    Unlike the controlled solver:
    - Uses cumulative production score (total economic value)
    - No quota or target - maximize production
    - Designed for long trajectories (5000+ steps)
    - Error recovery via game state rollback
    """

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        try:
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            env_id = metadata.get("env_id", "open_play_production")
            model_name = metadata.get("model", "openai/gpt-4o-mini")
            trajectory_length = metadata.get("trajectory_length", 5000)
            goal_description = metadata.get(
                "goal_description",
                "Achieve the highest automatic production score rate",
            )
            vision_enabled = os.environ.get("FLE_VISION", "").lower() == "true"

            logger.info(
                "Starting sandbox unbounded solver for %s (%d steps)",
                env_id,
                trajectory_length,
            )

            # Wait for bridge
            await _wait_for_bridge()

            # Reset environment
            await _bridge_exec("reset")

            # Get system prompt
            prompt_resp = await _bridge_exec("system-prompt")
            base_system_prompt = prompt_resp["system_prompt"]

            system_template = _load_prompt_template("unbounded_system.jinja2.md")
            full_system_prompt = system_template.render(
                base_system_prompt=base_system_prompt
            )

            original_user_message = (
                state.messages[0].content
                if state.messages
                else f"Begin task: {goal_description}"
            )
            state.messages = [ChatMessageSystem(content=full_system_prompt)]

            logger.info("Task: %s", goal_description)

            # Tracking
            production_scores = []
            automated_production_scores = []
            step_results = []
            game_ticks = []
            game_state_raws = []  # For error recovery

            previous_feedback_content = f"{original_user_message}\n\nAnalyze the current game state and begin your first action."
            previous_feedback_image = None

            produced_item_types_set: set = set()
            researched_technologies_set: set = set()

            inference_latencies = []
            env_execution_latencies = []
            policy_execution_latencies = []
            sleep_durations = []
            total_step_latencies = []
            program_codes = []

            for step in range(trajectory_length):
                step_start = time.time()

                try:
                    # Get observation from container
                    obs_dict = await _bridge_exec("observe")
                    observation = Observation.from_dict(obs_dict)

                    obs_formatted = TreeObservationFormatter(
                        include_research=False,
                        include_flows=False,
                    ).format(observation)

                    current_score = production_scores[-1] if production_scores else 0
                    step_template = _load_prompt_template("unbounded_step.jinja2.md")
                    step_content = step_template.render(
                        step=step + 1,
                        trajectory_length=trajectory_length,
                        progress=f"{(step / trajectory_length) * 100:.1f}",
                        game_state=obs_formatted.raw_str.replace("\\n", "\n"),
                    )

                    # Combine previous feedback
                    try:
                        if previous_feedback_content is not None:
                            combined_content = (
                                f"{previous_feedback_content}\n\n---\n\n{step_content}"
                            )
                            if previous_feedback_image is not None:
                                if not isinstance(
                                    previous_feedback_image, str
                                ) or not previous_feedback_image.startswith("data:"):
                                    step_message = ChatMessageUser(
                                        content=combined_content
                                    )
                                else:
                                    step_message = ChatMessageUser(
                                        content=[
                                            ContentImage(image=previous_feedback_image),
                                            ContentText(text=combined_content),
                                        ]
                                    )
                            else:
                                step_message = ChatMessageUser(content=combined_content)
                            previous_feedback_content = None
                            previous_feedback_image = None
                        else:
                            step_message = ChatMessageUser(content=step_content)
                    except Exception as msg_error:
                        logger.error("Error creating step message: %s", msg_error)
                        step_message = ChatMessageUser(content=step_content)
                        previous_feedback_content = None
                        previous_feedback_image = None

                    state.messages.append(step_message)

                    # Generate LLM response (host-side)
                    generation_config = {
                        "reasoning_tokens": 1024 * 4,
                        "cache": CachePolicy(per_epoch=False),
                    }
                    _model = get_model()
                    model_name_str = (
                        getattr(_model, "name", "") if hasattr(_model, "name") else ""
                    )
                    if model_name_str and "openrouter" in model_name_str:
                        generation_config["transforms"] = ["middle-out"]

                    inference_start = time.time()
                    try:
                        state.output = await _model.generate(
                            input=state.messages,
                            config=generation_config,
                        )
                    except Exception as gen_error:
                        logger.error("Model generation error: %s", gen_error)
                        raise
                    inference_time = int(time.time() - inference_start)
                    inference_latencies.append(inference_time)

                    state.messages.append(state.output.message)

                    # Parse program
                    program = parse_response(state.output)
                    if not program:
                        raise Exception(
                            "Could not parse program from model response. "
                            "Be sure to wrap your code in ``` blocks."
                        )

                    logger.info(
                        "Step %d: Generated %d char program",
                        step + 1,
                        len(program.code),
                    )
                    program_codes.append(program.code)

                    # Execute program INSIDE container
                    env_start = time.time()
                    try:
                        exec_result = await _bridge_exec(
                            "execute",
                            {"code": program.code, "agent_idx": 0},
                            timeout=180,
                        )
                    except Exception as ee:
                        logger.warning("Environment error: %s", ee)
                        previous_feedback_content = f"Environment error: {ee}"
                        previous_feedback_image = None
                        # Attempt recovery from last game state
                        if game_state_raws:
                            try:
                                await _bridge_exec(
                                    "reset", {"game_state": game_state_raws[-1]}
                                )
                                logger.warning(
                                    "Reset to previous game state after error"
                                )
                            except Exception:
                                pass
                        continue
                    env_time = time.time() - env_start
                    env_execution_latencies.append(env_time)

                    # Save game state for rollback
                    game_state_raw = exec_result.get("game_state_raw")
                    if game_state_raw:
                        game_state_raws.append(game_state_raw)
                        if len(game_state_raws) > 5:
                            game_state_raws.pop(0)

                    policy_time = exec_result.get("policy_execution_time", 0.0)
                    policy_execution_latencies.append(float(policy_time))
                    sleep_durations.append(
                        0.0
                    )  # Sleep tracking not available through bridge

                    # Process results
                    program_output = exec_result.get("result", "No output captured")
                    production_score = exec_result.get("production_score", 0)
                    production_scores.append(production_score)

                    automated_score = exec_result.get("automated_production_score", 0)
                    automated_production_scores.append(automated_score)

                    flow = exec_result.get("flows", {})
                    flows_formatted = exec_result.get("flows_formatted", "")
                    current_ticks = exec_result.get("ticks", 0)
                    terminated = exec_result.get("terminated", False)
                    truncated = exec_result.get("truncated", False)

                    # Extract item types from flows
                    if isinstance(flow, dict):
                        for key in ("harvested", "output"):
                            for item in flow.get(key, []):
                                if isinstance(item, dict) and "type" in item:
                                    produced_item_types_set.add(item["type"])
                        for craft in flow.get("crafted", []):
                            if isinstance(craft, dict) and "outputs" in craft:
                                produced_item_types_set.update(craft["outputs"].keys())

                    # Extract researched technologies
                    try:
                        for (
                            tech_name,
                            tech_state,
                        ) in observation.research.technologies.items():
                            if tech_state.researched:
                                researched_technologies_set.add(tech_name)
                    except Exception:
                        pass

                    # Game ticks
                    previous_ticks = game_ticks[-1] if game_ticks else 0
                    ticks_cost = current_ticks - previous_ticks
                    game_ticks.append(current_ticks)

                    total_seconds = current_ticks // 60
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    elapsed_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"

                    if not program_output:
                        program_output = (
                            "No code was submitted. Write code in ``` blocks."
                            if not program.code
                            else "None"
                        )

                    # Build feedback
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
                        flows=flows_formatted,
                        next_step=step + 2,
                    )

                    # Screenshot if vision enabled
                    updated_image_data_url = None
                    if vision_enabled:
                        try:
                            screenshot_resp = await _bridge_exec(
                                "screenshot", timeout=30
                            )
                            updated_image_data_url = screenshot_resp.get("base64")
                        except Exception as img_err:
                            logger.warning("Screenshot failed: %s", img_err)

                    previous_feedback_content = feedback_content
                    previous_feedback_image = updated_image_data_url

                    # Trim messages
                    if len(state.messages) > 25:
                        if state.messages and state.messages[0].role == "system":
                            system_message = state.messages[0]
                            state.messages = [system_message] + state.messages[-16:]
                            logger.info(
                                "Trimmed conversation to %d messages",
                                len(state.messages),
                            )

                    step_time = time.time() - step_start
                    total_step_latencies.append(step_time)

                    step_result = {
                        "step": step + 1,
                        "production_score": production_score,
                        "program_length": len(program.code),
                        "execution_time": step_time,
                        "program_content": (
                            program.code[:200] + "..."
                            if len(program.code) > 200
                            else program.code
                        ),
                        "program_output": (
                            str(program_output)[:200] + "..."
                            if len(str(program_output)) > 200
                            else str(program_output)
                        ),
                        "inference_latency": inference_time,
                        "env_execution_latency": env_time,
                        "policy_execution_latency": policy_time,
                        "sleep_duration": 0.0,
                    }
                    step_results.append(step_result)

                    logger.info(
                        "Step %d/%d: Score=%.1f, Time=%.1fs",
                        step + 1,
                        trajectory_length,
                        production_score,
                        step_time,
                    )

                    # Store intermediate progress
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
                    trajectory_data.inference_latencies = inference_latencies
                    trajectory_data.env_execution_latencies = env_execution_latencies
                    trajectory_data.policy_execution_latencies = (
                        policy_execution_latencies
                    )
                    trajectory_data.sleep_durations = sleep_durations
                    trajectory_data.total_step_latencies = total_step_latencies
                    trajectory_data.program_codes = program_codes

                    # Apply scoring
                    await score(state)

                    if terminated or truncated:
                        logger.info("Episode ended at step %d", step + 1)
                        state.complete = True
                        break

                except Exception as step_error:
                    logger.error("Step %d error: %s", step + 1, step_error)
                    previous_feedback_content = f"Step {step + 1} error: {step_error}"
                    previous_feedback_image = None

            # Final results
            final_score = production_scores[-1] if production_scores else 0.0
            final_automated_score = (
                automated_production_scores[-1] if automated_production_scores else 0.0
            )

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
            trajectory_data.inference_latencies = inference_latencies
            trajectory_data.env_execution_latencies = env_execution_latencies
            trajectory_data.policy_execution_latencies = policy_execution_latencies
            trajectory_data.sleep_durations = sleep_durations
            trajectory_data.total_step_latencies = total_step_latencies
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
                logger.info(
                    "Latency summary: avg_total=%.2fs, avg_inference=%.2fs, avg_env=%.2fs",
                    avg_total,
                    avg_inference,
                    avg_env,
                )

            state.output = ModelOutput(
                completion=f"Completed {len(step_results)}-step unbounded trajectory with final production score: {final_score:.1f}",
                model=model_name,
            )

            logger.info(
                "Unbounded trajectory complete: %.1f production score after %d steps",
                final_score,
                len(step_results),
            )

        except Exception as e:
            error_msg = (
                f"Sandbox unbounded solver error: {str(e)}\n{traceback.format_exc()}"
            )
            logger.error(error_msg)

            trajectory_data = store_as(TrajectoryData)
            trajectory_data.error = error_msg
            trajectory_data.production_score = 0.0
            trajectory_data.final_score = 0.0

            state.output = ModelOutput(
                completion=f"Error in unbounded trajectory: {error_msg}",
                model=metadata.get("model", "unknown") if metadata else "unknown",
            )

        return state

    return solve
