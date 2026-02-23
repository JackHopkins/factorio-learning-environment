#!/usr/bin/env python
"""
Run FLE eval with claude-sonnet-4-6 and produce real benchmark screenshots + MP4.

Flow:
1) Run agent loop and save game state after each step.
2) Copy all saves from the selected Factorio container.
3) Invoke render_saves.py once for catch-up rendering + video generation.
"""

import os
import sys
import time
import json
import shutil
import asyncio
import subprocess
import importlib.resources
from pathlib import Path
from typing import Dict, List, Set, Tuple

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("FACTORIO_SERVER_ADDRESS", "127.0.0.1")
os.environ.setdefault("FACTORIO_SERVER_PORT", "41000")

import gym

from fle.agents.gym_agent import GymAgent
from fle.commons.db_client import create_db_client, get_next_version
from fle.eval.tasks import TaskFactory
from fle.eval.algorithms.independent.trajectory_runner import GymTrajectoryRunner
from fle.eval.algorithms.independent.config import GymEvalConfig
from fle.env.gym_env.registry import get_environment_info
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.utils.controller_loader.system_prompt_generator import SystemPromptGenerator


# ---------- CONFIG ----------
MODEL = "claude-sonnet-4-6"
ENV_ID = os.getenv("ENV_ID", "automation_science_pack_throughput").strip()
if not ENV_ID:
    sys.exit("ERROR: ENV_ID must be non-empty")



def _env_int(name: str, default: int, minimum: int = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        sys.exit(f"ERROR: {name} must be an integer (got '{raw}')")
    if minimum is not None and value < minimum:
        sys.exit(f"ERROR: {name} must be >= {minimum} (got {value})")
    return value


MAX_STEPS = _env_int("MAX_STEPS", 30, minimum=1)
SCREENSHOT_BASE = Path(".fle/run_screenshots")
SAVES_DIR = Path("/tmp/fle-run-saves")
FACTORIO_BINARY = Path("/tmp/factorio/bin/x64/factorio")

SCREENSHOT_BACKEND = os.getenv("SCREENSHOT_BACKEND", "benchmark").strip().lower()
if SCREENSHOT_BACKEND != "benchmark":
    sys.exit(
        "ERROR: run_with_video.py only supports SCREENSHOT_BACKEND=benchmark. "
        "Use run_video_reliable.sh for the supported workflow."
    )

CATCHUP_RENDER_PARALLEL = _env_int("CATCHUP_RENDER_PARALLEL", 1, minimum=1)
CATCHUP_RENDER_TIMEOUT = _env_int("CATCHUP_RENDER_TIMEOUT", 900, minimum=1)
CATCHUP_RENDER_RETRIES = _env_int("CATCHUP_RENDER_RETRIES", 1, minimum=0)
CATCHUP_RENDER_TICKS = _env_int("CATCHUP_RENDER_TICKS", 60, minimum=1)
CATCHUP_PHASE_TIMEOUT = _env_int("CATCHUP_PHASE_TIMEOUT", 14400, minimum=1)

WORLD_PROFILE = os.getenv("WORLD_PROFILE", "open_world").strip()
if WORLD_PROFILE not in {"open_world", "default_lab_scenario"}:
    sys.exit(
        "ERROR: WORLD_PROFILE must be one of: open_world, default_lab_scenario"
    )

_WORLD_PROFILE_DEFAULT_RESOURCES = {
    "open_world": "iron-ore,copper-ore,coal,stone,crude-oil",
    "default_lab_scenario": "iron-ore,copper-ore,coal,stone",
}
WORLD_RESOURCE_RADIUS = _env_int("WORLD_RESOURCE_RADIUS", 600, minimum=1)
WORLD_WATER_RADIUS = _env_int("WORLD_WATER_RADIUS", 1200, minimum=1)
WORLD_REQUIRED_RESOURCES = tuple(
    resource.strip()
    for resource in os.getenv(
        "WORLD_REQUIRED_RESOURCES",
        _WORLD_PROFILE_DEFAULT_RESOURCES[WORLD_PROFILE],
    ).split(",")
    if resource.strip()
)
SKIP_WORLD_CHECK = os.getenv("SKIP_WORLD_CHECK", "0") == "1"
# ----------------------------



def _find_factorio_container_for_tcp_port(tcp_port: int) -> str:
    """Return running Factorio container that maps host tcp_port, else None."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        for name in names:
            if "factorio" not in name.lower():
                continue

            inspect = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.returncode != 0 or not inspect.stdout.strip():
                continue

            info = json.loads(inspect.stdout)[0]
            ports = info.get("NetworkSettings", {}).get("Ports", {})
            for port_spec, bindings in ports.items():
                if not port_spec.endswith("/tcp") or not bindings:
                    continue
                for binding in bindings:
                    host_port = binding.get("HostPort")
                    if host_port and int(host_port) == int(tcp_port):
                        return name
    except Exception:
        return None

    return None



def probe_world_signature(rcon_client, resource_radius: int, water_radius: int) -> Tuple[str, Dict[str, str]]:
    """Read-only world probe used to reject wrong maps before a run."""
    probe_cmd = (
        "/sc "
        "local p=game.players[1]; local s=game.surfaces[1]; "
        "local x,y=0,0; if p then x,y=p.position.x,p.position.y end; "
        f"local res_radius={resource_radius}; local water_radius={water_radius}; "
        "local names={'iron-ore','copper-ore','coal','stone','crude-oil'}; "
        "local out={'player@'..string.format('%.1f',x)..','..string.format('%.1f',y)}; "
        "for _,name in pairs(names) do "
        "  local ents=s.find_entities_filtered{position={x,y}, radius=res_radius, name=name}; "
        "  local best=nil; local bd=1e18; "
        "  for _,e in pairs(ents) do "
        "    local dx=e.position.x-x; local dy=e.position.y-y; local d=dx*dx+dy*dy; "
        "    if d<bd then bd=d; best=e end "
        "  end; "
        "  if best then "
        "    table.insert(out, name..'@'..string.format('%.1f',best.position.x)..','..string.format('%.1f',best.position.y)..':'..string.format('%.1f', math.sqrt(bd))) "
        "  else "
        "    table.insert(out, name..'@none') "
        "  end "
        "end; "
        "local wt=s.find_tiles_filtered{"
        "  area={{x-water_radius,y-water_radius},{x+water_radius,y+water_radius}}, "
        "  name={'water','deepwater','water-green','deepwater-green','water-shallow'}, "
        "  limit=1"
        "}; "
        "if #wt>0 then "
        "  local wp=wt[1].position; table.insert(out, 'water_tile@'..string.format('%.1f',wp.x)..','..string.format('%.1f',wp.y)) "
        "else "
        "  table.insert(out, 'water_tile@none') "
        "end; "
        "rcon.print(table.concat(out,'|'))"
    )

    raw = rcon_client.send_command(probe_cmd) or ""
    parsed: Dict[str, str] = {}
    for token in raw.split("|"):
        if "@" not in token:
            continue
        key, value = token.split("@", 1)
        parsed[key.strip()] = value.strip()
    return raw, parsed



def save_game_state(rcon_client, step_num: int, version: int) -> str:
    """Save game state via RCON and return the save name."""
    save_name = f"fle_run_v{version}_step_{step_num:03d}"
    rcon_client.send_command(f'/sc game.auto_save("{save_name}")')
    time.sleep(0.3)
    return save_name



def append_unique_save(save_names: List[str], seen: Set[str], save_name: str) -> None:
    if save_name in seen:
        return
    seen.add(save_name)
    save_names.append(save_name)



def copy_save_from_docker(container: str, save_name: str, dest_dir: Path) -> Path:
    """Copy one autosave from docker; returns local path or None."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    docker_path = f"{container}:/opt/factorio/saves/_autosave-{save_name}.zip"
    local_path = dest_dir / f"{save_name}.zip"
    result = subprocess.run(
        ["docker", "cp", docker_path, str(local_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not local_path.exists():
        print(f"  Warning: failed to copy save {save_name}")
        return None
    return local_path



def copy_saves_from_docker(container: str, save_names: List[str], dest_dir: Path) -> None:
    """Copy all unique save files from docker to local filesystem."""
    for name in save_names:
        copy_save_from_docker(container, name, dest_dir)



def run_catchup_renderer(save_dir: Path, screenshot_dir: Path) -> None:
    """Run standalone renderer on all copied saves."""
    render_script = Path(__file__).parent / "render_saves.py"
    cmd = [
        sys.executable,
        str(render_script),
        str(save_dir),
        str(screenshot_dir),
        "--skip-existing",
        "--no-clear",
    ]

    print(
        "\nLaunching catch-up renderer: "
        f"python {render_script} {save_dir} {screenshot_dir} --skip-existing --no-clear"
    )

    result = subprocess.run(
        cmd,
        timeout=CATCHUP_PHASE_TIMEOUT,
        env={
            **os.environ,
            "RENDER_MAX_PARALLEL": str(CATCHUP_RENDER_PARALLEL),
            "RENDER_TIMEOUT": str(CATCHUP_RENDER_TIMEOUT),
            "RENDER_RETRIES": str(CATCHUP_RENDER_RETRIES),
            "RENDER_TICKS": str(CATCHUP_RENDER_TICKS),
        },
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: catch-up renderer exited with code {result.returncode}")


async def main():
    print(f"=== FLE Run: {MODEL} on {ENV_ID}, {MAX_STEPS} steps ===")
    print("    Save per step + screenshot backend: benchmark")
    print(
        "    World profile: "
        f"{WORLD_PROFILE} "
        f"(required={','.join(WORLD_REQUIRED_RESOURCES)}, "
        f"resource_radius={WORLD_RESOURCE_RADIUS}, water_radius={WORLD_WATER_RADIUS})\n"
    )

    if not FACTORIO_BINARY.is_file():
        sys.exit(f"ERROR: Factorio binary not found at {FACTORIO_BINARY}")
    if not shutil.which("ffmpeg"):
        sys.exit("ERROR: ffmpeg not found (install ffmpeg)")
    if not shutil.which("xvfb-run"):
        sys.exit("ERROR: xvfb-run not found (install xvfb)")

    # Setup
    db_client = await create_db_client()
    env_info = get_environment_info(ENV_ID)
    task = TaskFactory.create_task(env_info["task_config_path"])
    object.__setattr__(task, "trajectory_length", MAX_STEPS)

    gym_env = gym.make(ENV_ID, run_idx=0)
    instance = gym_env.unwrapped.instance
    server_tcp_port = int(getattr(instance, "tcp_port", 0))
    if server_tcp_port <= 0:
        sys.exit(f"ERROR: invalid tcp port from environment instance: {server_tcp_port}")

    container = _find_factorio_container_for_tcp_port(server_tcp_port)
    if not container:
        sys.exit(
            "ERROR: could not resolve Factorio container for "
            f"tcp/{server_tcp_port}; refusing cross-world fallback."
        )

    print(f"Factorio server: 127.0.0.1:{server_tcp_port}")
    print(f"Docker container: {container}")

    if not SKIP_WORLD_CHECK:
        raw_probe, parsed_probe = probe_world_signature(
            instance.rcon_client,
            resource_radius=WORLD_RESOURCE_RADIUS,
            water_radius=WORLD_WATER_RADIUS,
        )
        print(f"World probe: {raw_probe}")

        missing_resources = [
            resource
            for resource in WORLD_REQUIRED_RESOURCES
            if parsed_probe.get(resource, "none").startswith("none")
        ]
        if parsed_probe.get("water_tile", "none").startswith("none"):
            missing_resources.append("water_tile")

        if missing_resources:
            sys.exit(
                "ERROR: Wrong world signature detected for profile "
                + f"{WORLD_PROFILE}. Missing resources in probe: "
                + ", ".join(missing_resources)
                + f" (required={','.join(WORLD_REQUIRED_RESOURCES)}, "
                + f"radius={WORLD_RESOURCE_RADIUS}, water_radius={WORLD_WATER_RADIUS}). "
                + "Set SKIP_WORLD_CHECK=1 to bypass."
            )
    else:
        print(f"World probe skipped (SKIP_WORLD_CHECK=1) for profile={WORLD_PROFILE}")

    generator = SystemPromptGenerator(str(importlib.resources.files("fle") / "env"))
    system_prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)

    agent = GymAgent(
        model=MODEL,
        system_prompt=system_prompt,
        task=task,
        agent_idx=0,
        observation_formatter=BasicObservationFormatter(include_research=False),
        system_prompt_formatter=SystemPromptFormatter(),
    )

    version = await get_next_version()
    config = GymEvalConfig(
        agents=[agent],
        version=version,
        version_description=f"model:{MODEL}\ntype:{task.task_key}\nnum_agents:1",
        task=task,
        agent_cards=[agent.get_agent_card()],
        env_id=ENV_ID,
    )

    log_dir = os.path.join(".fle", "trajectory_logs", f"v{version}")

    screenshot_dir = SCREENSHOT_BASE / f"v{version}"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    for old_png in screenshot_dir.glob("step_*.png"):
        old_png.unlink()

    save_dir = SAVES_DIR / f"v{version}"
    save_dir.mkdir(parents=True, exist_ok=True)
    for old_zip in save_dir.glob("*.zip"):
        old_zip.unlink()

    print(f"Version: {version}")
    print(f"Logs: {log_dir}")
    print(f"Screenshots: {screenshot_dir}")
    print(f"Saves: {save_dir}")
    print(f"World profile: {WORLD_PROFILE}")
    print()

    save_names: List[str] = []
    seen_save_names: Set[str] = set()

    initial_save = save_game_state(instance.rcon_client, 0, version)
    append_unique_save(save_names, seen_save_names, initial_save)
    print(f"Saved initial state: {initial_save}")

    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        db_client=db_client,
        log_dir=log_dir,
        process_id=0,
    )

    current_state, agent_steps = await runner._initialize_trajectory_state()
    _ = current_state

    for idx, configured_agent in enumerate(runner.agents):
        runner.logger.save_system_prompt(configured_agent, idx)

    from itertools import product as iprod

    from fle.env.gym_env.action import Action
    from fle.env.gym_env.observation import Observation
    from fle.agents import CompletionReason, CompletionResult

    step_count = 0
    done = False

    for _, agent_idx in iprod(range(MAX_STEPS), range(len(runner.agents))):
        agent_r = runner.agents[agent_idx]
        iteration_start = time.time()

        try:
            while agent_steps[agent_idx] < MAX_STEPS:
                policy = await agent_r.generate_policy()
                agent_steps[agent_idx] += 1
                step_count += 1

                if not policy:
                    print(f"[step {step_count}] Policy generation failed, skipping")
                    break

                action = Action(code=policy.code, agent_idx=agent_idx, game_state=None)
                obs_dict, reward, terminated, truncated, info = runner.gym_env.step(action)
                observation = Observation.from_dict(obs_dict)
                production_score = info["production_score"]
                done = terminated or truncated

                program = await runner.create_program_from_policy(
                    policy=policy,
                    agent_idx=agent_idx,
                    reward=reward,
                    response=obs_dict["raw_text"],
                    error_occurred=info["error_occurred"],
                    achievements=info["achievements"],
                    game_state=info["output_game_state"],
                    production_score=production_score,
                )

                await agent_r.update_conversation(observation, previous_program=program)

                runner._log_trajectory_state(
                    iteration_start,
                    agent_r,
                    agent_idx,
                    agent_steps[agent_idx],
                    production_score,
                    program,
                    observation,
                )

                elapsed = time.time() - iteration_start
                print(
                    f"[step {step_count:2d}/{MAX_STEPS}] "
                    f"reward={reward:.2f} score={production_score:.2f} "
                    f"err={info['error_occurred']} ({elapsed:.1f}s)"
                )

                save_name = save_game_state(instance.rcon_client, step_count, version)
                append_unique_save(save_names, seen_save_names, save_name)

                if done:
                    print(f"\n*** TASK COMPLETED at step {step_count}! ***")
                    for configured_agent in runner.agents:
                        await configured_agent.end(
                            CompletionResult(
                                step=agent_steps[agent_idx],
                                reason=CompletionReason.SUCCESS,
                            )
                        )
                    break

            if done:
                break

        except Exception as exc:
            print(f"[step {step_count}] Error: {exc}")
            import traceback

            traceback.print_exc()

            # Keep a snapshot for post-mortem, but dedupe names so counts stay stable.
            snapshot_step = max(step_count, 0)
            save_name = save_game_state(instance.rcon_client, snapshot_step, version)
            append_unique_save(save_names, seen_save_names, save_name)
            continue

        if done:
            break

    await db_client.cleanup()

    print(f"\nCopying {len(save_names)} saves from Docker...")
    copy_saves_from_docker(container, save_names, save_dir)

    run_catchup_renderer(save_dir, screenshot_dir)

    screenshot_count = len(list(screenshot_dir.glob("step_*.png")))
    expected_screenshots = len(save_names)
    if screenshot_count != expected_screenshots:
        sys.exit(
            f"ERROR: expected {expected_screenshots} screenshots, got {screenshot_count}."
        )

    print(f"\n{'=' * 60}")
    print(f"Run complete: {step_count} steps, {screenshot_count} screenshots")
    print(f"{'=' * 60}")

    print("\n=== ALL OUTPUTS ===")
    print(f"  Video:       {(screenshot_dir / 'run.mp4').resolve()}")
    print(f"  Screenshots: {screenshot_dir.resolve()}/step_*.png")
    print(f"  Logs:        {Path(log_dir).resolve()}/")
    print(f"  DB:          .fle/data.db (version {version})")


if __name__ == "__main__":
    asyncio.run(main())
