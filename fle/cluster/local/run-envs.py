#!/usr/bin/env python3
import os
import platform
import argparse
from pathlib import Path
import asyncio
import aiodocker
from aiodocker.exceptions import DockerError

from enum import Enum

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


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
        self.dry_run = dry_run
        self.docker = aiodocker.Docker()

    async def _ensure_image(self):
        try:
            await self.docker.images.inspect(self.config.image_name)
        except DockerError:
            print(f"'{self.config.image_name}' image not found locally.")
            print("Pulling from Docker Hub...")
            await self.docker.images.pull(self.config.image_name)
            print("Image pulled successfully.")

    def _get_ports(self, instance_index: int) -> dict:
        return {
            f"{self.config.udp_port}/udp": self.config.udp_port + instance_index,
            f"{self.config.rcon_port}/tcp": self.config.rcon_port + instance_index,
        }

    def _get_volumes(self, instance_index: int) -> list:
        vols = {
            self.config.mods_path: {"bind": "/factorio/mods", "mode": "rw"},
            str(self.config.saves_path / str(instance_index)): {
                "bind": "/factorio/saves",
                "mode": "rw",
            },
            str((self.config.scenario_dir / self.config.scenario_name).resolve()): {
                "bind": f"/factorio/scenarios/{self.config.scenario_name}",
                "mode": "rw",
            },
            str(self.config.screenshots_dir.resolve()): {
                "bind": "/factorio/script-output",
                "mode": "rw",
            },
        }
        # HostConfig.Binds expects ["host:container:mode", ...]
        return [f"{host}:{b['bind']}:{b['mode']}" for host, b in vols.items()]

    def _get_environment(self) -> list:
        env = {
            "LOAD_LATEST_SAVE": "true",
            "PORT": str(self.config.udp_port),
            "RCON_PORT": str(self.config.rcon_port),
            "SERVER_SCENARIO": self.config.scenario_name,
            "SAVES": "/opt/factorio/saves",
            "CONFIG": "/opt/factorio/config",
            "MODS": "/opt/factorio/mods",
            "SCENARIOS": "/opt/factorio/scenarios",
        }
        # Docker API wants ["KEY=VALUE", ...]
        return [f"{k}={v}" for k, v in env.items()]

    async def convert_scenario2map(self, name: str, instance_index: int):
        save_dir = self.config.saves_path / str(instance_index)
        save_dir.mkdir(parents=True, exist_ok=True)

        save_zips = list(save_dir.glob("*.zip"))
        if not save_zips:
            print(f"No save found for {name}")
            print(f"Converting {self.config.scenario_name} to saved map...")
            config = {
                "Image": self.config.image_name,
                "Env": self._get_environment(),
                "HostConfig": {"Binds": self._get_volumes(instance_index)},
                "Entrypoint": ["/scenario2map.sh"],
                "Cmd": [self.config.scenario_name],
                "Platform": self.docker_platform,
            }
            container = await self.docker.containers.run(
                config=config, name=f"conv_{name}"
            )
            await container.wait()
            await container.delete()
            print("Scenario converted successfully.")

    async def start(self):
        await self._ensure_image()
        for i in range(self.num):
            (self.config.saves_path / str(i)).mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            for i in range(self.num):
                name = f"factorio_{i}"
                print(f"\nContainer name: {name}")
                print(f"Port mappings: {self._get_ports(i)}")
                print(f"Volume mounts: {self._get_volumes(i)}")
                print(f"Environment variables: {self._get_environment()}")
                print(f"Docker platform: {self.docker_platform}")
                print("\n" + "=" * 80)
            return

        # Launch all instances concurrently
        tasks = [self._start_instance(i) for i in range(self.num)]
        await asyncio.gather(*tasks)

    async def _start_instance(self, instance_index: int):
        name = f"factorio_{instance_index}"
        await self.convert_scenario2map(name, instance_index)
        config = {
            "Image": self.config.image_name,
            "Env": self._get_environment(),
            "HostConfig": {
                "PortBindings": {
                    f"{self.config.udp_port}/udp": [
                        {"HostPort": str(self.config.udp_port + instance_index)}
                    ],
                    f"{self.config.rcon_port}/tcp": [
                        {"HostPort": str(self.config.rcon_port + instance_index)}
                    ],
                },
                "Binds": self._get_volumes(instance_index),
                "RestartPolicy": {"Name": "unless-stopped"},
                "Memory": 1024 * 1024 * 1024,
            },
            "Platform": self.docker_platform,
        }
        await self.docker.containers.run(config=config, name=name)

    async def stop(self):
        # Stop & remove any container whose name starts with "factorio_"
        ctrs = await self.docker.containers.list(all=True)
        # Prepare concurrent stop/delete tasks
        tasks = []
        for ctr in ctrs:
            info = await ctr.show()
            nm = info.get("Name", "").lstrip("/")
            if nm.startswith("factorio_"):
                tasks.append(self._stop_and_delete(ctr))
        # Run all stops/deletes concurrently
        await asyncio.gather(*tasks)

    async def _stop_and_delete(self, ctr):
        await ctr.stop()
        await ctr.delete()

    async def restart(self):
        ctrs = await self.docker.containers.list(all=True)
        tasks = []
        for ctr in ctrs:
            info = await ctr.show()
            nm = info.get("Name", "").lstrip("/")
            if nm.startswith("factorio_"):
                tasks.append(ctr.restart())
        await asyncio.gather(*tasks)


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
        "--force-amd64", action="store_true", help="Force use of amd64 platform"
    )
    p.add_argument("--dry-run", action="store_true", help="Dry run")
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


async def main():
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
        await mgr.start()
    elif args.command == "stop":
        await mgr.stop()
    elif args.command == "restart":
        await mgr.restart()

    await mgr.docker.close()


if __name__ == "__main__":
    asyncio.run(main())
