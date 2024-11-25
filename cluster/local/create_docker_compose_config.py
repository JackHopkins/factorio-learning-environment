import subprocess
import time

import yaml
import sys
from typing import Dict, Any


def generate_compose_config(num_instances: int) -> Dict[str, Any]:
    services = {}
    base_udp_port = 34197
    base_tcp_port = 27015

    for i in range(num_instances):
        service_name = f"factorio_{i}"
        services[service_name] = {
            "image": "factorio:latest",
            "platform": "linux/amd64",
            "environment": [
                f"SAVES=/opt/factorio/saves",
                f"CONFIG=/opt/factorio/config",
                f"MODS=/opt/factorio/mods",
                f"SCENARIOS=/opt/factorio/scenarios",
                f"PORT={base_udp_port}",
                f"RCON_PORT={base_tcp_port}"
            ],
            "volumes": [
                {
                    "type": "bind",
                    "source": "../scenarios/default_lab_scenario",
                    "target": "/opt/factorio/scenarios/default_lab_scenario"
                },
                {
                    "type": "bind",
                    "source": "~/Applications/Factorio.app/Contents/Resources/mods",
                    "target": "/opt/factorio/mods"
                }
            ],
            "ports": [
                f"{base_udp_port + i}:{base_udp_port}/udp",
                f"{base_tcp_port + i}:{base_tcp_port}/tcp"
            ],
            "restart": "unless-stopped",
            "user": "factorio",
            "entrypoint": [],
            "command": " ".join([
                "/opt/factorio/bin/x64/factorio",
                "--start-server-load-scenario default_lab_scenario",
                f"--port {base_udp_port}",
                "--server-settings /opt/factorio/config/server-settings.json",
                "--map-gen-settings /opt/factorio/config/map-gen-settings.json",
                "--map-settings /opt/factorio/config/map-settings.json",
                "--server-banlist /opt/factorio/config/server-banlist.json",
                f"--rcon-port {base_tcp_port}",
                '--rcon-password "factorio"',
                "--server-whitelist /opt/factorio/config/server-whitelist.json",
                "--use-server-whitelist",
                "--server-adminlist /opt/factorio/config/server-adminlist.json",
                "--mod-directory /opt/factorio/mods",
            ]),
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": "1",
                        "memory": "1024m"
                    }
                }
            }
        }

    return {"services": services}


def setup_docker_compose(num_instances: int):
    """Generate and write docker-compose.yml, then start the containers"""
    config = generate_compose_config(num_instances)

    # Write the configuration to docker-compose.yml
    with open(f'docker-compose-{num_instances}.yml', 'w') as f:
        yaml.dump(config, f)

    # Start the containers
    subprocess.run(["docker-compose", "up", "-d", f'docker-compose-{num_instances}.yml'])

    # Wait for containers to be ready
    time.sleep(10)

if __name__ == "__main__":
    num_instances = 8
    if len(sys.argv) != 2:
        print("Usage: python create_docker_compose_config.py <number_of_instances>")
    else:
        num_instances = int(sys.argv[1])

    setup_docker_compose(num_instances)
    print(f"Created docker-compose-{num_instances}.yml for {num_instances} Factorio instances.")
