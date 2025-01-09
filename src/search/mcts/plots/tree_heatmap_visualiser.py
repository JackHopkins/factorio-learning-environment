import asyncio
import os

import numpy as np
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

from dotenv import load_dotenv

from search.mcts.db_client import DBClient
from search.mcts.plots.run_results import RunResults, Node

load_dotenv()

@dataclass
class MCTSNode:
    depth: int
    value: float
    children: List['MCTSNode']


class MCTSVisualizer:
    def __init__(self, db_client):
        self.db_client = db_client
        self.versions_data = {}

    def load_versions(self, versions: List[int]):
        """Load data for multiple MCTS versions"""
        for version in versions:
            run_results = RunResults(version=version, db_client=self.db_client)
            root_nodes, _ = run_results._create_trees_from_db()
            self.versions_data[version] = root_nodes

    def generate_heatmap_data(self, metric='raw_reward', max_depth=100):
        """Generate heatmap data for all loaded versions"""
        heatmap_data = {}

        for version, root_nodes in self.versions_data.items():
            # Create depth-value matrix
            values_by_depth = defaultdict(list)

            def traverse_tree(node: Node, depth: int = 0, cumulative_value: float = 0):
                if depth > max_depth:
                    return

                current_value = node.metrics.get(metric, 0) or 0
                total_value = cumulative_value + current_value
                values_by_depth[depth].append(total_value)

                for child in node.children:
                    traverse_tree(child, depth + 1, total_value)

            # Collect values for all root nodes
            for root in root_nodes:
                traverse_tree(root)

            # Convert to numpy array and calculate statistics
            depth_stats = {}
            for depth in range(max_depth + 1):
                values = values_by_depth.get(depth, [0])
                depth_stats[depth] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'percentiles': {
                        p: np.percentile(values, p)
                        for p in [25, 50, 75]
                    }
                }

            heatmap_data[version] = depth_stats

        return heatmap_data

    # def export_latex_heatmap(self, heatmap_data, stat='mean', output_file='mcts_heatmap.tex'):
    #     """Export heatmap data as LaTeX tikz heatmap"""
    #     versions = sorted(heatmap_data.keys())
    #     max_depth = max(len(data) for data in heatmap_data.values())
    #
    #     # Prepare data table
    #     data_points = []
    #     for i, version in enumerate(versions):
    #         for j in range(max_depth):
    #             if stat == 'mean':
    #                 value = heatmap_data[version][j]['mean']
    #             elif stat in ['min', 'max', 'std']:
    #                 value = heatmap_data[version][j][stat]
    #             elif stat.startswith('percentile'):
    #                 p = int(stat.split('_')[1])
    #                 value = heatmap_data[version][j]['percentiles'][p]
    #             data_points.append(f"{j} {i} {value}")
    #
    #     # Get value range for colorbar
    #     values = [float(d.split()[2]) for d in data_points]
    #     vmin, vmax = min(values), max(values)
    #
    #     # Generate LaTeX code
    #     latex_code = []
    #     latex_code.append(r"\begin{tikzpicture}")
    #     latex_code.append(r"\begin{axis}[")
    #     latex_code.append(r"    xlabel=Depth,")
    #     latex_code.append(r"    ylabel=Version,")
    #     latex_code.append(r"    colormap/viridis,")
    #     latex_code.append(r"    colorbar,")
    #     latex_code.append(f"    point meta min={vmin},")
    #     latex_code.append(f"    point meta max={vmax},")
    #     latex_code.append(r"    view={0}{90},")
    #     latex_code.append(r"    matrix plot,")
    #     latex_code.append(f"    mesh/cols={max_depth},")
    #     latex_code.append(f"    mesh/rows={len(versions)},")
    #     latex_code.append(r"    point meta=explicit")
    #     latex_code.append(r"]")
    #
    #     # Add data table
    #     latex_code.append(r"\addplot[matrix plot*] table[meta=value] {")
    #     latex_code.append("x y value")
    #     latex_code.extend(data_points)
    #     latex_code.append("};")
    #
    #     latex_code.append(r"\end{axis}")
    #     latex_code.append(r"\end{tikzpicture}")
    #
    #     # Save to file
    #     with open(output_file, 'w') as f:
    #         f.write('\n'.join(latex_code))
    #
    #     return output_file
    #
    # def export_latex_heatmap_old(self, heatmap_data, stat='mean', output_file='mcts_heatmap.tex'):
    #     """Export heatmap data as LaTeX tikz heatmap"""
    #     versions = sorted(heatmap_data.keys())
    #     max_depth = max(len(data) for data in heatmap_data.values())
    #
    #     # Normalize values across all versions
    #     all_values = []
    #     for version in versions:
    #         for depth in range(max_depth):
    #             if stat == 'mean':
    #                 value = heatmap_data[version][depth]['mean']
    #             elif stat in ['min', 'max', 'std']:
    #                 value = heatmap_data[version][depth][stat]
    #             elif stat.startswith('percentile'):
    #                 p = int(stat.split('_')[1])
    #                 value = heatmap_data[version][depth]['percentiles'][p]
    #             all_values.append(value)
    #
    #     vmin, vmax = np.min(all_values), np.max(all_values)
    #
    #     # Generate LaTeX code
    #     latex_code = []
    #     latex_code.append(r"\begin{tikzpicture}")
    #     latex_code.append(r"\begin{axis}[")
    #     latex_code.append(r"    xlabel=Depth,")
    #     latex_code.append(r"    ylabel=Version,")
    #     latex_code.append(r"    colormap/viridis,")
    #     latex_code.append(r"    colorbar,")
    #     latex_code.append(r"    point meta min=" + f"{vmin},")
    #     latex_code.append(r"    point meta max=" + f"{vmax},")
    #     latex_code.append(r"]")
    #
    #     # Add heatmap matrix
    #     for i, version in enumerate(versions):
    #         for j in range(max_depth):
    #             if stat == 'mean':
    #                 value = heatmap_data[version][j]['mean']
    #             elif stat in ['min', 'max', 'std']:
    #                 value = heatmap_data[version][j][stat]
    #             elif stat.startswith('percentile'):
    #                 p = int(stat.split('_')[1])
    #                 value = heatmap_data[version][j]['percentiles'][p]
    #
    #             # Normalize value
    #             norm_value = (value - vmin) / (vmax - vmin) if vmax > vmin else 0
    #             latex_code.append(f"\\addplot[point meta={value}] coordinates {{({j},{i})}};")
    #
    #     latex_code.append(r"\end{axis}")
    #     latex_code.append(r"\end{tikzpicture}")
    #
    #     # Save to file
    #     with open(output_file, 'w') as f:
    #         f.write('\n'.join(latex_code))
    #
    #     return output_file

    def export_distribution_latex(self, heatmap_data, labels=None, output_file='mcts_distribution.tex', alpha=0.2,
                                  cumulative=True):
        """
        Export version distributions as LaTeX plot with shaded areas for ±1 STD

        Args:
            heatmap_data: Dictionary of statistics by version and depth
            labels: Dictionary mapping version numbers to display labels
            output_file: Output LaTeX file path
            alpha: Transparency value for shaded areas (0-1)
            cumulative: If True, show cumulative values over depth
        """
        versions = sorted(heatmap_data.keys())
        max_depth = max(len(data) for data in heatmap_data.values())

        if labels is None:
            labels = {v: f"Version {v}" for v in versions}

        colors = [
            'blue!80!red',
            'red!90!black',
            'green!70!blue',
            'orange!90!red'
        ]

        latex_code = []
        latex_code.append(r"\begin{figure*}[tp]")
        latex_code.append(r"\centering")
        latex_code.append(r"\begin{tikzpicture}")
        latex_code.append(r"\begin{axis}[")
        latex_code.append(r"    width=\textwidth,")
        latex_code.append(r"    height=0.6\textwidth,")
        latex_code.append(r"    xlabel=Search Depth,")
        latex_code.append(r"    ylabel=Cumulative Value" if cumulative else r"    ylabel=Value", )
        latex_code.append(r"    grid=major,")
        latex_code.append(r"    legend pos=north west,")
        latex_code.append(r"    legend style={font=\small},")
        latex_code.append(r"    legend cell align={left},")
        latex_code.append(f"    legend entries={{{','.join(labels[v] for v in versions)}}}")
        latex_code.append(r"]")

        # First pass: Define all paths
        for idx, version in enumerate(versions):
            color = colors[idx % len(colors)]
            safe_name = f"series_{idx}"

            means = []
            std_uppers = []
            std_lowers = []

            # Keep track of cumulative values
            cumulative_mean = 0
            cumulative_std_upper = 0
            cumulative_std_lower = 0

            for depth in range(max_depth):
                stats = heatmap_data[version][depth]
                mean = stats['mean']
                std = stats['std']

                if cumulative:
                    cumulative_mean += mean
                    # For cumulative std, we need to accumulate the variances
                    # std_upper and std_lower will track the cumulative boundaries
                    cumulative_std_upper += (mean + std)
                    cumulative_std_lower += (mean - std)

                    means.append(f"({depth},{cumulative_mean})")
                    std_uppers.append(f"({depth},{cumulative_std_upper})")
                    std_lowers.append(f"({depth},{cumulative_std_lower})")
                else:
                    means.append(f"({depth},{mean})")
                    std_uppers.append(f"({depth},{mean + std})")
                    std_lowers.append(f"({depth},{mean - std})")

            # Define upper and lower paths
            latex_code.append(f"% {labels[version]} boundaries")
            latex_code.append(f"\\addplot[{color}, dotted, name path={safe_name}_upper, forget plot] coordinates {{")
            latex_code.append("    " + " ".join(std_uppers))
            latex_code.append("};")

            latex_code.append(f"\\addplot[{color}, dotted, name path={safe_name}_lower, forget plot] coordinates {{")
            latex_code.append("    " + " ".join(std_lowers))
            latex_code.append("};")

        # Second pass: Fill between paths and add mean lines
        for idx, version in enumerate(versions):
            color = colors[idx % len(colors)]
            safe_name = f"series_{idx}"

            means = []
            cumulative_mean = 0

            for depth in range(max_depth):
                stats = heatmap_data[version][depth]
                if cumulative:
                    cumulative_mean += stats['mean']
                    means.append(f"({depth},{cumulative_mean})")
                else:
                    means.append(f"({depth},{stats['mean']})")

            # Fill between previously defined paths
            latex_code.append(f"% {labels[version]} fill and mean")
            latex_code.append(
                f"\\addplot[{color}, opacity={alpha}, forget plot] fill between[of={safe_name}_upper and {safe_name}_lower];")

            # Add mean line (this will show in legend)
            latex_code.append(f"\\addplot[{color}, thick] coordinates {{")
            latex_code.append("    " + " ".join(means))
            latex_code.append("};")

        latex_code.append(r"\end{axis}")
        latex_code.append(r"\end{tikzpicture}")
        latex_code.append(
            r"\caption{Cumulative value over search depth for different models, showing mean (solid line) and one standard deviation (dotted lines).}")
        latex_code.append(r"\label{fig:mcts-comparison}")
        latex_code.append(r"\end{figure*}")

        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_code))

        return output_file

    def export_distribution_latex2(self, heatmap_data, output_file='mcts_distribution.tex'):
        """Export version distributions as LaTeX plot with shaded areas for ±2 STD"""
        versions = sorted(heatmap_data.keys())
        max_depth = max(len(data) for data in heatmap_data.values())

        # Colors for different versions
        colors = ['blue', 'red', 'green!50!black', 'orange', 'purple', 'brown']

        latex_code = []
        latex_code.append(r"\begin{tikzpicture}")
        latex_code.append(r"\begin{axis}[")
        latex_code.append(r"    width=\textwidth,")
        latex_code.append(r"    height=0.6\textwidth,")
        latex_code.append(r"    xlabel=Depth,")
        latex_code.append(r"    ylabel=Value,")
        latex_code.append(r"    grid=major,")
        latex_code.append(r"    legend pos=north west,")
        latex_code.append(r"    legend style={font=\small},")

        # Generate legend entries
        legend_entries = [f"Version {v}" for v in versions]
        latex_code.append(f"    legend entries={{{','.join(legend_entries)}}}")
        latex_code.append(r"]")

        # Generate plots for each version
        for idx, version in enumerate(versions):
            color = colors[idx % len(colors)]

            # Collect coordinates
            means = []
            uppers = []
            lowers = []

            for depth in range(max_depth):
                stats = heatmap_data[version][depth]
                mean = stats['mean']
                std = stats['std']
                means.append(f"({depth},{mean})")
                uppers.append(f"({depth},{mean + 2 * std})")
                lowers.append(f"({depth},{mean - 2 * std})")

            # Add shaded area between upper and lower bounds
            latex_code.append(f"% Version {version} distribution")
            latex_code.append(f"\\addplot[draw={color}, name path=v{version}upper, forget plot] coordinates {{")
            latex_code.append("    " + " ".join(uppers))
            latex_code.append("};")

            latex_code.append(f"\\addplot[draw={color}, name path=v{version}lower, forget plot] coordinates {{")
            latex_code.append("    " + " ".join(lowers))
            latex_code.append("};")

            latex_code.append(
                f"\\addplot[{color}!20, opacity=0.3] fill between[of=v{version}upper and v{version}lower];")

            # Add mean line
            latex_code.append(f"\\addplot[{color}, thick] coordinates {{")
            latex_code.append("    " + " ".join(means))
            latex_code.append("};")

        latex_code.append(r"\end{axis}")
        latex_code.append(r"\end{tikzpicture}")

        # Save to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_code))

        return output_file

    def export_data_file(self, heatmap_data, output_file='mcts_data.json'):
        """Export raw data as JSON for further processing"""
        with open(output_file, 'w') as f:
            json.dump(heatmap_data, f, indent=2)

async def main():
    try:
        db_client = DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD")
        )
    except Exception as e:
        print("\033[91mError connecting to the database. Please check your credentials and try again.\033[91m")
        return

    # Initialize
    visualizer = MCTSVisualizer(db_client)

    # Load multiple versions
    versions = [331, 332, 334, 335, 336]
    labels={
        331: 'claude-3-5-sonnet-20241022',
        332: 'gpt-4o',
        334: 'gemini-2.0-flash-exp',
        335: 'Llama-3.3-70B-Instruct-Turbo',
        336: 'Llama-3.1-8B-Instruct-Turbo'
    }
    visualizer.load_versions(versions)

    # Generate heatmap data
    heatmap_data = visualizer.generate_heatmap_data(metric='value', max_depth=60)

    # Export as LaTeX
    visualizer.export_distribution_latex(heatmap_data, output_file='mcts_mean_heatmap.tex', labels=labels, cumulative=True)

    # Export raw data
    visualizer.export_data_file(heatmap_data, output_file='mcts_data.json')

if __name__ == '__main__':
    asyncio.run(main())