import asyncio
import time
from typing import Optional

from cluster.local.cluster_ips import get_local_container_ips
from eval.open.db_client import PostgresDBClient
from eval.open.mcts.mcts_worker import MCTSWorker, MCTSNode, MCTSConfig


class MCTSTrajectoryRunner:
    """Main MCTS controller that manages the search process"""

    def __init__(self, db_client: PostgresDBClient, config: MCTSConfig, num_workers: int):
        self.db_client = db_client
        self.config = config
        self.num_workers = num_workers
        self.workers = []
        self.root = None
        self.iteration_times = []
        self.start_time = 0

    async def initialize_workers(self):
        """Initialize worker pool"""
        ips, udp_ports, tcp_ports = get_local_container_ips()

        if self.num_workers > len(ips):
            raise ValueError(
                f"Not enough Factorio instances. Requested {self.num_workers} workers but only {len(ips)} instances available.")

        for i in range(self.num_workers):
            worker = MCTSWorker(
                worker_id=i,
                db_client=self.db_client,
                config=self.config,
                instance_address=ips[i],
                instance_tcp_port=tcp_ports[i]
            )
            self.workers.append(worker)

    async def initialize_search_tree(self):
        """Initialize the search tree with root node"""
        # Sample initial parent program from database
        parent_program = await self.config.sampler.sample_parent(version=self.config.version)

        if parent_program:
            self.root = MCTSNode(program=parent_program)
        else:
            # Create an empty root if no parent program available
            self.root = MCTSNode()

        return self.root

    async def run(self):
        """Run the MCTS search process"""
        self.start_time = time.time()

        # Initialize workers
        await self.initialize_workers()

        # Initialize search tree
        await self.initialize_search_tree()

        print(f"MCTS search started with {self.num_workers} workers")
        print(f"Version: {self.config.version}, Model: {self.config.agent.model}")

        # Main MCTS loop
        for iteration in range(self.config.max_iterations):
            iteration_start = time.time()

            # Run batch of simulations in parallel
            tasks = []
            selected_nodes = []

            # Select nodes for simulation
            for _ in range(min(self.config.batch_size, self.num_workers)):
                selected_node = self._select_node()
                selected_nodes.append(selected_node)
                selected_node.pending_visits += 1

            # Distribute nodes to workers for simulation
            for i, node in enumerate(selected_nodes):
                worker = self.workers[i % self.num_workers]
                tasks.append(asyncio.create_task(worker.simulate(node)))

            # Wait for all simulations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process simulation results
            for i, (value, program) in enumerate(results):
                node = selected_nodes[i]
                node.pending_visits -= 1

                # Handle simulation errors
                if isinstance(value, Exception):
                    print(f"Simulation error: {value}")
                    continue

                if program:
                    # Save program to database
                    saved_program = await self.db_client.create_program(program)

                    # Create child node
                    child = node.add_child(saved_program)

                    # Backpropagate results
                    self._backpropagate(child, value)

                    # Update visit count in sampler
                    if node.program and node.program.id:
                        await self.config.sampler.visit(node.program.id)

            # Record iteration time
            iteration_time = time.time() - iteration_start
            self.iteration_times.append(iteration_time)

            # Keep only last 50 iterations for moving average
            if len(self.iteration_times) > 50:
                self.iteration_times = self.iteration_times[-50:]

            # Log progress periodically
            if iteration % 10 == 0:
                elapsed = time.time() - self.start_time
                elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
                eta = self._get_eta(iteration)

                best_node = self._get_best_child(self.root)
                best_value = best_node.value / max(best_node.visits, 1) if best_node else 0

                print(f"\033[92m Iteration {iteration}/{self.config.max_iterations} - "
                      f"Best value: {best_value:.2f} - "
                      f"Tree size: {self._count_nodes(self.root)} - "
                      f"Elapsed: {elapsed_str} - "
                      f"ETA: {eta}")

    def _select_node(self) -> MCTSNode:
        """Select a promising node for expansion using UCT"""
        node = self.root

        # If node has no children, return it for expansion
        if not node.children:
            return node

        # Traverse tree to find best node to expand
        while node.children:
            # Apply UCT selection
            best_child = None
            best_uct = float('-inf')

            for child in node.children:
                # Skip nodes that are currently being evaluated
                if child.pending_visits > 0:
                    continue

                # Calculate UCT value
                uct = child.get_uct_value(self.config.exploration_weight)

                if uct > best_uct:
                    best_uct = uct
                    best_child = child

            # If no valid child found (all have pending visits), return current node
            if best_child is None:
                return node

            # Continue down the tree
            node = best_child

            # If node hasn't been fully expanded, return it
            if node.visits < 1:
                return node

        return node

    def _backpropagate(self, node: MCTSNode, value: float):
        """Backpropagate the simulation result up the tree"""
        while node is not None:
            node.visits += 1
            node.value += value
            node = node.parent

    def _get_best_child(self, node: MCTSNode) -> Optional[MCTSNode]:
        """Get the best child node based on average value"""
        if not node.children:
            return None

        best_child = None
        best_value = float('-inf')

        for child in node.children:
            # Skip nodes without visits
            if child.visits == 0:
                continue

            # Calculate average value
            avg_value = child.value / child.visits

            if avg_value > best_value:
                best_value = avg_value
                best_child = child

        return best_child

    def _count_nodes(self, node: MCTSNode) -> int:
        """Count total nodes in the tree"""
        if not node:
            return 0

        count = 1  # Count this node
        for child in node.children:
            count += self._count_nodes(child)

        return count

    def _get_eta(self, current_iteration: int) -> str:
        """Calculate estimated time remaining"""
        if not self.iteration_times:
            return "calculating..."

        avg_iteration_time = sum(self.iteration_times) / len(self.iteration_times)
        remaining_iterations = self.config.max_iterations - current_iteration
        seconds_remaining = avg_iteration_time * remaining_iterations

        # Convert to hours:minutes:seconds
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"