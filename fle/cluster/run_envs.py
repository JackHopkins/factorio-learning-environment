#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import sys
import socket
from pathlib import Path
import shutil
import yaml
import zipfile

# Root directory - equivalent to ../ usage in shell script
ROOT_DIR = Path(__file__).parent.parent.parent


def setup_compose_cmd():
    candidates = [
        ["docker", "compose", "version"],
        ["docker-compose", "--version"],
    ]
    for cmd in candidates:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return " ".join(cmd[:2]) if cmd[0] == "docker" else "docker-compose"
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    print("Error: Docker Compose not found. Install Docker Desktop or docker-compose.")
    sys.exit(1)


class ComposeGenerator:
    """Compose YAML generator with centralized path handling."""

    rcon_password = "factorio"
    image = "factoriotools/factorio:1.1.110"
    map_gen_seed = 44340
    internal_rcon_port = 27015
    internal_game_port = 34197

    def __init__(
        self,
        root_dir: Path,
        attach_mod=False,
        save_file=None,
        scenario="default_lab_scenario",
    ):
        self.root_dir = root_dir
        self.arch = platform.machine()
        self.os_name = platform.system()
        self.attach_mod = attach_mod
        self.save_file = save_file
        self.scenario = scenario

    def _docker_platform(self):
        if self.arch in ["arm64", "aarch64"]:
            return "linux/arm64"
        else:
            return "linux/amd64"

    def _emulator(self):
        if self.arch in ["arm64", "aarch64"]:
            return "/bin/box64"
        else:
            return ""

    def _command(self):
        launch_command = f"--start-server-load-scenario {self.scenario}"
        if self.save_file:
            # Use only the basename inside the command
            launch_command = f"--start-server {Path(self.save_file).name}"
        args = [
            f"--port {self.internal_game_port}",
            f"--rcon-port {self.internal_rcon_port}",
            f"--rcon-password {self.rcon_password}",
            "--server-settings /opt/factorio/config/server-settings.json",
            "--map-gen-settings /opt/factorio/config/map-gen-settings.json",
            "--map-settings /opt/factorio/config/map-settings.json",
            "--server-adminlist /opt/factorio/config/server-adminlist.json",
            "--server-banlist /opt/factorio/config/server-banlist.json",
            "--server-whitelist /opt/factorio/config/server-whitelist.json",
            "--use-server-whitelist",
        ]
        if self.scenario == "open_world":
            args.append(f"--map-gen-seed {self.map_gen_seed}")
        if self.attach_mod:
            args.append("--mod-directory /opt/factorio/mods")
        factorio_bin = f"{self._emulator()} /opt/factorio/bin/x64/factorio".strip()
        return " ".join([factorio_bin, launch_command] + args)

    def _mod_path(self):
        if self.os_name == "Windows":
            appdata = os.environ.get("APPDATA")
            if not appdata:
                # Fallback to the typical path if APPDATA is missing
                appdata = Path.home() / "AppData" / "Roaming"
            return Path(appdata) / "Factorio" / "mods"
        elif self.os_name == "Darwin":
            return Path.home() / "Library" / "Application Support" / "factorio" / "mods"
        else:  # Linux
            return Path.home() / ".factorio" / "mods"

    def _save_path(self):
        return self.root_dir / ".fle" / "saves"

    def _copy_save(self, save_file: str):
        save_dir = self._save_path().resolve()
        save_file_name = Path(save_file).name

        # Ensure the file is a zip file
        if not save_file_name.lower().endswith(".zip"):
            raise ValueError(f"Save file '{save_file}' is not a zip file.")

        # Check that the zip contains a level.dat file
        with zipfile.ZipFile(save_file, "r") as zf:
            if "level.dat" not in zf.namelist():
                raise ValueError(
                    f"Save file '{save_file}' does not contain a 'level.dat' file."
                )

        shutil.copy2(save_file, save_dir / save_file_name)
        print(f"Copied save file to {save_dir / save_file_name}")

    def _mods_volume(self):
        return {
            "source": str(self._mod_path().resolve()),
            "target": "/opt/factorio/mods",
            "type": "bind",
        }

    def _save_volume(self):
        return {
            "source": str(self._save_path().resolve()),
            "target": "/opt/factorio/saves",
            "type": "bind",
        }

    def _screenshots_volume(self):
        return {
            "source": str((self.root_dir / ".fle" / "data" / "_screenshots").resolve()),
            "target": "/opt/factorio/script-output",
            "type": "bind",
        }

    def _scenarios_volume(self):
        scenarios_dir = self.root_dir / "fle" / "cluster" / "scenarios"
        if not scenarios_dir.exists():
            raise ValueError(f"Scenarios directory '{scenarios_dir}' does not exist.")
        return {
            "source": str(scenarios_dir.resolve()),
            "target": "/opt/factorio/scenarios",
            "type": "bind",
        }

    def _config_volume(self):
        config_dir = self.root_dir / "fle" / "cluster" / "config"
        if not config_dir.exists():
            raise ValueError(f"Config directory '{config_dir}' does not exist.")
        return {
            "source": str(config_dir.resolve()),
            "target": "/opt/factorio/config",
            "type": "bind",
        }

    def services_dict(self, num_instances):
        services = {}
        for i in range(num_instances):
            host_udp = self.internal_game_port + i
            host_tcp = self.internal_rcon_port + i
            volumes = [
                self._scenarios_volume(),
                self._config_volume(),
                self._screenshots_volume(),
            ]
            if self.save_file:
                volumes.append(self._save_volume())
            if self.attach_mod:
                volumes.append(self._mods_volume())
            services[f"factorio_{i}"] = {
                "image": self.image,
                "platform": self._docker_platform(),
                "command": self._command(),
                "deploy": {"resources": {"limits": {"cpus": "1", "memory": "1024m"}}},
                "entrypoint": [],
                "ports": [
                    f"{host_udp}:{self.internal_game_port}/udp",
                    f"{host_tcp}:{self.internal_rcon_port}/tcp",
                ],
                "pull_policy": "missing",
                "restart": "unless-stopped",
                "user": "factorio",
                "volumes": volumes,
            }
        return services

    def compose_dict(self, num_instances):
        return {"services": self.services_dict(num_instances)}

    def write(self, path: str, num_instances: int):
        # Handle save file copy if provided
        if self.save_file:
            save_dir = self.root_dir / ".fle" / "saves"
            save_dir.mkdir(parents=True, exist_ok=True)
            self._copy_save(self.save_file)
        data = self.compose_dict(num_instances)
        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)


class ClusterManager:
    """Simple class wrapper to manage platform detection, compose, and lifecycle."""

    def __init__(self):
        self.root_dir = ROOT_DIR
        self.compose_cmd = setup_compose_cmd()
        self.internal_rcon_port = ComposeGenerator.internal_rcon_port
        self.internal_game_port = ComposeGenerator.internal_game_port

    def _run_compose(self, args):
        cmd = self.compose_cmd.split() + args
        subprocess.run(cmd, check=True)

    def generate(self, num_instances, scenario, attach_mod=False, save_file=None):
        generator = ComposeGenerator(
            root_dir=self.root_dir,
            attach_mod=attach_mod,
            save_file=save_file,
            scenario=scenario,
        )
        generator.write("docker-compose.yml", num_instances)
        print(
            f"Generated docker-compose.yml with {num_instances} Factorio instance(s) using scenario {scenario}"
        )

    def _is_tcp_listening(self, port):
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(0.2)
            c.connect(("127.0.0.1", port))
            c.close()
            return True
        except OSError:
            return False

    def _find_port_conflicts(self, num_instances):
        listening = []
        for i in range(num_instances):
            tcp_port = self.internal_rcon_port + i
            if self._is_tcp_listening(tcp_port):
                listening.append(f"tcp/{tcp_port}")
        return listening

    def start(self, num_instances, scenario, attach_mod=False, save_file=None):
        listening = self._find_port_conflicts(num_instances)
        if listening:
            print("Error: Required ports are in use:")
            print("  " + ", ".join(listening))
            print(
                "It looks like a Factorio cluster (or another service) is running. "
                "Stop it with 'fle cluster stop' (or 'docker compose -f docker-compose.yml down' in fle/cluster) and retry."
            )
            sys.exit(1)

        self.generate(num_instances, scenario, attach_mod, save_file)

        print(
            f"Starting {num_instances} Factorio instance(s) with scenario {scenario}..."
        )
        self._run_compose(["-f", "docker-compose.yml", "up", "-d"])
        print(
            f"Factorio cluster started with {num_instances} instance(s) using scenario {scenario}"
        )

    def stop(self):
        if not Path("docker-compose.yml").exists():
            print("Error: docker-compose.yml not found. No cluster to stop.")
            sys.exit(1)
        print("Stopping Factorio cluster...")
        self._run_compose(["-f", "docker-compose.yml", "down"])
        print("Cluster stopped.")

    def restart(self):
        if not Path("docker-compose.yml").exists():
            print("Error: docker-compose.yml not found. No cluster to restart.")
            sys.exit(1)
        print(
            "Restarting existing Factorio services without regenerating docker-compose..."
        )
        self._run_compose(["-f", "docker-compose.yml", "restart"])
        print("Factorio services restarted.")


def start_cluster(num_instances, scenario, attach_mod=False, save_file=None):
    manager = ClusterManager()
    manager.start(
        num_instances=num_instances,
        scenario=scenario,
        attach_mod=attach_mod,
        save_file=save_file,
    )


def stop_cluster():
    manager = ClusterManager()
    manager.stop()


def restart_cluster():
    manager = ClusterManager()
    manager.restart()


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
        if not (1 <= args.number <= 33):
            print("Error: number of instances must be between 1 and 33.")
            sys.exit(1)
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
