# Local Factorio Cluster

This directory contains scripts and configuration files for running and managing multiple Factorio game servers locally using Docker containers.

## Overview

The system allows you to:
- Create and manage multiple Factorio server instances using Docker
- Automatically connect to and initialize each server instance
- Configure server settings, ports, and resources for each instance
- Share mods and scenarios across instances

## Files

- `create_docker_compose_config.py` - Generates Docker Compose configuration for multiple Factorio instances
- `cluster_ips.py` - Utility for retrieving IP addresses and ports of running Factorio containers
- `factorio_server_login.py` - Automates the process of connecting to and initializing each server instance
- `docker-compose-4.yml` - Example configuration for running 4 Factorio server instances

## Setup and Usage

### Prerequisites

- Docker installed and running
- Python 3.x with required packages:
  - PyYAML
  - psutil
  - pyautogui
  - dotenv
- Factorio game client installed locally

### Creating Server Instances

1. Generate a Docker Compose configuration:
```bash
python create_docker_compose_config.py <number_of_instances>
```

For example, to create 4 instances:
```bash
python create_docker_compose_config.py 4
```

### Server Configuration

Each Factorio instance is configured with:
- Resource limits: 1 CPU core and 1024MB memory
- Shared scenarios directory
- Shared mods directory
- Unique UDP port for game traffic (starting at 34197)
- Unique TCP port for RCON (starting at 27015)

### Server Initialization

To connect to and initialize all server instances:
```bash
python factorio_server_login.py
```

This script will:
1. Detect running Factorio containers
2. Launch the Factorio client
3. Automatically connect to each server from the client (necessary to initialise the game servers)
4. Initialize necessary configurations

## Port Mappings

- Game ports (UDP): 34197-34200
- RCON ports (TCP): 27015-27018

## Volume Mounts

The following directories are mounted in each container:
- Scenarios: `../scenarios/default_lab_scenario`
- Mods: `~/Applications/Factorio.app/Contents/Resources/mods`

## Notes

- The server instances use the `factorio:latest` Docker image (which you can build from the provided Dockerfile in the `docker` directory)
- Each instance runs with the `default_lab_scenario` by default - which is a laboratory environment.
- RCON password is set to "factorio"
- Containers are configured to restart unless stopped manually
- Screen coordinates in `factorio_server_login.py` may need adjustment based on your display resolution

## Troubleshooting

If you encounter issues:
1. Ensure Docker is running and has sufficient resources
2. Check container logs using `docker logs factorio_<instance_number>`
3. Verify port availability using `netstat` or similar tools
4. Adjust screen coordinates in `factorio_server_login.py` if automation fails