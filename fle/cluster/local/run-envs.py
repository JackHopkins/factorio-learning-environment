#!/usr/bin/env python3
import os
import platform
import argparse
from pathlib import Path
import docker

import docker.errors

from enum import Enum

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

print(ROOT_DIR)

# Enable docker debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('docker').setLevel(logging.DEBUG)



class Scenario(Enum):
    OPEN_WORLD = "open_world"
    DEFAULT_LAB_SCENARIO = "default_lab_scenario"


class PlatformConfig:
    def __init__(self):
        self.arch = platform.machine()
        self.saves_path = ROOT_DIR / ".fle" / "saves"
        self.os_name = platform.system()
        self.fle_dir = ROOT_DIR
        self.mods_path = self._detect_mods_path()
        self.compose_path = (
            ROOT_DIR / "fle" / "cluster" / "local" / "docker-compose.yml"
        )
        self.rcon_port = 27015
        self.udp_port = 34197
        self.rcon_password = "factorio"
        self.map_gen_seed = 44340
        self.cluster_dir = ROOT_DIR / "fle" / "cluster"
        self.scenario_dir = self.cluster_dir / "scenarios"
        self.screenshots_dir = ROOT_DIR / "data" / "_screenshots"
        self.factorio_path = "/factorio/bin/x64/factorio"
        self.image_name = "factoriotools/factorio:1.1.110"
        self.scenario_name = Scenario.DEFAULT_LAB_SCENARIO.value

    def _detect_mods_path(self) -> str:
        if any(x in self.os_name for x in ("MINGW", "MSYS", "CYGWIN")):
            path = os.getenv("APPDATA", "")
            mods = Path(path) / "Factorio" / "mods"
            if mods.exists():
                return str(mods)
            return str(
                Path(os.getenv("USERPROFILE", ""))
                / "AppData"
                / "Roaming"
                / "Factorio"
                / "mods"
            )
        else:
            return str(
                Path.home()
                / "Applications"
                / "Factorio.app"
                / "Contents"
                / "Resources"
                / "mods"
            )


class FactorioClusterManager:
    def __init__(
        self,
        docker_platform: str,
        config: PlatformConfig,
        num_instances: int,
        dry_run: bool = False,
    ):
        self.docker_platform = docker_platform
        self.config = config
        self.num = num_instances
        self.client = docker.from_env()
        self.dry_run = dry_run

    def _ensure_image(self):
        """
        Ensure the Factorio Docker image is available locally; pull it if missing.
        """
        try:
            self.client.images.get(self.config.image_name)
        except docker.errors.ImageNotFound:
            print(f"'{self.config.image_name}' Image not found locally.")
            print("Pulling from Docker Hub...")
            self.client.images.pull(self.config.image_name, platform=self.docker_platform)
            print("Image pulled successfully.")

    def start(self):
        # Make sure the Factorio image is present
        self._ensure_image()
        # ensure save subdirs exist
        for i in range(self.num):
            (self.config.saves_path / str(i)).mkdir(parents=True, exist_ok=True)

        # render compose file
        for i in range(self.num):
            name = f"factorio_{i}"
            self.convert_scenario2map(name, i)
            if self.dry_run:
                print(f"\nContainer name: {name}")
                print(f"Port mappings: {self._get_ports(i)}")
                print(f"Volume mounts: {self._get_volumes(i)}")
                print(f"Environment variables: {self._get_environment()}")
                print(f"Docker platform: {self.docker_platform}")
                print("\n" + "=" * 80)
            else:
                self.client.containers.run(
                    self.config.image_name,
                    name=name,
                    ports=self._get_ports(i),
                    volumes=self._get_volumes(i),
                    environment=self._get_environment(),
                    detach=True,
                    platform=self.docker_platform,
                    restart_policy={"Name": "unless-stopped"},
                    mem_limit="1024m",
                )

    def stop(self, force: bool = False, timeout: int = 10):
        """
        Stop and remove all factorio containers.
        
        Args:
            force: If True, force kill containers instead of graceful stop
            timeout: Timeout in seconds for graceful stop (ignored if force=True)
        """
        containers_to_stop = []
        
        # Find all factorio containers
        for container in self.client.containers.list(all=True):
            if container.name.startswith("factorio_"):
                containers_to_stop.append(container)
        
        if not containers_to_stop:
            print("No factorio containers found to stop.")
            return
        
        print(f"Stopping {len(containers_to_stop)} factorio container(s)...")
        
        for container in containers_to_stop:
            try:
                print(f"Stopping container: {container.name}")
                
                if force:
                    # Force kill the container
                    container.kill()
                    print(f"Force killed: {container.name}")
                    container.remove()
                    print(f"Removed: {container.name}")
                else:
                    # Graceful stop with timeout
                    container.stop(timeout=timeout)
                    print(f"Gracefully stopped: {container.name}")
                
                
            except docker.errors.NotFound:
                print(f"Container {container.name} not found (already removed)")
            except docker.errors.APIError as e:
                print(f"Error stopping {container.name}: {e}")
            except Exception as e:
                print(f"Unexpected error with {container.name}: {e}")
        
        print("Stop operation completed.")

    def restart(self):
        self.stop()
        self.start()

    def convert_scenario2map(self, name: str, instance_index: int):
        save_dir = self.config.saves_path / str(instance_index)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing .zip saves
        save_zips = list(save_dir.glob("*.zip"))
        print(f"before:instance_index: {instance_index}, save_zips: {save_zips}")
        if not save_zips:
            print(f"No save found for {name}")
            print(f"Converting {self.config.scenario_name} to saved map...")
            conversion = self.client.containers.run(
                self.config.image_name,
                name=name,
                volumes=self._get_volumes(instance_index),
                environment=self._get_environment(),
                entrypoint=f"/scenario2map.sh",
                command=[self.config.scenario_name],
                detach=True,
                platform=self.docker_platform,
                auto_remove=True,
            )
            conversion.wait()
            save_zips = list(save_dir.glob("*.zip"))
            print("Scenario converted successfully.")
        print(f"after: instance_index: {instance_index}, save_zips: {save_zips}")
    
    def _get_ports(self, instance_index: int) -> dict:
        return {
            f"{self.config.udp_port}/udp": self.config.udp_port + instance_index,
            f"{self.config.rcon_port}/tcp": self.config.rcon_port + instance_index,
        }

    def _get_volumes(self, instance_index: int) -> dict:
        return {
            self.config.mods_path: {"bind": "/factorio/mods", "mode": "rw"},
            str(self.config.saves_path / str(instance_index)): {
                "bind": "/factorio/saves",
                "mode": "rw",
            },
            str((self.config.scenario_dir / self.config.scenario_name).resolve()): {
                "bind": f"/factorio/scenarios/{self.config.scenario_name}",
                "mode": "rw",
            },
            str((self.config.screenshots_dir).resolve()): {
                "bind": "/factorio/script-output",
                "mode": "rw",
            },
        }

    def _get_environment(self) -> dict:
        """Get environment variables for the container."""
        return {
            "LOAD_LATEST_SAVE": "true",  # "true" string not python bool !
            "PORT": str(self.config.udp_port),
            "RCON_PORT": str(self.config.rcon_port),
            "SERVER_SCENARIO": self.config.scenario_name,
        }


def parse_args():
    p = argparse.ArgumentParser(description="Manage a local Factorio cluster")
    p.add_argument(
        "command", choices=["start", "stop", "restart"], nargs="?", default="start"
    )
    p.add_argument("-n", type=int, default=1, help="Number of instances (1-33)")
    p.add_argument(
        "-s",
        choices=[s.value for s in Scenario],
        default=Scenario.DEFAULT_LAB_SCENARIO.value,
        help="Scenario to load",
    )
    p.add_argument(
        "--force-amd64",
        action="store_true",
        help="Force use of amd64 platform",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Force kill containers instead of graceful stop",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for graceful stop (default: 10)",
    )
    return p.parse_args()


def main():
    args = parse_args()
    config = PlatformConfig()

    docker_platform = (
        "linux/arm64" if config.arch in ("arm64", "aarch64") else "linux/amd64"
    )
    if args.force_amd64:
        docker_platform = "linux/amd64"

    if args.s == Scenario.OPEN_WORLD.value:
        config.scenario_name = Scenario.OPEN_WORLD.value
    elif args.s == Scenario.DEFAULT_LAB_SCENARIO.value:
        config.scenario_name = Scenario.DEFAULT_LAB_SCENARIO.value

    mgr = FactorioClusterManager(docker_platform, config, args.n, args.dry_run)

    if args.command == "start":
        mgr.start()
    elif args.command == "stop":
        mgr.stop(force=args.force, timeout=args.timeout)
    elif args.command == "restart":
        mgr.stop(force=args.force, timeout=args.timeout)
        mgr.start()


if __name__ == "__main__":
    main()
