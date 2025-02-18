import os
import argparse
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

from data.screenshots_to_mp4 import png_to_mp4
from instance import FactorioInstance
from models.program import Program
from models.game_state import GameState
from cluster.local.cluster_ips import get_local_container_ips

load_dotenv()


def get_db_connection():
    """Create a database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
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
        all_technologies_researched=False
    )
    return instance


def capture_screenshots(program_ids, output_dir: str, instance: FactorioInstance, conn):
    """Capture screenshots for each program state"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for idx, (program_id, created_at) in enumerate(program_ids):
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
            save_path=screenshot_path,
            resolution="1920x1080",
            center_on_factory=True
        )
        print(f"Captured screenshot {idx + 1}/{len(program_ids)}")


def main():
    # Default version for running in IDE
    DEFAULT_VERSION = 560

    parser = argparse.ArgumentParser(description='Capture Factorio program evolution screenshots')
    parser.add_argument('--version', '-v', type=int, default=DEFAULT_VERSION,
                        help=f'Program version to capture (default: {DEFAULT_VERSION})')
    parser.add_argument('--output-dir', '-o', default='screenshots',
                        help='Output directory for screenshots and video')
    parser.add_argument('--framerate', '-f', type=int, default=30,
                        help='Framerate for output video')

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
        program_ids = get_program_chain(conn, args.version)
        if not program_ids:
            print(f"No programs found for version {args.version}")
            return

        print(f"Found {len(program_ids)} programs")

        # Create Factorio instance
        instance = create_factorio_instance()

        # Capture screenshots
        capture_screenshots(program_ids, str(version_dir), instance, conn)

        # Convert to video
        output_video = version_dir / "output.mp4"
        png_to_mp4(str(version_dir), str(output_video), args.framerate)
        print(f"Created video: {output_video}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()