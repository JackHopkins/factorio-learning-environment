import argparse
import asyncio
import aiodocker
from aiodocker.exceptions import DockerError
from typing import List, Dict

from fle.services.docker.config import DockerConfig, Scenario, Mode


class FactorioHeadlessServer:
    instance_id: int
    config: DockerConfig
    docker: aiodocker.Docker

    def __init__(
        self,
        instance_id: int,
        docker_config: DockerConfig,
    ):
        self.instance_id = instance_id
        self.config = docker_config
    
    @property
    def rcon_port(self) -> int:
        return self.config.rcon_port + self.instance_id
    
    @property
    def udp_port(self) -> int:
        return self.config.udp_port + self.instance_id
    
    @property
    def address(self) -> str:
        return self.config.address
    
    @property
    def container_name(self) -> str:
        return f"{self.config.name_prefix}{self.instance_id}"
    
    @property
    def rcon_password(self) -> str:
        return self.config.factorio_password

    def connect(self):
        self.docker = aiodocker.Docker()

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
    
    def _get_save_volume(self) -> str:
        return {
            self.config.mods_path: {"bind": "/factorio/mods", "mode": "rw"},
            str(self.config.saves_path / str(self.instance_id)): {
                "bind": "/factorio/saves",
                "mode": "rw",
            },
        }

    async def restart(self, save_name: str = None):
        ctr = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}{self.instance_id}"]}
        )
        if len(ctr) == 0:
            raise Exception(
                f"Container {self.config.name_prefix}{self.instance_id} not found"
            )
        ctr = ctr[0]
        if save_name:
            self._make_save_latest(save_name)
        await ctr.restart()

    def _make_save_latest(self, save_name: str):
        save_dir = self.config.saves_path / str(self.instance_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{save_name}.zip"
        if not save_path.exists():
            raise Exception(f"Save {save_name} not found")
        save_path.touch(exist_ok=True)


class FactorioHeadlessClusterManager:
    def __init__(
        self,
        config: DockerConfig,
        docker_platform: str,
        num_instances: int,
        dry_run: bool = False,
    ):
        self.docker_platform = docker_platform
        self.config = config
        self.num = num_instances
        self.dry_run = dry_run
        self.docker = aiodocker.Docker()
        self.docker_configs_raw = {}

    @property
    def servers(self) -> Dict[int, FactorioHeadlessServer]:
        if not hasattr(self, '_servers'):
            self._servers = {i: FactorioHeadlessServer(i, self.config) for i in range(self.num)}
        return self._servers
    
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
            "MODE": self.config.mode,
            # "SAVE_NAME": save_name,
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
            config=config, name=f"conv_{self.config.name_prefix}{instance_index}"
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
            config=config, name=f"{self.config.name_prefix}{instance_index}"
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
                name = f"{self.config.name_prefix}{i}"
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
        ctrs = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}"]}
        )
        tasks_stop = [ctr.stop() for ctr in ctrs]
        tasks_delete = [ctr.delete() for ctr in ctrs]
        await asyncio.gather(*tasks_stop)
        await asyncio.gather(*tasks_delete)

    async def restart(self):
        ctrs = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}"]}
        )
        tasks = [ctr.restart() for ctr in ctrs]
        await asyncio.gather(*tasks)

    async def hot_reload_scenario(self):
        # Sync scenario files into the server's temp directory for hot-reload
        containers = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}"]}
        )

        async def sync_container(ctr):
            cmd = (
                f"docker exec -u root {ctr.id} sh -c "
                f"'cp -a /factorio/scenarios/{self.config.scenario_name}/. {self.config.temp_playing_dir} && "
                f"chown -R factorio:factorio {self.config.temp_playing_dir}'"
            )

            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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

    async def attach_docker_configs(self):
        """Attach docker config to FactorioClusterManager"""
        containers = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}"]}
        )
        container_ids = [ctr.id for ctr in containers]
        if not container_ids or container_ids[0] == "":
            print("No running Factorio containers found")
            return
        tasks = [ctr.show() for ctr in containers]
        container_infos = await asyncio.gather(*tasks)
        info_to_keep = [
            "Id",
            "Name",
            "State",
            "Image",
            "HostConfig",
            "Config",
            "LogPath",
            "RestartCount",
            "Mounts",
        ]
        hostconfig_to_keep = [
            "PortBindings",
            "Binds",
            "Memory",
            "RestartPolicy",
            "NetworkMode",
        ]
        config_to_keep = ["Env", "Entrypoint", "Cmd", "WorkingDir"]
        network_to_keep = ["Ports", "IPAddress", "Gateway"]
        for container_info in container_infos:
            self.docker_configs_raw[container_info["Name"]] = {
                k: container_info[k] for k in info_to_keep
            }
            self.docker_configs_raw[container_info["Name"]]["Config"] = {
                k: container_info["Config"][k] for k in config_to_keep
            }
            self.docker_configs_raw[container_info["Name"]]["NetworkSettings"] = {
                k: container_info["NetworkSettings"][k] for k in network_to_keep
            }
            self.docker_configs_raw[container_info["Name"]]["HostConfig"] = {
                k: container_info["HostConfig"][k] for k in hostconfig_to_keep
            }

    async def get_local_container_ips(self) -> tuple[List[str], List[int], List[int]]:
        """Get IP addresses of running Factorio containers in the local Docker setup."""
        # Get container IDs for factorio containers
        containers = await self.docker.containers.list(
            filters={"name": [f"/{self.config.name_prefix}"]}
        )
        container_ids = [ctr.id for ctr in containers]

        if not container_ids or container_ids[0] == "":
            print("No running Factorio containers found")
            return ([], [], [])

        ips = []
        udp_ports = []
        tcp_ports = []
        tasks = [ctr.show() for ctr in containers]
        container_infos = await asyncio.gather(*tasks)

        for container_info in container_infos:
            ports = container_info["NetworkSettings"]["Ports"]

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
    config = DockerConfig()

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

    mgr = FactorioHeadlessClusterManager(config, docker_platform, args.n, args.dry_run)
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
    await mgr.attach_docker_configs()
    await mgr.docker.close()


if __name__ == "__main__":
    asyncio.run(main())
