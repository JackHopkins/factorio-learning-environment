#!/usr/bin/env python3
import os
import platform
import argparse
from pathlib import Path
import docker

from enum import Enum

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

print(ROOT_DIR)


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

    def start(self, scenario: str, use_latest: bool):
        # ensure save subdirs exist
        if use_latest:
            for i in range(self.num):
                (self.config.saves_path / str(i)).mkdir(parents=True, exist_ok=True)

        # render compose file
        for i in range(self.num):
            name = f"factorio_{i}"
            ports = {
                f"{self.config.udp_port}/udp": self.config.udp_port + i,
                f"{self.config.rcon_port}/tcp": self.config.rcon_port + i,
            }
            command = [
                f"/opt/factorio/bin/x64/factorio",
                self._get_start_command(use_latest),
                *self._get_connection_flags(),
                *self._get_server_settings(),
            ]
            if self.dry_run:
                print(name)
                print(ports)
                print(" ".join(command))
                print(self._get_volumes(i))
                print(self.docker_platform)
                print("-" * 100)
            else:
                self.client.containers.run(
                    "factorio",
                    command=command,
                    name=name,
                    ports=ports,
                    volumes=self._get_volumes(i),
                    detach=True,
                    platform=self.docker_platform,
                    restart_policy={"Name": "unless-stopped"},
                    mem_limit="1024m",
                )

    def stop(self):
        for container in self.client.containers.list(all=True):
            if container.name.startswith("factorio_"):
                container.stop()
                container.remove()

    def restart(self, scenario: str, use_latest: bool):
        self.stop()
        self.start(scenario, use_latest)

    def _get_start_command(self, use_latest: bool) -> str:
        return (
            f"--start-server-load-latest"
            if use_latest
            else f"--start-server-load-scenario {self.config.scenario}"
        )

    def _get_connection_flags(self) -> list[str]:
        return [
            "--rcon-port",
            str(self.config.rcon_port),
            "--rcon-password",
            self.config.rcon_password,
            "--port",
            str(self.config.udp_port),
        ]

    def _get_server_settings(self) -> list[str]:
        server_setting = (
            "--server-settings",
            "/opt/factorio/config/server-settings.json",
        )
        map_gen_settings = (
            "--map-gen-settings",
            "/opt/factorio/config/map-gen-settings.json",
        )
        map_settings = (
            "--map-settings",
            "/opt/factorio/config/map-settings.json",
        )
        mod_directory = (
            "--mod-directory",
            "/opt/factorio/mods",
        )
        map_gen_seed = (
            "--map-gen-seed",
            str(self.config.map_gen_seed),
        )
        return [
            *server_setting,
            *map_gen_settings,
            *map_settings,
            *mod_directory,
            *map_gen_seed,
        ]

    def _get_volumes(self, instance_index: int) -> dict:
        return {
            self.config.mods_path: {"bind": "/opt/factorio/mods", "mode": "rw"},
            str(self.config.saves_path / str(instance_index)): {
                "bind": "/opt/factorio/saves",
                "mode": "rw",
            },
            str((self.config.scenario_dir / self.config.scenario).resolve()): {
                "bind": f"/opt/factorio/scenarios/{self.config.scenario}",
                "mode": "rw",
            },
            str((self.config.screenshots_dir).resolve()): {
                "bind": "/opt/factorio/script-output",
                "mode": "rw",
            },
        }


def parse_args():
    p = argparse.ArgumentParser(description="Manage a local Factorio cluster")
    p.add_argument(
        "command", choices=["start", "stop", "restart"], nargs="?", default="start"
    )
    p.add_argument("-n", type=int, default=1, help="Number of instances (1-33)")
    p.add_argument(
        "-s",
        choices=Scenario,
        default=Scenario.DEFAULT_LAB_SCENARIO.value,
        help="Scenario to load",
    )
    p.add_argument(
        "-l", action="store_true", help="Use latest save instead of scenario"
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
        config.scenario = Scenario.OPEN_WORLD.value
    elif args.s == Scenario.DEFAULT_LAB_SCENARIO.value:
        config.scenario = Scenario.DEFAULT_LAB_SCENARIO.value

    mgr = FactorioClusterManager(docker_platform, config, args.n, args.dry_run)

    if args.command == "start":
        mgr.start(args.s, args.l)
    elif args.command == "stop":
        mgr.stop()
    elif args.command == "restart":
        mgr.restart(args.s, args.l)


if __name__ == "__main__":
    main()
