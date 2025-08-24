# Local Factorio Cluster

This directory contains scripts and configuration files for running and managing multiple Factorio game servers locally using Docker containers.

## Overview

The system allows you to:

- Create and manage multiple Factorio server instances using Docker
- Automatically connect to and initialize each server instance
- Configure server settings, ports, and resources for each instance
- Share scenarios across instances
- Choose between different scenarios (open_world or default_lab_scenario)

## `run-envs.sh`

 - Main script for generating compose yaml
 - Running and managing Factorio instances with options for scenario selection

## Setup and Usage

### Prerequisites

- Docker installed and running
- Optional: Factorio game client installed locally

### Managing Server Instances with run-envs.sh

The `run-envs.sh` script provides a convenient way to start, stop, and manage Factorio server instances.

#### Basic Usage

```bash
# Start a single instance with default settings (default_lab_scenario)
./run-envs.sh

# Start 5 instances with default scenario
./run-envs.sh -n 5

# Start 3 instances with open_world scenario
./run-envs.sh -n 3 -s open_world

# Stop all running instances
./run-envs.sh stop

# Restart the current cluster with the same configuration
./run-envs.sh restart

# Show help information
./run-envs.sh help
```

#### Command Line Options

- `-n NUMBER` - Number of Factorio instances to run (1-33, default: 1)
- `-s SCENARIO` - Scenario to run (open_world or default_lab_scenario, default: default_lab_scenario)

#### Available Commands

- `start` - Start Factorio instances (default command)
- `stop` - Stop all running instances
- `restart` - Restart the current cluster with the same configuration
- `help` - Show help information

#### Examples with Explicit Commands

```bash
# Start 10 instances with open_world scenario
./run-envs.sh start -n 10 -s open_world

# Restart the current cluster
./run-envs.sh restart
```


### Server Configuration

Each Factorio instance is configured with:

- Resource limits: 1 CPU core and 1024MB memory
- Shared scenarios directory
- Unique UDP port for game traffic (starting at 34197)
- Unique TCP port for RCON (starting at 27015)
- Choice of scenario (open_world or default_lab_scenario)

## Port Mappings

- Game ports (UDP): 34197 + instance_number
- RCON ports (TCP): 27000 + instance_number

## Volume Mounts

The following directories are mounted in each container:

- Scenarios: `../scenarios/default_lab_scenario`, `../scenarios/open_world`
- Mods: `~/Applications/Factorio.app/Contents/Resources/mods`
- Screenshots: `../../data/_screenshots`

## Notes

- The server instances use the `factorio:latest` Docker image (which you can build from the provided Dockerfile in the `docker` directory)
- Each instance can run with either the `default_lab_scenario` or `open_world` scenario
- RCON password is set to "factorio"
- Containers are configured to restart unless stopped manually

## Troubleshooting

If you encounter issues:

1. Ensure Docker is running and has sufficient resources
2. Check container logs using `docker logs factorio_<instance_number>`
3. Verify port availability using `netstat` or similar tools
