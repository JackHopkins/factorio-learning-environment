import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, NamedTuple
import numpy as np
import pandas as pd
from collections import defaultdict
import pickle
import os

from dotenv import load_dotenv
from eval.open.plots.simple_run_visualiser import Node

load_dotenv()


class StatsResult(NamedTuple):
    """Container for statistical results"""

    mean: float
    median: float
    std: float


@dataclass
class Achievement:
    """Represents an achievement milestone"""

    depth: int
    ticks: int
    item_name: str
    ingredients: int
    is_dynamic: bool


@dataclass
class ModelStats:
    """Statistics for a model at a specific timestep"""

    gdp: StatsResult
    achievement_count: StatsResult
    error_rate: StatsResult
    growth_rate: Optional[StatsResult] = None


class ProgressionAnalyzer:
    """Analyzes progression metrics across different models"""

    def __init__(self, cache_file: str = "viz_cache.pkl"):
        self.cache_file = cache_file
        self.versions = {}  # version -> {nodes: List[Node], label: str}
        self.achievements = defaultdict(list)
        self.timesteps = [8, 16, 32, 64, 128, 256, 512, 1000]

    def _deserialize_version_data(self, serialized):
        """Restore version data from cached format"""
        for version, data in serialized.items():
            # First create all Node objects without children
            nodes_dict = {}
            for node_id, node_data in data["nodes_dict"].items():
                nodes_dict[node_id] = Node(
                    id=node_data["id"],
                    parent_id=node_data["parent_id"],
                    metrics=node_data["metrics"],
                    static_achievements=node_data["static_achievements"],
                    dynamic_achievements=node_data["dynamic_achievements"],
                    children=[],
                )

            # Then populate children
            for node_id, node_data in data["nodes_dict"].items():
                nodes_dict[node_id].children = [
                    nodes_dict[child_id] for child_id in node_data["children_ids"]
                ]

            self.versions[version] = {
                "nodes": [nodes_dict[root_id] for root_id in data["root_ids"]],
                "label": data["label"],
            }

    def load_data(self, versions: List[int], labels: Dict[int, str]):
        """Load data from cache file"""
        if not os.path.exists(self.cache_file):
            raise FileNotFoundError(f"Cache file {self.cache_file} not found")

        try:
            with open(self.cache_file, "rb") as f:
                cached_data = pickle.load(f)
                if cached_data.get("versions") == versions:
                    self._deserialize_version_data(cached_data["data"])
                    self.achievements = cached_data["achievements"]
                else:
                    raise ValueError("Cache versions don't match requested versions")
        except Exception as e:
            raise Exception(f"Error loading cache: {e}")

    def _calculate_stats(self, values: List[float]) -> StatsResult:
        """Calculate mean, median, and standard deviation for a list of values"""
        if not values:
            return StatsResult(0.0, 0.0, 0.0)

        return StatsResult(
            mean=np.mean(values),
            median=np.median(values),
            std=np.std(values, ddof=1) if len(values) > 1 else 0.0,
        )

    def _calculate_stats_at_timestep(
        self, nodes: List[Node], timestep: int
    ) -> ModelStats:
        """Calculate statistics for a specific timestep"""
        gdp_values = []
        achievement_counts = []
        error_rates = []

        # Calculate stats for each root node to get distribution
        for root in nodes:
            total_gdp = 0
            achievements = set()
            error_count = 0
            total_nodes = 0

            stack = [(root, 0, 0)]  # (node, depth, cumulative_value)
            while stack:
                node, depth, prev_value = stack.pop()
                if depth > timestep:
                    continue

                total_nodes += 1
                if "error" in str(node.metrics.get("response", "")).lower():
                    error_count += 1

                value = prev_value + node.metrics["value"]
                total_gdp = max(total_gdp, value)

                achievements.update(node.static_achievements.keys())
                achievements.update(node.dynamic_achievements.keys())

                stack.extend((child, depth + 1, value) for child in node.children)

            gdp_values.append(total_gdp)
            achievement_counts.append(len(achievements))
            error_rates.append(error_count / max(1, total_nodes))

        return ModelStats(
            gdp=self._calculate_stats(gdp_values),
            achievement_count=self._calculate_stats(achievement_counts),
            error_rate=self._calculate_stats(error_rates),
        )

    def _calculate_per_step_growth_rate(
        self, current_stats: StatsResult, prev_stats: StatsResult, steps_between: int
    ) -> StatsResult:
        """Calculate the average per-step growth rate statistics between two timesteps"""
        if prev_stats.mean <= 0 or current_stats.mean <= 0:
            return StatsResult(0.0, 0.0, 0.0)

        # Calculate growth rates using different statistical measures
        mean_growth = (current_stats.mean / prev_stats.mean) - 1
        median_growth = (current_stats.median / prev_stats.median) - 1

        # Calculate per-step rates
        mean_rate = ((1 + mean_growth) ** (1 / steps_between)) - 1
        median_rate = ((1 + median_growth) ** (1 / steps_between)) - 1

        # Calculate growth rate standard deviation using error propagation
        relative_error = np.sqrt(
            (current_stats.std / current_stats.mean) ** 2
            + (prev_stats.std / prev_stats.mean) ** 2
        )
        rate_std = mean_rate * relative_error

        # Convert to percentages
        return StatsResult(
            mean=mean_rate * 100, median=median_rate * 100, std=rate_std * 100
        )

    def generate_analysis(self) -> pd.DataFrame:
        """Generate analysis table for all models and timesteps"""
        data = []

        for version, info in self.versions.items():
            model_name = info["label"]
            timestep_stats = {}

            # First pass: calculate stats for all timesteps
            for timestep in self.timesteps:
                stats = self._calculate_stats_at_timestep(info["nodes"], timestep)
                timestep_stats[timestep] = stats.gdp

            # Second pass: calculate growth rates and compile data
            for i, timestep in enumerate(self.timesteps):
                stats = self._calculate_stats_at_timestep(info["nodes"], timestep)

                # Calculate growth rate
                if i > 0:
                    prev_timestep = self.timesteps[i - 1]
                    steps_between = timestep - prev_timestep
                    growth_stats = self._calculate_per_step_growth_rate(
                        timestep_stats[timestep],
                        timestep_stats[prev_timestep],
                        steps_between,
                    )
                else:
                    growth_stats = self._calculate_per_step_growth_rate(
                        timestep_stats[timestep],
                        StatsResult(1.0, 1.0, 0.0),  # Assume starting GDP of 1
                        timestep,
                    )

                final_gdp = timestep_stats[self.timesteps[-1]]
                data.append(
                    {
                        "Model": f"{model_name} (~GDP: {final_gdp.mean:.1f}/{final_gdp.median:.1f}±{final_gdp.std:.1f})",
                        "Timestep": timestep,
                        "GDP": f"{stats.gdp.mean:.1f}/{stats.gdp.median:.1f}±{stats.gdp.std:.1f}",
                        "GDP Growth Rate": f"{growth_stats.mean:.1f}/{growth_stats.median:.1f}±{growth_stats.std:.1f}%",
                        "Achievements": f"{stats.achievement_count.mean:.1f}/{stats.achievement_count.median:.1f}±{stats.achievement_count.std:.1f}",
                        "Error Rate": f"{stats.error_rate.mean:.2%}/{stats.error_rate.median:.2%}±{stats.error_rate.std:.2%}",
                    }
                )

        return pd.DataFrame(data)

    def export_analysis(self, output_file: str):
        """Export analysis to CSV file"""
        df = self.generate_analysis()

        # Pivot tables for better readability
        gdp_table = df.pivot(index="Model", columns="Timestep", values="GDP")
        growth_table = df.pivot(
            index="Model", columns="Timestep", values="GDP Growth Rate"
        )
        achievements_table = df.pivot(
            index="Model", columns="Timestep", values="Achievements"
        )
        error_table = df.pivot(index="Model", columns="Timestep", values="Error Rate")

        # Combine tables with headers
        with open(output_file, "w") as f:
            f.write("GDP by Timestep (mean/median±std)\n")
            f.write(gdp_table.to_csv())
            f.write("\nGDP Growth Rate by Timestep (per step) (mean/median±std)\n")
            f.write(growth_table.to_csv())
            f.write("\nAchievements by Timestep (mean/median±std)\n")
            f.write(achievements_table.to_csv())
            f.write("\nError Rate by Timestep (mean/median±std)\n")
            f.write(error_table.to_csv())


async def main():
    # Configure versions to plot
    versions = {
        492: "Claude",
        490: "GPT-4",
        505: "GPT-4-Mini",
        488: "LLaMA-70B",
    }

    # Generate analysis tables
    analyzer = ProgressionAnalyzer()
    analyzer.load_data(list(versions.keys()), versions)
    analyzer.export_analysis("progression_analysis.csv")


if __name__ == "__main__":
    asyncio.run(main())
