import subprocess
import time

import yaml
import sys
from typing import Dict, Any


def generate_compose_config(num_instances: int, map: str) -> Dict[str, Any]:
    services = {}
    base_udp_port = 34197
    base_tcp_port = 27000

    for i in range(num_instances):
        service_name = f"factorio_{i}"
        services[service_name] = {
            "image": "factorio",
            "pull_policy": "never",
            "platform": "linux/amd64",
            "environment": [
                "SAVES=/opt/factorio/saves",
                "CONFIG=/opt/factorio/config",
                "MODS=/opt/factorio/mods",
                "SCENARIOS=/opt/factorio/scenarios",
                f"PORT={base_udp_port}",
                "RCON_PORT=27015",
            ],
            "volumes": [
                {
                    "type": "bind",
                    "source": "../scenarios/default_lab_scenario",
                    "target": "/opt/factorio/scenarios/default_lab_scenario",
                },
                {
                    "type": "bind",
                    "source": "../scenarios/open_world",
                    "target": "/opt/factorio/scenarios/open_world",
                },
                {
                    "type": "bind",
                    "source": "~/Applications/Factorio.app/Contents/Resources/mods",
                    "target": "/opt/factorio/mods",
                },
                {
                    "type": "bind",
                    "source": "../../data/_screenshots",
                    "target": "/opt/factorio/script-output",
                },
            ],
            "ports": [
                f"{base_udp_port + i}:{base_udp_port}/udp",
                f"{base_tcp_port + i}:27015/tcp",
            ],
            "restart": "unless-stopped",
            "user": "factorio",
            "entrypoint": [],
            "command": " ".join(
                [
                    "/opt/factorio/bin/x64/factorio",
                    f"--start-server-load-scenario {map}",
                    f"--port {base_udp_port}",
                    "--server-settings /opt/factorio/config/server-settings.json",
                    "--map-gen-settings /opt/factorio/config/map-gen-settings.json",
                    "--map-settings /opt/factorio/config/map-settings.json",
                    "--server-banlist /opt/factorio/config/server-banlist.json",
                    "--rcon-port 27015",
                    '--rcon-password "factorio"',
                    "--server-whitelist /opt/factorio/config/server-whitelist.json",
                    "--use-server-whitelist",
                    "--server-adminlist /opt/factorio/config/server-adminlist.json",
                    "--mod-directory /opt/factorio/mods",
                    "--map-gen-seed 44340",
                ]
            ),
            "deploy": {"resources": {"limits": {"cpus": "1", "memory": "1024m"}}},
        }

    return {"services": services}


def setup_docker_compose(num_instances: int, map: str):
    """Generate and write docker-compose.yml, then start the containers"""
    config = generate_compose_config(num_instances, map)

    # Write the configuration to docker-compose.yml
    with open(f"docker-compose-{num_instances}.yml", "w") as f:
        yaml.dump(config, f)

    # Start the containers
    subprocess.run(
        ["docker-compose", "up", "-d", f"docker-compose-{num_instances}.yml"]
    )

    # Wait for containers to be ready
    time.sleep(10)


if __name__ == "__main__":
    num_instances = 33
    map = "open_world"  # or default_lab_scenario
    if len(sys.argv) != 2:
        print("Usage: python create_docker_compose_config.py <number_of_instances>")
    else:
        num_instances = int(sys.argv[1])

    setup_docker_compose(num_instances, map)
    print(
        f"Created docker-compose-{num_instances}.yml for {num_instances} Factorio instances."
    )
