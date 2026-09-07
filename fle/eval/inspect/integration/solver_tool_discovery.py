"""Tool-discovery solver: the agent is not given the API manual up front.

Every other solver injects the full SystemPromptGenerator manual into the
system prompt and streams the entire game state back after every step.
This solver inverts both: a minimal system prompt, and a set of
Inspect-native tools through which the agent pulls what it needs —
documentation (list_methods/manual), state (entities/inventory/summary),
its objective (task), and execution (run_code). run_code returns only the
program's own STDOUT/STDERR; observing the world is a deliberate,
separate act.

Budget semantics: only `run_code` calls count against trajectory_length.
Documentation and state queries are free, so scores stay comparable with
the controlled solver's step budget; the discovery cost shows up as
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
from fle.env.gym_env.registry import get_environment_info
from fle.eval.inspect.integration.simple_server_pool import get_simple_server_pool
from fle.eval.inspect.integration.solver import TrajectoryData
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS

logger = logging.getLogger(__name__)

AGENT_TOOLS_DIR = Path(
    str(importlib.resources.files("fle") / "env" / "tools" / "agent")
)

SYSTEM_PROMPT = """You control a character in a Factorio world by writing Python programs.

You have NOT been given the API documentation or the game state. Pull what
you need through your tools:

Documentation (free):
- list_methods() lists every method in the environment API
- manual(method) returns the full documentation for one method

State (free):
- task() shows your objective, current score, and remaining step budget
- entities() lists entities on the map
- inventory() shows what you are carrying
- summary() gives a one-glance situational overview

Action (budgeted):
- run_code(code) executes a Python program in the environment and returns
  its STDOUT/STDERR. You have {budget} run_code calls.

The Python namespace persists between run_code calls. Read the manual for a
method before using it; API misuse wastes budget. Check state deliberately —
run_code will not echo the world back at you."""


def _make_tools(
    gym_env: FactorioGymEnv, trajectory: TrajectoryData, budget: int, task_meta: dict
):
    """Build per-sample tool closures over the live gym environment."""
    ns = (
        gym_env.unwrapped.instance.namespace
        if hasattr(gym_env, "unwrapped")
        else gym_env.instance.namespace
    )

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
    def task():
        async def execute() -> str:
            """Show the objective, target quota, current score, and remaining budget."""
            return (
                f"Objective: {task_meta['goal']}\n"
                f"Target: {task_meta['quota']}\n"
                f"Current production score: {trajectory.current_score:.1f}\n"
                f"run_code calls used: {trajectory.total_steps}/{budget}"
            )

        return execute

    @tool
    def entities():
        async def execute() -> str:
            """List the entities currently on the map."""
            found = ns.get_entities()
            if not found:
                return "No entities on the map yet."
            return "\n".join(repr(e) for e in found)

        return execute

    @tool
    def inventory():
        async def execute() -> str:
            """Show the contents of your inventory."""
            inv = ns.inspect_inventory()
            items = dict(inv.items()) if hasattr(inv, "items") else dict(inv)
            if not items:
                return "Inventory is empty."
            return "\n".join(
                f"{name}: {count}" for name, count in sorted(items.items())
            )

        return execute

    @tool
    def summary():
        async def execute() -> str:
            """One-glance overview: position, score, budget, entity and item counts."""
            found = ns.get_entities()
            inv = ns.inspect_inventory()
            items = dict(inv.items()) if hasattr(inv, "items") else dict(inv)
            pos = getattr(ns, "player_location", None)
            return (
                f"Position: {pos}\n"
                f"Production score: {trajectory.current_score:.1f} (target {task_meta['quota']})\n"
                f"run_code budget: {budget - trajectory.total_steps} of {budget} remaining\n"
                f"Entities on map: {len(found)}\n"
                f"Inventory: {sum(items.values())} items across {len(items)} types"
            )

        return execute

    @tool
    def run_code():
        async def execute(code: str) -> str:
            """Execute a Python program in the environment.

            Counts against the step budget. The namespace persists between
            calls. Returns the program's STDOUT/STDERR only — use the state
            tools to observe the world.

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
            return f"{program_output}\n[step {trajectory.total_steps}/{budget} used]"

        return execute

    return [
        list_methods(),
        manual(),
        task(),
        entities(),
        inventory(),
        summary(),
        run_code(),
    ]


def _trim_messages(messages, keep_last: int = 40):
    """Keep the system prompt, the opening user message, and the recent tail.

    The tail must not begin with tool-result messages: their parent
    assistant tool_call message would be trimmed away, and OpenAI rejects
    histories containing a function result with no matching call ("No tool
    call found for function call output with call_id ...").
    """
    if len(messages) <= keep_last + 2:
        return messages
    tail = messages[-keep_last:]
    while tail and getattr(tail[0], "role", None) == "tool":
        tail = tail[1:]
    return messages[:2] + tail


@solver
def factorio_tool_discovery_solver():
    """Solver where the agent discovers the API and state through tools."""

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
            task_config = THROUGHPUT_TASKS.get(env_id)
            task_meta = {
                "goal": env_info.get("description")
                or (task_config.goal_description if task_config else env_id),
                "quota": task_config.quota if task_config else "n/a",
            }

            trajectory = store_as(TrajectoryData)
            tools = _make_tools(gym_env, trajectory, budget, task_meta)

            messages = [
                ChatMessageSystem(content=SYSTEM_PROMPT.format(budget=budget)),
                ChatMessageUser(
                    content="Begin. Check task(), discover the API, then work toward the goal."
                ),
            ]

            # Free tool calls mean more generations than steps; cap
            # generations so a model that never acts still halts.
            max_generations = budget * 3
            generations = 0
            output = None

            while trajectory.total_steps < budget and generations < max_generations:
                generations += 1
                output = await get_model().generate(
                    input=_trim_messages(messages),
                    tools=tools,
                    # timeout: a hung provider request otherwise stalls the
                    # epoch indefinitely (observed with OpenRouter).
                    config=GenerateConfig(max_tokens=4096, timeout=300, max_retries=3),
                )
                messages.append(output.message)

                if output.message.tool_calls:
                    result = await execute_tools(messages, tools)
                    messages.extend(result.messages)
                else:
                    messages.append(
                        ChatMessageUser(
                            content="Use your tools: read manuals, check state, or run_code."
                        )
                    )

            trajectory.final_score = trajectory.current_score
            trajectory.final_automated_score = trajectory.automated_production_score
            logger.info(
                f"tool_discovery: finished with score {trajectory.final_score:.1f} "
                f"after {trajectory.total_steps} steps / {generations} generations"
            )

            state.messages = messages
            if output is not None:
                state.output = output
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
