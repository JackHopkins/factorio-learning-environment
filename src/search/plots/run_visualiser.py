import asyncio
from abc import ABC, abstractmethod
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
import os

import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.patches import Circle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

from search.db_client import DBClient
from search.plots.run_results import RunResults

load_dotenv()


@dataclass
class Achievement:
    depth: int
    item_name: str
    quantity: int
    is_dynamic: bool
    ingredients: int
    ticks: int


class BaseRunVisualizer(ABC):
    def __init__(self, db_client, icons_path: str, x_axis: Literal["steps", "ticks"] = "steps"):
        self.db_client = db_client
        self.icons_path = icons_path
        self.version_data = {}
        self.achievements = defaultdict(list)
        self.x_axis = x_axis

    def load_versions(self, versions: List[int], labels: Dict[int, str]):
        """Load data for multiple versions, keeping only the best run for each version"""
        for version in versions:
            run_results = RunResults(version=version, db_client=self.db_client)
            root_nodes, _ = run_results._create_trees_from_db()

            # Find the best run based on maximum GDP
            best_root = None
            max_gdp = float('-inf')

            for root in root_nodes:
                final_gdp = self._calculate_final_gdp(root)
                count = self._count(root)
                if final_gdp > max_gdp:
                    max_gdp = final_gdp
                    best_root = root

            if best_root:
                self.version_data[version] = {
                    'nodes': [best_root],
                    'label': f"{labels[version]} (GDP: {max_gdp:.1f})"
                }

    def _calculate_final_gdp(self, root_node):
        """Calculate the final GDP value for a run"""
        final_gdp = 0

        def traverse(node):
            nonlocal final_gdp
            current_value = node.metrics.get('value', 0) or 0
            final_gdp = final_gdp + current_value #max(final_gdp, current_value)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return final_gdp

    def _count(self, root_node):
        """Calculate the final GDP value for a run"""
        count = 0

        def traverse(node):
            nonlocal count

            count =count + 1

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return count


    def count_total_ingredients(self, recipe_dict):
        """Count total unique ingredients in recipe tree"""
        seen = set()

        def traverse_ingredients(item):
            seen.add(item['name'])
            for ingredient in item.get('ingredients', []):
                traverse_ingredients(ingredient)

        traverse_ingredients(recipe_dict)
        return len(seen) - 1

    def _calculate_cumulative_ticks(self, node, depth=0):
        """Calculate cumulative ticks up to a given depth"""
        if depth == 0:
            return 0

        total_ticks = 0
        current_depth = 0

        def traverse(n, current_depth):
            nonlocal total_ticks
            if current_depth >= depth:
                return

            ticks = n.metrics.get('ticks', 0) or 0
            total_ticks += ticks

            for child in n.children:
                traverse(child, current_depth + 1)

        traverse(node, current_depth)
        return total_ticks

    def process_achievements(self, max_depth: int = 1000):
        """Process achievements for all versions with tick support"""
        recipes = {}
        with open('recipes.jsonl', 'r') as f:
            for line in f:
                recipe = json.loads(line)
                recipes[recipe['name']] = recipe

        for version, data in self.version_data.items():
            seen_items = set()

            def traverse_tree(node, depth=0):
                if depth > max_depth:
                    return

                # Calculate cumulative ticks for this depth
                cumulative_ticks = self._calculate_cumulative_ticks(data['nodes'][0], depth)

                if hasattr(node, 'static_achievements'):
                    for category in ['static', 'dynamic']:
                        items = (node.static_achievements if category == 'static'
                                 else node.dynamic_achievements)
                        for item_name, quantity in items.items():
                            if item_name not in seen_items:
                                self.achievements[version].append(Achievement(
                                    depth=depth,
                                    ticks=cumulative_ticks,
                                    item_name=item_name,
                                    quantity=quantity,
                                    ingredients=self.count_total_ingredients(recipes[item_name])
                                    if item_name in recipes else 0,
                                    is_dynamic=(category == 'dynamic')
                                ))
                                seen_items.add(item_name)

                for child in node.children:
                    traverse_tree(child, depth + 1)

            for root in data['nodes']:
                traverse_tree(root)

            self.achievements[version].sort(key=lambda x: (x.ingredients, x.item_name))

    def calculate_version_stats(self, version: int, max_depth: int):
        """Calculate statistics for a specific version with tick support"""
        values_by_x = defaultdict(list)
        ticks_by_depth = {}  # Store cumulative ticks for each depth

        def traverse_tree(node, depth=0, cumulative_value=0):
            if depth > max_depth:
                return

            current_value = node.metrics.get('value', 0) or 0
            total_value = cumulative_value + current_value

            # Calculate cumulative ticks if needed
            if self.x_axis == "ticks":
                x_coord = self._calculate_cumulative_ticks(self.version_data[version]['nodes'][0], depth)
                ticks_by_depth[depth] = x_coord
            else:
                x_coord = depth

            values_by_x[x_coord].append(total_value)

            for child in node.children:
                traverse_tree(child, depth + 1, total_value)

        achievements_by_x = defaultdict(list)
        for achievement in self.achievements[version]:
            x_coord = achievement.ticks if self.x_axis == "ticks" else achievement.depth
            achievements_by_x[x_coord].append(achievement)

        for root in self.version_data[version]['nodes']:
            traverse_tree(root)

        stats = {}
        x_values = values_by_x.keys() if self.x_axis == "steps" else sorted(ticks_by_depth.values())

        for x in x_values:
            values = values_by_x.get(x, [0])
            stats[x] = {
                'mean': np.mean(values),
                'std': np.std(values)
            }

        return stats, achievements_by_x


    @abstractmethod
    def export_visualization(self, output_file: str, max_depth: int = 100):
        """Abstract method to be implemented by concrete visualizer classes"""
        pass


class MatplotlibRunVisualizer(BaseRunVisualizer):
    def __init__(self, db_client, icons_path: str, x_axis_type: str = 'steps'):
        super().__init__(db_client, icons_path, x_axis_type)
        self.colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
        self.ICON_SIZE_PIXELS = 20
        self.VERTICAL_SPACING_PIXELS = 8
        self.HORIZONTAL_OFFSET_PIXELS = 0

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

    def create_circle_background(self, color, alpha=0.7):
        """Create a circular background image with transparency"""
        size = 50
        img = np.zeros((size, size, 4))  # RGBA

        # Create a circle mask
        y, x = np.ogrid[-size / 2:size / 2, -size / 2:size / 2]
        mask = x * x + y * y <= (size / 2) * (size / 2)

        # Set white background with partial transparency
        img[..., :3][mask] = 1  # White fill
        img[..., 3][mask] = alpha  # Alpha opacity for fill

        # Add colored edge
        edge = np.zeros_like(mask)
        edge_width = 2
        for i in range(edge_width):
            edge_mask = (x * x + y * y <= (size / 2 - i) * (size / 2 - i)) & (
                    x * x + y * y >= (size / 2 - i - 1) * (size / 2 - i - 1))
            edge |= edge_mask

        # Convert color hex to RGB and apply with transparency
        rgb_color = np.array([int(color[1:][i:i + 2], 16) / 255 for i in (0, 2, 4)])
        img[..., :3][edge] = rgb_color
        img[..., 3][edge] = 0.7  # Edge opacity

        return img

    def organize_achievement_positions(self, achievements_by_depth, depth_stats, ax, series_index, used_positions):
        """Organize achievement positions with constant pixel spacing and series offset"""
        positions = {}  # (depth, base_position) -> list of achievements
        x_threshold = 0.15
        final_positions = {}

        # Helper function to convert between data and display coordinates
        def to_display(x, y):
            return ax.transData.transform(np.array([[x, y]]))[0]

        def to_data(x, y):
            return ax.transData.inverted().transform(np.array([[x, y]]))[0]

        # First pass: group achievements that are close on x-axis
        for depth, achievements_list in achievements_by_depth.items():
            if depth == 0 or depth_stats[depth]['mean'] <= 4:
                continue

            base_position = max(depth_stats[depth]['mean'], 4)

            # Find nearby groups
            grouped = False
            for (existing_depth, existing_base) in positions.keys():
                if abs(depth - existing_depth) / existing_depth < x_threshold:
                    positions[(existing_depth, existing_base)].extend(
                        [(depth, base_position, achievement) for achievement in achievements_list]
                    )
                    grouped = True
                    break

            if not grouped:
                positions[(depth, base_position)] = [
                    (depth, base_position, achievement) for achievement in achievements_list
                ]

        # Second pass: calculate positions with constant pixel spacing and series offset
        for group_key, achievement_list in positions.items():
            group_depth, group_base_y = group_key
            achievement_list.sort(key=lambda x: (x[2].ingredients, x[2].item_name))

            # Get base position in display coordinates
            base_display_x, base_display_y = to_display(group_depth, group_base_y)

            # Check if we need to offset this group horizontally
            depth_key = round(group_depth, 1)  # Round to avoid floating point comparison issues
            if depth_key in used_positions:
                # Add horizontal offset based on series index
                base_display_x += self.HORIZONTAL_OFFSET_PIXELS * (series_index + 1)
            else:
                used_positions[depth_key] = True

            for i, (orig_depth, orig_base, achievement) in enumerate(achievement_list):
                # Calculate new position in display coordinates
                display_y = base_display_y + (i * self.VERTICAL_SPACING_PIXELS)

                # Convert back to data coordinates
                data_x, data_y = to_data(base_display_x, display_y)

                achievement_key = (achievement.item_name, orig_depth)
                final_positions[achievement_key] = (data_x, data_y)

        return final_positions

    def export_visualization(self, output_file: str, max_depth: int = 100, xmin=0, xmax=10**6):
        """Export visualization with support for both steps and ticks"""
        self.process_icons()

        plt.figure(figsize=(12, 8), dpi=100)
        ax = plt.gca()

        # Set up log scale axes
        ax.set_xscale('log', base=10)
        ax.set_yscale('log', base=10)

        # Configure axes labels
        ax.set_xlabel('Cumulative Ticks' if self.x_axis == "ticks" else 'Steps')
        ax.set_ylabel('Total GDP')

        # Set axis limits based on x_axis type
        if self.x_axis == "ticks":
            ax.set_xlim(2 * 10 ** 3, 10 ** 6)  # Adjust based on your tick ranges
            ax.set_ylim(10 ** 0, 10 ** 5)
        else:
            ax.set_xlim(10 ** 0, 10 ** 3)
            ax.set_ylim(10 ** 1, 10 ** 5)

        ax.grid(True, which='both', linestyle='--', alpha=0.3)

        # Sort versions by GDP
        version_achievements = []
        for version in self.version_data:
            label = self.version_data[version]['label']
            achievements = self.achievements[version]
            color = self.colors[list(self.version_data.keys()).index(version) % len(self.colors)]
            final_gdp = self._calculate_final_gdp(self.version_data[version]['nodes'][0])
            version_achievements.append((version, label, achievements, color, final_gdp))

        version_achievements.sort(key=lambda x: x[4], reverse=True)

        used_positions = {}

        # Plot data for each version
        for i, (version, label, achievements, color, gdp) in enumerate(version_achievements):
            stats, achievements_by_x = self.calculate_version_stats(version, max_depth)
            if not stats:
                continue

            # Plot the main line
            valid_stats = {x: s for x, s in stats.items() if s['mean'] > 4}
            x_coords = sorted(valid_stats.keys())  # Sort x coordinates
            means = [max(valid_stats[x]['mean'], 4) for x in x_coords]

            ax.plot(x_coords, means, color=color, label=f"{label}", linewidth=2)

            # Calculate achievement positions
            achievement_positions = self.organize_achievement_positions(
                achievements_by_x,
                stats,
                ax,
                i,
                used_positions
            )

            # Collect and sort achievements
            achievement_data = []
            for ticks, achievements_list in achievements_by_x.items():
                if ticks == 0 or stats[ticks]['mean'] <= 4:
                    continue

                for achievement in achievements_list:
                    achievement_key = (achievement.item_name, achievement.depth)
                    if achievement_key in achievement_positions:
                        x_pos, y_pos = achievement_positions[achievement_key]
                        achievement_data.append({
                            'achievement': achievement,
                            'x_pos': x_pos,
                            'y_pos': y_pos,
                            'color': color
                        })

            achievement_data.sort(key=lambda x: x['y_pos'])

            # Draw achievements
            for data in achievement_data:
                circle_img = self.create_circle_background(data['color'])
                circle_box = OffsetImage(circle_img, zoom=0.3)
                circle_box.image.axes = ax

                ab_circle = AnnotationBbox(
                    circle_box,
                    (data['x_pos'], data['y_pos']),
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                    pad=0,
                    xycoords='data'
                )
                ax.add_artist(ab_circle)

                icon_path = f"icons/{data['achievement'].item_name}.png"
                if os.path.exists(icon_path):
                    try:
                        icon = plt.imread(icon_path)
                        icon_box = OffsetImage(icon, zoom=0.16)
                        icon_box.image.axes = ax

                        ab_icon = AnnotationBbox(
                            icon_box,
                            (data['x_pos'], data['y_pos']),
                            frameon=False,
                            box_alignment=(0.5, 0.5),
                            pad=0,
                            xycoords='data'
                        )
                        ax.add_artist(ab_icon)
                    except Exception as e:
                        print(f"Failed to add icon for {data['achievement'].item_name}: {e}")
                else:
                    print(f"Icon not found: {icon_path}")

        # Add legend
        ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)

        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close()


# Example usage:
async def main():
    db_client = DBClient(
        max_conversation_length=40,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )

    icons_path = "/data/icons/early_icons"

    # Create visualizer with specified x-axis type
    visualizer = MatplotlibRunVisualizer(
        db_client,
        icons_path,
        x_axis_type='steps'  # or 'steps'
    )

    labels = {
        # 416: 'claude-new',
        434: 'claude-2@4',
        448: 'gpt-4o-mini@4',
        449: 'gpt-4o@4',
        436: 'claude-2@4-2'
    }

    versions = list(labels.keys())
    visualizer.load_versions(versions, labels)
    visualizer.process_achievements(max_depth=1024)
    visualizer.export_visualization('mcts_progression.png', max_depth=1024)

if __name__ == '__main__':
    asyncio.run(main())