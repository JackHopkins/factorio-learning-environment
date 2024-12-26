import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Set

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

from search.mcts.db_client import DBClient

@dataclass
class Node:
    id: int
    parent_id: Optional[int]
    source_code: str
    response: Optional[str]
    static_achievements: Dict
    dynamic_achievements: Dict
    children: List['Node']
    metrics: Dict

class RunResults:

    def __init__(self, version: int, db_client: DBClient):
        self.version = version
        self.db_client = db_client

    def save_plots(self):
        import os
        results = self._create_trees_from_db()
        dir_path = f"plots/{self.version}"
        os.makedirs(dir_path, exist_ok=True)

        metrics = ['raw_reward', 'static_achievements', 'dynamic_achievements', 'achievements']
        for metric in metrics:
            print(f"\nGenerating plots for metric: {metric}")
            plots = {}

            print(f"Generating tree cumulative plot")
            plots[f'{metric}_tree_cumulative.png'] = self.plot_reward_tree(results[0], cumulative=True, metric=metric)

            print(f"Generating tree raw plot")
            plots[f'{metric}_tree_raw.png'] = self.plot_reward_tree(results[0], cumulative=False, metric=metric)

            print(f"Generating percentiles cumulative plot")
            plots[f'{metric}_percentiles_cumulative.png'] = self.plot_reward_percentiles(results[0],
                                                                                         percentiles=[5 * i for i in
                                                                                                      range(1, 20)],
                                                                                         cumulative=True, metric=metric)

            print(f"Generating percentiles raw plot")
            plots[f'{metric}_percentiles_raw.png'] = self.plot_reward_percentiles(results[0],
                                                                                  percentiles=[5 * i for i in
                                                                                               range(1, 20)],
                                                                                  cumulative=False, metric=metric)

            for filename, plot in plots.items():
                print(f"Saving: {filename}")
                plot.savefig(f"{dir_path}/{filename}")
                plot.close()
            plt.close('all')

            # Save readme
            with self.db_client.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT version_description FROM programs WHERE version = {self.version} LIMIT 1")
                    version_description = cur.fetchone()[0]

            with open(f"{dir_path}/README.md", 'w') as f:
                f.write(f"# Version {self.version}\n\n{version_description}")

    def plot_results(self):
        results = self._create_trees_from_db()
        plot_cum = self.plot_reward_tree(results[0], cumulative=True)
        plot_cum.show()

        percentile_plot_cum = self.plot_reward_percentiles(results[0],
                                                          percentiles=[5 * i for i in range(1, 20)],
                                                          cumulative=True)  # run.plot_reward_tree(results[0])
        percentile_plot_cum.show()
        percentile_plot = self.plot_reward_percentiles(results[0],
                                                      percentiles=[5 * i for i in range(1, 20)],
                                                      cumulative=False)
        percentile_plot.show()

        plot = self.plot_reward_tree(results[0], cumulative=False)
        plot.show()

    def calculate_set_value(self, node: Node, depth: int, parent_set: Optional[set] = None, metric: str = '') -> Tuple[
        float, set]:
        if parent_set is None:
            parent_set = set()

        current_set = parent_set.union(node.metrics[metric])
        value = len(current_set)
        return value, current_set

    def _create_trees_from_db(self) -> Tuple[List[Node], Set[int]]:
        # Get all nodes for this version
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""SELECT id, parent_id, code, response, achievements_json, value, raw_reward FROM programs WHERE version = {self.version}""")
                nodes = cur.fetchall()


        # Create mapping of nodes
        node_map: Dict[int, Node] = {}
        root_nodes: List[Node] = []
        processed_ids = set()

        # Create Node objects
        for node in nodes:
            id, parent_id, source_code, response, achievements_json, value, raw_reward = node
            processed_ids.add(id)

            try:
                achievements = json.loads(achievements_json) if achievements_json else {}
            except:
                achievements = achievements_json
            # Parse achievements
            static_achievements = achievements['static'] if achievements else {}
            dynamic_achievements = achievements['dynamic'] if achievements else {}
            metrics_dict = {
                'value': value,
                'raw_reward': raw_reward,
                'dynamic_achievement_count': len(dynamic_achievements),
                'static_achievement_count': len(static_achievements),
                'dynamic_achievements': set(dynamic_achievements.keys()),
                'static_achievements': set(static_achievements.keys()),
                'achievements': set(static_achievements.keys()).union(set(dynamic_achievements.keys()))
            }

            # Create node
            node_obj = Node(
                id=id,
                parent_id=parent_id,
                source_code=source_code,
                response=response,
                static_achievements=static_achievements,
                dynamic_achievements=dynamic_achievements,
                children=[],
                metrics=metrics_dict
            )
            node_map[id] = node_obj

        # Build tree structure
        for node in node_map.values():
            if node.parent_id is None or node.parent_id not in node_map:
                root_nodes.append(node)
            else:
                parent = node_map[node.parent_id]
                parent.children.append(node)

        return root_nodes, processed_ids

    def plot_reward_percentiles(self, root_nodes: List[Node], percentiles=[25, 50, 75], cumulative=True,
                                metric='raw_reward'):
        rewards_by_depth = defaultdict(list)

        def collect_rewards(node: Node, depth: int = 0, parent_value: float = 0, parent_set: Optional[set] = None):
            print(f"Using metric {metric}, value: {node.metrics[metric]}")
            if isinstance(node.metrics[metric], set):
                current_set = parent_set.union(node.metrics[metric]) if parent_set else node.metrics[metric]
                value = len(current_set)
            else:
                value = parent_value + (node.metrics[metric] or 0)
                current_set = None

            rewards_by_depth[depth].append(value)
            for child in node.children:
                collect_rewards(child, depth + 1, value if cumulative else 0, current_set if current_set else None)

        for root in root_nodes:
            collect_rewards(root)

        max_depth = max(rewards_by_depth.keys())
        depths = range(max_depth + 1)

        fig, ax = plt.subplots(figsize=(12, 8))
        percentile_values = {p: [] for p in percentiles}

        for depth in depths:
            values = rewards_by_depth[depth]
            for p in percentiles:
                percentile_values[p].append(np.percentile(values, p) if values else 0)

        for p in percentiles:
            ax.plot(depths, percentile_values[p], label=f'{p}th percentile')

        name = metric.replace("_", " ").title()
        ax.set_xlabel('Depth')
        ax.set_ylabel(f'Cumulative {name}' if cumulative else name)
        ax.set_title(
            f'{"Cumulative " if cumulative else ""}{name} Distribution Over Tree Depth - Version {self.version}')
        ax.legend()

        return plt

    def plot_reward_tree(self, root_nodes: List[Node], cumulative: bool = True, metric='raw_reward'):
        G = nx.DiGraph()
        nodes_by_depth = defaultdict(list)
        processed_nodes = set()

        def calculate_cumulative_value(node: Node, depth: int, parent_value: float = 0,
                                       parent_set: Optional[set] = None) -> float:
            if node.id in processed_nodes:
                return G.nodes[node.id]['value']

            processed_nodes.add(node.id)

            if isinstance(node.metrics[metric], set):
                value, current_set = self.calculate_set_value(node, depth, parent_set, metric)
            else:
                raw_reward = node.metrics[metric] or 0
                value = parent_value + raw_reward
                current_set = None

            G.add_node(node.id, value=value)
            nodes_by_depth[depth].append(node.id)

            for child in node.children:
                G.add_edge(node.id, child.id)
                calculate_cumulative_value(child, depth + 1, value, current_set if current_set else None)
            return value

        def add_nodes(node: Node, depth: int = 0):
            if cumulative:
                calculate_cumulative_value(node, depth)
            else:
                value = len(node.metrics[metric]) if isinstance(node.metrics[metric], set) else (
                            node.metrics[metric] or 0)
                G.add_node(node.id, value=value)
                nodes_by_depth[depth].append(node.id)

            for child in node.children:
                G.add_edge(node.id, child.id)
                if child.id not in processed_nodes:
                    add_nodes(child, depth + 1)

        for root in root_nodes:
            add_nodes(root)

        pos = {}
        max_depth = max(nodes_by_depth.keys())
        for depth, nodes in nodes_by_depth.items():
            for i, node_id in enumerate(nodes):
                x = depth / max_depth if max_depth > 0 else 0
                y = G.nodes[node_id]['value']
                pos[node_id] = (x, y)

        fig, ax = plt.subplots(figsize=(12, 8))
        values = [G.nodes[node]['value'] for node in G.nodes()]
        nodes = nx.draw_networkx_nodes(G, pos,
                                       node_color=values,
                                       node_size=18,
                                       cmap=plt.cm.viridis,
                                       ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, ax=ax, width=0.5)
        name = metric.replace("_", " ").title()
        plt.colorbar(nodes, ax=ax, label=f'Cumulative {name}' if cumulative else name)
        ax.set_xlabel('Depth')
        ax.set_ylabel(f'Cumulative {name}' if cumulative else name)
        ax.set_title(f'MCTS Tree Visualization - Version {self.version}')
        return plt