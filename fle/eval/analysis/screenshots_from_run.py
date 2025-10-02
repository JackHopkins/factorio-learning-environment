import os
import argparse
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import time
import shutil

from fle.env.utils.camera import Camera

from fle.eval.analysis.screenshots_to_mp4 import png_to_mp4
from fle.env.instance import FactorioInstance
from fle.commons.models.program import Program
from fle.commons.cluster_ips import get_local_container_ips
from fle.env.lua_manager import LuaScriptManager

load_dotenv()


class ScreenshotInstance(FactorioInstance):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.rcon_client.send_command("/c global.camera = nil")

    def screenshot(
        self,
        script_output_path,
        resolution="1920x1080",
        save_path=None,
        zoom=None,
        center_on_factory=False,
    ):
        """
        Take a screenshot in game and optionally save it to a specific location.

        This does nothing in headless mode.

        Args:
            resolution (str, optional): Screenshot resolution (e.g., "1920x1080")
            save_path (str, optional): Path where to save the screenshot copy
            zoom (float, optional): Zoom level for the screenshot (e.g., 0.5 for zoomed out, 2.0 for zoomed in)

        Returns:
            str: Path to the saved screenshot, or None if failed
        """
        # Clear rendering
        camera: Camera = self.first_namespace._get_factory_centroid()
        POS_STRING = ""
        if camera:
            centroid = camera.position
            POS_STRING = (
                ", position={x=" + str(centroid.x) + ", y=" + str(centroid.y) + "}"
            )

        self.rcon_client.send_command("/sc rendering.clear()")

        # Use proper Factorio Lua API with blocking screenshot
        # Take screenshot and wait for completion
        command = (
            "/sc game.take_screenshot({player=1, zoom="
            + str(camera.zoom)
            + ", show_entity_info=true, hide_clouds=true, hide_fog=true "
            + POS_STRING
            + "}); game.set_wait_for_screenshots_to_finish()"
        )
        self.rcon_client.send_command(command)

        # Poll for screenshot completion by checking if file exists and is non-empty
        screenshot_path = self._wait_for_screenshot_completion(script_output_path)
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

    def _wait_for_screenshot_completion(self, script_output_path, max_wait=5.0):
        """
        Wait for screenshot completion by polling for screenshot.png to be updated and non-empty.
        Factorio saves screenshots as screenshot.png and overwrites it each time.
        """
        start_time = time.time()
        screenshot_path = os.path.join(script_output_path, "screenshot.png")
        initial_mtime = 0

        # Get initial modification time if file exists
        try:
            if os.path.exists(screenshot_path):
                initial_mtime = os.path.getmtime(screenshot_path)
        except Exception:
            pass

        while time.time() - start_time < max_wait:
            try:
                # Check if screenshot.png exists and has been updated
                if os.path.exists(screenshot_path):
                    current_mtime = os.path.getmtime(screenshot_path)
                    current_size = os.path.getsize(screenshot_path)

                    # File has been updated and is non-empty
                    if current_mtime > initial_mtime and current_size > 0:
                        return screenshot_path

            except Exception as e:
                print(f"Error checking for screenshot: {e}")

            time.sleep(0.1)  # Check every 100ms

        return None

    def _get_latest_screenshot(self, script_output_path, max_wait=0.1):
        """
        Get the path to screenshot.png in the script-output directory.
        Factorio saves screenshots as screenshot.png and overwrites it each time.
        """
        screenshot_path = os.path.join(script_output_path, "screenshot.png")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                if (
                    os.path.exists(screenshot_path)
                    and os.path.getsize(screenshot_path) > 0
                ):
                    return screenshot_path
            except Exception as e:
                print(f"Error checking for screenshot: {e}")

            time.sleep(0.01)  # Much shorter wait since API handles the heavy lifting

        return None


def get_db_connection():
    """Create a database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )


def get_program_chain(conn, version: int, limit: int = 3000):
    """Get all programs for a specific version ordered by time"""
    query = """
    SELECT id, created_at FROM programs
    WHERE version = %s
    AND state_json IS NOT NULL
    ORDER BY created_at ASC
    LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(query, (version, limit))
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


def create_factorio_instance(output_dir, script_output_path) -> ScreenshotInstance:
    """Create a Factorio instance for taking screenshots"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = ScreenshotInstance(
        address=ips[-1],  # Use last instance (less likely to be in use)
        tcp_port=tcp_ports[-1],
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=False,
    )
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find the highest existing screenshot number
    def get_highest_screenshot_number():
        existing_files = list(output_path.glob("*.png"))
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

    # Make screenshot counter accessible from the instance
    instance.screenshot_counter = screenshot_counter

    # Reset camera settings
    instance.rcon_client.send_command("/c global.camera = nil")

    def capture_after_placement(tool_instance, result):
        nonlocal screenshot_counter

        # Format screenshot name with the current counter value
        screenshot_filename = f"{screenshot_counter:06d}.png"
        screenshot_path = str(output_path / screenshot_filename)

        # Take the screenshot
        instance.screenshot(
            script_output_path=script_output_path,
            save_path=screenshot_path,
            resolution="1920x1080",
            center_on_factory=True,
        )
        print(f"Captured placement screenshot: {screenshot_filename}")

        # Increment the counter for the next screenshot
        screenshot_counter += 1
        # Keep instance counter in sync
        instance.screenshot_counter = screenshot_counter

    # Register post-tool hook for place_entity
    for tool in [
        "place_entity",
        "place_entity_next_to",
        "connect_entities",
        "harvest_resource",
        "move_to",
        "rotate_entity",
        "shift_entity",
    ]:
        LuaScriptManager.register_post_tool_hook(
            instance, tool, capture_after_placement
        )

    return instance


def get_existing_screenshots(output_dir: Path) -> set:
    """Get a set of indices for screenshots that already exist"""
    existing = set()
    for file in output_dir.glob("*.png"):
        try:
            # Extract the index from filename (e.g., "000123.png" -> 123)
            idx = int(file.stem)
            existing.add(idx)
        except ValueError:
            continue
    return existing


def capture_screenshots_with_hooks(
    program_ids,
    output_dir: str,
    script_output_path: str,
    instance: ScreenshotInstance,
    conn,
    max_steps=1000,
):
    """
    Capture screenshots for each program state and after each entity placement,
    using sequential integer filenames.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Use the screenshot counter from the instance (already initialized in create_factorio_instance)
    # This ensures we have a single, consistent counter throughout the process
    screenshot_counter = instance.screenshot_counter

    # Process each program
    total_programs = len(program_ids)
    for idx, (program_id, created_at) in enumerate(program_ids):
        if idx >= max_steps:
            print(f"Reached max_steps limit ({max_steps}), stopping")
            break

        # Print program progress with nice formatting
        print(f"\n{'=' * 20} Program {idx + 1:3d}/{total_programs:3d} {'=' * 20}")

        # Load program state JIT
        program = get_program_state(conn, program_id)
        if not program or not program.state:
            print(f"Skipping program {program_id} - no state available")
            continue

        # Reset game state
        instance.reset(program.state)

        # Execute the program code which will trigger our hook for each place_entity call
        instance.eval(program.code)

        # Take main program screenshot using the current counter value
        screenshot_filename = f"{screenshot_counter:06d}.png"
        screenshot_path = output_path / screenshot_filename

        instance.screenshot(
            script_output_path=script_output_path,
            save_path=str(screenshot_path),
            resolution="1920x1080",
            center_on_factory=True,
        )
        print(f"Captured final program screenshot: {screenshot_filename}")

        # Increment counter for the next screenshot
        screenshot_counter += 1
        # Keep instance counter in sync
        instance.screenshot_counter = screenshot_counter

    # Add a few final frames to show completion (optional)
    print("Adding final completion frames...")
    for i in range(5):  # Reduced from 30 to 5
        try:
            instance.eval("sleep(15)")
            screenshot_filename = f"{screenshot_counter:06d}.png"
            screenshot_path = output_path / screenshot_filename

            instance.screenshot(
                script_output_path=script_output_path,
                save_path=str(screenshot_path),
                resolution="1920x1080",
                center_on_factory=True,
            )
            print(f"Captured final completion frame: {screenshot_filename}")
            screenshot_counter += 1
            # Keep instance counter in sync
            instance.screenshot_counter = screenshot_counter
        except Exception as e:
            print(f"Error in final frames: {e}")
            break


def capture_screenshots(
    program_ids,
    output_dir: str,
    script_output_path: str,
    instance: ScreenshotInstance,
    conn,
    max_steps=1000,
):
    """Capture screenshots for each program state, skipping existing ones"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get set of existing screenshot indices
    existing_screenshots = get_existing_screenshots(output_path)
    total_needed = len(program_ids)
    existing_count = len(existing_screenshots)

    print(f"Found {existing_count} existing screenshots out of {total_needed} needed")

    instance.rcon_client.send_command("/c global.camera = nil")

    for idx, (program_id, created_at) in enumerate(program_ids):
        # Skip if screenshot already exists
        if idx in existing_screenshots:
            print(f"Skipping existing screenshot {idx + 1}/{total_needed}")
            continue

        if idx > max_steps:
            continue

        # Load program state JIT
        program = get_program_state(conn, program_id)
        if not program or not program.state:
            print(f"Skipping program {program_id} - no state available")
            continue

        # Load game state
        instance.reset(program.state)

        instance.eval(program.code)

        # instance.lua_script_manager = LuaScriptManager(instance.rcon_client, True)
        # Take screenshot
        screenshot_path = str(output_path / f"{idx:06d}.png")
        instance.screenshot(
            script_output_path=script_output_path,
            save_path=screenshot_path,
            resolution="1920x1080",
            center_on_factory=True,
        )
        print(f"Captured screenshot {idx + 1}/{total_needed}")


def main():
    for version in [
        2755,
        2757,
    ]:  # range(1892, 1895):#range(755, 775):#[764]:#[804, 798, 800, 598, 601, 576, 559 ]:
        parser = argparse.ArgumentParser(
            description="Capture Factorio program evolution screenshots"
        )
        parser.add_argument(
            "--version",
            "-v",
            type=int,
            default=version,
            help=f"Program version to capture (default: {version})",
        )
        parser.add_argument(
            "--output-dir",
            "-o",
            default="screenshots",
            help="Output directory for screenshots and video",
        )
        parser.add_argument(
            "--framerate", "-f", type=int, default=30, help="Framerate for output video"
        )
        parser.add_argument(
            "--script_output_path",
            "-s",
            type=str,
            default="/Users/harshitsharma/Library/Application Support/factorio/script-output",
            help="path where the factorio script will save screenshots to",
        )
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=1000,
            help="Maximum number of programs to process (default: 1000)",
        )

        # When running in IDE, use no args. When running from command line, parse args
        import sys

        if len(sys.argv) > 1:
            args = parser.parse_args()
        else:
            args = parser.parse_args([])

        # Create output directory structure
        output_base = Path(args.output_dir)
        version_dir = output_base / str(args.version)
        version_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing PNG files and prompt user
        existing_pngs = list(version_dir.glob("*.png"))
        if existing_pngs:
            print(
                f"Found {len(existing_pngs)} existing PNG files in {version_dir.absolute()}"
            )
            response = (
                input("Clear existing PNG files and restart? (Y/n): ").strip().lower()
            )
            if response in ["", "y", "yes"]:  # Empty string means default (Y)
                print("Clearing existing PNG files...")
                for png_file in existing_pngs:
                    png_file.unlink()
                print(f"Cleared {len(existing_pngs)} PNG files")
            else:
                print("User chose not to clear existing files. Exiting with no-op.")
                return

        print(f"Screenshots will be saved to: {version_dir.absolute()}")
        print(f"Video will be saved to: {output_base.absolute()}/{args.version}.mp4")

        # Connect to database
        conn = get_db_connection()
        try:
            # Get program chain
            print(
                f"Getting program chain for version {args.version} (limit: {args.limit})"
            )

            program_ids = get_program_chain(conn, args.version, args.limit)

            if not program_ids:
                print(f"No programs found for version {args.version}")
                print("Script finished - exiting")
                return

            print(f"Found {len(program_ids)} programs")

            # Create Factorio instance
            print("Creating Factorio instance...")
            instance = create_factorio_instance(version_dir, args.script_output_path)

            # Capture screenshots
            print("Starting screenshot capture...")
            capture_screenshots_with_hooks(
                program_ids,
                str(version_dir),
                args.script_output_path,
                instance,
                conn,
                max_steps=args.limit,
            )
            print("Screenshot capture completed!")

            # Convert to video
            print("Converting screenshots to video...")
            output_video = output_base / f"{args.version}.mp4"
            try:
                png_to_mp4(str(version_dir), str(output_video), args.framerate)
                print(f"Successfully created video: {output_video}")
            except Exception as e:
                print(f"Failed to create video: {e}")

        except Exception as e:
            print(f"Error during processing: {e}")
            print("Script encountered an error - exiting")
        finally:
            # Clean up resources
            try:
                if "instance" in locals():
                    instance.cleanup()
                    print("Factorio instance cleaned up")
            except Exception as e:
                print(f"Warning: Failed to cleanup instance: {e}")

            conn.close()
            print(f"Completed processing version {args.version}")
            print("Script finished successfully - exiting")
            break  # Exit after processing one version


if __name__ == "__main__":
    main()
