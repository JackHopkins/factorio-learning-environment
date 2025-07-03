import os
import sys
from pathlib import Path

import pytest

from fle.commons.cluster_ips import get_local_container_ips
from fle.env import FactorioInstance

# Add the src directory to the Python path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Get the project root directory
project_root = Path(__file__).parent.parent.parent


@pytest.fixture()  # scope="session")
def instance():
    print("\n=== Setting up Factorio instance ===")

    # Get container IPs and ports
    try:
        ips, udp_ports, tcp_ports = get_local_container_ips()
        print(f"Discovered IPs: {ips}")
        print(f"Discovered UDP ports: {udp_ports}")
        print(f"Discovered TCP ports: {tcp_ports}")

        # If no TCP ports found, fall back to environment variable
        if not tcp_ports:
            tcp_port = int(os.environ.get('FACTORIO_RCON_PORT', '27016'))
            print(f"No TCP ports discovered, using env/default: {tcp_port}")
            tcp_ports = [tcp_port]
    except Exception as e:
        print(f"Error discovering container IPs: {e}")
        # Fallback to environment variable or default
        tcp_port = int(os.environ.get('FACTORIO_RCON_PORT', '27016'))
        print(f"Falling back to port from env/default: {tcp_port}")
        tcp_ports = [tcp_port]

    if not tcp_ports:
        raise ValueError("No TCP ports found for RCON connection!")

    tcp_port = tcp_ports[-1]
    print(f"Using TCP port: {tcp_port}")

    # You might also want to check if FACTORIO_HOST is set
    host = os.environ.get('FACTORIO_HOST', 'localhost')
    print(f"Using host: {host}")

    try:
        instance = FactorioInstance(
            address=host,
            bounding_box=200,
            tcp_port=tcp_port,
            cache_scripts=False,
            fast=True,
            inventory={
                'coal': 50,
                'copper-plate': 50,
                'iron-plate': 50,
                'iron-chest': 2,
                'burner-mining-drill': 3,
                'electric-mining-drill': 1,
                'assembling-machine-1': 1,
                'stone-furnace': 9,
                'transport-belt': 50,
                'boiler': 1,
                'burner-inserter': 32,
                'pipe': 15,
                'steam-engine': 1,
                'small-electric-pole': 10
            }
        )
        print("✓ Successfully created Factorio instance")
        yield instance
    except Exception as e:
        print(f"✗ Failed to create Factorio instance: {e}")
        raise e
    finally:
        # Cleanup RCON connections to prevent connection leaks
        if 'instance' in locals():
            print("Cleaning up instance...")
            instance.cleanup()