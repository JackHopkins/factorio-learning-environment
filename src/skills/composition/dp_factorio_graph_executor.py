import re
from dataclasses import dataclass
from typing import Dict, Set, List, Tuple, Optional
import networkx as nx
from copy import deepcopy

from skills.composition.factorio_graph_executor import FactorioGraphExecutor
from skills.composition.factorio_graph_generator import Objective


@dataclass
class SubgraphSolution:
    implementation: str
    score: int
    entities: Set[str]
    inventory_delta: Dict[str, int]


class DPFactorioGraphExecutor(FactorioGraphExecutor):
    def __init__(self, factorio_instance, llm_factory, implementation_dao):
        super().__init__(factorio_instance, llm_factory, implementation_dao)
        self.solutions_cache: Dict[str, SubgraphSolution] = {}

    def _parse_mermaid_to_nx(self, mermaid_graph: str) -> nx.DiGraph:
        """Convert Mermaid flowchart to NetworkX graph"""
        G = nx.DiGraph()

        # Parse entity definitions and connections
        for line in mermaid_graph.split('\n'):
            line = line.strip()
            if not line or line.startswith('%%'):
                continue

            # Parse entity definitions
            if '[' in line and ']' in line:
                node_match = re.search(r'(\w+)\[(.*?)\]', line)
                if node_match:
                    node_id, node_label = node_match.groups()
                    G.add_node(node_id, label=node_label)

            # Parse connections
            if '-->' in line:
                parts = line.split('-->')
                if len(parts) == 2:
                    source = parts[0].strip()
                    connection_type = ''
                    target = ''

                    # Extract connection type if specified
                    if '|' in parts[1]:
                        conn_parts = parts[1].split('|')
                        connection_type = conn_parts[0].strip('|')
                        target = conn_parts[1].strip('[').strip(']')
                    else:
                        target = parts[1].strip('[').strip(']')

                    G.add_edge(source, target, type=connection_type)

        return G

    def _get_subgraphs(self, G: nx.DiGraph) -> List[nx.DiGraph]:
        """Generate meaningful subgraphs for solving"""
        subgraphs = []
        subgraphsA = []
        subgraphsB = []
        # Strategy 1: Individual nodes with their immediate connections
        for node in G.nodes():
            subgraph = G.subgraph({node} | set(G.predecessors(node)) | set(G.successors(node)))
            subgraphs.append(subgraph)
            subgraphsA.append(subgraph)

        # Strategy 2: Connected components up to size 3
        for size in range(2, 4):
            for node in G.nodes():
                neighbors = set()
                current_set = {node}

                # Get nodes within distance 'size'
                for _ in range(size):
                    for n in list(current_set):
                        neighbors.update(G.predecessors(n))
                        neighbors.update(G.successors(n))
                    current_set.update(neighbors)

                if len(current_set) <= size:
                    subgraph = G.subgraph(current_set)
                    subgraphs.append(subgraph)
                    subgraphsB.append(subgraph)

        for subgraph in subgraphsA:
            representation = self._subgraph_to_mermaid(subgraph)
            pass
        for subgraph in subgraphsB:
            representation = self._subgraph_to_mermaid(subgraph)
            pass

        return subgraphs

    def _subgraph_to_mermaid(self, G: nx.DiGraph) -> str:
        """Convert NetworkX subgraph back to Mermaid format"""
        mermaid_lines = ["flowchart TD"]

        # Add node definitions
        for node, attrs in G.nodes(data=True):
            label = attrs.get('label', node)
            mermaid_lines.append(f"    {node}[{label}]")

        # Add connections
        for source, target, attrs in G.edges(data=True):
            connection_type = attrs.get('type', '')
            if connection_type:
                mermaid_lines.append(f"    {source} -->|{connection_type}| {target}")
            else:
                mermaid_lines.append(f"    {source} --> {target}")

        return "\n".join(mermaid_lines)

    def _merge_solutions(self, sol1: SubgraphSolution, sol2: SubgraphSolution) -> SubgraphSolution:
        """Merge two subgraph solutions"""
        merged_impl = []

        # Add implementation lines while avoiding duplicates
        seen_lines = set()
        for impl in [sol1.implementation, sol2.implementation]:
            for line in impl.split('\n'):
                line = line.strip()
                if line and line not in seen_lines:
                    merged_impl.append(line)
                    seen_lines.add(line)

        return SubgraphSolution(
            implementation='\n'.join(merged_impl),
            score=sol1.score + sol2.score,
            entities=sol1.entities | sol2.entities,
            inventory_delta={
                k: sol1.inventory_delta.get(k, 0) + sol2.inventory_delta.get(k, 0)
                for k in set(sol1.inventory_delta) | set(sol2.inventory_delta)
            }
        )

    def _verify_subgraph(self, implementation: str, starting_inventory: Dict[str, int]) -> SubgraphSolution:
        """Verify a subgraph implementation and return its solution details"""
        self.factorio.reset()
        self.factorio.set_inventory(**starting_inventory)
        initial_inventory = deepcopy(self.factorio.inspect_inventory().__dict__)

        success, error_message, score, progress = self.verify_implementation(implementation)
        if not success:
            raise Exception(f"Subgraph verification failed: {error_message}")

        final_inventory = self.factorio.inspect_inventory().__dict__
        inventory_delta = {
            k: final_inventory.get(k, 0) - initial_inventory.get(k, 0)
            for k in set(final_inventory) | set(initial_inventory)
        }

        entities = set(self.factorio.get_entities().keys())

        return SubgraphSolution(
            implementation=implementation,
            score=score,
            entities=entities,
            inventory_delta=inventory_delta
        )

    def execute_graph_dp(self, graph: str, objective: Objective, max_repair_attempts=12) -> Tuple[
        str, Dict[str, int], int, int]:
        """Execute graph using dynamic programming approach"""
        # Convert to NetworkX for analysis
        G = self._parse_mermaid_to_nx(graph)

        # Generate and solve subgraphs
        subgraphs = self._get_subgraphs(G)

        # Solve subproblems
        for subgraph in subgraphs:
            mermaid_repr = self._subgraph_to_mermaid(subgraph)

            # Skip if we already have this solution
            subgraph_hash = hash(mermaid_repr)
            if subgraph_hash in self.solutions_cache:
                continue

            # Generate and verify implementation for this subgraph
            implementation = self.generate_implementation(mermaid_repr, objective.objective)
            try:
                solution = self._verify_subgraph(implementation, objective.starting_inventory)
                self.solutions_cache[subgraph_hash] = solution
            except Exception as e:
                print(f"Failed to solve subgraph: {str(e)}")
                continue

        # Build complete solution bottom-up
        def combine_subgraphs(G1: nx.DiGraph, G2: nx.DiGraph) -> Optional[SubgraphSolution]:
            """Try to combine two subgraph solutions"""
            # Check if solutions exist for both subgraphs
            hash1 = hash(self._subgraph_to_mermaid(G1))
            hash2 = hash(self._subgraph_to_mermaid(G2))

            if hash1 not in self.solutions_cache or hash2 not in self.solutions_cache:
                return None

            # Merge the solutions
            merged = self._merge_solutions(
                self.solutions_cache[hash1],
                self.solutions_cache[hash2]
            )

            # Verify the merged solution
            try:
                merged_impl = merged.implementation
                verified = self._verify_subgraph(merged_impl, objective.starting_inventory)
                return verified
            except Exception:
                return None

        # Try combining subgraphs until we have a complete solution
        while len(subgraphs) > 1:
            new_subgraphs = []
            merged = False

            for i in range(len(subgraphs)):
                for j in range(i + 1, len(subgraphs)):
                    # Try to merge subgraphs[i] and subgraphs[j]
                    combined_graph = nx.compose(subgraphs[i], subgraphs[j])
                    solution = combine_subgraphs(subgraphs[i], subgraphs[j])

                    if solution:
                        # Store the solution for the combined graph
                        hash_key = hash(self._subgraph_to_mermaid(combined_graph))
                        self.solutions_cache[hash_key] = solution
                        new_subgraphs.append(combined_graph)
                        merged = True

                    # Keep any subgraphs that weren't merged
                    if not merged:
                        if subgraphs[i] not in new_subgraphs:
                            new_subgraphs.append(subgraphs[i])
                        if j == len(subgraphs) - 1 and subgraphs[j] not in new_subgraphs:
                            new_subgraphs.append(subgraphs[j])

            if not merged:
                raise Exception("Failed to merge subgraphs into complete solution")

            subgraphs = new_subgraphs

        # Get the final solution
        final_hash = hash(self._subgraph_to_mermaid(subgraphs[0]))
        final_solution = self.solutions_cache[final_hash]

        return (
            final_solution.implementation,
            final_solution.inventory_delta,
            1,  # attempts (always 1 since we build up the solution)
            final_solution.score
        )