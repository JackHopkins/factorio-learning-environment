import asyncio
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from PIL import Image
import numpy as np
from collections import defaultdict

from dotenv import load_dotenv

from search.db_client import DBClient
from search.mcts.plots.run_results import RunResults

load_dotenv()

@dataclass
class Achievement:
    depth: int
    item_name: str
    quantity: int
    is_dynamic: bool


class MultiVersionMCTSVisualizer:
    def __init__(self, db_client, icons_path: str):
        self.db_client = db_client
        self.icons_path = icons_path
        self.version_data = {}  # Store data for multiple versions
        self.achievements = defaultdict(list)  # Achievements per version

    def load_versions(self, versions: List[int], labels: Dict[int, str]):
        """Load data for multiple MCTS versions"""
        for version in versions:
            run_results = RunResults(version=version, db_client=self.db_client)
            root_nodes, _ = run_results._create_trees_from_db()
            self.version_data[version] = {
                'nodes': root_nodes,
                'label': labels[version]
            }

    def process_achievements(self, max_depth: int = 100):
        """Process achievements for all versions"""
        for version, data in self.version_data.items():
            seen_items = set()

            def traverse_tree(node, depth=0):
                if depth > max_depth:
                    return

                if hasattr(node, 'static_achievements'):
                    for category in ['static', 'dynamic']:
                        items = node.static_achievements if category == 'static' else node.dynamic_achievements
                        for item_name, quantity in items.items():
                            if item_name not in seen_items:
                                self.achievements[version].append(Achievement(
                                    depth=depth,
                                    item_name=item_name,
                                    quantity=quantity,
                                    is_dynamic=(category == 'dynamic')
                                ))
                                seen_items.add(item_name)

                for child in node.children:
                    traverse_tree(child, depth + 1)

            for root in data['nodes']:
                traverse_tree(root)

            self.achievements[version].sort(key=lambda x: x.depth)

    def process_icons(self):
        """Process icons for all achievements"""
        os.makedirs("icons", exist_ok=True)

        all_items = set()
        for achievements in self.achievements.values():
            for achievement in achievements:
                all_items.add(achievement.item_name)

        for item_name in all_items:
            icon_path = os.path.join(self.icons_path, f"{item_name}.png")
            output_path = f"icons/{item_name}.png"

            if os.path.exists(icon_path) and not os.path.exists(output_path):
                with Image.open(icon_path) as img:
                    tile_size = img.height
                    first_tile = img.crop((0, 0, tile_size, tile_size))
                    first_tile.save(output_path)

    def calculate_version_stats(self, version: int, max_depth: int):
        """Calculate statistics for a specific version"""
        values_by_depth = defaultdict(list)

        def traverse_tree(node, depth=0, cumulative_value=0):
            if depth > max_depth:
                return

            current_value = node.metrics.get('value', 0) or 0
            total_value = cumulative_value + current_value
            values_by_depth[depth].append(total_value)

            for child in node.children:
                traverse_tree(child, depth + 1, total_value)

        achievements_by_depth = defaultdict(list)
        for achievement in self.achievements[version]:
            achievements_by_depth[achievement.depth].append(achievement)

        for root in self.version_data[version]['nodes']:
            traverse_tree(root)

        # Calculate statistics for each depth
        depth_stats = {}
        for depth in range(max_depth + 1):
            values = values_by_depth.get(depth, [0])
            depth_stats[depth] = {
                'mean': np.mean(values),
                'std': np.std(values)
            }

        return depth_stats, achievements_by_depth

    def export_latex_progression(self, output_file: str = 'mcts_progression.tex', max_depth: int = 100):
        """Export multi-version visualization as LaTeX"""
        self.process_icons()

        # Collect first-step achievements for each model
        initial_achievements = {}
        for version, data in self.version_data.items():
            initial_achievements[version] = [
                achievement for achievement in self.achievements[version]
                if achievement.depth == 0 or achievement.depth == 1
            ]

        # Define colors for different versions
        colors = ['blue!80!red', 'red!90!black', 'green!70!blue', 'orange!90!red', 'blue!80!red', 'red!90!black']

        # Generate LaTeX code
        latex_code = []

        # Start the tikzpicture environment
        latex_code.append(r"\begin{tikzpicture}")

        # Main plot axis settings
        latex_code.append(r"\begin{axis}[")
        latex_code.append(r"    name=mainplot,")
        latex_code.append(r"    width=\textwidth,")
        latex_code.append(r"    height=0.6\textwidth,")
        latex_code.append(r"    xlabel=Search Depth,")
        latex_code.append(r"    ylabel=Cumulative Value,")
        latex_code.append(r"    grid style={line width=.1pt, draw=gray!10},")
        latex_code.append(r"    major grid style={line width=.2pt,draw=gray!50},")
        latex_code.append(r"    grid=both,")
        latex_code.append(r"    minor tick num=1,")
        latex_code.append(r"    clip=false,")
        latex_code.append(r"    xmode=log,")
        latex_code.append(r"    log basis x=2,")
        latex_code.append(r"    ymode=log,")
        latex_code.append(r"    log basis y=2,")
        latex_code.append(r"    enlarge x limits=false,")
        latex_code.append(r"    xmin=1,")
        latex_code.append(r"    xmax=32,")
        latex_code.append(r"    xtick={1,2,4,8,16,32},")
        latex_code.append(r"    xticklabels={$2^0$,$2^1$,$2^2$,$2^3$,$2^4$,$2^5$},")
        latex_code.append(r"    ymin=64,")
        latex_code.append(r"    ymax=16384,")
        latex_code.append(r"    ytick={64,128,256,512,1024,2048,4096,8192,16384},")
        latex_code.append(r"    yticklabels={$2^6$,$2^7$,$2^8$,$2^9$,$2^{10}$,$2^{11}$,$2^{12}$,$2^{13}$,$2^{14}$},")
        latex_code.append(r"    legend pos=north west,")
        latex_code.append(r"    legend style={font=\small},")
        latex_code.append(r"    legend cell align={left},")
        # Escape model names for LaTeX
        legend_entries = [data['label'].replace('_', '\\_') for data in self.version_data.values()]
        latex_code.append(r"    legend entries={" + ",".join(legend_entries) + "}")
        latex_code.append(r"]")

        # Plot data for each version
        for i, version in enumerate(self.version_data):
            depth_stats, achievements_by_depth = self.calculate_version_stats(version, max_depth)
            if not depth_stats:  # Skip if no data
                continue

            color = colors[i % len(colors)]

            # Add achievement markers and icons
            for depth, achievements in achievements_by_depth.items():
                value = depth_stats[depth]['mean']
                if value <= 64:  # Skip if below y-axis minimum
                    continue

                # Calculate vertical offsets for stacking icons
                num_achievements = len(achievements)
                spacing = max(value * 0.05, 32)  # Minimum spacing of 64 (ymin)
                total_height = num_achievements * spacing
                start_offset = -(total_height - spacing) / 2

                # Add icons with vertical offsets
                for j, achievement in enumerate(achievements):
                    icon_output = f"icons/{achievement.item_name}.png"
                    if os.path.exists(icon_output):
                        vertical_offset = start_offset + (j * spacing)
                        position = max(value + vertical_offset, 64)  # Ensure position is above ymin
                        latex_code.append(f"\\node at (axis cs:{depth + 1 if depth == 0 else depth},{position}) {{")
                        latex_code.append(f"    \\includegraphics[width=1em]{{{icon_output}}}")
                        latex_code.append("};")

            # Only add plots if we have valid data
            valid_stats = {d: s for d, s in depth_stats.items() if s['mean'] > 64}
            if valid_stats:
                # Add confidence bounds
                latex_code.append(f"\\addplot[{color}, dotted, name path=series_{i}_upper, forget plot] coordinates {{")
                latex_code.extend(f"({d},{max(s['mean'] + s['std'], 64)})" for d, s in valid_stats.items())
                latex_code.append("};")

                latex_code.append(f"\\addplot[{color}, dotted, name path=series_{i}_lower, forget plot] coordinates {{")
                latex_code.extend(f"({d},{max(s['mean'] - s['std'], 64)})" for d, s in valid_stats.items())
                latex_code.append("};")

                # Add filled area between bounds
                latex_code.append(
                    f"\\addplot[{color}, opacity=0.2, forget plot] fill between[of=series_{i}_upper and series_{i}_lower];")

                # Add mean line
                latex_code.append(f"\\addplot[{color}, thick] coordinates {{")
                latex_code.extend(f"({d},{max(s['mean'], 64)})" for d, s in valid_stats.items())
                latex_code.append("};")

        latex_code.append(r"\end{axis}")

        # Add achievement legend below
        latex_code.append(r"\node[below=2.0cm of mainplot, anchor=north, align=left] {")
        latex_code.append(r"    \vspace{0.2cm}")
        latex_code.append(r"    \begin{tabular}{l@{\hspace{0.5cm}}l@{\hspace{0.5cm}}l}")

        # Sort versions by achievement count
        version_achievements = []
        for version in self.version_data:
            label = self.version_data[version]['label'].replace('_', '\\_')  # Escape underscores
            achievements = initial_achievements[version]
            color = colors[list(self.version_data.keys()).index(version) % len(colors)]
            version_achievements.append((version, label, achievements, color))

        # Sort by achievement count in descending order
        version_achievements.sort(key=lambda x: len(x[2]), reverse=True)

        # Add each model's achievements with color indicator line
        for version, label, achievements, color in version_achievements:
            # Create a small line plot indicator
            line_indicator = f"\\raisebox{{0.5ex}}{{\\tikz\\draw[{color}, thick] (0,0) -- (1em,0);}}"

            if not achievements:
                latex_code.append(f"    {line_indicator} & \\textbf{{{label}}} & $\\varnothing$ \\\\[0.2cm]")
                continue

            icons = " ".join([
                f"\\includegraphics[width=1em]{{icons/{ach.item_name}.png}}"
                for ach in sorted(achievements, key=lambda x: x.item_name)
            ])

            # Add line indicator before the label
            latex_code.append(
                f"    {line_indicator} & \\textbf{{{label}}} & {icons} \\\\[0.2cm]"
            )

        latex_code.append(r"    \end{tabular}")
        latex_code.append(r"};")
        latex_code.append(r"\end{tikzpicture}")

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_code))


async def main():
    # Initialize database client
    db_client = DBClient(
        max_conversation_length=40,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )

    # Initialize visualizer
    icons_path = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/icons/early_icons"
    visualizer = MultiVersionMCTSVisualizer(db_client, icons_path)

    # Load multiple versions
   # versions = [361]#, 332, 334, 335, 336, 344]
    labels = {
        361: 'claude-3-5-sonnet-20241022',
        366: 'gpt-4o',
        #375: 'gemini-2.0-flash-exp',
        374: 'Llama-3.3-70B-Instruct-Turbo',
        381: 'gpt-4o-mini',
        382: 'Qwen/Qwen2.5-72B-Instruct-Turbo',
        # 332: 'gpt-4o',
        # 334: 'gemini-2.0-flash-exp',
        # 335: 'Llama-3.3-70B-Instruct-Turbo',
        336: 'Llama-3.1-8B-Instruct-Turbo',
        # 344: 'Qwen/Qwen2.5-72B-Instruct-Turbo'
    }
    versions = list(labels.keys())
    # Process data and generate visualization
    visualizer.load_versions(versions, labels)
    visualizer.process_achievements(max_depth=32)
    visualizer.export_latex_progression('mcts_progression_content.tex', max_depth=32)


if __name__ == '__main__':
    asyncio.run(main())