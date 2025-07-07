import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import pyautogui
import time
import subprocess
import sys
from dotenv import load_dotenv

from cluster.remote.cluster_ips import get_public_ips
from fle.env import FactorioInstance

"""
This script is used to connect the client to each Factorio server running on an ECS cluster,
and initialise it by creating a player.
"""

# Adjust these coordinates based on your screen resolution and game UI - These are my values
# configured using `pyautogui.position()` and manually adjusting in the Factorio game with a 1400x900 resolution
MULTIPLAYER_BUTTON = (720, 410)
CONNECT_TO_ADDRESS_BUTTON = (720, 525)
IP_INPUT_FIELD = (720, 445)
CONNECT_BUTTON = (850, 480)
ESC_MENU_QUIT_BUTTON = (720, 520)


def launch_factorio():
    # Adjust the path to your Factorio executable
    process = subprocess.Popen(["open", "-a", "Factorio"])
    time.sleep(10)  # Wait for the game to launch
    return process


def focus_factorio():
    # Use AppleScript to focus Factorio
    applescript = """
    tell application "Factorio" to activate
    """
    subprocess.run(["osascript", "-e", applescript])
    time.sleep(1)  # Wait a moment for the window to come into focus


def connect_to_server(ip_address):
    focus_factorio()
    # Make sure the game is on the main menu
    pyautogui.press("esc")
    pyautogui.press("esc")
    pyautogui.press("esc")
    # Navigate to multiplayer
    pyautogui.click(MULTIPLAYER_BUTTON)
    # Click on "Connect to address"
    pyautogui.click(CONNECT_TO_ADDRESS_BUTTON)
    # Input the IP address and port
    pyautogui.click(IP_INPUT_FIELD)
    # Delete the existing IP address
    pyautogui.hotkey("command", "a")
    pyautogui.press("delete")
    pyautogui.write(f"{ip_address}:34197")
    # Click connect
    pyautogui.click(CONNECT_BUTTON)
    time.sleep(5)  # Wait for connection attempt
    # Quit the game
    pyautogui.press("esc")
    pyautogui.click(ESC_MENU_QUIT_BUTTON)
    time.sleep(3)  # Wait for the game to close


def is_initialised(ip_address, port):
    try:
        instance = FactorioInstance(  # noqa
            address=ip_address,
            bounding_box=200,
            tcp_port=port,
            cache_scripts=True,
            fast=True,
        )
        return True
    except Exception as e:
        print(f"Error connecting to {ip_address}: {str(e)}")
        return False


def get_uninitialised_ips(
    ip_addresses: List[str], tcp_ports: List[str], max_workers: int = 8
) -> List[str]:
    """
    Check multiple IP addresses in parallel using ThreadPoolExecutor.

    Args:
        ip_addresses: List of IP addresses to check
        max_workers: Maximum number of concurrent threads (default: 20)

    Returns:
        List of IP addresses that successfully initialized
    """
    invalid_ips = []
    total_ips = len(ip_addresses)

    print(f"Starting initialization check for {total_ips} IP addresses...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary to map futures to their IP addresses
        future_to_ip = {
            executor.submit(is_initialised, ip, port): ip
            for ip, port in zip(ip_addresses, tcp_ports)
        }

        # Process completed futures as they finish
        for i, future in enumerate(as_completed(future_to_ip), 1):
            ip = future_to_ip[future]
            try:
                if future.result():
                    print(f"Progress: {i}/{total_ips} - {ip} is valid")
                else:
                    invalid_ips.append(ip)
                    print(f"Progress: {i}/{total_ips} - {ip} is invalid")
            except Exception as e:
                print(
                    f"Progress: {i}/{total_ips} - Unexpected error with {ip}: {str(e)}"
                )

    elapsed_time = time.time() - start_time
    print(f"\nCompleted in {elapsed_time:.2f} seconds")
    print(f"Found {len(invalid_ips)} uninitialised IPs out of {total_ips}")

    return invalid_ips


def main(cluster_name):
    ip_addresses = get_public_ips(cluster_name)

    # filter out the ips that are not initialised
    ip_addresses = get_uninitialised_ips(ip_addresses)

    # a threadpool implementation would be better here

    # ip_addresses = ["localhost"]  # Uncomment for testing
    factorio_process = launch_factorio()
    for ip in ip_addresses:
        connect_to_server(ip)
        print(f"Connected to and quit from {ip}")
    factorio_process.terminate()  # Ensure Factorio is closed at the end


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    # Get cluster name from .env file or c19734.201.524;34ommand line argument
    default_cluster_name = os.getenv("CLUSTER_NAME")
    if len(sys.argv) == 2:
        cluster_name = sys.argv[1]
    elif default_cluster_name:
        cluster_name = default_cluster_name
    else:
        print("Error: CLUSTER_NAME not set in .env file and not provided as argument")
        print("Usage: python factorio_server_login.py [cluster_name]")
        sys.exit(1)
    main(cluster_name)
