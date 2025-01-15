import asyncio
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from PIL import Image
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
    ingredients: int


class RunVisualizer:
    def __init__(self, db_client, icons_path: str):
        self.db_client = db_client
        self.icons_path = icons_path
        self.version_data = {}
        self.achievements = defaultdict(list)

    def load_versions(self, versions: List[int], labels: Dict[int, str]):
        """Load data for multiple MCTS versions"""
        for version in versions:
            run_results = RunResults(version=version, db_client=self.db_client)
            root_nodes, _ = run_results._create_trees_from_db()
            self.version_data[version] = {
                'nodes': root_nodes,
                'label': labels[version]
            }

    def count_total_ingredients(self, recipe_dict):
        """Count total unique ingredients in recipe tree"""
        seen = set()

        def traverse_ingredients(item):
            # Add current ingredient
            seen.add(item['name'])
            # Recursively process sub-ingredients
            for ingredient in item.get('ingredients', []):
                traverse_ingredients(ingredient)

        traverse_ingredients(recipe_dict)
        # Subtract 1 to not count the item itself
        return len(seen) - 1

    def process_achievements(self, max_depth: int = 100):
        """Process achievements for all versions"""

        # Write to file
        recipes = {}
        with open('./recipes.jsonl', 'r') as f:
            for line in f:
                recipe = json.loads(line)
                recipes[recipe['name']] = recipe

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
                                    ingredients=self.count_total_ingredients(recipes[item_name]) if item_name in recipes else 0,
                                    is_dynamic=(category == 'dynamic')
                                ))
                                seen_items.add(item_name)

                for child in node.children:
                    traverse_tree(child, depth + 1)

            for root in data['nodes']:
                traverse_tree(root)

            self.achievements[version].sort(key=lambda x: (x.ingredients, x.item_name))

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

    def export_latex_progression(self, output_file: str = 'mcts_progression.tex', max_depth: int = 100):
        """Export multi-version visualization as optimized LaTeX"""
        self.process_icons()

        colors = ['blue!80!red', 'red!90!black', 'green!70!blue', 'orange!90!red', 'blue!80!red', 'red!90!black']

        latex_code = []

        # Start the main tikzpicture
        latex_code.append(r"\begin{tikzpicture}")

        # Sort versions by achievement count for legend
        version_achievements = []
        for version in self.version_data:
            label = self.version_data[version]['label'].replace('_', '\\_')
            achievements = self.achievements[version]
            color = colors[list(self.version_data.keys()).index(version) % len(colors)]
            version_achievements.append((version, label, achievements, color))

        version_achievements.sort(key=lambda x: len(x[2]), reverse=True)

        # Create legend node
        latex_code.append(
            r"\node[anchor=south,draw=black!50,thin,fill=white,inner sep=4pt] at (0.45\textwidth,0.9\textwidth) {")
        latex_code.append(r"    \begin{tabular}{@{}l@{\hspace{0.75cm}}l@{\hspace{0.75cm}}l@{}}")

        # Add legend entries
        for version, label, achievements, color in version_achievements:
            line_indicator = f"\\raisebox{{0.5ex}}{{\\tikz\\draw[{color}, thick] (0,0) -- (1em,0);}}"

            if not achievements:
                latex_code.append(f"    {line_indicator} & \\textbf{{{label}}} & $\\varnothing$ \\\\")
                continue

            icons = " ".join([
                f"\\includegraphics[width=1em]{{icons/{ach.item_name}.png}}"
                for ach in sorted(achievements, key=lambda x: x.ingredients)
            ])

            latex_code.append(f"    {line_indicator} & \\textit{{{label}}} & {icons} \\\\")

        latex_code.extend([
            r"    \end{tabular}",
            r"}",
        ])

        # Add the axis environment with adjusted positioning
        latex_code.extend([
            r"\begin{axis}[",
            r"    name=mainplot,",
            r"    set layers=standard,",
            r"    every axis plot/.style={on layer=main},",
            r"    width=\textwidth,",
            r"    height=0.55\textwidth,",
            r"    anchor=north west,",
            r"    at={(0,0.85\textwidth)},",  # Adjusted position to be closer to legend
            r"    xlabel=Environment Steps,",
            r"    ylabel=Total GDP,",
            r"    grid style={line width=.1pt, draw=gray!10},",
            r"    major grid style={line width=.2pt,draw=gray!50},",
            r"    grid=both,",
            r"    minor tick num=1,",
            r"    clip=false,",
            r"    xmode=log,",
            r"    log basis x=2,",
            r"    ymode=log,",
            r"    log basis y=2,",
            r"    enlarge x limits=false,",
            r"    xmin=1,",
            r"    xmax=128,",
            r"    xtick={1,2,4,8,16,32,64,128},",
            r"    xticklabels={$2^0$,$2^1$,$2^2$,$2^3$,$2^4$,$2^5$,$2^6$,$2^7$},",
            r"    ymin=128,",
            r"    ymax=65536,",
            r"    ytick={128,256,512,1024,2048,4096,8192,16384,32768,65536},",
            r"    yticklabels={$2^7$,$2^8$,$2^9$,$2^{10}$,$2^{11}$,$2^{12}$,$2^{13}$,$2^{14}$,$2^{15}$,$2^{16}$,$2^{17}$,$2^{18}$},",
            r"    clip=false",
            r"]"
        ])

        # Plot all series data with chunking for memory optimization
        for i, version in enumerate(self.version_data):
            depth_stats, achievements_by_depth = self.calculate_version_stats(version, max_depth)
            if not depth_stats:
                continue

            color = colors[i % len(colors)]

            # Split coordinates into chunks
            chunk_size = 50
            valid_stats = {d: s for d, s in depth_stats.items() if s['mean'] > 64}
            coords = [(d, max(s['mean'], 64)) for d, s in valid_stats.items()]

            for chunk_start in range(0, len(coords), chunk_size):
                chunk = coords[chunk_start:chunk_start + chunk_size]
                latex_code.append(f"\\addplot[{color}, thick] coordinates {{")
                latex_code.extend(f"({x},{y})" for x, y in chunk)
                latex_code.append("};")

        # Add achievement markers with optimizations
        latex_code.append(r"\pgfonlayer{axis foreground}")

        # Process achievements with batching
        for i, version in enumerate(self.version_data):
            depth_stats, achievements_by_depth = self.calculate_version_stats(version, max_depth)
            if not depth_stats:
                continue

            color = colors[i % len(colors)]

            for depth, achievements in achievements_by_depth.items():
                if depth == 0:
                    continue

                value = depth_stats[depth]['mean']
                if value <= 64:
                    continue

                base_position = max(value, 64)

                # Process achievements in smaller batches
                for j, achievement in enumerate(achievements):
                    icon_output = f"icons/{achievement.item_name}.png"
                    if not os.path.exists(icon_output):
                        continue

                    position = base_position + (j * base_position * 0.08 if len(achievements) > 1 else 0)

                    latex_code.extend([
                        f"\\node[circle, fill=white, draw={color}, line width=0.5pt, minimum size=1.1em] "
                        f"at (axis cs:{depth},{position}) {{}};",
                        f"\\node[above delimiter] at (axis cs:{depth},{position}) {{",
                        f"    \\includegraphics[width=0.8em]{{{icon_output}}}",
                        "};"
                    ])

        # Close environments
        latex_code.extend([
            r"\endpgfonlayer",
            r"\end{axis}",
            r"\end{tikzpicture}"
        ])

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_code))

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

        depth_stats = {}
        for depth in range(max_depth + 1):
            values = values_by_depth.get(depth, [0])
            depth_stats[depth] = {
                'mean': np.mean(values),
                'std': np.std(values)
            }

        return depth_stats, achievements_by_depth

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
    visualizer = RunVisualizer(db_client, icons_path)

    labels = {
        #391: 'claude-3-5-sonnet-20241022',
        392: 'gpt-4o',
        400: 'gpt-4o-mini',
        405: 'claude-3-5-sonnet-20241022',
        416: 'claude-new'
    }
    versions = list(labels.keys())
    visualizer.load_versions(versions, labels)
    visualizer.process_achievements(max_depth=128)
    visualizer.export_latex_progression('mcts_progression_content.tex', max_depth=128)


if __name__ == '__main__':
    asyncio.run(main())