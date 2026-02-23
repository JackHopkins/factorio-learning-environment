#!/usr/bin/env python
"""
Run FLE eval with Sonnet 4.6, 30 steps, real Factorio screenshots + MP4.

Saves game state after each step, renders screenshots live in the background,
then runs a catch-up render phase for any missing frames.

Usage:
    python run_with_video.py
"""

import os
import sys
import time
import json
import shutil
import asyncio
import subprocess
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("FACTORIO_SERVER_ADDRESS", "127.0.0.1")
os.environ.setdefault("FACTORIO_SERVER_PORT", "41000")

import gym
import importlib.resources
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
ENV_ID = "automation_science_pack_throughput"
MAX_STEPS = 30
SCREENSHOT_BASE = Path(".fle/run_screenshots")
SAVES_DIR = Path("/tmp/fle-run-saves")
FACTORIO_BINARY = Path("/tmp/factorio/bin/x64/factorio")
FACTORIO_DATA = Path("/tmp/factorio/data")
SCREENSHOT_BACKEND = os.getenv("SCREENSHOT_BACKEND", "benchmark").strip().lower()
MAX_RENDER_PARALLEL = 2  # concurrent --benchmark-graphics processes
LIVE_RENDER_PARALLEL = int(os.getenv("LIVE_RENDER_PARALLEL", "0"))  # default off for reliability
CATCHUP_RENDER_PARALLEL = int(os.getenv("CATCHUP_RENDER_PARALLEL", "1"))
CATCHUP_RENDER_TIMEOUT = int(os.getenv("CATCHUP_RENDER_TIMEOUT", "900"))
CATCHUP_RENDER_RETRIES = int(os.getenv("CATCHUP_RENDER_RETRIES", "1"))
CATCHUP_RENDER_TICKS = int(os.getenv("CATCHUP_RENDER_TICKS", "60"))
CATCHUP_PHASE_TIMEOUT = int(os.getenv("CATCHUP_PHASE_TIMEOUT", "14400"))
WORLD_PROFILE = os.getenv("WORLD_PROFILE", "open_world").strip()
if WORLD_PROFILE not in {"open_world", "default_lab_scenario"}:
    sys.exit(
        "ERROR: WORLD_PROFILE must be one of: "
        "open_world, default_lab_scenario"
    )
_WORLD_PROFILE_DEFAULT_RESOURCES = {
    "open_world": "iron-ore,copper-ore,coal,stone,crude-oil",
    "default_lab_scenario": "iron-ore,copper-ore,coal,stone",
}
WORLD_RESOURCE_RADIUS = int(os.getenv("WORLD_RESOURCE_RADIUS", "600"))
WORLD_WATER_RADIUS = int(os.getenv("WORLD_WATER_RADIUS", "1200"))
WORLD_REQUIRED_RESOURCES = tuple(
    r.strip()
    for r in os.getenv(
        "WORLD_REQUIRED_RESOURCES",
        _WORLD_PROFILE_DEFAULT_RESOURCES[WORLD_PROFILE],
    ).split(",")
    if r.strip()
)
SKIP_WORLD_CHECK = os.getenv("SKIP_WORLD_CHECK", "0") == "1"
# ----------------------------


# ── Screenshot mod that fires on load (for --benchmark-graphics) ──────────
_SCREENSHOT_MOD_INFO = """{
  "name": "fle_screenshot",
  "version": "1.0.0",
  "title": "FLE Screenshot Renderer",
  "author": "FLE",
  "factorio_version": "1.1"
}"""

# This mod runs when a save is loaded via --benchmark-graphics.
# It calculates camera bounds from player-force entities and takes
# a 1920x1080 screenshot centered on the factory.
_SCREENSHOT_MOD_CONTROL = r"""
local EX = {
    ["character"] = true,
    ["entity-ghost"] = true,
    ["tile-ghost"] = true,
    ["electric-energy-interface"] = true,
    ["resource"] = true,
}

local function take_factory_screenshot()
    local s = game.surfaces[1]
    local raw = s.find_entities_filtered{force = "player"}
    local es = {}
    for _, e in pairs(raw) do
        if not EX[e.type] then es[#es + 1] = e end
    end

    local cx, cy, zoom = 0, 0, 0.5
    if #es > 0 then
        local xs, ys = {}, {}
        for _, e in pairs(es) do
            xs[#xs + 1] = e.position.x
            ys[#ys + 1] = e.position.y
        end
        table.sort(xs)
        table.sort(ys)
        local mid = math.floor(#xs / 2) + 1
        local mx, my = xs[mid], ys[mid]

        -- Robust outlier filtering via MAD
        local da, db = {}, {}
        for i, x in ipairs(xs) do da[i] = math.abs(x - mx) end
        for i, y in ipairs(ys) do db[i] = math.abs(y - my) end
        table.sort(da)
        table.sort(db)
        local ma = math.max(da[mid], 5)
        local mb = math.max(db[mid], 5)
        local tx, ty = ma * 5, mb * 5

        local nb = {}
        for _, e in pairs(es) do
            if math.abs(e.position.x - mx) <= tx and math.abs(e.position.y - my) <= ty then
                nb[#nb + 1] = e
            end
        end
        if #nb == 0 then nb = es end

        local x1, y1, x2, y2 = math.huge, math.huge, -math.huge, -math.huge
        for _, e in pairs(nb) do
            local b = e.bounding_box
            if b.left_top.x < x1 then x1 = b.left_top.x end
            if b.left_top.y < y1 then y1 = b.left_top.y end
            if b.right_bottom.x > x2 then x2 = b.right_bottom.x end
            if b.right_bottom.y > y2 then y2 = b.right_bottom.y end
        end
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        local w = x2 - x1 + 6
        local h = y2 - y1 + 6
        zoom = math.min(1920 / (w * 32), 1080 / (h * 32), 2)
        zoom = math.max(zoom, 0.125)
    end

    -- Chart the area so it's revealed
    game.forces["player"].chart(s, {{cx - 200, cy - 200}, {cx + 200, cy + 200}})

    -- Set daytime
    s.always_day = true
    s.daytime = 0
    s.freeze_daytime = true

    -- Clear rendering overlays
    rendering.clear()

    game.take_screenshot{
        surface = s,
        position = {cx, cy},
        resolution = {1920, 1080},
        zoom = zoom,
        path = "factory.png",
        show_entity_info = true,
        show_gui = false,
        force_render = true,
    }
end

local function capture_once()
    local ok, err = pcall(take_factory_screenshot)
    log("FLE_SCREENSHOT config_changed ok=" .. tostring(ok) .. " err=" .. tostring(err))
end

-- --benchmark-graphics reliably runs this hook when an extra mod is injected.
-- on_load/on_init screenshot calls can crash this Factorio build for some saves.
script.on_configuration_changed(capture_once)
"""


def _find_factorio_container() -> str:
    """Find any running Factorio Docker container."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=factorio_",
             "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                return line.strip()
    except Exception:
        pass
    return None


def _find_factorio_container_for_tcp_port(tcp_port: int) -> str:
    """Find the running Factorio container that maps host tcp_port."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        names = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        for name in names:
            if "factorio" not in name.lower():
                continue
            inspect = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True, text=True, timeout=10,
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
        pass
    return None


def probe_world_signature(rcon_client, resource_radius: int, water_radius: int):
    """Read-only world probe used to reject obviously wrong maps before a run."""
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
    parsed = {}
    for token in raw.split("|"):
        if "@" not in token:
            continue
        key, value = token.split("@", 1)
        parsed[key.strip()] = value.strip()
    return raw, parsed


def save_game_state(rcon_client, step_num: int, version: int) -> str:
    """Save game state via RCON. Returns the save name."""
    save_name = f"fle_run_v{version}_step_{step_num:03d}"
    rcon_client.send_command(f'/sc game.auto_save("{save_name}")')
    time.sleep(0.3)  # brief pause for save to complete
    return save_name


def copy_save_from_docker(container: str, save_name: str, dest_dir: Path):
    """Copy a single save file from Docker. Returns local path or None."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    docker_path = f"{container}:/opt/factorio/saves/_autosave-{save_name}.zip"
    local_path = dest_dir / f"{save_name}.zip"
    result = subprocess.run(
        ["docker", "cp", docker_path, str(local_path)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or not local_path.exists():
        print(f"  Warning: failed to copy save {save_name}")
        return None
    return local_path


def copy_saves_from_docker(container: str, save_names: list, dest_dir: Path):
    """Copy save files from Docker container to local filesystem."""
    for name in save_names:
        copy_save_from_docker(container, name, dest_dir)


def render_step_from_docker(
    container: str,
    save_name: str,
    step_idx: int,
    save_dir: Path,
    screenshot_dir: Path,
) -> bool:
    """Copy one save from Docker and render it to step_{idx}.png."""
    save_zip = copy_save_from_docker(container, save_name, save_dir)
    if not save_zip:
        return False
    output_png = screenshot_dir / f"step_{step_idx:03d}.png"
    return render_screenshot(save_zip, output_png, container=container)


def render_simple_screenshot(instance, output_png: Path) -> bool:
    """Render screenshot using Python-side renderer (no Factorio benchmark)."""
    try:
        image = instance.namespace._render_simple()
        output_png.parent.mkdir(parents=True, exist_ok=True)
        image.image.save(output_png)
        return True
    except Exception as e:
        print(f"  Error render_simple for {output_png.name}: {e}")
        return False


def render_screenshot(save_zip: Path, output_png: Path, container: str = None) -> bool:
    """Render a screenshot from a save file using --benchmark-graphics.

    This is a standalone function suitable for ProcessPoolExecutor.
    Returns True on success.
    """
    tmpdir = tempfile.mkdtemp(prefix="fle_render_")
    try:
        # Create mod directory
        mod_dir = Path(tmpdir) / "mods" / "fle_screenshot"
        mod_dir.mkdir(parents=True)
        (mod_dir / "info.json").write_text(_SCREENSHOT_MOD_INFO)
        (mod_dir / "control.lua").write_text(_SCREENSHOT_MOD_CONTROL)

        # Write config.ini
        config_ini = Path(tmpdir) / "config.ini"
        script_output = Path(tmpdir) / "script-output"
        script_output.mkdir()
        config_ini.write_text(
            f"[path]\n"
            f"read-data={FACTORIO_DATA}\n"
            f"write-data={tmpdir}\n"
        )

        # Run benchmark-graphics
        cmd = [
            "xvfb-run", "-a", "-s", "-screen 0 1920x1080x24",
            str(FACTORIO_BINARY),
            "--benchmark-graphics", str(save_zip),
            "--benchmark-ticks", str(CATCHUP_RENDER_TICKS),
            "--benchmark-ignore-paused",
            "--mod-directory", str(Path(tmpdir) / "mods"),
            "-c", str(config_ini),
            "--disable-audio",
            "--disable-migration-window",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )

        # Find the screenshot
        screenshot = script_output / "factory.png"
        if screenshot.exists() and screenshot.stat().st_size > 0:
            output_png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(screenshot, output_png)
            return True
        else:
            print(f"  Warning: no screenshot produced for {save_zip.name}")
            if result.returncode != 0:
                print(f"  Exit code: {result.returncode}")
                stderr_tail = result.stderr[-500:] if result.stderr else ""
                print(f"  Stderr: {stderr_tail}")
            return False
    except Exception as e:
        print(f"  Error rendering {save_zip.name}: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def batch_render_screenshots(
    save_dir: Path,
    screenshot_dir: Path,
    max_parallel: int = MAX_RENDER_PARALLEL,
):
    """Render all saves to screenshots in parallel."""
    saves = sorted(save_dir.glob("*.zip"))
    if not saves:
        print("No saves to render")
        return 0

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nRendering {len(saves)} screenshots ({max_parallel} parallel)...")
    t0 = time.time()
    success = 0

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {}
        for i, save_zip in enumerate(saves):
            output_png = screenshot_dir / f"step_{i:03d}.png"
            future = executor.submit(render_screenshot, save_zip, output_png)
            futures[future] = (i, save_zip.name)

        for future in as_completed(futures):
            idx, name = futures[future]
            try:
                ok = future.result()
                if ok:
                    success += 1
                    print(f"  [{success}/{len(saves)}] Rendered step_{idx:03d}.png")
            except Exception as e:
                print(f"  Error rendering {name}: {e}")

    dt = time.time() - t0
    print(f"Rendered {success}/{len(saves)} screenshots in {dt:.1f}s")
    return success


def png_to_mp4(png_dir: Path, output_path: Path, seconds_per_frame: float = 3.0) -> bool:
    """Convert PNGs to MP4, holding each frame for seconds_per_frame seconds."""
    pngs = sorted(f for f in png_dir.glob("step_*.png"))
    if not pngs:
        print("No PNGs to convert")
        return False
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found in PATH")
        return False

    concat_file = png_dir / "_concat.txt"
    with concat_file.open("w") as f:
        for png in pngs:
            f.write(f"file '{png.resolve()}'\n")
            f.write(f"duration {seconds_per_frame}\n")
        f.write(f"file '{pngs[-1].resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    print(f"\nGenerating video: {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-300:]}")
        return False
    else:
        print(f"Video saved: {output_path} ({len(pngs)} frames, {seconds_per_frame}s each)")
        return True


async def main():
    print(f"=== FLE Run: {MODEL} on {ENV_ID}, {MAX_STEPS} steps ===")
    print(f"    Save per step + screenshot backend: {SCREENSHOT_BACKEND}")
    print(
        "    World profile: "
        f"{WORLD_PROFILE} "
        f"(required={','.join(WORLD_REQUIRED_RESOURCES)}, "
        f"resource_radius={WORLD_RESOURCE_RADIUS}, water_radius={WORLD_WATER_RADIUS})\n"
    )

    if SCREENSHOT_BACKEND not in {"render_simple", "benchmark"}:
        sys.exit(
            f"ERROR: invalid SCREENSHOT_BACKEND={SCREENSHOT_BACKEND}. "
            "Use 'render_simple' or 'benchmark'."
        )

    if not FACTORIO_BINARY.is_file():
        sys.exit(f"ERROR: Factorio binary not found at {FACTORIO_BINARY}")
    if not shutil.which("ffmpeg"):
        sys.exit("ERROR: ffmpeg not found (install ffmpeg)")
    if SCREENSHOT_BACKEND == "benchmark" and not shutil.which("xvfb-run"):
        sys.exit("ERROR: xvfb-run not found (install xvfb)")

    # Setup
    db_client = await create_db_client()
    env_info = get_environment_info(ENV_ID)
    task = TaskFactory.create_task(env_info["task_config_path"])
    object.__setattr__(task, 'trajectory_length', MAX_STEPS)

    gym_env = gym.make(ENV_ID, run_idx=0)
    instance = gym_env.unwrapped.instance
    server_tcp_port = int(getattr(instance, "tcp_port", 0))

    container = _find_factorio_container_for_tcp_port(server_tcp_port)
    if not container:
        container = _find_factorio_container()
    if not container:
        sys.exit("ERROR: No Factorio Docker container found")
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
            resource for resource in WORLD_REQUIRED_RESOURCES
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

    SCREENSHOT_DIR = SCREENSHOT_BASE / f"v{version}"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for f in SCREENSHOT_DIR.glob("step_*.png"):
        f.unlink()

    # Prepare save directory
    SAVE_DIR = SAVES_DIR / f"v{version}"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    for f in SAVE_DIR.glob("*.zip"):
        f.unlink()

    print(f"Version: {version}")
    print(f"Logs: {log_dir}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print(f"Saves: {SAVE_DIR}")
    print(f"Screenshot backend: {SCREENSHOT_BACKEND}")
    print(f"World profile: {WORLD_PROFILE}")
    print(f"Live render workers: {LIVE_RENDER_PARALLEL}")
    print()

    use_benchmark_backend = SCREENSHOT_BACKEND == "benchmark"
    live_render_enabled = use_benchmark_backend and LIVE_RENDER_PARALLEL > 0
    live_render_executor = ThreadPoolExecutor(max_workers=LIVE_RENDER_PARALLEL) if live_render_enabled else None
    live_render_futures = {}

    def submit_live_render(step_idx: int, save_name: str):
        if not live_render_enabled:
            return
        step_future = live_render_executor.submit(
            render_step_from_docker,
            container,
            save_name,
            step_idx,
            SAVE_DIR,
            SCREENSHOT_DIR,
        )
        live_render_futures[step_future] = (step_idx, save_name)

    # Save initial game state
    save_names = []
    initial_save = save_game_state(instance.rcon_client, 0, version)
    save_names.append(initial_save)
    print(f"Saved initial state: {initial_save}")
    if use_benchmark_backend:
        submit_live_render(0, initial_save)
    else:
        output_png = SCREENSHOT_DIR / "step_000.png"
        ok = render_simple_screenshot(instance, output_png)
        if ok:
            print("Captured step_000.png via render_simple")
        else:
            print("Warning: failed to capture step_000.png via render_simple")

    # Run the trajectory
    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        db_client=db_client,
        log_dir=log_dir,
        process_id=0,
    )

    max_steps = MAX_STEPS
    current_state, agent_steps = await runner._initialize_trajectory_state()

    for idx, a in enumerate(runner.agents):
        runner.logger.save_system_prompt(a, idx)

    from itertools import product as iprod
    from fle.env.gym_env.action import Action
    from fle.env.gym_env.observation import Observation
    from fle.agents import CompletionReason, CompletionResult

    step_count = 0
    done = False
    for _, agent_idx in iprod(range(max_steps), range(len(runner.agents))):
        agent_r = runner.agents[agent_idx]
        iteration_start = time.time()

        try:
            while agent_steps[agent_idx] < max_steps:
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
                    iteration_start, agent_r, agent_idx,
                    agent_steps[agent_idx], production_score, program, observation,
                )

                elapsed = time.time() - iteration_start
                print(f"[step {step_count:2d}/{max_steps}] reward={reward:.2f} score={production_score:.2f} err={info['error_occurred']} ({elapsed:.1f}s)")

                # Save game state after this step
                sn = save_game_state(instance.rcon_client, step_count, version)
                save_names.append(sn)
                if use_benchmark_backend:
                    submit_live_render(step_count, sn)
                else:
                    output_png = SCREENSHOT_DIR / f"step_{step_count:03d}.png"
                    ok = render_simple_screenshot(instance, output_png)
                    if not ok:
                        print(f"Warning: failed to capture {output_png.name} via render_simple")

                if done:
                    print(f"\n*** TASK COMPLETED at step {step_count}! ***")
                    for a in runner.agents:
                        await a.end(CompletionResult(step=agent_steps[agent_idx], reason=CompletionReason.SUCCESS))
                    break

            if done:
                break

        except Exception as e:
            print(f"[step {step_count}] Error: {e}")
            import traceback
            traceback.print_exc()
            # Save anyway
            sn = save_game_state(instance.rcon_client, step_count, version)
            save_names.append(sn)
            if use_benchmark_backend:
                submit_live_render(step_count, sn)
            else:
                output_png = SCREENSHOT_DIR / f"step_{step_count:03d}.png"
                render_simple_screenshot(instance, output_png)
            continue

        if done:
            break

    await db_client.cleanup()

    if use_benchmark_backend:
        if live_render_enabled:
            print(f"\nWaiting for {len(live_render_futures)} live render jobs to finish...")
            live_render_success = 0
            for future in as_completed(live_render_futures):
                step_idx, name = live_render_futures[future]
                try:
                    ok = future.result()
                    if ok:
                        live_render_success += 1
                        print(f"  Live render OK: step_{step_idx:03d}.png ({name})")
                    else:
                        print(f"  Live render failed: step_{step_idx:03d}.png ({name})")
                except Exception as e:
                    print(f"  Live render error step_{step_idx:03d} ({name}): {e}")
            live_render_executor.shutdown(wait=True)
            print(f"Live render complete: {live_render_success}/{len(live_render_futures)}")
        else:
            print("\nLive rendering disabled (LIVE_RENDER_PARALLEL=0)")

        # Copy saves from Docker container to ensure full local save set
        print(f"\nCopying {len(save_names)} saves from Docker...")
        copy_saves_from_docker(container, save_names, SAVE_DIR)

        # Catch-up render for any missing screenshots + MP4 generation.
        render_script = Path(__file__).parent / "render_saves.py"
        print(f"\nLaunching catch-up renderer: python {render_script} {SAVE_DIR} {SCREENSHOT_DIR} --skip-existing --no-clear")
        render_result = subprocess.run(
            [sys.executable, str(render_script), str(SAVE_DIR), str(SCREENSHOT_DIR), "--skip-existing", "--no-clear"],
            timeout=CATCHUP_PHASE_TIMEOUT,
            env={
                **os.environ,
                "FLE_RENDER_CONTAINER": container,
                "RENDER_MAX_PARALLEL": str(CATCHUP_RENDER_PARALLEL),
                "RENDER_TIMEOUT": str(CATCHUP_RENDER_TIMEOUT),
                "RENDER_RETRIES": str(CATCHUP_RENDER_RETRIES),
                "RENDER_TICKS": str(CATCHUP_RENDER_TICKS),
            },
        )
        if render_result.returncode != 0:
            sys.exit(f"ERROR: catch-up renderer exited with code {render_result.returncode}")
    else:
        print("\nUsing render_simple backend: screenshots captured inline during the run.")
        print(f"\nCopying {len(save_names)} saves from Docker...")
        copy_saves_from_docker(container, save_names, SAVE_DIR)
        if not png_to_mp4(SCREENSHOT_DIR, SCREENSHOT_DIR / "run.mp4", seconds_per_frame=3.0):
            sys.exit("ERROR: failed to generate run.mp4")

    screenshot_count = len(list(SCREENSHOT_DIR.glob("step_*.png")))
    expected_screenshots = len(save_names)
    if screenshot_count != expected_screenshots:
        sys.exit(
            f"ERROR: expected {expected_screenshots} screenshots, got {screenshot_count}."
        )
    print(f"\n{'='*60}")
    print(f"Run complete: {step_count} steps, {screenshot_count} screenshots")
    print(f"{'='*60}")

    print(f"\n=== ALL OUTPUTS ===")
    print(f"  Video:       {(SCREENSHOT_DIR / 'run.mp4').resolve()}")
    print(f"  Screenshots: {SCREENSHOT_DIR.resolve()}/step_*.png")
    print(f"  Logs:        {Path(log_dir).resolve()}/")
    print(f"  DB:          .fle/data.db (version {version})")


if __name__ == "__main__":
    asyncio.run(main())
