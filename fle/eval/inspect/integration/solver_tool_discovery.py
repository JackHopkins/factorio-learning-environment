"""Tool-discovery solver: the agent is not given the API manual up front.

Every other solver injects the full SystemPromptGenerator manual into the
system prompt and ablates observations/images. This solver inverts that:
a minimal system prompt plus Inspect-native tools that let the agent look
the rules up itself (the same content the MCP server exposes via ls/man),
so the cost of acquiring the rules becomes part of the measured behavior.

Budget semantics: only `run_code` calls count against trajectory_length.
Reading manuals and observing are free actions, so scores stay comparable
with the controlled solver's step budget; the discovery cost shows up as
extra tokens and wall-clock, not lost game actions.
"""

import importlib.resources
import logging
from pathlib import Path

import gymnasium as gym
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    get_model,
    execute_tools,
)
from inspect_ai.agent import AgentState
from inspect_ai.solver import solver
from inspect_ai.tool import tool
from inspect_ai.util import store_as

from fle.env.gym_env.action import Action
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import TreeObservationFormatter
from fle.env.gym_env.registry import get_environment_info
from fle.eval.inspect.integration.simple_server_pool import get_simple_server_pool
from fle.eval.inspect.integration.solver import TrajectoryData

logger = logging.getLogger(__name__)

AGENT_TOOLS_DIR = Path(
    str(importlib.resources.files("fle") / "env" / "tools" / "agent")
)

SYSTEM_PROMPT = """You control a character in a Factorio world by writing Python programs.

You have NOT been given the API documentation. Discover it with your tools:
- list_methods() lists every method in the environment API
- manual(method) returns the full documentation for one method
- observe() shows your inventory, position, and nearby entities (free)
- run_code(code) executes a Python program in the environment and returns \
the resulting game state (counts against your step budget)

Goal: {goal}

You have {budget} run_code calls. Reading manuals and observing are free.
Read the manuals for methods before using them; API misuse wastes steps.
Programs run in a persistent namespace: variables survive between run_code calls."""


def _format_observation(observation: Observation) -> str:
    formatted = TreeObservationFormatter(
        include_research=False, include_flows=False
    ).format(observation)
    return formatted.raw_str.replace("\\n", "\n")


def _make_tools(gym_env: FactorioGymEnv, trajectory: TrajectoryData, budget: int):
    """Build per-sample tool closures over the live gym environment."""

    @tool
    def list_methods():
        async def execute() -> str:
            """List every method available in the environment API."""
            names = sorted(
                p.name
                for p in AGENT_TOOLS_DIR.iterdir()
                if p.is_dir() and (p / "agent.md").exists()
            )
            return "\n".join(names)

        return execute

    @tool
    def manual():
        async def execute(method: str) -> str:
            """Return the full documentation for one API method.

            Args:
                method: Name of the method, as returned by list_methods().
            """
            doc = AGENT_TOOLS_DIR / method / "agent.md"
            if not doc.exists():
                return (
                    f"No such method: {method}. Use list_methods() to see valid names."
                )
            return doc.read_text()

        return execute

    @tool
    def observe():
        async def execute() -> str:
            """Show current inventory, position, and nearby entities. Free."""
            observation = gym_env.get_observation()
            return _format_observation(observation)

        return execute

    @tool
    def run_code():
        async def execute(code: str) -> str:
            """Execute a Python program in the environment.

            Counts against the step budget. The namespace persists between
            calls. Returns program output and the updated game state.

            Args:
                code: Python source using the environment API.
            """
            if trajectory.total_steps >= budget:
                return "Step budget exhausted. No more run_code calls are allowed."

            action = Action(agent_idx=0, code=code)
            obs, reward, terminated, truncated, info = gym_env.step(action)
            trajectory.total_steps += 1

            score = obs.get("score") or 0.0
            trajectory.current_score = score
            trajectory.production_score = score

            program_output = (info.get("result") if info else "") or "(no output)"

            observation = gym_env.get_observation()
            remaining = budget - trajectory.total_steps
            return (
                f"[step {trajectory.total_steps}/{budget}, "
                f"production score {score:.1f}]\n\n"
                f"Program output (STDOUT/STDERR):\n"
                f"```\n{program_output}\n```\n\n"
                f"Game state:\n{_format_observation(observation)}\n"
                f"({remaining} run_code calls remaining)"
            )

        return execute

    return [list_methods(), manual(), observe(), run_code()]


def _trim_messages(messages, keep_last: int = 40):
    """Keep the system prompt, the opening user message, and the recent tail."""
    if len(messages) <= keep_last + 2:
        return messages
    return messages[:2] + messages[-keep_last:]


@solver
def factorio_tool_discovery_solver():
    """Solver where the agent discovers the API through tools instead of the prompt."""

    async def solve(state: AgentState, *args, **kwargs) -> AgentState:
        run_idx = None
        gym_env = None
        pool = None

        try:
            metadata = getattr(state, "metadata", {}) or {}
            env_id = metadata.get("env_id", "iron_ore_throughput")
            budget = int(metadata.get("trajectory_length", 64))

            pool = await get_simple_server_pool()
            allocation = await pool.get_server_allocation()
            run_idx = allocation.run_idx
            logger.info(f"tool_discovery: allocated server factorio_{run_idx}")

            gym_env = gym.make(env_id, disable_env_checker=True, run_idx=run_idx)
            gym_env.reset()

            env_info = get_environment_info(env_id) or {}
            goal = env_info.get("description", f"complete the task {env_id}")

            trajectory = store_as(TrajectoryData)
            tools = _make_tools(gym_env, trajectory, budget)

            messages = [
                ChatMessageSystem(
                    content=SYSTEM_PROMPT.format(goal=goal, budget=budget)
                ),
                ChatMessageUser(
                    content="Begin. Discover the API, then work toward the goal."
                ),
            ]

            # Free tool calls (manuals, observe) mean more generations than
            # steps; cap generations so a model that never acts still halts.
            max_generations = budget * 3
            generations = 0

            while trajectory.total_steps < budget and generations < max_generations:
                generations += 1
                output = await get_model().generate(
                    input=_trim_messages(messages),
                    tools=tools,
                    config=GenerateConfig(max_tokens=4096),
                )
                messages.append(output.message)

                if output.message.tool_calls:
                    result = await execute_tools(messages, tools)
                    messages.extend(result.messages)
                else:
                    messages.append(
                        ChatMessageUser(
                            content="Use your tools: read manuals, observe, or run_code."
                        )
                    )

            trajectory.final_score = trajectory.current_score
            trajectory.final_automated_score = trajectory.automated_production_score
            logger.info(
                f"tool_discovery: finished with score {trajectory.final_score:.1f} "
                f"after {trajectory.total_steps} steps / {generations} generations"
            )

            state.messages = messages
            state.output = output if generations else state.output
            return state

        finally:
            if gym_env is not None:
                try:
                    gym_env.close()
                except Exception:
                    pass
            if pool is not None and run_idx is not None:
                await pool.release_run_idx(run_idx)
                logger.info(f"tool_discovery: released server factorio_{run_idx}")

    return solve
