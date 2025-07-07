import asyncio
import sys
from abc import ABC, abstractmethod
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Literal
import os

import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

from fle.commons.db_client import DBClient
from eval.open.plots.run_results import RunResults

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
    def __init__(
        self, db_client, icons_path: str, x_axis: Literal["steps", "ticks"] = "steps"
    ):
        self.db_client = db_client
        self.icons_path = icons_path
        self.version_data = {}
        self.achievements = defaultdict(list)
        self.x_axis = x_axis
        self.cumulative_ticks_cache = {}  # Add cache

    def load_versions(self, versions: List[int], labels: Dict[int, str]):
        """Load data for multiple versions, keeping all runs for each version"""
        for version in versions:
            print(f"\nLoading version {version}")
            run_results = RunResults(version=version, db_client=self.db_client)
            root_nodes, processed_ids = run_results._create_trees_from_db()
            print(
                f"Found {len(root_nodes)} root nodes with {len(processed_ids)} total nodes for version {version}"
            )
            print(f"Root node IDs: {[node.id for node in root_nodes]}")

            # Keep all runs and calculate mean GDP
            if root_nodes:
                gdps = [self._calculate_final_gdp(root) for root in root_nodes]
                mean_gdp = np.mean(gdps)
                print(f"GDP values for each run: {gdps}")
                self.version_data[version] = {
                    "nodes": root_nodes,
                    "label": f"{labels[version]} (Mean GDP: {mean_gdp:.1f})",
                }

    def _calculate_cumulative_ticks_with_cache(self, node, depth=0):
        """Calculate cumulative ticks with caching"""
        cache_key = (node.id, depth)
        if cache_key in self.cumulative_ticks_cache:
            return self.cumulative_ticks_cache[cache_key]

        if depth == 0:
            return 0

        total_ticks = 0
        stack = [(node, 0)]
        visited = set()

        while stack:
            current_node, current_depth = stack.pop()

            if current_node.id in visited or current_depth >= depth:
                continue

            visited.add(current_node.id)
            total_ticks += current_node.metrics.get("ticks", 0) or 0

            for child in reversed(current_node.children):
                if child.id not in visited:
                    stack.append((child, current_depth + 1))

        self.cumulative_ticks_cache[cache_key] = total_ticks
        return total_ticks

    def _calculate_cumulative_ticks_iterative(self, node, target_depth=0):
        """Calculate cumulative ticks up to a given depth using iteration"""
        if target_depth == 0:
            return 0

        total_ticks = 0
        current_depth = 0
        # Stack stores tuples of (node, depth)
        stack = [(node, 0)]
        visited = set()

        print(f"\nCalculating ticks for node {node.id} to depth {target_depth}")

        while stack:
            current_node, current_depth = stack.pop()

            if current_node.id in visited:
                continue

            visited.add(current_node.id)

            if current_depth >= target_depth:
                continue

            # Add ticks for current node
            node_ticks = current_node.metrics.get("ticks", 0) or 0
            total_ticks += node_ticks
            print(
                f"  Depth {current_depth}: Adding {node_ticks} ticks from node {current_node.id}"
            )

            # Add children to stack in reverse order to maintain original traversal order
            for child in reversed(current_node.children):
                if child.id not in visited:
                    stack.append((child, current_depth + 1))

        print(f"Total cumulative ticks: {total_ticks}")
        return total_ticks

    def _calculate_final_gdp(self, root_node):
        """Calculate the final GDP value for a run using iteration"""
        final_gdp = 0
        stack = [root_node]

        while stack:
            node = stack.pop()
            current_value = node.metrics.get("value", 0) or 0
            final_gdp += current_value

            # Add children to stack
            stack.extend(node.children)

        return final_gdp

    def _count(self, root_node):
        """Count nodes in the tree using iteration"""
        count = 0
        stack = [root_node]

        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children)

        return count

    def count_total_ingredients(self, recipe_dict):
        """Count total unique ingredients in recipe tree"""
        seen = set()

        def traverse_ingredients(item):
            seen.add(item["name"])
            for ingredient in item.get("ingredients", []):
                traverse_ingredients(ingredient)

        traverse_ingredients(recipe_dict)
        return len(seen) - 1

    sys.setrecursionlimit(5000)

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

            ticks = n.metrics.get("ticks", 0) or 0
            total_ticks += ticks

            for child in n.children:
                traverse(child, current_depth + 1)

        traverse(node, current_depth)
        return total_ticks

    def process_achievements(self, max_depth: int = 1000):
        """Process achievements for all versions using iteration instead of recursion"""
        recipes = {}
        with open("recipes.jsonl", "r") as f:
            for line in f:
                recipe = json.loads(line)
                recipes[recipe["name"]] = recipe

        for version, data in self.version_data.items():
            seen_items = set()
            # Stack stores tuples of (node, depth)
            stack = [(root, 0) for root in data["nodes"]]

            while stack:
                node, depth = stack.pop()

                if depth > max_depth:
                    continue

                # Calculate cumulative ticks for this depth
                cumulative_ticks = self._calculate_cumulative_ticks_iterative(
                    data["nodes"][0], depth
                )

                # Process achievements
                if hasattr(node, "static_achievements"):
                    # Process static achievements
                    for item_name, quantity in node.static_achievements.items():
                        if item_name not in seen_items:
                            self.achievements[version].append(
                                Achievement(
                                    depth=depth,
                                    ticks=cumulative_ticks,
                                    item_name=item_name,
                                    quantity=quantity,
                                    ingredients=self.count_total_ingredients(
                                        recipes[item_name]
                                    )
                                    if item_name in recipes
                                    else 0,
                                    is_dynamic=False,
                                )
                            )
                            seen_items.add(item_name)

                    # Process dynamic achievements
                    for item_name, quantity in node.dynamic_achievements.items():
                        if item_name not in seen_items:
                            self.achievements[version].append(
                                Achievement(
                                    depth=depth,
                                    ticks=cumulative_ticks,
                                    item_name=item_name,
                                    quantity=quantity,
                                    ingredients=self.count_total_ingredients(
                                        recipes[item_name]
                                    )
                                    if item_name in recipes
                                    else 0,
                                    is_dynamic=True,
                                )
                            )
                            seen_items.add(item_name)

                # Add children to stack in reverse order to maintain original traversal order
                for child in reversed(node.children):
                    stack.append((child, depth + 1))

            # Sort achievements by ingredients and item name
            self.achievements[version].sort(key=lambda x: (x.ingredients, x.item_name))

    def calculate_version_stats(self, version: int, max_depth: int):
        """Optimized version stats calculation"""
        # Pre-calculate all cumulative values in one pass
        cumulative_values = {}  # (node_id, depth) -> (cumulative_value, cumulative_ticks)

        for root in self.version_data[version]["nodes"]:
            stack = [(root, 0, 0, 0)]  # (node, depth, cum_value, cum_ticks)
            while stack:
                node, depth, parent_value, parent_ticks = stack.pop()
                if depth > max_depth:
                    continue

                current_value = node.metrics.get("value", 0) or 0
                current_ticks = node.metrics.get("ticks", 0) or 0
                total_value = parent_value + current_value
                total_ticks = parent_ticks + current_ticks

                cumulative_values[(node.id, depth)] = (total_value, total_ticks)

                for child in reversed(node.children):
                    stack.append((child, depth + 1, total_value, total_ticks))

        # Now use pre-calculated values for stats
        values_by_x = defaultdict(list)
        for (_, depth), (total_value, total_ticks) in cumulative_values.items():
            x_coord = total_ticks if self.x_axis == "ticks" else depth
            values_by_x[x_coord].append(total_value)

        stats = {}
        for x_coord, values in values_by_x.items():
            if values:
                stats[x_coord] = {"mean": np.mean(values), "std": np.std(values)}

        # Process achievements once using cached values
        achievements_by_x = defaultdict(list)
        for achievement in self.achievements[version]:
            x_coord = achievement.ticks if self.x_axis == "ticks" else achievement.depth
            achievements_by_x[x_coord].append(achievement)

        return stats, achievements_by_x

    def calculate_version_stats_old(self, version: int, max_depth: int):
        """Calculate statistics for a specific version with tick support"""
        values_by_x = defaultdict(list)
        ticks_by_depth = {}  # Store cumulative ticks for each depth

        def traverse_tree(node, depth=0, cumulative_value=0):
            if depth > max_depth:
                return

            current_value = node.metrics.get("value", 0) or 0
            total_value = cumulative_value + current_value

            # Calculate cumulative ticks if needed
            if self.x_axis == "ticks":
                x_coord = self._calculate_cumulative_ticks(
                    self.version_data[version]["nodes"][0], depth
                )
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

        for root in self.version_data[version]["nodes"]:
            traverse_tree(root)

        stats = {}
        x_values = (
            values_by_x.keys()
            if self.x_axis == "steps"
            else sorted(ticks_by_depth.values())
        )

        for x in x_values:
            values = values_by_x.get(x, [0])
            stats[x] = {"mean": np.mean(values), "std": np.std(values)}

        return stats, achievements_by_x

    @abstractmethod
    def export_visualization(self, output_file: str, max_depth: int = 100):
        """Abstract method to be implemented by concrete visualizer classes"""
        pass


class MatplotlibRunVisualizer(BaseRunVisualizer):
    def __init__(self, db_client, icons_path: str, x_axis_type: str = "steps"):
        super().__init__(db_client, icons_path, x_axis_type)
        self.colors = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b"]
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
        y, x = np.ogrid[-size / 2 : size / 2, -size / 2 : size / 2]
        mask = x * x + y * y <= (size / 2) * (size / 2)

        # Set white background with partial transparency
        img[..., :3][mask] = 1  # White fill
        img[..., 3][mask] = alpha  # Alpha opacity for fill

        # Add colored edge
        edge = np.zeros_like(mask)
        edge_width = 2
        for i in range(edge_width):
            edge_mask = (x * x + y * y <= (size / 2 - i) * (size / 2 - i)) & (
                x * x + y * y >= (size / 2 - i - 1) * (size / 2 - i - 1)
            )
            edge |= edge_mask

        # Convert color hex to RGB and apply with transparency
        rgb_color = np.array([int(color[1:][i : i + 2], 16) / 255 for i in (0, 2, 4)])
        img[..., :3][edge] = rgb_color
        img[..., 3][edge] = 0.7  # Edge opacity

        return img

    def organize_achievement_positions(
        self, achievements_by_depth, depth_stats, ax, series_index, used_positions
    ):
        positions = {}
        final_positions = {}
        x_threshold = 0.15

        def to_display(x, y):
            return ax.transData.transform(np.array([[x, y]]))[0]

        def to_data(x, y):
            return ax.transData.inverted().transform(np.array([[x, y]]))[0]

        for x_coord, achievements_list in achievements_by_depth.items():
            if x_coord not in depth_stats or depth_stats[x_coord]["mean"] <= 4:
                continue

            base_position = max(depth_stats[x_coord]["mean"], 4)

            grouped = False
            for existing_x, existing_base in positions.keys():
                if self.x_axis == "ticks":
                    relative_diff = abs(x_coord - existing_x) / max(1000, existing_x)
                else:
                    relative_diff = abs(x_coord - existing_x) / max(1, existing_x)

                if relative_diff < x_threshold:
                    positions[(existing_x, existing_base)].extend(
                        [
                            (x_coord, base_position, achievement)
                            for achievement in achievements_list
                        ]
                    )
                    grouped = True
                    break

            if not grouped:
                positions[(x_coord, base_position)] = [
                    (x_coord, base_position, achievement)
                    for achievement in achievements_list
                ]

        for group_key, achievement_list in positions.items():
            group_x, group_base_y = group_key
            achievement_list.sort(key=lambda x: (x[2].ingredients, x[2].item_name))

            base_display_x, base_display_y = to_display(group_x, group_base_y)

            x_key = round(group_x, -3 if self.x_axis == "ticks" else 1)
            if x_key in used_positions:
                base_display_x += self.HORIZONTAL_OFFSET_PIXELS * (series_index + 1)
            else:
                used_positions[x_key] = True

            for i, (orig_x, orig_base, achievement) in enumerate(achievement_list):
                display_y = base_display_y + (i * self.VERTICAL_SPACING_PIXELS)
                data_x, data_y = to_data(base_display_x, display_y)

                achievement_key = (achievement.item_name, orig_x)
                final_positions[achievement_key] = (data_x, data_y)

        return final_positions

    def export_visualization(
        self, output_file: str, max_depth: int = 100, xmin=0, xmax=10**6
    ):
        """Export visualization with support for both steps and ticks"""
        self.process_icons()

        plt.figure(figsize=(12, 8), dpi=100, tight_layout=True)
        ax = plt.gca()

        # Set font sizes
        plt.rcParams.update({"font.size": 16})
        ax.tick_params(axis="both", which="major", labelsize=16)
        ax.tick_params(axis="both", which="minor", labelsize=16)

        # Set up log scale axes
        ax.set_xscale("log", base=10)
        ax.set_yscale("log", base=10)

        # Configure axes labels with larger font
        ax.set_xlabel(
            "Cumulative Ticks" if self.x_axis == "ticks" else "Steps", fontsize=16
        )
        ax.set_ylabel("Total GDP", fontsize=16)

        # Set axis limits based on x_axis type
        if self.x_axis == "ticks":
            ax.set_xlim(2 * 10**3, 10**7)  # Adjust based on your tick ranges
            ax.set_ylim(10**1, 10**5)
        else:
            ax.set_xlim(10**0, 10**3)
            ax.set_ylim(10**1, 10**6)

        ax.grid(True, which="both", linestyle="--", alpha=0.3)

        # Sort versions by GDP
        version_achievements = []
        for version in self.version_data:
            label = self.version_data[version]["label"]
            achievements = self.achievements[version]
            color = self.colors[
                list(self.version_data.keys()).index(version) % len(self.colors)
            ]
            final_gdp = self._calculate_final_gdp(
                self.version_data[version]["nodes"][0]
            )
            version_achievements.append(
                (version, label, achievements, color, final_gdp)
            )

        version_achievements.sort(key=lambda x: x[4], reverse=True)

        used_positions = {}

        # Plot data for each version
        for i, (version, label, achievements, color, gdp) in enumerate(
            version_achievements
        ):
            stats, achievements_by_x = self.calculate_version_stats(version, max_depth)
            if not stats:
                continue

            # Plot the main line
            valid_stats = {x: s for x, s in stats.items() if s["mean"] > 4}
            x_coords = sorted(valid_stats.keys())  # Sort x coordinates
            means = [max(valid_stats[x]["mean"], 4) for x in x_coords]

            ax.plot(x_coords, means, color=color, label=f"{label}", linewidth=2)

            # Calculate achievement positions
            achievement_positions = self.organize_achievement_positions(
                achievements_by_x, stats, ax, i, used_positions
            )
            # Collect and sort achievements
            achievement_data = []
            for ticks, achievements_list in achievements_by_x.items():
                if ticks == 0 or stats[ticks]["mean"] <= 4:
                    continue

                for achievement in achievements_list:
                    achievement_key = (achievement.item_name, achievement.depth)
                    if achievement_key in achievement_positions:
                        x_pos, y_pos = achievement_positions[achievement_key]
                        achievement_data.append(
                            {
                                "achievement": achievement,
                                "x_pos": x_pos,
                                "y_pos": y_pos,
                                "color": color,
                            }
                        )

            achievement_data.sort(key=lambda x: x["y_pos"])

            # Draw achievements
            for data in achievement_data:
                circle_img = self.create_circle_background(data["color"])
                circle_box = OffsetImage(circle_img, zoom=0.3)
                circle_box.image.axes = ax

                ab_circle = AnnotationBbox(
                    circle_box,
                    (data["x_pos"], data["y_pos"]),
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                    pad=0,
                    xycoords="data",
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
                            (data["x_pos"], data["y_pos"]),
                            frameon=False,
                            box_alignment=(0.5, 0.5),
                            pad=0,
                            xycoords="data",
                        )
                        ax.add_artist(ab_icon)
                    except Exception as e:
                        print(
                            f"Failed to add icon for {data['achievement'].item_name}: {e}"
                        )
                else:
                    print(f"Icon not found: {icon_path}")

        # Add legend
        ax.legend(loc="lower right", fontsize=16)
        # ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)

        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()


class BootstrappedRunVisualizer(MatplotlibRunVisualizer):
    def __init__(
        self,
        db_client,
        icons_path: str,
        x_axis_type: str = "steps",
        n_bootstrap: int = 100,
        window_size: int = 5,
        plot_type: str = "line",
        fit_degree: int = 1,
    ):
        super().__init__(db_client, icons_path, x_axis_type)
        self.n_bootstrap = n_bootstrap
        self.max_depth = 1024
        self.window_size = window_size
        self.plot_type = plot_type
        self.fit_degree = fit_degree

    # Add new method to BootstrappedRunVisualizer class
    def calculate_fit_line(self, x_values, y_values):
        """Calculate polynomial fit line, ensuring it passes through the origin"""
        import numpy as np

        # Convert to log scale for fitting
        log_x = np.log10(x_values)
        log_y = np.log10(y_values)

        # Add origin point (with small offset to avoid log(0))
        min_x = min(x_values)
        min_y = min(y_values)
        origin_x = min_x * 0.01  # One order of magnitude lower than minimum x
        origin_y = min_y * 0.01  # One order of magnitude lower than minimum y
        # origin_x, origin_y = 0, 0
        # Add origin point to arrays
        log_x = np.append(log_x, np.log10(origin_x))
        log_y = np.append(log_y, np.log10(origin_y))

        # Calculate polynomial fit
        coeffs = np.polyfit(log_x, log_y, self.fit_degree)
        poly = np.poly1d(coeffs)

        # Generate points for the fit line, starting from origin
        x_fit = np.logspace(np.log10(origin_x), max(log_x), 100, base=10)
        log_y_fit = poly(np.log10(x_fit))
        y_fit = 10**log_y_fit

        return x_fit, y_fit

    # def calculate_version_stats(self, version: int, max_depth: int):
    #     """Calculate statistics with improved tick binning"""
    #     values_by_x_by_run = defaultdict(lambda: defaultdict(float))
    #
    #     def get_bin_size(tick_value):
    #         if tick_value < 500:
    #             return 20
    #         elif tick_value < 5000:
    #             return 100
    #         elif tick_value < 10000:
    #             return 500
    #         elif tick_value < 50000:
    #             return 1000
    #         elif tick_value < 100000:
    #             return 2000
    #         else:
    #             return 5000
    #
    #     def traverse_tree(node, run_index, depth=0, path_value=0, path_ticks=0):
    #         if depth > max_depth:
    #             return
    #
    #         current_value = node.metrics.get('value', 0) or 0
    #         current_ticks = node.metrics.get('ticks', 0) or 0
    #         total_value = path_value + current_value
    #         total_ticks = path_ticks + current_ticks
    #
    #         x_coord = total_ticks if self.x_axis == "ticks" else depth
    #         if self.x_axis == "ticks":
    #             bin_size = get_bin_size(total_ticks)
    #             x_coord = round(x_coord / bin_size) * bin_size
    #
    #         values_by_x_by_run[x_coord][run_index] = max(
    #             values_by_x_by_run[x_coord][run_index],
    #             total_value
    #         )
    #
    #         for child in node.children:
    #             traverse_tree(child, run_index, depth + 1, total_value, total_ticks)
    #
    #     for run_idx, root in enumerate(self.version_data[version]['nodes']):
    #         traverse_tree(root, run_idx)
    #
    #     stats = {}
    #     for x_coord, run_values in values_by_x_by_run.items():
    #         values = list(run_values.values())
    #         if values:
    #             stats[x_coord] = self.bootstrap_statistics(values, self.n_bootstrap)
    #
    #     achievements_by_x = defaultdict(list)
    #     for achievement in self.achievements[version]:
    #         x_coord = achievement.ticks if self.x_axis == "ticks" else achievement.depth
    #         if self.x_axis == "ticks":
    #             bin_size = get_bin_size(x_coord)
    #             x_coord = round(x_coord / bin_size) * bin_size
    #         achievements_by_x[x_coord].append(achievement)
    #
    #
    #     return stats, achievements_by_x  # Empty achievements for now to debug stats

    # Modify the calculate_version_stats method to include raw points
    def calculate_version_stats(self, version: int, max_depth: int):
        if self.plot_type == "scatter" and self.x_axis == "ticks":
            values_by_run = defaultdict(list)

            def traverse_tree(node, run_index, path_value=0, path_ticks=0):
                if path_ticks > max_depth * 1000:  # Arbitrary limit
                    return

                current_value = node.metrics.get("value", 0) or 0
                current_ticks = node.metrics.get("ticks", 0) or 0
                total_value = path_value + current_value
                total_ticks = path_ticks + current_ticks

                if total_ticks > 0 and total_value > 0:
                    values_by_run[run_index].append((total_ticks, total_value))

                for child in node.children:
                    traverse_tree(child, run_index, total_value, total_ticks)

            for run_idx, root in enumerate(self.version_data[version]["nodes"]):
                traverse_tree(root, run_idx)

            # Collect all points
            all_points = []
            for run_points in values_by_run.values():
                all_points.extend(run_points)

            # Sort by x coordinate
            all_points.sort(key=lambda x: x[0])

            # Create a stats dictionary with a structure matching what organize_achievement_positions expects
            x_coords = sorted(set(p[0] for p in all_points))
            stats = {x: {"mean": 0} for x in x_coords}  # Initialize with empty means
            for x in x_coords:
                y_values = [p[1] for p in all_points if p[0] == x]
                if y_values:
                    stats[x]["mean"] = np.mean(y_values)

            return {"scatter_points": all_points, "line_stats": stats}, defaultdict(
                list
            )
        else:
            values_by_x_by_run = defaultdict(lambda: defaultdict(float))

            def get_bin_size(tick_value):
                if tick_value < 500:
                    return 20
                elif tick_value < 5000:
                    return 100
                elif tick_value < 10000:
                    return 500
                elif tick_value < 50000:
                    return 1000
                elif tick_value < 100000:
                    return 2000
                else:
                    return 5000

            def traverse_tree(node, run_index, depth=0, path_value=0, path_ticks=0):
                if depth > max_depth:
                    return

                current_value = node.metrics.get("value", 0) or 0
                current_ticks = node.metrics.get("ticks", 0) or 0
                total_value = path_value + current_value
                total_ticks = path_ticks + current_ticks

                x_coord = total_ticks if self.x_axis == "ticks" else depth
                if self.x_axis == "ticks":
                    bin_size = get_bin_size(total_ticks)
                    x_coord = round(x_coord / bin_size) * bin_size

                values_by_x_by_run[x_coord][run_index] = max(
                    values_by_x_by_run[x_coord][run_index], total_value
                )

                for child in node.children:
                    traverse_tree(child, run_index, depth + 1, total_value, total_ticks)

            for run_idx, root in enumerate(self.version_data[version]["nodes"]):
                traverse_tree(root, run_idx)

            stats = {}
            for x_coord, run_values in values_by_x_by_run.items():
                values = list(run_values.values())
                if values:
                    stats[x_coord] = self.bootstrap_statistics(values, self.n_bootstrap)

            achievements_by_x = defaultdict(list)
            for achievement in self.achievements[version]:
                x_coord = (
                    achievement.ticks if self.x_axis == "ticks" else achievement.depth
                )
                if self.x_axis == "ticks":
                    bin_size = get_bin_size(x_coord)
                    x_coord = round(x_coord / bin_size) * bin_size
                achievements_by_x[x_coord].append(achievement)

            return stats, achievements_by_x

    def bootstrap_statistics(self, values, n_bootstrap=1000):
        """Compute bootstrapped statistics for a set of values, enforcing monotonicity"""
        if not values:
            return None

        values = np.array(values)
        if len(values) == 0:
            return {"mean": 0, "ci_lower": 0, "ci_upper": 0, "std": 0}

        bootstrap_means = []
        mean_value = np.mean(values)
        min_value = np.min(values)  # Get minimum value across all runs

        for _ in range(n_bootstrap):
            sample_idx = np.random.randint(0, len(values), size=len(values))
            bootstrap_sample = values[sample_idx]
            bootstrap_means.append(np.mean(bootstrap_sample))

        bootstrap_means = np.array(bootstrap_means)

        return {
            "mean": mean_value,
            "ci_lower": max(
                np.percentile(bootstrap_means, 2.5), min_value
            ),  # Never go below minimum
            "ci_upper": np.percentile(bootstrap_means, 97.5),
            "std": np.std(values),
        }

    def bootstrap_statistics_old(self, values, n_bootstrap=1000):
        """Compute bootstrapped statistics for a set of values"""
        if not values:
            return None

        values = np.array(values)
        if len(values) == 0:
            return {"mean": 0, "ci_lower": 0, "ci_upper": 0, "std": 0}

        bootstrap_means = []
        mean_value = np.mean(values)

        for _ in range(n_bootstrap):
            sample_idx = np.random.randint(0, len(values), size=len(values))
            bootstrap_sample = values[sample_idx]
            bootstrap_means.append(np.mean(bootstrap_sample))

        bootstrap_means = np.array(bootstrap_means)

        return {
            "mean": mean_value,
            "ci_lower": max(np.percentile(bootstrap_means, 2.5), 0.1),
            "ci_upper": np.percentile(bootstrap_means, 97.5),
            "std": np.std(values),
        }

    def smooth_data(self, x_values, y_values, window_size):
        """Apply sliding window smoothing to the data while preserving monotonicity"""
        if len(x_values) < window_size:
            return x_values, y_values

        smoothed_y = []
        valid_indices = []
        current_max = 0  # Track maximum value seen so far

        for i in range(len(y_values)):
            # Get window indices
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(y_values), i + window_size // 2 + 1)

            window_x = x_values[start_idx:end_idx]
            window_y = y_values[start_idx:end_idx]

            if self.x_axis == "ticks":
                center_x = x_values[i]
                valid_window_indices = [
                    j for j, x in enumerate(window_x) if 0.1 <= x / center_x <= 10
                ]
                if valid_window_indices:
                    window_y = [window_y[j] for j in valid_window_indices]
                    smoothed_value = max(
                        np.mean(window_y), current_max
                    )  # Ensure monotonicity
                    current_max = smoothed_value
                    smoothed_y.append(smoothed_value)
                    valid_indices.append(i)
            else:
                smoothed_value = max(
                    np.mean(window_y), current_max
                )  # Ensure monotonicity
                current_max = smoothed_value
                smoothed_y.append(smoothed_value)
                valid_indices.append(i)

        return [x_values[i] for i in valid_indices], smoothed_y

    def smooth_data_old(self, x_values, y_values, window_size):
        """Apply sliding window smoothing to the data"""
        if len(x_values) < window_size:
            return x_values, y_values

        smoothed_y = []
        valid_indices = []

        for i in range(len(y_values)):
            # Get window indices
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(y_values), i + window_size // 2 + 1)

            # Only include points where x values are within reasonable range
            window_x = x_values[start_idx:end_idx]
            window_y = y_values[start_idx:end_idx]

            # For log-scale x-axis, check if points are within reasonable ratio
            if self.x_axis == "ticks":
                center_x = x_values[i]
                valid_window_indices = [
                    j
                    for j, x in enumerate(window_x)
                    if 0.1 <= x / center_x <= 10  # Adjust ratio as needed
                ]
                if valid_window_indices:
                    window_y = [window_y[j] for j in valid_window_indices]
                    smoothed_y.append(np.mean(window_y))
                    valid_indices.append(i)
            else:
                smoothed_y.append(np.mean(window_y))
                valid_indices.append(i)

        return [x_values[i] for i in valid_indices], smoothed_y

    def export_visualization(
        self, output_file: str, max_depth: int = 100, xmin=0, xmax=10**6
    ):
        """Export visualization with bootstrapped confidence intervals, smoothing, and achievement icons"""
        self.process_icons()

        plt.figure(figsize=(12, 8), dpi=100, tight_layout=True)
        ax = plt.gca()

        # Set font sizes and axes configuration
        plt.rcParams.update({"font.size": 16})
        ax.tick_params(axis="both", which="major", labelsize=16)
        ax.tick_params(axis="both", which="minor", labelsize=16)
        ax.set_xscale("log", base=10)
        ax.set_yscale("log", base=10)
        ax.set_xlabel(
            "Cumulative Ticks" if self.x_axis == "ticks" else "Steps", fontsize=16
        )
        ax.set_ylabel("Total GDP", fontsize=16)

        if self.x_axis == "ticks":
            ax.set_xlim(2 * 10**2, 10**7)
            ax.set_ylim(10**1, 10**5)
        else:
            ax.set_xlim(10**0, 10**3)
            ax.set_ylim(10**1, 10**5)

        ax.grid(True, which="both", linestyle="--", alpha=0.3)

        # Sort versions and prepare for plotting
        version_achievements = []
        for version in self.version_data:
            label = self.version_data[version]["label"]
            achievements = self.achievements[version]
            color = self.colors[
                list(self.version_data.keys()).index(version) % len(self.colors)
            ]
            final_gdp = self._calculate_final_gdp(
                self.version_data[version]["nodes"][0]
            )
            version_achievements.append(
                (version, label, achievements, color, final_gdp)
            )

        version_achievements.sort(key=lambda x: x[4], reverse=True)
        used_positions = {}

        # Plot data for each version
        for i, (version, label, achievements, color, gdp) in enumerate(
            version_achievements
        ):
            stats, achievements_by_x = self.calculate_version_stats(version, max_depth)
            if not stats:
                continue

            if (
                self.plot_type == "scatter"
                and self.x_axis == "ticks"
                and "scatter_points" in stats
            ):
                points = stats["scatter_points"]
                line_stats = stats["line_stats"]  # For achievement positioning
                if points:
                    x_values = [p[0] for p in points]
                    y_values = [p[1] for p in points]

                    # Plot scatter points
                    ax.scatter(
                        x_values, y_values, color=color, alpha=0.05, s=2
                    )  # , label=f"{label} (fit)")

                    # Calculate and plot fit line
                    if len(points) > 2:
                        x_fit, y_fit = self.calculate_fit_line(x_values, y_values)
                        ax.plot(
                            x_fit,
                            y_fit,
                            color=color,
                            linestyle="--",
                            label=f"{label} (fit)",
                            linewidth=2,
                        )

                # Use line_stats for achievement positioning
                stats = line_stats
            else:
                x_coords = sorted(stats.keys())
                means = [stats[x]["mean"] for x in x_coords]
                ci_lower = [stats[x]["ci_lower"] for x in x_coords]
                ci_upper = [stats[x]["ci_upper"] for x in x_coords]

                if x_coords:
                    # Plot original data with low alpha
                    ax.plot(x_coords, means, color=color, alpha=0.3, linewidth=1)
                    ax.fill_between(
                        x_coords, ci_lower, ci_upper, color=color, alpha=0.1
                    )

                    # Apply smoothing and plot smoothed data
                    smoothed_x, smoothed_means = self.smooth_data(
                        x_coords, means, self.window_size
                    )
                    _, smoothed_lower = self.smooth_data(
                        x_coords, ci_lower, self.window_size
                    )
                    _, smoothed_upper = self.smooth_data(
                        x_coords, ci_upper, self.window_size
                    )

                    # Plot smoothed lines with full alpha
                    ax.plot(
                        smoothed_x,
                        smoothed_means,
                        color=color,
                        label=f"{label}",
                        linewidth=2,
                    )
                    ax.fill_between(
                        smoothed_x,
                        smoothed_lower,
                        smoothed_upper,
                        color=color,
                        alpha=0.2,
                    )

            # Calculate and plot achievement positions
            achievement_positions = self.organize_achievement_positions(
                achievements_by_x,
                stats,  # Now using the appropriate stats structure
                ax,
                i,
                used_positions,
            )

            # Draw achievements
            achievement_data = []
            for x_coord, achievements_list in achievements_by_x.items():
                if x_coord == 0:
                    continue

                for achievement in achievements_list:
                    achievement_key = (achievement.item_name, achievement.depth)
                    if achievement_key in achievement_positions:
                        x_pos, y_pos = achievement_positions[achievement_key]
                        achievement_data.append(
                            {
                                "achievement": achievement,
                                "x_pos": x_pos,
                                "y_pos": y_pos,
                                "color": color,
                            }
                        )

            achievement_data.sort(key=lambda x: x["y_pos"])

            for data in achievement_data:
                circle_img = self.create_circle_background(data["color"])
                circle_box = OffsetImage(circle_img, zoom=0.24)
                circle_box.image.axes = ax

                ab_circle = AnnotationBbox(
                    circle_box,
                    (data["x_pos"], data["y_pos"]),
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                    pad=0,
                    xycoords="data",
                )
                ax.add_artist(ab_circle)

                icon_path = f"icons/{data['achievement'].item_name}.png"
                if os.path.exists(icon_path):
                    try:
                        icon = plt.imread(icon_path)
                        icon_box = OffsetImage(icon, zoom=0.12)
                        icon_box.image.axes = ax

                        ab_icon = AnnotationBbox(
                            icon_box,
                            (data["x_pos"], data["y_pos"]),
                            frameon=False,
                            box_alignment=(0.5, 0.5),
                            pad=0,
                            xycoords="data",
                        )
                        ax.add_artist(ab_icon)
                    except Exception as e:
                        print(
                            f"Failed to add icon for {data['achievement'].item_name}: {e}"
                        )
                else:
                    print(f"Icon not found: {icon_path}")

        ax.legend(loc="lower right", fontsize=16)
        plt.tight_layout()
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()


# Example usage:
async def main():
    for type in ["ticks", "steps"]:
        db_client = DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD"),
        )

        icons_path = "/data/icons/early_icons"

        # Create visualizer with specified x-axis type
        visualizer = BootstrappedRunVisualizer(
            db_client,
            icons_path,
            x_axis_type=type,
            n_bootstrap=100,
            window_size=5 if type == "steps" else 20,
            plot_type="scatter" if type == "ticks" else "line",
        )

        labels = {
            # 416: 'claude-new',
            # 434: 'claude-2@4',
            # 452: 'gpt-4o-mini@4',
            # #451: 'gpt-4o-mini@4-2',
            # 453: 'gpt-4o@4',
            # 436: 'claude-2@4-2'
            # 457: 'gpt-4o-mini@4',
            # 456: 'claude@4',
            # 455: 'gpt4o@4',
            # 460: 'gpt-4o-mini@4',
            # 459: 'claude@4',
            # 458: 'gpt4o@4',
            488: "llama-70b3@4",
            487: "gpt-4o-mini@4",
            490: "gpt4o@4",
            491: "deepseek-3@4",
            492: "claude@4",
        }

        versions = list(labels.keys())
        visualizer.load_versions(versions, labels)
        visualizer.process_achievements(max_depth=1024)
        visualizer.export_visualization(f"mcts_progression_{type}.png", max_depth=1024)


if __name__ == "__main__":
    asyncio.run(main())
