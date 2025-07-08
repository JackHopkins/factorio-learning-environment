import os
import argparse
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

from data.screenshots_to_mp4 import png_to_mp4
from fle.env import FactorioInstance
from fle.commons.models.program import Program
from cluster.local.cluster_ips import get_local_container_ips

load_dotenv()


def get_program_chain_backtracking(conn, version: int):
    """Get the chain of programs for a specific version for the backtracking chain"""
    query = f"""
    SELECT meta, code, response, id, created_at FROM programs 
    WHERE version = {version}
    ORDER BY created_at ASC
    """

    model = "anthropic/claude-3.5-sonnet-open-router"

    with conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()
    data = [
        (x[-2], x[-1])
        for x in data
        if x[0]["model"] == model and not x[0]["error_occurred"]
    ]
    return data


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
    """Get the chain of programs for a specific version using recursive CTE"""

    # First get the most recent program id for this version
    latest_query = """
    SELECT id FROM programs 
    WHERE version = %s 
    AND state_json IS NOT NULL 
    ORDER BY created_at DESC 
    LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(latest_query, (version,))
        latest_result = cur.fetchone()
        if not latest_result:
            return []

        latest_id = latest_result[0]

        # Now use recursive CTE to get the full chain, but only fetch minimal fields
        recursive_query = """
        WITH RECURSIVE program_trace AS (
            -- Base case: start with most recent program
            SELECT 
                id,
                parent_id,
                created_at
            FROM programs
            WHERE id = %s

            UNION ALL

            -- Recursive case: get the parent program
            SELECT 
                p.id,
                p.parent_id,
                p.created_at
            FROM programs p
            INNER JOIN program_trace pt ON p.id = pt.parent_id
        )
        SELECT id, created_at FROM program_trace
        ORDER BY created_at ASC
        LIMIT 3000
        """

        cur.execute(recursive_query, (latest_id,))
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


def create_factorio_instance() -> FactorioInstance:
    """Create a Factorio instance for taking screenshots"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = FactorioInstance(
        address=ips[-1],  # Use last instance (less likely to be in use)
        tcp_port=tcp_ports[-1],
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=False,
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
    instance: FactorioInstance,
    conn,
    max_steps=1000,
):
    """
    Capture screenshots for each program state and after each entity placement,
    using sequential integer filenames.
    """
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
        instance.register_post_tool_hook(tool, capture_after_placement)

    # Process each program
    for idx, (program_id, created_at) in enumerate(program_ids):
        if idx >= max_steps:
            break

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

    for i in range(30):
        # Execute the program code which will trigger our hook for each place_entity call
        instance.eval("sleep(15)")

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


def capture_screenshots(
    program_ids,
    output_dir: str,
    script_output_path: str,
    instance: FactorioInstance,
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
    # 718
    backtracking_chain = True
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
            default="/Users/jackhopkins/Library/Application Support/factorio/script-output",
            help="path where the factorio script will save screenshots to",
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

        # Connect to database
        conn = get_db_connection()
        try:
            # Get program chain
            print(f"Getting program chain for version {args.version}")

            program_ids = (
                get_program_chain_backtracking(conn, args.version)
                if backtracking_chain
                else get_program_chain(conn, args.version)
            )

            if not program_ids:
                print(f"No programs found for version {args.version}")
                return

            print(f"Found {len(program_ids)} programs")

            # Create Factorio instance
            instance = create_factorio_instance()

            # Capture screenshots
            capture_screenshots_with_hooks(
                program_ids, str(version_dir), args.script_output_path, instance, conn
            )

            # Convert to video
            output_video = version_dir / "output.mp4"
            png_to_mp4(str(version_dir), str(output_video), args.framerate)
            print(f"Created video: {output_video}")

        finally:
            conn.close()


if __name__ == "__main__":
    main()
