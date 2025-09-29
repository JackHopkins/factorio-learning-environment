"""
Server management for concurrent evaluations.

Handles allocation and tracking of Factorio server instances across
multiple concurrent evaluation processes.
"""

import threading
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta

from fle.commons.cluster_ips import get_local_container_ips


@dataclass
class ServerAllocation:
    """Tracks allocation of a Factorio server to a job"""

    server_id: int
    server_address: str
    tcp_port: int
    udp_port: int
    job_id: str
    allocated_at: datetime
    process_id: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            "server_id": self.server_id,
            "server_address": self.server_address,
            "tcp_port": self.tcp_port,
            "udp_port": self.udp_port,
            "job_id": self.job_id,
            "allocated_at": self.allocated_at.isoformat(),
            "process_id": self.process_id,
        }


class ServerManager:
    """Manages allocation of Factorio servers across concurrent jobs"""

    def __init__(self, max_allocation_time_hours: float = 2.0):
        """Initialize server manager

        Args:
            max_allocation_time_hours: Maximum time to hold a server allocation
        """
        self._lock = threading.Lock()
        self._allocations: Dict[int, ServerAllocation] = {}
        self._available_servers: List[int] = []
        self._allocated_servers: Set[int] = set()
        self.max_allocation_time = timedelta(hours=max_allocation_time_hours)
        self._initialized = False

    def _discover_servers(self) -> bool:
        """Discover available Factorio servers

        Returns:
            True if servers were found, False otherwise
        """
        try:
            ips, udp_ports, tcp_ports = get_local_container_ips()

            if not tcp_ports:
                print("⚠️  No Factorio containers found")
                return False

            self._available_servers = list(range(len(tcp_ports)))
            self._server_info = {
                i: {
                    "address": ips[i],
                    "tcp_port": tcp_ports[i],
                    "udp_port": udp_ports[i],
                }
                for i in range(len(tcp_ports))
            }

            print(f"🖥️  Discovered {len(tcp_ports)} Factorio servers:")
            for i, (ip, tcp_port) in enumerate(zip(ips, tcp_ports)):
                print(f"   Server {i}: {ip}:{tcp_port}")

            self._initialized = True
            return True

        except Exception as e:
            print(f"❌ Error discovering servers: {e}")
            return False

    def initialize(self) -> bool:
        """Initialize server discovery

        Returns:
            True if initialization was successful
        """
        with self._lock:
            if not self._initialized:
                return self._discover_servers()
            return True

    def get_available_server_count(self) -> int:
        """Get number of currently available servers"""
        with self._lock:
            if not self._initialized:
                self._discover_servers()
            return len(self._available_servers) - len(self._allocated_servers)

    def get_total_server_count(self) -> int:
        """Get total number of discovered servers"""
        with self._lock:
            if not self._initialized:
                self._discover_servers()
            return len(self._available_servers)

    def allocate_server(
        self, job_id: str, process_id: Optional[int] = None
    ) -> Optional[ServerAllocation]:
        """Allocate a server for a job

        Args:
            job_id: Unique identifier for the job
            process_id: Optional process ID for tracking

        Returns:
            ServerAllocation if successful, None if no servers available
        """
        with self._lock:
            # Initialize if needed
            if not self._initialized:
                if not self._discover_servers():
                    return None

            # Clean up expired allocations
            self._cleanup_expired_allocations()

            # Find available server
            available_servers = [
                server_id
                for server_id in self._available_servers
                if server_id not in self._allocated_servers
            ]

            if not available_servers:
                print(
                    f"⚠️  No servers available for job {job_id} (all {len(self._available_servers)} servers allocated)"
                )
                return None

            # Allocate first available server
            server_id = available_servers[0]
            server_info = self._server_info[server_id]

            allocation = ServerAllocation(
                server_id=server_id,
                server_address=server_info["address"],
                tcp_port=server_info["tcp_port"],
                udp_port=server_info["udp_port"],
                job_id=job_id,
                allocated_at=datetime.now(),
                process_id=process_id,
            )

            self._allocations[server_id] = allocation
            self._allocated_servers.add(server_id)

            print(
                f"🖥️  Allocated server {server_id} ({allocation.server_address}:{allocation.tcp_port}) to job {job_id}"
            )

            return allocation

    def release_server(self, job_id: str) -> bool:
        """Release server allocation for a job

        Args:
            job_id: Job identifier to release

        Returns:
            True if server was found and released
        """
        with self._lock:
            # Find allocation by job_id
            server_id = None
            for sid, allocation in self._allocations.items():
                if allocation.job_id == job_id:
                    server_id = sid
                    break

            if server_id is not None:
                allocation = self._allocations.pop(server_id)
                self._allocated_servers.remove(server_id)
                print(f"🔓 Released server {server_id} from job {job_id}")
                return True

            return False

    def release_server_by_id(self, server_id: int) -> bool:
        """Release server allocation by server ID

        Args:
            server_id: Server ID to release

        Returns:
            True if server was found and released
        """
        with self._lock:
            if server_id in self._allocations:
                allocation = self._allocations.pop(server_id)
                self._allocated_servers.remove(server_id)
                print(
                    f"🔓 Released server {server_id} (was allocated to {allocation.job_id})"
                )
                return True

            return False

    def _cleanup_expired_allocations(self):
        """Clean up allocations that have been held too long (called with lock held)"""
        current_time = datetime.now()
        expired_servers = []

        for server_id, allocation in self._allocations.items():
            if current_time - allocation.allocated_at > self.max_allocation_time:
                expired_servers.append(server_id)

        for server_id in expired_servers:
            allocation = self._allocations.pop(server_id)
            self._allocated_servers.remove(server_id)
            print(
                f"⏰ Released expired allocation: server {server_id} (was allocated to {allocation.job_id})"
            )

    def get_allocation_status(self) -> Dict:
        """Get current allocation status

        Returns:
            Dictionary with allocation information
        """
        with self._lock:
            if not self._initialized:
                self._discover_servers()

            self._cleanup_expired_allocations()

            return {
                "total_servers": len(self._available_servers),
                "allocated_servers": len(self._allocated_servers),
                "available_servers": len(self._available_servers)
                - len(self._allocated_servers),
                "allocations": [
                    allocation.to_dict() for allocation in self._allocations.values()
                ],
                "initialized": self._initialized,
            }

    def get_server_assignment_for_job(self, job_id: str) -> Optional[Dict]:
        """Get server assignment for a specific job

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with server info or None if not found
        """
        with self._lock:
            for allocation in self._allocations.values():
                if allocation.job_id == job_id:
                    return {
                        "server_id": allocation.server_id,
                        "address": allocation.server_address,
                        "tcp_port": allocation.tcp_port,
                        "udp_port": allocation.udp_port,
                        "allocated_at": allocation.allocated_at.isoformat(),
                    }
            return None

    def force_release_all(self):
        """Force release all server allocations (emergency cleanup)"""
        with self._lock:
            released_count = len(self._allocations)
            self._allocations.clear()
            self._allocated_servers.clear()

            if released_count > 0:
                print(f"🧹 Force released all {released_count} server allocations")

    def print_status(self):
        """Print current server allocation status"""
        status = self.get_allocation_status()

        print("🖥️  Server Allocation Status:")
        print(f"   Total servers: {status['total_servers']}")
        print(f"   Available: {status['available_servers']}")
        print(f"   Allocated: {status['allocated_servers']}")

        if status["allocations"]:
            print("   Current allocations:")
            for alloc in status["allocations"]:
                print(
                    f"     Server {alloc['server_id']}: {alloc['job_id']} "
                    f"(since {alloc['allocated_at'][:19]})"
                )


# Global server manager instance
_global_server_manager: Optional[ServerManager] = None


def get_server_manager() -> ServerManager:
    """Get or create global server manager instance"""
    global _global_server_manager

    if _global_server_manager is None:
        _global_server_manager = ServerManager()
        _global_server_manager.initialize()

    return _global_server_manager


if __name__ == "__main__":
    # Test server manager
    manager = ServerManager()
    manager.initialize()
    manager.print_status()

    # Test allocation
    alloc1 = manager.allocate_server("test_job_1")
    alloc2 = manager.allocate_server("test_job_2")

    manager.print_status()

    if alloc1:
        manager.release_server("test_job_1")
    if alloc2:
        manager.release_server("test_job_2")

    manager.print_status()
