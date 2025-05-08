#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Optional
from factorio_rcon import RCONClient


def generate_client_config(base_dir: str, client_index: int) -> str:
    """Generate config directory and player data for a single client.
    
    Args:
        base_dir: Base directory for all client configs
        client_index: Index of the client to generate config for
        
    Returns:
        Path to the generated client directory
    """
    client_dir = os.path.join(base_dir, f"client_{client_index}")
    os.makedirs(client_dir, exist_ok=True)
    
    # Write config.ini
    config_ini_template = """[path]
use-system-read-write-data-directories=false
write-data={client_dir}"""
    
    config_path = os.path.join(client_dir, "config.ini")
    with open(config_path, 'w') as f:
        f.write(config_ini_template.format(client_dir=os.path.abspath(client_dir)))
    
    # Generate player-data.json
    player_data = {
        "service-username": f"client{client_index}",
    }
    player_data_path = os.path.join(client_dir, "player-data.json")
    with open(player_data_path, 'w') as f:
        json.dump(player_data, f, indent=2)
        
    return client_dir


def launch_client(client_dir: str, server_address: str, factorio_binary_path: str, 
                 client_index: int, timeout: int = 60) -> bool:
    """Launch a Factorio client and wait for successful connection.
    
    Args:
        client_dir: Directory containing client config
        server_address: Address of the server to connect to
        factorio_binary_path: Path to the Factorio binary
        client_index: Index of the client (for logging)
        timeout: Maximum time to wait for connection in seconds
        
    Returns:
        True if client connected successfully, False otherwise
    """
    config_path = os.path.join(client_dir, "config.ini")
    cmd = [
        factorio_binary_path,
        "--config", config_path,
        "--mp-connect", server_address
    ]
    print(f"[Client {client_index}] Launching...")
    
    try:
        # Launch with piped output to monitor logs
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        start_time = time.time()
        connected = False
        
        # Monitor output for successful connection
        while process.poll() is None and time.time() - start_time < timeout:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            # Only print important messages
            if any(msg in line for msg in ["Joining game", "Connection established", "Error", "Failed"]):
                print(f"[Client {client_index}] {line.strip()}")
            
            if "Joining game" in line or "Connection established" in line:
                connected = True
                print(f"[Client {client_index}] Successfully connected!")
                break
        
        if not connected:
            print(f"[Client {client_index}] Failed to connect within {timeout} seconds")
            process.terminate()
            return False
            
        # Give a moment for the connection to stabilize
        time.sleep(2)

        # Connect to RCON and verify player joined
        try:
            rcon = RCONClient('localhost', 27000, 'factorio')
            response = rcon.send_command(f'/players')
            if f'client{client_index}' not in response:
                print(f"[Client {client_index}] Could not verify player joined via RCON")
                process.terminate()
                return False
            print(f"[Client {client_index}] Verified player joined via RCON")
        except Exception as e:
            print(f"[Client {client_index}] RCON error: {e}")
            process.terminate() 
            return False

        process.terminate()
        process.wait()
        return True
        
    except Exception as e:
        print(f"[Client {client_index}] Error: {e}")
        return False


def cleanup_client_dir(client_dir: str, client_index: int) -> None:
    """Clean up a client's config directory.
    
    Args:
        client_dir: Directory to clean up
        client_index: Index of the client (for logging)
    """
    try:
        shutil.rmtree(client_dir)
        print(f"[Client {client_index}] Cleaned up config directory")
    except Exception as e:
        print(f"[Client {client_index}] Error cleaning up: {e}")


def setup_multiagent(num_clients: int, server_address: str, factorio_binary_path: str,
                    base_dir: str = "factorio_configs", timeout: int = 60) -> None:
    """Set up multiple Factorio clients sequentially.
    
    Args:
        num_clients: Number of clients to set up
        server_address: Address of the server to connect to
        factorio_binary_path: Path to the Factorio binary
        base_dir: Base directory for client configs
        timeout: Maximum time to wait for each client to connect
    """
    # Create base config directory
    os.makedirs(base_dir, exist_ok=True)
    successful_connections = 0
    try:
        for i in range(num_clients):
            print(f"\n[Progress] Setting up client {i+1}/{num_clients}")
            client_dir = generate_client_config(base_dir, i)
            if launch_client(client_dir, server_address, factorio_binary_path, i, timeout):
                successful_connections += 1
            cleanup_client_dir(client_dir, i)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
    finally:
        # Clean up base directory
        try:
            shutil.rmtree(base_dir)
            print("\nCleaned up base config directory")
        except Exception as e:
            print(f"\nError cleaning up base directory: {e}")
            
    print(f"\nSetup complete. {successful_connections}/{num_clients} clients connected successfully.")


def main():
    parser = argparse.ArgumentParser(description="Set up multiple Factorio clients")
    parser.add_argument("num_clients", type=int, help="Number of clients to set up")
    parser.add_argument("--server", default="localhost:34197", help="Server address (default: localhost:34197)")
    parser.add_argument("--factorio", default="/Applications/factorio.app/Contents/MacOS/factorio",
                      help="Path to Factorio binary")
    parser.add_argument("--config-dir", default="factorio_configs",
                      help="Base directory for client configs")
    parser.add_argument("--timeout", type=int, default=60,
                      help="Timeout for client connection in seconds")
    
    args = parser.parse_args()
    
    setup_multiagent(
        args.num_clients,
        args.server,
        args.factorio,
        args.config_dir,
        args.timeout
    )


if __name__ == "__main__":
    main() 