#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

# Root directory - equivalent to ../ usage in shell script
ROOT_DIR = Path(__file__).parent.parent.parent


def setup_platform():
    """Detect and set host architecture"""
    arch = platform.machine()
    os_name = platform.system()

    if arch in ["arm64", "aarch64"]:
        emulator = "/bin/box64"
        docker_platform = "linux/arm64"
    else:
        emulator = ""
        docker_platform = "linux/amd64"

    # Detect OS for mods path
    if any(win_os in os_name for win_os in ["MINGW", "MSYS", "CYGWIN"]):
        # Windows detected
        # Use %APPDATA% which is available in Windows bash environments
        appdata = os.environ.get("APPDATA", "")
        if not appdata or appdata == "/Factorio/mods":
            mods_path = (
                Path(os.environ.get("USERPROFILE", ""))
                / "AppData"
                / "Roaming"
                / "Factorio"
                / "mods"
            )
        else:
            mods_path = Path(appdata) / "Factorio" / "mods"
    else:
        # Assume Unix-like OS (Linux, macOS)
        mods_path = (
            Path.home()
            / "Applications"
            / "Factorio.app"
            / "Contents"
            / "Resources"
            / "mods"
        )

    print(f"Detected architecture: {arch}, using platform: {docker_platform}")
    print(f"Using mods path: {mods_path}")

    return emulator, docker_platform, mods_path


def setup_compose_cmd():
    """Check for docker compose command"""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return "docker compose"
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Docker not found. Please install Docker.")
        sys.exit(1)


def generate_compose_file(
    num_instances,
    scenario,
    emulator,
    docker_platform,
    mods_path,
    attach_mod=False,
    save_file=None,
):
    """Generate the dynamic docker-compose.yml file"""
    command = f"--start-server-load-scenario {scenario}"

    # Build optional mods volume block based on ATTACH_MOD
    mods_volume = ""
    if attach_mod:
        mods_volume = f"    - source: {mods_path}\n      target: /opt/factorio/mods\n      type: bind\n"

    # Build optional save file volume block based on SAVE_ADDED
    save_volume = ""
    save_added = save_file is not None
    if save_added:
        # Check if SAVE_FILE is a .zip file
        if not save_file.endswith(".zip"):
            print("Error: Save file must be a .zip file.")
            sys.exit(1)

        # Create saves directory if it doesn't exist
        saves_dir = ROOT_DIR / ".fle" / "saves"
        saves_dir.mkdir(parents=True, exist_ok=True)

        # Get the save file name (basename)
        save_file_name = Path(save_file).name

        # Copy the save file to the local saves directory
        import shutil

        shutil.copy2(save_file, saves_dir / save_file_name)

        # Create variable for the container path
        # container_save_path = f"/opt/factorio/saves/{save_file_name}"

        save_volume = f"    - source: {ROOT_DIR / '.fle' / 'saves'}\n      target: /opt/factorio/saves\n      type: bind"
        command = f"--start-server {save_file_name}"

    # Validate scenario
    if scenario not in ["open_world", "default_lab_scenario"]:
        print("Error: Scenario must be either 'open_world' or 'default_lab_scenario'.")
        sys.exit(1)

    # Validate input
    if not isinstance(num_instances, int) or num_instances < 1 or num_instances > 33:
        print("Error: Number of instances must be between 1 and 33.")
        sys.exit(1)

    # Create the docker-compose file
    compose_content = """version: '3'

services:
"""

    # Add the specified number of factorio services
    for i in range(num_instances):
        udp_port = 34197 + i
        tcp_port = 27000 + i

        compose_content += f"""  factorio_{i}:
    image: factoriotools/factorio:1.1.110
    platform: ${{DOCKER_PLATFORM:-linux/amd64}}
    command: {emulator} /opt/factorio/bin/x64/factorio {command}
      --port 34197 --server-settings /opt/factorio/config/server-settings.json --map-gen-settings
      /opt/factorio/config/map-gen-settings.json --map-settings /opt/factorio/config/map-settings.json
      --server-banlist /opt/factorio/config/server-banlist.json --rcon-port 27015
      --rcon-password "factorio" --server-whitelist /opt/factorio/config/server-whitelist.json
      --use-server-whitelist --server-adminlist /opt/factorio/config/server-adminlist.json
      --mod-directory /opt/factorio/mods --map-gen-seed 44340
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1024m
    entrypoint: []
    ports:
    - {udp_port}:34197/udp
    - {tcp_port}:27015/tcp
    pull_policy: missing
    restart: unless-stopped
    user: factorio
    volumes:
    - source: ./scenarios
      target: /opt/factorio/scenarios
      type: bind
    - source: ./config
      target: /opt/factorio/config
      type: bind
    - source: {ROOT_DIR / ".fle" / "data" / "_screenshots"}
      target: /opt/factorio/script-output
      type: bind
{save_volume}
{mods_volume}"""

    # Write the docker-compose.yml file
    Path("docker-compose.yml").write_text(compose_content)

    print(
        f"Generated docker-compose.yml with {num_instances} Factorio instance(s) using scenario {scenario}"
    )


def start_cluster(num_instances, scenario, attach_mod=False, save_file=None):
    """Start Factorio cluster"""
    emulator, docker_platform, mods_path = setup_platform()
    compose_cmd = setup_compose_cmd()

    # Generate the docker-compose file
    generate_compose_file(
        num_instances,
        scenario,
        emulator,
        docker_platform,
        mods_path,
        attach_mod,
        save_file,
    )

    # Run the docker-compose file
    print(f"Starting {num_instances} Factorio instance(s) with scenario {scenario}...")

    # Execute docker compose command
    cmd = compose_cmd.split() + ["-f", "docker-compose.yml", "up", "-d"]
    subprocess.run(cmd, check=True)

    print(
        f"Factorio cluster started with {num_instances} instance(s) using platform {docker_platform} and scenario {scenario}"
    )


def stop_cluster():
    """Stop Factorio cluster"""
    compose_cmd = setup_compose_cmd()

    if not Path("docker-compose.yml").exists():
        print("Error: docker-compose.yml not found. No cluster to stop.")
        sys.exit(1)

    print("Stopping Factorio cluster...")
    cmd = compose_cmd.split() + ["-f", "docker-compose.yml", "down"]
    subprocess.run(cmd, check=True)
    print("Cluster stopped.")


def restart_cluster():
    """Restart Factorio cluster"""
    compose_cmd = setup_compose_cmd()

    if not Path("docker-compose.yml").exists():
        print("Error: docker-compose.yml not found. No cluster to restart.")
        sys.exit(1)

    print(
        "Restarting existing Factorio services without regenerating docker-compose..."
    )
    cmd = compose_cmd.split() + ["-f", "docker-compose.yml", "restart"]
    subprocess.run(cmd, check=True)
    print("Factorio services restarted.")


def show_help():
    """Show usage information"""
    script_name = os.path.basename(__file__)
    print(f"Usage: {script_name} [COMMAND] [OPTIONS]")
    print("")
    print("Commands:")
    print("  start         Start Factorio instances (default command)")
    print("  stop          Stop all running instances")
    print("  restart       Restart the current cluster with the same configuration")
    print("  help          Show this help message")
    print("")
    print("Options:")
    print("  -n NUMBER     Number of Factorio instances to run (1-33, default: 1)")
    print(
        "  -s SCENARIO   Scenario to run (open_world or default_lab_scenario, default: default_lab_scenario)"
    )
    print("  -sv SAVE_FILE, --use_save SAVE_FILE Use a .zip save file from factorio")
    print("  -m, --attach_mods Attach mods to the instances")
    print("")
    print("Examples:")
    print(
        f"  {script_name}                           Start 1 instance with default_lab_scenario"
    )
    print(
        f"  {script_name} -n 5                      Start 5 instances with default_lab_scenario"
    )
    print(
        f"  {script_name} -n 3 -s open_world        Start 3 instances with open_world"
    )
    print(
        f"  {script_name} start -n 10 -s open_world Start 10 instances with open_world"
    )
    print(f"  {script_name} stop                      Stop all running instances")
    print(f"  {script_name} restart                   Restart the current cluster")


def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Factorio Learning Environment Cluster Manager"
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start Factorio instances")
    start_parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        help="Number of Factorio instances to run (1-33, default: 1)",
    )
    start_parser.add_argument(
        "-s",
        "--scenario",
        choices=["open_world", "default_lab_scenario"],
        default="default_lab_scenario",
        help="Scenario to run (default: default_lab_scenario)",
    )
    start_parser.add_argument(
        "-sv", "--use_save", type=str, help="Use a .zip save file from factorio"
    )
    start_parser.add_argument(
        "-m", "--attach_mods", action="store_true", help="Attach mods to the instances"
    )

    # Stop command
    subparsers.add_parser("stop", help="Stop all running instances")

    # Restart command
    subparsers.add_parser("restart", help="Restart the current cluster")

    # Help command
    subparsers.add_parser("help", help="Show help message")

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, default to start
    if args.command is None:
        args.command = "start"
        # Create a namespace with default values for start command
        args.number = 1
        args.scenario = "default_lab_scenario"
        args.use_save = None
        args.attach_mods = False

    # Execute the appropriate command
    if args.command == "start":
        # Validate save file if provided
        if args.use_save and not Path(args.use_save).exists():
            print(f"Error: Save file '{args.use_save}' does not exist.")
            sys.exit(1)

        start_cluster(args.number, args.scenario, args.attach_mods, args.use_save)
    elif args.command == "stop":
        stop_cluster()
    elif args.command == "restart":
        restart_cluster()
    elif args.command == "help":
        show_help()
    else:
        print(f"Error: Unknown command '{args.command}'")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
