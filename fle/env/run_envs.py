#!/usr/bin/env python3
import os
import platform
import argparse
from pathlib import Path
import asyncio
import aiodocker
from aiodocker.exceptions import DockerError
from typing import List
import json

from enum import Enum

ROOT_DIR = Path(__file__).resolve().parent.parent

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Scenario(Enum):
    OPEN_WORLD = "open_world"
    DEFAULT_LAB_SCENARIO = "default_lab_scenario"


class Mode(Enum):
    SAVE_BASED = "save-based"
    SCENARIO = "scenario"


class PlatformConfig:
    def __init__(self):
        self.arch = platform.machine()
        self.os_name = platform.system()
        self.saves_path = ROOT_DIR / ".fle" / "saves"
        self.screenshots_dir = ROOT_DIR / "data" / "_screenshots"
        self.mods_path = self._detect_mods_path()
        self.image_name = "factoriotools/factorio:1.1.110"
        self.rcon_port = 27015
        self.udp_port = 34197
        self.scenario_name = Scenario.DEFAULT_LAB_SCENARIO.value
        self.scenario_dir = Path(__file__).parent.resolve() / "factorio" / "scenarios"
        self.server_config_dir = Path(__file__).parent.resolve() / "factorio" / "config"
        self.mode = Mode.SAVE_BASED.value
        self.temp_playing_dir = "/opt/factorio/temp/currently-playing"
        with open(self.server_config_dir / "rconpw", "r") as f:
            self.factorio_password = f.read().strip()

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
            await self.docker.images.pull(
                self.config.image_name, platform=self.docker_platform
            )
            print("Image pulled successfully.")

    def _get_ports(self, instance_index: int) -> dict:
        ports = {
            f"{self.config.udp_port}/udp": [
                {"HostPort": str(self.config.udp_port + instance_index)}
            ],
            f"{self.config.rcon_port}/tcp": [
                {"HostPort": str(self.config.rcon_port + instance_index)}
            ],
        }
        return ports

    def _get_volumes(self, instance_index: int, for_server: bool = True) -> list:
        vols = {
            self.config.mods_path: {"bind": "/factorio/mods", "mode": "rw"},
            str(self.config.saves_path / str(instance_index)): {
                "bind": "/factorio/saves",
                "mode": "rw",
            },
            str(self.config.scenario_dir.resolve()): {
                "bind": f"/factorio/scenarios/",
                "mode": "rw",
            },
            str(self.config.screenshots_dir.resolve()): {
                "bind": "/factorio/script-output",
                "mode": "rw",
            },
        }
        if for_server:
            vols[str(self.config.server_config_dir.resolve())] = {
                "bind": "/factorio/config",
                "mode": "rw",
            }
        # HostConfig.Binds expects ["host:container:mode", ...]
        return [f"{host}:{b['bind']}:{b['mode']}" for host, b in vols.items()]

    def _get_environment(self) -> list:
        env = {
            "LOAD_LATEST_SAVE": (
                "true" if self.config.mode == Mode.SAVE_BASED.value else "false"
            ),
            "PORT": str(self.config.udp_port),
            "RCON_PORT": str(self.config.rcon_port),
            "SERVER_SCENARIO": self.config.scenario_name,
            "DLC_SPACE_AGE": "false",
        }
        if self.config.mode == Mode.SCENARIO.value:
            env["PRESET"] = "default"
        # Docker API wants ["KEY=VALUE", ...]
        return [f"{k}={v}" for k, v in env.items()]

    def check_save_exists(self, instance_index: int):
        save_dir = self.config.saves_path / str(instance_index)
        save_dir.mkdir(parents=True, exist_ok=True)

        save_zips = list(save_dir.glob("*.zip"))
        return len(save_zips) > 0

    async def get_scenario2map_ctr(self, instance_index: int):
        config = {
            "Image": self.config.image_name,
            "Env": self._get_environment(),
            "HostConfig": {
                "Binds": self._get_volumes(instance_index, for_server=False)
            },
            "Entrypoint": ["/scenario2map.sh"],
            "Cmd": [self.config.scenario_name],
            "Platform": self.docker_platform,
        }
        return await self.docker.containers.run(
            config=config, name=f"conv_factorio_{instance_index}"
        )

    async def get_server_ctr(self, instance_index: int):
        config = {
            "Image": self.config.image_name,
            "Env": self._get_environment(),
            "HostConfig": {
                "PortBindings": self._get_ports(instance_index),
                "Binds": self._get_volumes(instance_index),
                # "RestartPolicy": {"Name": "unless-stopped"},
                "Memory": 1024 * 1024 * 1024,
            },
            "Platform": self.docker_platform,
        }
        if self.config.mode == Mode.SCENARIO.value:
            config["Entrypoint"] = ["/scenario.sh"]
            config["Cmd"] = [self.config.scenario_name]
        print(config)
        return await self.docker.containers.create_or_replace(
            config=config, name=f"factorio_{instance_index}"
        )

    async def get_containers_to_run(self):
        scenario2map_tasks = [
            self.get_scenario2map_ctr(i)
            for i in range(self.num)
            if not self.check_save_exists(i)
        ]
        server_tasks = [self.get_server_ctr(i) for i in range(self.num)]

        scenario2map_ctrs = await asyncio.gather(*scenario2map_tasks)
        server_ctrs = await asyncio.gather(*server_tasks)

        return scenario2map_ctrs, server_ctrs

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
        if self.config.mode == Mode.SAVE_BASED.value:
            scenario2map_ctrs = await asyncio.gather(
                *[
                    self.get_scenario2map_ctr(i)
                    for i in range(self.num)
                    if not self.check_save_exists(i)
                ]
            )
            await asyncio.gather(*[item.wait() for item in scenario2map_ctrs])
            await asyncio.gather(*[item.delete() for item in scenario2map_ctrs])

        server_ctrs = await asyncio.gather(
            *[self.get_server_ctr(i) for i in range(self.num)]
        )
        await asyncio.gather(*[item.start() for item in server_ctrs])

    async def stop(self):
        # Stop & remove any container whose name starts with "factorio_"
        ctrs = await self.docker.containers.list(filters={"name": ["/factorio_"]})
        tasks_stop = [ctr.stop() for ctr in ctrs]
        tasks_delete = [ctr.delete() for ctr in ctrs]
        await asyncio.gather(*tasks_stop)
        await asyncio.gather(*tasks_delete)

    async def restart(self):
        ctrs = await self.docker.containers.list(filters={"name": ["/factorio_"]})
        tasks = [ctr.restart() for ctr in ctrs]
        await asyncio.gather(*tasks)

    async def hot_reload_scenario(self):
        # Sync scenario files into the server's temp directory for hot-reload
        containers = await self.docker.containers.list(filters={"name": ["/factorio_"]})
        
        async def sync_container(ctr):
            cmd = (
                f"docker exec -u root {ctr.id} sh -c "
                f"'cp -a /factorio/scenarios/{self.config.scenario_name}/. {self.config.temp_playing_dir} && "
                f"chown -R factorio:factorio {self.config.temp_playing_dir}'"
            )
            
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if stdout:
                print(f"stdout: {stdout.decode()}")
            if stderr:
                print(f"stderr: {stderr.decode()}")
            print(f"Container {ctr.id} sync complete (exit code: {proc.returncode})")
        
        # Run all container syncs concurrently
        await asyncio.gather(*[sync_container(ctr) for ctr in containers])
        print("Hot-reload sync complete.")

    async def get_local_container_ips(self) -> tuple[List[str], List[int], List[int]]:
        """Get IP addresses of running Factorio containers in the local Docker setup."""
        # Get container IDs for factorio containers
        containers = await self.docker.containers.list(filters={"name": ["/factorio_"]})
        container_ids = [ctr.id for ctr in containers]
        print(container_ids)

        if not container_ids or container_ids[0] == "":
            print("No running Factorio containers found")
            return []

        ips = []
        udp_ports = []
        tcp_ports = []
        for container in containers:
            # Get container details in JSON format
            container_info = await container.show()
            # print(container_info)

            # Get host ports for UDP game port
            ports = container_info["NetworkSettings"]["Ports"]

            # Find the UDP port mapping
            for port, bindings in ports.items():
                if "/udp" in port and bindings:
                    udp_port = bindings[0]["HostPort"]
                    udp_ports.append(int(udp_port))

                if "/tcp" in port and bindings:
                    tcp_port = bindings[0]["HostPort"]
                    tcp_ports.append(int(tcp_port))

            # Append the IP address with the UDP port to the list
            ips.append("127.0.0.1")

        # order by port number
        udp_ports.sort(key=lambda x: int(x))
        tcp_ports.sort(key=lambda x: int(x))

        return ips, udp_ports, tcp_ports


def parse_args():
    p = argparse.ArgumentParser(description="Manage a local Factorio cluster")
    p.add_argument(
        "command",
        choices=["start", "stop", "restart", "hot-reload-scenario", "get-ips"],
        nargs="?",
        default="start",
    )
    p.add_argument(
        "--mode",
        choices=["scenario", "save-based"],
        default="save-based",
        help="Mode to run the server in",
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
    if args.mode == Mode.SCENARIO.value:
        config.mode = Mode.SCENARIO.value
    elif args.mode == Mode.SAVE_BASED.value:
        config.mode = Mode.SAVE_BASED.value

    mgr = FactorioClusterManager(docker_platform, config, args.n, args.dry_run)
    if args.command == "start":
        await mgr.start()
    elif args.command == "stop":
        await mgr.stop()
    elif args.command == "restart":
        await mgr.restart()
    elif args.command == "hot-reload-scenario":
        if config.mode == Mode.SAVE_BASED.value:
            raise ValueError("Hot-reload is not supported in save-based mode")
        await mgr.hot_reload_scenario()
    elif args.command == "get-ips":
        ips, udp_ports, tcp_ports = await mgr.get_local_container_ips()
        print(ips, udp_ports, tcp_ports)
    await mgr.docker.close()


if __name__ == "__main__":
    asyncio.run(main())
