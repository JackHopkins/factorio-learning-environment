#!/usr/bin/env python3
"""
Generate screenshots and create MP4 videos from Factorio program versions.

This script combines screenshot generation from database-stored program chains
with video creation using FFmpeg.
"""

import os
import sys
import argparse
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import tempfile
import subprocess
import shutil
import time
import math

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import gymnasium as gym
from fle.env.gym_env.action import Action
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.registry import list_available_environments
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.commons.models.program import Program
from fle.env.lua_manager import LuaScriptManager

load_dotenv()


def get_db_connection():
    """Create a database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )


def get_program_chain(conn, version: int):
    """Get all programs for a specific version ordered by time"""
    query = """
    SELECT id, created_at FROM programs
    WHERE version = %s
    AND state_json IS NOT NULL
    ORDER BY created_at ASC
    LIMIT 3000
    """

    with conn.cursor() as cur:
        cur.execute(query, (version,))
        return cur.fetchall()


def get_program_state(conn, program_id: int):
    """Fetch a single program's full state by ID"""
    query = """
    SELECT * FROM programs WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(query, (program_id,))
        row = cur.fetchone()
        if not row:
            return None

        col_names = [desc[0] for desc in cur.description]
        return Program.from_row(dict(zip(col_names, row)))


def create_gym_environment(version: int) -> FactorioGymEnv:
    """Create a gym environment based on the task from the first program of a version"""

    # First, list all available environments for debugging
    available_envs = list_available_environments()
    print(
        f"Available gym environments: {available_envs[:5]}... (total: {len(available_envs)})"
    )

    conn = get_db_connection()
    try:
        # Get the first program to determine the task
        query = """
        SELECT meta FROM programs
        WHERE version = %s
        AND meta IS NOT NULL
        ORDER BY created_at ASC
        LIMIT 1
        """

        with conn.cursor() as cur:
            cur.execute(query, (version,))
            result = cur.fetchone()

            if not result:
                raise ValueError(f"No programs found for version {version}")

            meta = result[0]

            # Try to extract task from version_description in meta
            version_description = meta.get("version_description", "")
            if "type:" in version_description:
                task_key = version_description.split("type:")[1].split("\n")[0].strip()
            else:
                # Fallback: use first available environment as default
                task_key = (
                    available_envs[0] if available_envs else "iron_plate_throughput"
                )
                print(
                    f"Warning: Could not determine task from version {version}, using default: {task_key}"
                )

            # The gym environment ID is just the task key
            env_id = task_key

            print(f"Trying to create environment: {env_id}")

            # Check if the environment is in the available list
            if env_id not in available_envs:
                print(
                    f"Warning: Environment {env_id} not in available list. Available: {available_envs[:10]}"
                )
                # Use first available environment as fallback
                if available_envs:
                    env_id = available_envs[0]
                    print(f"Using fallback environment: {env_id}")
                else:
                    raise ValueError("No gym environments available!")

            try:
                gym_env = gym.make(env_id, run_idx=0)
                print(f"Successfully created gym environment: {env_id}")
                return gym_env
            except Exception as e:
                print(f"Failed to create gym environment {env_id}: {e}")
                # Try the first available environment as final fallback
                if available_envs and env_id != available_envs[0]:
                    fallback_env_id = available_envs[0]
                    print(f"Trying final fallback environment: {fallback_env_id}")
                    gym_env = gym.make(fallback_env_id, run_idx=0)
                    return gym_env
                else:
                    raise e
    finally:
        conn.close()


def ease_in_out_cubic(t):
    """Cubic ease-in-out function for smooth transitions.

    Args:
        t: Progress from 0.0 to 1.0

    Returns:
        Eased value between 0.0 and 1.0
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        p = 2 * t - 2
        return 1 + p * p * p / 2


def ease_in_out_sine(t):
    """Sine ease-in-out function for very smooth transitions.

    Args:
        t: Progress from 0.0 to 1.0

    Returns:
        Eased value between 0.0 and 1.0
    """
    return -(math.cos(math.pi * t) - 1) / 2


def interpolate_camera(
    start_pos, end_pos, start_zoom, end_zoom, progress, easing_func=ease_in_out_cubic
):
    """Interpolate camera position and zoom with easing.

    Args:
        start_pos: (x, y) starting camera position
        end_pos: (x, y) ending camera position
        start_zoom: Starting zoom level
        end_zoom: Ending zoom level
        progress: Progress from 0.0 to 1.0
        easing_func: Easing function to use

    Returns:
        Tuple of (x, y, zoom) for interpolated camera state
    """
    # Apply easing to progress
    eased_progress = easing_func(progress)

    # Interpolate position
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * eased_progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * eased_progress

    # Interpolate zoom (use logarithmic interpolation for smoother zoom)
    if start_zoom > 0 and end_zoom > 0:
        log_start = math.log(start_zoom)
        log_end = math.log(end_zoom)
        log_zoom = log_start + (log_end - log_start) * eased_progress
        zoom = math.exp(log_zoom)
    else:
        zoom = start_zoom + (end_zoom - start_zoom) * eased_progress

    return x, y, zoom


def get_camera_state_for_factory(instance, resolution="1920x1080"):
    """Calculate the optimal camera state for the current factory.

    Returns:
        Dict with 'position' and 'zoom' keys, or None if no factory
    """
    min_x, min_y, max_x, max_y = get_factory_bounds(instance)

    if max_x == 0 and max_y == 0:
        return None

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Calculate factory dimensions with padding
    factory_width = max_x - min_x + 20
    factory_height = max_y - min_y + 20

    # Calculate optimal zoom
    zoom = calculate_optimal_zoom(factory_width, factory_height, resolution)

    return {"position": (center_x, center_y), "zoom": zoom}


def capture_camera_transition(
    instance,
    script_output_path,
    output_dir,
    screenshot_counter,
    start_camera,
    end_camera,
    transition_frames=15,
    easing_func=ease_in_out_cubic,
):
    """Capture a smooth camera transition between two states.

    Args:
        instance: Game instance
        script_output_path: Path to script output
        output_dir: Directory to save screenshots
        screenshot_counter: Current screenshot counter
        start_camera: Starting camera state dict with 'position' and 'zoom'
        end_camera: Ending camera state dict with 'position' and 'zoom'
        transition_frames: Number of interpolation frames
        easing_func: Easing function to use

    Returns:
        Updated screenshot_counter
    """
    if start_camera is None or end_camera is None:
        # If we don't have valid camera states, just take a single shot
        screenshot_filename = f"{screenshot_counter:06d}.png"
        save_path = str(output_dir / screenshot_filename)
        take_screenshot(instance, script_output_path, save_path=save_path)
        return screenshot_counter + 1

    # Check if camera actually needs to move
    pos_diff = math.sqrt(
        (end_camera["position"][0] - start_camera["position"][0]) ** 2
        + (end_camera["position"][1] - start_camera["position"][1]) ** 2
    )
    zoom_diff = abs(end_camera["zoom"] - start_camera["zoom"])

    # Skip transition if movement is minimal
    if pos_diff < 5 and zoom_diff < 0.1:
        transition_frames = 1

    # Capture interpolated frames
    for i in range(transition_frames):
        progress = i / max(transition_frames - 1, 1)

        # Interpolate camera state
        cam_x, cam_y, cam_zoom = interpolate_camera(
            start_camera["position"],
            end_camera["position"],
            start_camera["zoom"],
            end_camera["zoom"],
            progress,
            easing_func,
        )

        # Take screenshot at interpolated position
        screenshot_filename = f"{screenshot_counter:06d}.png"
        save_path = str(output_dir / screenshot_filename)

        take_screenshot(
            instance,
            script_output_path,
            save_path=save_path,
            camera_position=(cam_x, cam_y),
            camera_zoom=cam_zoom,
        )

        screenshot_counter += 1

        # Small delay to ensure Factorio processes the screenshot
        time.sleep(0.05)

    return screenshot_counter


def get_factory_bounds(instance):
    """Get the bounding box of all entities in the factory."""
    bounds_cmd = """/sc local entities = game.surfaces[1].find_entities_filtered{force=game.forces.player}
    if #entities == 0 then
        rcon.print("0,0,0,0")
    else
        local min_x, min_y = math.huge, math.huge
        local max_x, max_y = -math.huge, -math.huge
        for _, e in pairs(entities) do
            if e.position.x < min_x then min_x = e.position.x end
            if e.position.y < min_y then min_y = e.position.y end
            if e.position.x > max_x then max_x = e.position.x end
            if e.position.y > max_y then max_y = e.position.y end
        end
        rcon.print(string.format("%.2f,%.2f,%.2f,%.2f", min_x, min_y, max_x, max_y))
    end
    """

    try:
        bounds_result = instance.rcon_client.send_command(bounds_cmd)
        min_x, min_y, max_x, max_y = map(float, bounds_result.split(","))
        return min_x, min_y, max_x, max_y
    except:
        return 0, 0, 0, 0


def calculate_optimal_zoom(factory_width, factory_height, resolution="1920x1080"):
    """Calculate the optimal zoom level to fit the factory in the screenshot."""
    # Parse resolution
    width, height = map(int, resolution.split("x"))
    aspect_ratio = width / height

    # Base tiles visible at zoom level 1
    BASE_VISIBLE_HEIGHT = 25  # tiles visible vertically at zoom 1
    BASE_VISIBLE_WIDTH = BASE_VISIBLE_HEIGHT * aspect_ratio

    # Calculate required zoom based on both dimensions
    if factory_width > 0 and factory_height > 0:
        zoom_by_width = BASE_VISIBLE_WIDTH / factory_width
        zoom_by_height = BASE_VISIBLE_HEIGHT / factory_height

        # Use the smaller zoom to ensure entire factory is visible
        optimal_zoom = min(zoom_by_width, zoom_by_height)

        # Add padding (20% margin)
        optimal_zoom *= 1.2

        # Clamp zoom to reasonable values
        MIN_ZOOM = 0.1
        MAX_ZOOM = 4.0
        optimal_zoom = max(MIN_ZOOM, min(MAX_ZOOM, optimal_zoom))

        return round(optimal_zoom, 2)

    return 1.0


def get_latest_screenshot(script_output_path, max_wait=2):
    """Get the path to the latest screenshot in the script-output directory."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Get list of screenshot files
            screenshots = [
                f
                for f in os.listdir(script_output_path)
                if f.endswith(".png") and f.startswith("screenshot")
            ]

            if screenshots:
                # Sort by modification time to get the latest
                latest = max(
                    screenshots,
                    key=lambda x: os.path.getmtime(os.path.join(script_output_path, x)),
                )
                return os.path.join(script_output_path, latest)
        except Exception as e:
            print(f"Error checking for screenshots: {e}")

        time.sleep(0.1)  # Wait before checking again

    return None


def take_screenshot(
    instance,
    script_output_path: str,
    save_path: str = None,
    resolution: str = "1920x1080",
    center_on_factory: bool = True,
    camera_position=None,
    camera_zoom=None,
):
    """Take a screenshot using Factorio's game.take_screenshot API."""

    # Clear rendering
    instance.rcon_client.send_command("/sc rendering.clear()")

    # Use explicit camera parameters if provided
    if camera_position is not None and camera_zoom is not None:
        center_x, center_y = camera_position
        zoom = camera_zoom
        position_str = f", position={{x={center_x}, y={center_y}}}"
    elif center_on_factory:
        # Get factory bounds and center position
        min_x, min_y, max_x, max_y = get_factory_bounds(instance)

        if max_x != 0 or max_y != 0:
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            # Calculate factory dimensions with padding
            factory_width = max_x - min_x + 20
            factory_height = max_y - min_y + 20

            # Calculate optimal zoom
            zoom = calculate_optimal_zoom(factory_width, factory_height, resolution)

            position_str = f", position={{x={center_x}, y={center_y}}}"
        else:
            zoom = 1.0
            position_str = ""
    else:
        zoom = 1.0
        position_str = ""

    # Build and send the screenshot command
    command = (
        f"/sc game.take_screenshot({{zoom={zoom}, "
        f"show_entity_info=true, hide_clouds=true, hide_fog=true"
        f"{position_str}}})"
    )

    instance.rcon_client.send_command(command)
    time.sleep(0.2)  # Wait for screenshot to be saved

    # Get the latest screenshot file
    screenshot_path = get_latest_screenshot(script_output_path)
    if not screenshot_path:
        print("Screenshot file not found")
        return None

    # If save_path is provided, copy the screenshot there
    if save_path:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

            # Copy the file
            shutil.copy2(screenshot_path, save_path)
            return save_path
        except Exception as e:
            print(f"Failed to copy screenshot: {e}")
            return screenshot_path

    return screenshot_path


def capture_screenshots_gym(
    program_ids,
    output_dir: Path,
    script_output_path: str,
    gym_env: FactorioGymEnv,
    conn,
    max_steps: int,
    capture_interval: float = 0,
    transition_frames: int = 10,
    easing: str = "cubic",
    args=None,
):
    """
    Capture screenshots by replaying programs through a gym environment.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find the highest existing screenshot number
    def get_highest_screenshot_number():
        existing_files = list(output_dir.glob("*.png"))
        if not existing_files:
            return -1

        highest = -1
        for file in existing_files:
            try:
                num = int(file.stem)
                highest = max(highest, num)
            except ValueError:
                continue
        return highest

    # Initialize the screenshot counter
    screenshot_counter = get_highest_screenshot_number() + 1
    print(f"Starting screenshot numbering from {screenshot_counter}")

    # Get the instance from the gym environment
    instance = gym_env.unwrapped.instance

    # Set up screenshot hooks for key tools if requested
    if hasattr(args, "hook_tools") and args.hook_tools:
        screenshot_hook_counter = {"count": 0}

        def capture_after_tool(tool_instance, result):
            """Hook to capture screenshot after tool execution"""
            nonlocal screenshot_counter
            if screenshot_hook_counter["count"] % args.hook_frequency == 0:
                screenshot_filename = f"{screenshot_counter:06d}.png"
                save_path = str(output_dir / screenshot_filename)

                # Get current camera state for smooth transitions
                current_camera = get_camera_state_for_factory(instance)
                if current_camera:
                    take_screenshot(
                        instance,
                        script_output_path,
                        save_path=save_path,
                        camera_position=current_camera["position"],
                        camera_zoom=current_camera["zoom"],
                    )
                else:
                    take_screenshot(instance, script_output_path, save_path=save_path)

                screenshot_counter += 1
            screenshot_hook_counter["count"] += 1

        # Register hooks for important placement and connection tools
        hook_tools = [
            "place_entity",
            "place_entity_next_to",
            "connect_entities",
            "insert_item",
            "pickup_entity",
            "rotate_entity",
            "move_to",
        ]

        for tool_name in hook_tools:
            LuaScriptManager.register_post_tool_hook(
                instance, tool_name, capture_after_tool
            )

        print(f"Registered screenshot hooks for: {', '.join(hook_tools)}")

    # Reset the environment to get initial observation
    # Don't pass game_state - let the environment use its already-configured initial state
    # This matches what trajectory_runner does (passes None for fresh runs)
    observation, info = gym_env.reset()

    # Take initial screenshot and get initial camera state
    initial_camera = get_camera_state_for_factory(instance)
    if initial_camera is None:
        initial_camera = {"position": (0, 0), "zoom": 1.0}

    screenshot_filename = f"{screenshot_counter:06d}.png"
    save_path = str(output_dir / screenshot_filename)
    if take_screenshot(instance, script_output_path, save_path=save_path):
        print(f"Captured initial screenshot: {screenshot_filename}")
    screenshot_counter += 1

    # Track the current game state and camera position for smooth transitions
    current_game_state = None
    previous_camera = initial_camera

    # Process each program
    for idx, (program_id, created_at) in enumerate(program_ids):
        if idx >= max_steps:
            break

        # Load program state JIT
        program = get_program_state(conn, program_id)
        if not program or not program.code:
            print(f"Skipping program {program_id} - no code available")
            continue

        print(f"Processing program {idx + 1}/{len(program_ids)}: {program_id}")
        print(f"Code: {program.code[:100]}...")  # Show first 100 chars

        try:
            # Create action from program code with the current starting state
            # For the first program, current_game_state will be None (use env's initial state)
            # For subsequent programs, use the result state from the previous program
            action = Action(code=program.code, game_state=current_game_state)

            # If capture_interval is set, capture screenshots during execution
            if capture_interval > 0:
                import threading
                import time as time_module

                stop_capture = threading.Event()
                capture_exception = None

                def capture_during_execution():
                    nonlocal screenshot_counter, capture_exception
                    last_capture_time = time_module.time()

                    while not stop_capture.is_set():
                        current_time = time_module.time()
                        if current_time - last_capture_time >= capture_interval:
                            screenshot_filename = f"{screenshot_counter:06d}.png"
                            save_path = str(output_dir / screenshot_filename)

                            try:
                                if take_screenshot(
                                    instance, script_output_path, save_path=save_path
                                ):
                                    print(
                                        f"  Captured mid-execution screenshot: {screenshot_filename}"
                                    )
                                screenshot_counter += 1
                                last_capture_time = current_time
                            except Exception as e:
                                capture_exception = e

                        time_module.sleep(0.1)  # Check every 100ms

                capture_thread = threading.Thread(
                    target=capture_during_execution, daemon=True
                )
                capture_thread.start()

                # Step through the environment
                observation, reward, terminated, truncated, info = gym_env.step(action)

                # Stop background capture
                stop_capture.set()
                capture_thread.join(timeout=1.0)

                # Check if capture thread had any exceptions
                if capture_exception:
                    print(
                        f"  Warning: Screenshot capture thread error: {capture_exception}"
                    )
            else:
                # Step through the environment without time-based capture
                observation, reward, terminated, truncated, info = gym_env.step(action)

            print(
                f"  Reward: {reward:.2f}, Terminated: {terminated}, Truncated: {truncated}"
            )
            raw_text = BasicObservationFormatter.format_raw_text(
                observation["raw_text"]
            )
            print(raw_text)

            # Update current_game_state to the result of this program execution
            # This will be used as the starting state for the next program
            current_game_state = program.state

            # Get new camera state after program execution
            new_camera = get_camera_state_for_factory(instance)
            if new_camera is None:
                new_camera = previous_camera  # Keep previous if no factory visible

            # Select easing function
            if easing == "sine":
                easing_func = ease_in_out_sine
            elif easing == "linear":
                easing_func = lambda t: t  # noqa Linear, no easing
            else:
                easing_func = ease_in_out_cubic

            # Capture smooth transition to new camera state
            print(f"  Capturing camera transition ({transition_frames} frames)...")
            screenshot_counter = capture_camera_transition(
                instance,
                script_output_path,
                output_dir,
                screenshot_counter,
                previous_camera,
                new_camera,
                transition_frames=transition_frames,
                easing_func=easing_func,
            )

            # Update previous camera for next transition
            previous_camera = new_camera

            # If environment is terminated, we can't continue
            if terminated:
                print(f"  Environment terminated after program {idx + 1}")
                break

        except Exception as e:
            print(f"  Error executing program {program_id}: {e}")
            # On error, still update the state if the program has one
            if program.state:
                current_game_state = program.state

            # Still capture camera state even on error
            error_camera = get_camera_state_for_factory(instance)
            if error_camera is None:
                error_camera = previous_camera

            # Take a few frames to show error state
            for _ in range(3):
                screenshot_filename = f"{screenshot_counter:06d}.png"
                save_path = str(output_dir / screenshot_filename)
                if take_screenshot(
                    instance,
                    script_output_path,
                    save_path=save_path,
                    camera_position=error_camera["position"],
                    camera_zoom=error_camera["zoom"],
                ):
                    print(f"  Captured error-state screenshot: {screenshot_filename}")
                screenshot_counter += 1

            # Update camera for continuity
            previous_camera = error_camera
            continue

    # Add some final frames showing the completed state
    print("Capturing final state frames...")
    for i in range(10):
        # Sleep in the environment to show animation
        try:
            action = Action(code="sleep(15)")
            observation, reward, terminated, truncated, info = gym_env.step(action)
        except:
            pass  # Ignore errors during final frames

        screenshot_filename = f"{screenshot_counter:06d}.png"
        save_path = str(output_dir / screenshot_filename)

        if take_screenshot(instance, script_output_path, save_path=save_path):
            print(f"  Captured final frame {i + 1}/10: {screenshot_filename}")

        screenshot_counter += 1

    print(f"Screenshot capture complete. Total screenshots: {screenshot_counter - 1}")


def png_to_mp4(png_dir: Path, output_path: Path, framerate: int = 30):
    """Convert a directory of PNG files to an MP4 video using FFmpeg."""

    # Get all PNG files
    png_files = sorted(png_dir.glob("*.png"))
    if not png_files:
        print(f"No PNG files found in {png_dir}")
        return False

    print(f"Found {len(png_files)} PNG files to convert")

    # Create a temporary directory for continuous numbering
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create symlinks with continuous numbering
        for i, png_file in enumerate(png_files):
            link_name = temp_path / f"{i:06d}.png"
            link_name.symlink_to(png_file.absolute())

        # Run FFmpeg with scaling filter to ensure dimensions are divisible by 2
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-framerate",
            str(framerate),
            "-i",
            str(temp_path / "%06d.png"),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # Ensure dimensions are divisible by 2
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]

        print(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False

        print(f"Successfully created video: {output_path}")
        return True


def process_version(
    version: int,
    output_base: Path,
    script_output_path: str,
    framerate: int,
    max_steps: int,
    with_hooks: bool,
    skip_screenshots: bool,
    skip_video: bool,
    capture_interval: float,
    transition_frames: int = 10,
    easing: str = "cubic",
    args=None,
):
    """Process a single version: generate screenshots and create video."""

    version_dir = output_base / str(version)
    version_dir.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = get_db_connection()
    try:
        if not skip_screenshots:
            # Get program chain
            print(f"\nProcessing version {version}")
            print("Getting program chain from database...")

            program_ids = get_program_chain(conn, version)

            if not program_ids:
                print(f"No programs found for version {version}")
                return False

            print(f"Found {len(program_ids)} programs")

            # Create gym environment
            print("Creating gym environment...")
            gym_env = create_gym_environment(version)

            # Capture screenshots using gym environment
            print("Capturing screenshots using gym environment...")
            capture_screenshots_gym(
                program_ids,
                version_dir,
                script_output_path,
                gym_env,
                conn,
                max_steps,
                capture_interval=capture_interval,
                transition_frames=transition_frames,
                easing=easing,
                args=args,
            )

        if not skip_video:
            # Convert to video
            output_video = version_dir / "output.mp4"
            print("\nCreating video from screenshots...")
            success = png_to_mp4(version_dir, output_video, framerate)
            if success:
                print(f"Video saved to: {output_video}")
                return True
            else:
                print(f"Failed to create video for version {version}")
                return False

        return True

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate screenshots and create MP4 videos from Factorio program versions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single version with default settings
  %(prog)s 2755

  # Process multiple versions
  %(prog)s 2755 2757 2760

  # Custom output directory and framerate
  %(prog)s 2755 --output-dir my_videos --framerate 60

  # Only generate screenshots, skip video creation
  %(prog)s 2755 --skip-video

  # Only create video from existing screenshots
  %(prog)s 2755 --skip-screenshots

  # Disable hooks for faster processing (less detailed)
  %(prog)s 2755 --no-hooks
        """,
    )

    parser.add_argument(
        "versions",
        nargs="+",
        type=int,
        help="Version numbers to process",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default="videos",
        help="Base output directory for screenshots and videos (default: videos)",
    )

    parser.add_argument(
        "--framerate",
        "-f",
        type=int,
        default=30,
        help="Framerate for output video (default: 30)",
    )

    parser.add_argument(
        "--script-output-path",
        "-s",
        type=str,
        help="Path where Factorio saves screenshots (defaults to auto-detect based on platform)",
    )

    parser.add_argument(
        "--max-steps",
        "-m",
        type=int,
        default=1000,
        help="Maximum number of program steps to capture (default: 1000)",
    )

    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hooks for entity placement (faster but less detailed)",
    )

    parser.add_argument(
        "--skip-screenshots",
        action="store_true",
        help="Skip screenshot generation, only create video from existing PNGs",
    )

    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Skip video creation, only generate screenshots",
    )

    parser.add_argument(
        "--capture-interval",
        "-c",
        type=float,
        default=0,
        help="Capture screenshots every N seconds during program execution (0 = disabled, only capture after each program)",
    )
    parser.add_argument(
        "--transition-frames",
        "-t",
        type=int,
        default=10,
        help="Number of frames for smooth camera transitions between programs (default: 10)",
    )
    parser.add_argument(
        "--easing",
        type=str,
        default="cubic",
        choices=["cubic", "sine", "linear"],
        help="Easing function for camera transitions (default: cubic)",
    )
    parser.add_argument(
        "--hook-tools",
        action="store_true",
        help="Capture screenshots after tool executions (place_entity, connect_entities, etc.)",
    )
    parser.add_argument(
        "--hook-frequency",
        type=int,
        default=1,
        help="Capture screenshot every N tool executions when using --hook-tools (default: 1)",
    )

    args = parser.parse_args()

    # Auto-detect script output path if not provided
    if not args.script_output_path:
        if sys.platform == "darwin":  # macOS
            args.script_output_path = os.path.expanduser(
                "~/Library/Application Support/factorio/script-output"
            )
        elif sys.platform == "linux":
            args.script_output_path = os.path.expanduser("~/.factorio/script-output")
        elif sys.platform == "win32":
            args.script_output_path = os.path.expanduser(
                "~/AppData/Roaming/Factorio/script-output"
            )
        else:
            print(
                f"Warning: Could not auto-detect script output path for platform {sys.platform}"
            )
            print("Please specify with --script-output-path")
            sys.exit(1)

    # Validate script output path
    script_output_path = Path(args.script_output_path)
    if not script_output_path.exists():
        print(f"Warning: Script output path does not exist: {script_output_path}")
        print("Creating directory...")
        script_output_path.mkdir(parents=True, exist_ok=True)

    # Process each version
    output_base = Path(args.output_dir)
    output_base.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for version in args.versions:
        try:
            success = process_version(
                version,
                output_base,
                str(script_output_path),
                args.framerate,
                args.max_steps,
                not args.no_hooks,
                args.skip_screenshots,
                args.skip_video,
                args.capture_interval,
                args.transition_frames,
                args.easing,
                args,
            )
            if success:
                success_count += 1
        except Exception as e:
            print(f"Error processing version {version}: {e}")
            import traceback

            traceback.print_exc()

    print(f"\nProcessed {success_count}/{len(args.versions)} versions successfully")

    if success_count == len(args.versions):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
