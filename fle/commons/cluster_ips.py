import subprocess
import json
from typing import List


def get_local_container_ips() -> tuple[List[str], List[int], List[int]]:
    """Get IP addresses of running Factorio containers in the local Docker setup."""
    # Get container IDs for factorio containers
    cmd = ["docker", "ps", "--filter", "name=factorio_", "--format", '"{{.ID}}"']
    result = subprocess.run(cmd, capture_output=True, text=True)
    container_ids = result.stdout.strip().split("\n")
    container_ids = [id.strip('"') for id in container_ids]

    if not container_ids or container_ids[0] == "":
        print("No running Factorio containers found")
        return []

    ips = []
    udp_ports = []
    tcp_ports = []
    for container_id in container_ids:
        # Get container details in JSON format
        cmd = ["docker", "inspect", container_id]
        result = subprocess.run(cmd, capture_output=True, text=True)
        container_info = json.loads(result.stdout)

        # Get host ports for UDP game port
        ports = container_info[0]["NetworkSettings"]["Ports"]

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


if __name__ == "__main__":
    ips, udp_ports, tcp_ports = get_local_container_ips()
    if ips:
        print("Local Factorio container addresses:")
        for ip in ips:
            print(ip)
    else:
        print("No local Factorio containers found.")
