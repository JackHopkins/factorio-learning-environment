import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from fle.commons.db_client import DBClient


@dataclass
class Node:
    id: int
    parent_id: Optional[int]
    source_code: str
    response: Optional[str]
    static_achievements: Dict
    dynamic_achievements: Dict
    children: List["Node"]
    metrics: Dict


class RunResults:
    def __init__(self, version: int, db_client: DBClient, neptune_run=None):
        self.version = version
        self.db_client = db_client
        self.neptune_run = neptune_run
        self.dir_path = Path(f"runs/{self.version}")

    def plot_reward_mean_std(
        self, root_nodes: List[Node], metric="raw_reward", cumulative=True
    ):
        """
        Creates a plot showing mean reward over depth with standard deviation bands.

        Args:
            root_nodes: List of root nodes to analyze
            metric (str): The metric to plot
            cumulative (bool): Whether to use cumulative values

        Returns:
            matplotlib.figure: The generated plot
        """
        rewards_by_depth = defaultdict(list)

        def collect_rewards(
            node: Node,
            depth: int = 0,
            parent_value: float = 0,
            parent_set: Optional[set] = None,
        ):
            if isinstance(node.metrics[metric], set):
                current_set = (
                    parent_set.union(node.metrics[metric])
                    if parent_set
                    else node.metrics[metric]
                )
                value = len(current_set)
            else:
                value = parent_value + (node.metrics[metric] or 0)
                current_set = None

            rewards_by_depth[depth].append(value)
            for child in node.children:
                collect_rewards(
                    child,
                    depth + 1,
                    value if cumulative else 0,
                    current_set if current_set else None,
                )

        # Collect rewards for all root nodes
        for root in root_nodes:
            collect_rewards(root)

        max_depth = max(rewards_by_depth.keys())
        depths = range(max_depth + 1)

        # Calculate mean and std for each depth
        means = []
        stds = []
        for depth in depths:
            values = rewards_by_depth[depth]
            means.append(np.mean(values) if values else 0)
            stds.append(np.std(values) if values else 0)

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot mean line
        ax.plot(depths, means, "r-", label="Mean")

        # Plot STD lines as dotted
        ax.plot(
            depths, np.array(means) + np.array(stds), "r:", alpha=0.2
        )  # Upper STD line
        ax.plot(
            depths, np.array(means) - np.array(stds), "r:", alpha=0.2
        )  # Lower STD line

        # Plot standard deviation bands
        ax.fill_between(
            depths,
            np.array(means) - np.array(stds),
            np.array(means) + np.array(stds),
            color="red",
            alpha=0.2,
            label="±1 STD",
        )

        name = metric.replace("_", " ").title()
        ax.set_xlabel("Depth")
        ax.set_ylabel(f"Cumulative {name}" if cumulative else name)
        ax.set_title(
            f"{'Cumulative ' if cumulative else ''}{name} Distribution Over Tree Depth - Version {self.version}"
        )
        ax.legend()
        ax.grid(True)

        return plt

    def plot_dynamic_resources_by_depth(
        self, root_nodes: List[Node], cumulative: bool = True
    ):
        """
        Create a stacked bar chart showing average/cumulative average number of each type of
        dynamically crafted resource at each depth.

        Args:
            root_nodes: List of root nodes in the MCTS tree
            cumulative: If True, show cumulative averages; if False, show per-depth averages

        Returns:
            matplotlib.pyplot figure
        """
        # Dictionary to store resources by depth
        resources_by_depth = defaultdict(lambda: defaultdict(list))
        all_resource_types = set()

        def traverse_tree(node: Node, depth: int = 0, parent_resources=None):
            if parent_resources is None and cumulative:
                parent_resources = defaultdict(int)

            # Get current node's dynamic achievements
            current_resources = defaultdict(int)
            for achievement, count in node.dynamic_achievements.items():
                current_resources[achievement] = count
                all_resource_types.add(achievement)

            # If cumulative, add parent resources
            if cumulative:
                for resource_type in all_resource_types:
                    current_resources[resource_type] += parent_resources[resource_type]

            # Store resources for this depth
            for resource_type in all_resource_types:
                resources_by_depth[depth][resource_type].append(
                    current_resources[resource_type]
                )

            # Traverse children
            for child in node.children:
                traverse_tree(
                    child, depth + 1, current_resources.copy() if cumulative else None
                )

        # Collect data from all root nodes
        for root in root_nodes:
            traverse_tree(root)

        # Calculate averages for each resource type at each depth
        max_depth = max(resources_by_depth.keys())
        resource_types = sorted(all_resource_types)
        averages = {resource: [0] * (max_depth + 1) for resource in resource_types}

        for depth in range(max_depth + 1):
            for resource in resource_types:
                values = resources_by_depth[depth][resource]
                if values:
                    averages[resource][depth] = np.mean(values)

        # Create stacked bar chart
        fig, ax = plt.subplots(figsize=(12, 8))

        bottom = np.zeros(max_depth + 1)
        bars = []
        for resource in resource_types:
            bars.append(
                ax.bar(
                    range(max_depth + 1),
                    averages[resource],
                    bottom=bottom,
                    label=resource,
                )
            )
            bottom += averages[resource]

        # Customize the plot
        ax.set_xlabel("Depth")
        ax.set_ylabel(f"{'Cumulative ' if cumulative else ''}Average Resources")
        ax.set_title(
            f"{'Cumulative ' if cumulative else ''}Average Dynamic Resources by Depth - Version {self.version}"
        )
        ax.legend(title="Resource Types", bbox_to_anchor=(1.05, 1), loc="upper left")

        # Adjust layout to prevent label cutoff
        plt.tight_layout()

        return plt

    def save_plots(self):
        import os

        results = self._create_trees_from_db()
        os.makedirs(self.dir_path, exist_ok=True)

        # Log run configuration to Neptune
        if self.neptune_run:
            self._log_config_to_neptune()

        metrics = [
            "raw_reward",
            "static_achievements",
            "dynamic_achievements",
            "achievements",
        ]
        for metric in metrics:
            print(f"\nGenerating plots for metric: {metric}")
            plots = {}

            print("Generating tree cumulative plot")
            plots[f"{metric}_tree_cumulative.png"] = self.plot_reward_tree(
                results[0], cumulative=True, metric=metric
            )

            print("Generating tree raw plot")
            plots[f"{metric}_tree_raw.png"] = self.plot_reward_tree(
                results[0], cumulative=False, metric=metric
            )

            print("Generating percentiles cumulative plot")
            plots[f"{metric}_percentiles_cumulative.png"] = (
                self.plot_reward_percentiles(
                    results[0],
                    percentiles=[5 * i for i in range(1, 20)],
                    cumulative=True,
                    metric=metric,
                )
            )

            print("Generating percentiles raw plot")
            plots[f"{metric}_percentiles_raw.png"] = self.plot_reward_percentiles(
                results[0],
                percentiles=[5 * i for i in range(1, 20)],
                cumulative=False,
                metric=metric,
            )

            print("Generating mean/std cumulative plot")
            plots[f"{metric}_mean_std_cumulative.png"] = self.plot_reward_mean_std(
                results[0], metric=metric, cumulative=True
            )

            print("Generating mean/std raw plot")
            plots[f"{metric}_mean_std_raw.png"] = self.plot_reward_mean_std(
                results[0], metric=metric, cumulative=False
            )

            for filename, plot in plots.items():
                filepath = Path(f"{self.dir_path}/{filename}")
                print(f"Saving: {self.dir_path}/{filename}")

                plot.savefig(f"{self.dir_path}/{filename}")

                # Log plot to Neptune
                if self.neptune_run:
                    self.neptune_run[f"plots/{metric}/{filename}"].upload(str(filepath))

                plot.close()
            plt.close("all")

        # Generate and save dynamic resources plots
        print("\nGenerating dynamic resources plots")
        dynamic_plots = {
            "dynamic_resources_cumulative.png": self.plot_dynamic_resources_by_depth(
                results[0], cumulative=True
            ),
            "dynamic_resources_raw.png": self.plot_dynamic_resources_by_depth(
                results[0], cumulative=False
            ),
        }

        for filename, plot in dynamic_plots.items():
            filepath = Path(f"{self.dir_path}/{filename}")
            print(f"Saving: {self.dir_path}/{filename}")
            plot.savefig(f"{self.dir_path}/{filename}")

            # Log plot to Neptune
            if self.neptune_run:
                self.neptune_run[f"plots/dynamic_resources/{filename}"].upload(
                    str(filepath)
                )

            plot.close()
        plt.close("all")

        # Save and log readme
        self._save_and_log_readme()

        # Log config
        self._log_config()

        # Log metrics to Neptune
        if self.neptune_run:
            node = Node(
                id=-1,
                parent_id=None,
                source_code="",
                response=None,
                static_achievements={},
                dynamic_achievements={},
                children=results[0],
                metrics={"raw_reward": 0},
            )
            for result in results[0]:
                result.parent_id = -1
            self._log_step_metrics(node)  # Add this line
            self._log_metrics_to_neptune(node)

    def _log_step_metrics(self, root_node: Node):
        """Log step-by-step metrics for generating charts in Neptune"""
        # Initialize depth-based tracking
        rewards_by_depth = defaultdict(list)
        static_achievements_by_depth = defaultdict(set)
        dynamic_achievements_by_depth = defaultdict(set)
        total_nodes_by_depth = defaultdict(int)
        success_rate_by_depth = defaultdict(lambda: {"success": 0, "total": 0})

        def traverse_tree(node: Node, depth: int = 0, cumulative_reward: float = 0):
            current_reward = node.metrics["raw_reward"] or 0
            cumulative_reward += current_reward

            # Track rewards
            rewards_by_depth[depth].append(current_reward)

            # Track achievements
            static_achievements_by_depth[depth].update(node.static_achievements.keys())
            dynamic_achievements_by_depth[depth].update(
                node.dynamic_achievements.keys()
            )

            # Track node count
            total_nodes_by_depth[depth] += 1

            # Track success rate (non-error executions)
            success_rate_by_depth[depth]["total"] += 1
            if node.response and not any(
                error_term in node.response.lower()
                for error_term in ["error", "exception", "failed"]
            ):
                success_rate_by_depth[depth]["success"] += 1

            # Traverse children
            for child in node.children:
                traverse_tree(child, depth + 1, cumulative_reward)

        # Collect metrics across the tree
        traverse_tree(root_node)
        max_depth = max(rewards_by_depth.keys())

        # Log step-by-step metrics for charts
        for depth in range(max_depth + 1):
            # Rewards
            if rewards_by_depth[depth]:
                self.neptune_run["charts/avg_reward_by_depth"].append(
                    np.mean(rewards_by_depth[depth])
                )
                self.neptune_run["charts/max_reward_by_depth"].append(
                    max(rewards_by_depth[depth])
                )

            # Achievements
            self.neptune_run["charts/static_achievements_by_depth"].append(
                len(static_achievements_by_depth[depth])
            )
            self.neptune_run["charts/dynamic_achievements_by_depth"].append(
                len(dynamic_achievements_by_depth[depth])
            )

            # Node count
            self.neptune_run["charts/nodes_by_depth"].append(
                total_nodes_by_depth[depth]
            )

            # Success rate
            if success_rate_by_depth[depth]["total"] > 0:
                success_rate = (
                    success_rate_by_depth[depth]["success"]
                    / success_rate_by_depth[depth]["total"]
                    * 100
                )
                self.neptune_run["charts/success_rate_by_depth"].append(success_rate)

        # Log cumulative metrics
        cumulative_static = set()
        cumulative_dynamic = set()
        for depth in range(max_depth + 1):
            cumulative_static.update(static_achievements_by_depth[depth])
            cumulative_dynamic.update(dynamic_achievements_by_depth[depth])

            self.neptune_run["charts/cumulative_static_achievements"].append(
                len(cumulative_static)
            )
            self.neptune_run["charts/cumulative_dynamic_achievements"].append(
                len(cumulative_dynamic)
            )
            self.neptune_run["charts/cumulative_total_achievements"].append(
                len(cumulative_static.union(cumulative_dynamic))
            )

    def _log_config_to_neptune(self):
        """Log run configuration to Neptune"""
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                # Get version description
                cur.execute(
                    f"SELECT version_description FROM programs WHERE version = {self.version} LIMIT 1"
                )
                version_description = cur.fetchone()[0]

                # Parse and log configuration
                for line in version_description.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        self.neptune_run[f"parameters/{key.strip()}"] = value.strip()

    def _log_metrics_to_neptune(self, root_node: Node):
        """Log metrics and statistics to Neptune"""
        # Calculate and log various metrics
        max_reward = self._calculate_max_reward(root_node)
        avg_reward = self._calculate_avg_reward(root_node)
        tree_depth = self._calculate_tree_depth(root_node)
        total_nodes = self._calculate_total_nodes(root_node)

        self.neptune_run["metrics/max_reward"] = max_reward
        self.neptune_run["metrics/avg_reward"] = avg_reward
        self.neptune_run["metrics/tree_depth"] = tree_depth
        self.neptune_run["metrics/total_nodes"] = total_nodes

        # Log achievement statistics
        achievement_stats = self._calculate_achievement_stats(root_node)
        for key, value in achievement_stats.items():
            self.neptune_run[f"achievements/{key}"] = value

    def _save_and_log_readme(self):
        """Save README and log it to Neptune"""
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT version_description FROM programs WHERE version = {self.version} LIMIT 1"
                )
                version_description = cur.fetchone()[0]

        readme_path = self.dir_path / "README.md"
        readme_content = f"# Version {self.version}\n\n{version_description}"

        with open(readme_path, "w") as f:
            f.write(readme_content)

        if self.neptune_run:
            self.neptune_run["artifacts/README.md"].upload(str(readme_path))

    def _log_config(self):
        # Load the run.json file
        with open(self.dir_path / "config.json", "r") as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                self.neptune_run[f"config/{key}"] = value

    def _calculate_max_reward(self, node: Node) -> float:
        """Calculate maximum reward in the tree"""
        max_reward = node.metrics["raw_reward"] or 0
        for child in node.children:
            max_reward = max(max_reward, self._calculate_max_reward(child))
        return max_reward

    def _calculate_avg_reward(self, node: Node) -> float:
        """Calculate average reward across all nodes"""
        total_reward = 0
        total_nodes = 0

        def traverse(n: Node):
            nonlocal total_reward, total_nodes
            total_reward += n.metrics["raw_reward"] or 0
            total_nodes += 1
            for child in n.children:
                traverse(child)

        traverse(node)
        return total_reward / total_nodes if total_nodes > 0 else 0

    def _calculate_tree_depth(self, node: Node, current_depth: int = 0) -> int:
        """Calculate maximum depth of the tree"""
        if not node.children:
            return current_depth
        return max(
            self._calculate_tree_depth(child, current_depth + 1)
            for child in node.children
        )

    def _calculate_total_nodes(self, node: Node) -> int:
        """Calculate total number of nodes in the tree"""
        return 1 + sum(self._calculate_total_nodes(child) for child in node.children)

    def _calculate_achievement_stats(self, node: Node) -> Dict[str, int]:
        """Calculate achievement statistics"""
        static_achievements = set()
        dynamic_achievements = set()

        def collect_achievements(n: Node):
            static_achievements.update(n.static_achievements.keys())
            dynamic_achievements.update(n.dynamic_achievements.keys())
            for child in n.children:
                collect_achievements(child)

        collect_achievements(node)

        return {
            "total_static": len(static_achievements),
            "total_dynamic": len(dynamic_achievements),
            "total_unique": len(static_achievements.union(dynamic_achievements)),
        }

    def plot_results(self):
        results = self._create_trees_from_db()
        plot_cum = self.plot_reward_tree(results[0], cumulative=True)
        plot_cum.show()

        percentile_plot_cum = self.plot_reward_percentiles(
            results[0], percentiles=[5 * i for i in range(1, 20)], cumulative=True
        )  # run.plot_reward_tree(results[0])
        percentile_plot_cum.show()
        percentile_plot = self.plot_reward_percentiles(
            results[0], percentiles=[5 * i for i in range(1, 20)], cumulative=False
        )
        percentile_plot.show()

        plot = self.plot_reward_tree(results[0], cumulative=False)
        plot.show()

    def calculate_set_value(
        self, node: Node, depth: int, parent_set: Optional[set] = None, metric: str = ""
    ) -> Tuple[float, set]:
        if parent_set is None:
            parent_set = set()

        current_set = parent_set.union(node.metrics[metric])
        value = len(current_set)
        return value, current_set

    def _create_trees_from_db(self) -> Tuple[List[Node], Set[int]]:
        # Get all nodes for this version
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                print(f"\nExecuting SQL query for version {self.version}")
                cur.execute(f"""SELECT id, parent_id, code, response, achievements_json, value, raw_reward, ticks 
                              FROM programs WHERE version = {self.version}""")
                nodes = cur.fetchall()
                print(f"Found {len(nodes)} total database rows")
                if nodes:
                    print(f"Sample row: {nodes[0]}")

        # Create mapping of nodes
        node_map: Dict[int, Node] = {}
        root_nodes: List[Node] = []
        processed_ids = set()

        print("\nProcessing nodes:")
        # Create Node objects
        for node in nodes:
            (
                id,
                parent_id,
                source_code,
                response,
                achievements_json,
                value,
                raw_reward,
                ticks,
            ) = node
            processed_ids.add(id)
            print(f"Processing node {id} with parent {parent_id}")

            try:
                achievements = (
                    json.loads(achievements_json) if achievements_json else {}
                )
            except:
                achievements = achievements_json
            # Parse achievements
            static_achievements = achievements["static"] if achievements else {}
            dynamic_achievements = achievements["dynamic"] if achievements else {}
            metrics_dict = {
                "value": value,
                "raw_reward": raw_reward,
                "dynamic_achievement_count": len(dynamic_achievements),
                "static_achievement_count": len(static_achievements),
                "dynamic_achievements": set(dynamic_achievements.keys()),
                "static_achievements": set(static_achievements.keys()),
                "achievements": set(static_achievements.keys()).union(
                    set(dynamic_achievements.keys())
                ),
                "ticks": ticks,
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
                metrics=metrics_dict,
            )
            node_map[id] = node_obj

        print("\nBuilding tree structure:")
        # Build tree structure
        for node in node_map.values():
            if node.parent_id is None or node.parent_id not in node_map:
                root_nodes.append(node)
                print(f"Found root node: {node.id}")
            else:
                parent = node_map[node.parent_id]
                parent.children.append(node)
                print(f"Added node {node.id} as child of {node.parent_id}")

        print("\nFinal summary:")
        print(f"Total nodes processed: {len(processed_ids)}")
        print(f"Root nodes found: {[node.id for node in root_nodes]}")

        return root_nodes, processed_ids

    def plot_reward_percentiles(
        self,
        root_nodes: List[Node],
        percentiles=[25, 50, 75],
        cumulative=True,
        metric="raw_reward",
    ):
        rewards_by_depth = defaultdict(list)

        def collect_rewards(
            node: Node,
            depth: int = 0,
            parent_value: float = 0,
            parent_set: Optional[set] = None,
        ):
            # print(f"Using metric {metric}, value: {node.metrics[metric]}")
            if isinstance(node.metrics[metric], set):
                current_set = (
                    parent_set.union(node.metrics[metric])
                    if parent_set
                    else node.metrics[metric]
                )
                value = len(current_set)
            else:
                value = parent_value + (node.metrics[metric] or 0)
                current_set = None

            rewards_by_depth[depth].append(value)
            for child in node.children:
                collect_rewards(
                    child,
                    depth + 1,
                    value if cumulative else 0,
                    current_set if current_set else None,
                )

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
            ax.plot(depths, percentile_values[p], label=f"{p}th percentile")

        name = metric.replace("_", " ").title()
        ax.set_xlabel("Depth")
        ax.set_ylabel(f"Cumulative {name}" if cumulative else name)
        ax.set_title(
            f"{'Cumulative ' if cumulative else ''}{name} Distribution Over Tree Depth - Version {self.version}"
        )
        ax.legend()

        return plt

    def plot_reward_tree(
        self, root_nodes: List[Node], cumulative: bool = True, metric="raw_reward"
    ):
        G = nx.DiGraph()
        nodes_by_depth = defaultdict(list)
        processed_nodes = set()

        def calculate_cumulative_value(
            node: Node,
            depth: int,
            parent_value: float = 0,
            parent_set: Optional[set] = None,
        ) -> float:
            if node.id in processed_nodes:
                return G.nodes[node.id]["value"]

            processed_nodes.add(node.id)

            if isinstance(node.metrics[metric], set):
                value, current_set = self.calculate_set_value(
                    node, depth, parent_set, metric
                )
            else:
                raw_reward = node.metrics[metric] or 0
                value = parent_value + raw_reward
                current_set = None

            G.add_node(node.id, value=value)
            nodes_by_depth[depth].append(node.id)

            for child in node.children:
                G.add_edge(node.id, child.id)
                calculate_cumulative_value(
                    child, depth + 1, value, current_set if current_set else None
                )
            return value

        def add_nodes(node: Node, depth: int = 0):
            if cumulative:
                calculate_cumulative_value(node, depth)
            else:
                value = (
                    len(node.metrics[metric])
                    if isinstance(node.metrics[metric], set)
                    else (node.metrics[metric] or 0)
                )
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
                y = G.nodes[node_id]["value"]
                pos[node_id] = (x, y)

        fig, ax = plt.subplots(figsize=(12, 8))
        values = [G.nodes[node]["value"] for node in G.nodes()]
        nodes = nx.draw_networkx_nodes(
            G, pos, node_color=values, node_size=18, cmap=plt.cm.viridis, ax=ax
        )
        nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, ax=ax, width=0.5)
        name = metric.replace("_", " ").title()
        plt.colorbar(nodes, ax=ax, label=f"Cumulative {name}" if cumulative else name)
        ax.set_xlabel("Depth")
        ax.set_ylabel(f"Cumulative {name}" if cumulative else name)
        ax.set_title(f"MCTS Tree Visualization - Version {self.version}")
        return plt
