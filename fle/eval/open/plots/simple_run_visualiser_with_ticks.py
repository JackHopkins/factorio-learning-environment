import asyncio
import json
import pickle
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from matplotlib.ticker import LogLocator

from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os

from fle.commons.db_client import PostgresDBClient
from eval.open.independent_runs.value_calculator import ValueCalculator

load_dotenv()


@dataclass
class Node:
    """Represents a node in the MCTS tree"""

    id: int
    parent_id: Optional[int]
    metrics: Dict  # Contains 'value', 'ticks'
    static_achievements: Dict[str, int]
    dynamic_achievements: Dict[str, int]
    children: List["Node"]

    def to_dict(self):
        """Convert Node to dictionary for caching"""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "metrics": self.metrics,
            "static_achievements": self.static_achievements,
            "dynamic_achievements": self.dynamic_achievements,
            "children_ids": [child.id for child in self.children],
        }

    @staticmethod
    def from_dict(data: Dict, nodes_dict: Dict[int, "Node"]):
        """Create Node from dictionary and populate children from nodes_dict"""
        node = Node(
            id=data["id"],
            parent_id=data["parent_id"],
            metrics=data["metrics"],
            static_achievements=data["static_achievements"],
            dynamic_achievements=data["dynamic_achievements"],
            children=[],
        )
        node.children = [nodes_dict[child_id] for child_id in data["children_ids"]]
        return node


@dataclass
class Achievement:
    """Represents an achievement milestone"""

    depth: int
    ticks: int
    item_name: str
    ingredients: int
    is_dynamic: bool


# In _plot_production_volumes method, modify the legend creation:

# First, import necessary components at the top of the file


class ProgressionVisualizerWithTicks:
    """Creates publication-quality visualizations of agent progression"""

    VERTICAL_SPACING_PIXELS = 12
    HORIZONTAL_OFFSET_PIXELS = 0
    BASE_STACK_TOLERANCE = 4  # Base tolerance that will be scaled with x-position
    STACK_VERTICAL_SPACING = 12  # Pixels between stacked achievements
    MAX_STACK_SIZE = 5  # Maximum number of achievements to stack vertically

    def __init__(
        self,
        db_client,
        icons_path: str,
        x_axis: Literal["steps", "ticks"] = "steps",
        cache_file: str = "viz_cache.pkl",
        x_base: float = 10,
        y_base: float = 10,
        use_value_gdp=False,
        recipes_file="recipes.jsonl",
        use_log_scale: bool = True,
    ):  # Added use_log_scale parameter
        self.db_client = db_client
        self.icons_path = icons_path
        self.x_axis = x_axis
        self.cache_file = cache_file
        self.x_base = x_base
        self.y_base = y_base
        self.versions = {}
        self.achievements = defaultdict(list)
        # self.colors = [ '#EE6677', '#228833', '#CCBB44', '#4477AA']
        # self.colors = ['#8fd7d7', '#FFCD8E', '#00b0be', '#ff8ca1', '#f45f74', '#bdd373', '#98c127', '#ffb255']
        self.colors = [
            "#8fd7d7",
            "#FFCD8E",
            "#00b0be",
            "#ff8ca1",
            "#f45f74",
            "#bdd373",
            "#98c127",
            "#ffb255",
        ]

        self.use_value_gdp = use_value_gdp
        self.value_calculator = ValueCalculator(recipes_file) if use_value_gdp else None
        self.use_log_scale = use_log_scale  # Store the scale preference

    def _serialize_version_data(self):
        """Convert version data to cacheable format"""
        serialized = {}
        for version, data in self.versions.items():
            nodes_dict = {}
            for root in data["nodes"]:
                stack = [root]
                while stack:
                    node = stack.pop()
                    nodes_dict[node.id] = node.to_dict()
                    stack.extend(node.children)

            serialized[version] = {
                "nodes_dict": nodes_dict,
                "root_ids": [root.id for root in data["nodes"]],
                "label": data["label"],
            }
        return serialized

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

    def load_data(self, version_groups: Dict[str, List[int]], labels: Dict[str, str]):
        """
        Load and process data for multiple version groups, using cache if available

        Args:
            version_groups: Dict mapping model names to lists of version numbers
            labels: Dict mapping model names to display labels
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    cached_data = pickle.load(f)
                    if cached_data.get("version_groups") == version_groups:
                        self._deserialize_version_data(cached_data["data"])
                        self.achievements = cached_data["achievements"]
                        return
            except Exception as e:
                print(f"Error loading cache: {e}")
                os.remove(self.cache_file)

        for model_name, versions in version_groups.items():
            print(f"\nLoading model {model_name} (versions: {versions})")

            # Load and merge nodes from all versions for this model
            all_nodes = []
            for version in versions:
                nodes = self._load_version_from_db(version)
                if nodes:
                    all_nodes.extend(nodes)

            if all_nodes:
                gdps = [self._calculate_gdp(root) for root in all_nodes]
                print(f"Mean GDP across all versions: {np.mean(gdps):.1f}")
                print(f"STD GDP across all versions: {np.std(gdps):.1f}")

                self.versions[model_name] = {
                    "nodes": all_nodes,
                    "label": f"{labels[model_name]}",
                }

                # Process achievements across all versions
                self._process_merged_achievements(model_name, versions)

        # Cache the loaded data
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(
                    {
                        "version_groups": version_groups,
                        "data": self._serialize_version_data(),
                        "achievements": self.achievements,
                    },
                    f,
                )
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _process_merged_achievements(self, model_name: str, versions: List[int]):
        """Process achievements across multiple versions of the same model"""
        print(f"\nProcessing achievements for model {model_name}")

        with open("recipes.jsonl", "r") as f:
            recipes = {r["name"]: r for r in map(json.loads, f)}

        seen = set()
        model_achievements = []

        # Process achievements across all versions
        for version in versions:
            for root in self._load_version_from_db(version):
                current_path = []
                stack = [(root, 0, [])]

                while stack:
                    node, depth, path = stack.pop()
                    current_path = path + [node]
                    path_ticks = sum(n.metrics["ticks"] for n in current_path)

                    for achievements_dict, is_dynamic in [
                        (node.static_achievements, False),
                        (node.dynamic_achievements, True),
                    ]:
                        for item, quantity in achievements_dict.items():
                            achievement_key = (version, item)
                            if achievement_key not in seen:
                                print(
                                    f"\nProcessing achievement: {item} (version {version})"
                                )
                                print(f"Original ticks: {path_ticks}, depth: {depth}")

                                model_achievements.append(
                                    Achievement(
                                        depth=depth,
                                        ticks=path_ticks,
                                        item_name=item,
                                        ingredients=self._count_ingredients(
                                            recipes.get(item, {})
                                        ),
                                        is_dynamic=is_dynamic,
                                    )
                                )
                                seen.add(achievement_key)

                    for child in reversed(node.children):
                        stack.append((child, depth + 1, current_path))

        # Store earliest achievement for each item across all versions
        earliest_achievements = {}
        for achievement in model_achievements:
            key = achievement.item_name
            if key not in earliest_achievements or (
                achievement.ticks < earliest_achievements[key].ticks
                or (
                    achievement.ticks == earliest_achievements[key].ticks
                    and achievement.depth < earliest_achievements[key].depth
                )
            ):
                earliest_achievements[key] = achievement

        self.achievements[model_name] = list(earliest_achievements.values())
        print(
            f"Total unique achievements processed for model {model_name}: {len(earliest_achievements)}"
        )

    def organize_achievement_positions(
        self, achievements_by_depth, depth_stats, ax, series_index, used_positions
    ):
        """Organize achievement positions with improved stacking logic and priority items"""
        final_positions = {}
        stacks = defaultdict(list)  # Track achievement stacks by x-coordinate bucket

        # Priority achievements that should appear at the top
        PRIORITY_ACHIEVEMENTS = {"lab", "steam"}

        # First pass: Group achievements by x-coordinate bucket
        for x_coord, achievements_list in achievements_by_depth.items():
            if x_coord in depth_stats and depth_stats[x_coord]["mean"] > 0:
                base_position = depth_stats[x_coord]["mean"]

                # Calculate tolerance based on x-position
                if self.x_axis == "ticks":
                    # For ticks (log scale), tolerance increases with x
                    log_x = np.log10(x_coord)
                    tolerance = self.BASE_STACK_TOLERANCE * log_x
                    bucket_key = round(x_coord / (x_coord * tolerance)) * (
                        x_coord * tolerance
                    )
                else:
                    # For steps, use smaller fixed tolerance for linear scale
                    if x_coord < 50:
                        tolerance = self.BASE_STACK_TOLERANCE
                    elif x_coord < 100:
                        tolerance = self.BASE_STACK_TOLERANCE * 2
                    elif x_coord < 400:
                        tolerance = self.BASE_STACK_TOLERANCE * 4
                    else:
                        tolerance = self.BASE_STACK_TOLERANCE * 8
                    bucket_key = round(x_coord / tolerance) * tolerance

                # Custom sorting key function that prioritizes lab and steam
                def sort_key(achievement):
                    # First priority: lab and steam achievements
                    is_priority = achievement.item_name in PRIORITY_ACHIEVEMENTS
                    # Second priority: complexity (ingredients)
                    # Third priority: name for stable sorting
                    return (
                        int(is_priority),
                        -achievement.ingredients,
                        achievement.item_name,
                    )

                # Sort achievements using the custom key
                achievements_list.sort(key=sort_key)

                stacks[bucket_key].extend(
                    [
                        (x_coord, achievement, base_position)
                        for achievement in achievements_list
                    ]
                )

        # Second pass: Calculate stacked positions
        for bucket_key, stack in stacks.items():
            if not stack:
                continue

            # Get display coordinates for base position
            base_x_coord, _, base_y = stack[0]
            base_display_coords = ax.transData.transform([[base_x_coord, base_y]])[0]
            base_display_x, base_display_y = base_display_coords

            # Apply horizontal offset for series if needed
            x_key = round(bucket_key, -3 if self.x_axis == "ticks" else 1)
            if x_key in used_positions:
                base_display_x += self.HORIZONTAL_OFFSET_PIXELS * (series_index + 1)
            else:
                used_positions[x_key] = True

            # Calculate stacked positions
            stack_size = min(len(stack), self.MAX_STACK_SIZE)
            for i in range(stack_size):
                x_coord, achievement, base_y = stack[i]

                # Calculate vertical offset for this position in the stack
                stack_center_offset = (stack_size - 1) * self.STACK_VERTICAL_SPACING / 2
                vertical_offset = i * self.STACK_VERTICAL_SPACING - stack_center_offset

                # Apply the offset in display coordinates
                display_y = base_display_y + vertical_offset

                # Transform back to data coordinates
                data_coords = ax.transData.inverted().transform(
                    [[base_display_x, display_y]]
                )[0]
                data_x, data_y = data_coords

                # Store final position
                achievement_key = (achievement.item_name, x_coord)
                final_positions[achievement_key] = (data_x, data_y)

        return final_positions

    def _get_stack_vertical_spacing(self, ax):
        """Calculate appropriate vertical spacing based on plot dimensions"""
        # Get the figure height in pixels
        bbox = ax.get_window_extent().transformed(ax.figure.dpi_scale_trans.inverted())
        fig_height_pixels = bbox.height * ax.figure.dpi

        # Adjust spacing based on figure height
        base_spacing = fig_height_pixels * 0.02  # 2% of figure height
        return max(10, min(base_spacing, 20))  # Constrain between 10 and 20 pixels

    def _prepare_achievement_stack(self, achievements, max_stack_size=5):
        """Prepare achievement stack with priority based on complexity"""
        # Sort achievements by complexity (ingredients) and name
        sorted_achievements = sorted(
            achievements, key=lambda a: (a.ingredients, a.item_name)
        )

        # If we have more achievements than max_stack_size, prioritize most complex ones
        if len(sorted_achievements) > max_stack_size:
            return sorted_achievements[:max_stack_size]

        return sorted_achievements

    def organize_achievement_positions2(
        self, achievements_by_depth, depth_stats, ax, series_index, used_positions
    ):
        """Organize achievement positions with improved tick mapping"""
        positions = {}
        final_positions = {}

        # First pass: Group achievements by their x-coordinate
        for x_coord, achievements_list in achievements_by_depth.items():
            if x_coord in depth_stats and depth_stats[x_coord]["mean"] > 0:
                base_position = depth_stats[x_coord]["mean"]
                positions[x_coord] = {
                    "achievements": achievements_list,
                    "base_y": base_position,
                }

        # Second pass: Calculate final positions with proper coordinate transformation
        for x_coord, group_data in positions.items():
            achievements = group_data["achievements"]
            base_y = group_data["base_y"]

            # Sort achievements by complexity (ingredients) then name
            achievements.sort(key=lambda a: (a.ingredients, a.item_name))

            # Transform base coordinates to display coordinates
            display_coords = ax.transData.transform([[x_coord, base_y]])[0]
            base_display_x, base_display_y = display_coords

            # Apply horizontal offset for overlapping x-coordinates
            x_key = round(x_coord, -3 if self.x_axis == "ticks" else 1)
            if x_key in used_positions:
                base_display_x += self.HORIZONTAL_OFFSET_PIXELS * (series_index + 1)
            else:
                used_positions[x_key] = True

            # Calculate vertical spacing for each achievement
            for i, achievement in enumerate(achievements):
                # Apply vertical offset in display coordinates
                vertical_offset = i * self.VERTICAL_SPACING_PIXELS
                display_y = base_display_y + vertical_offset

                # Transform back to data coordinates
                data_coords = ax.transData.inverted().transform(
                    [[base_display_x, display_y]]
                )[0]
                data_x, data_y = data_coords

                # Store final position
                achievement_key = (achievement.item_name, x_coord)
                final_positions[achievement_key] = (data_x, data_y)

        return final_positions

    def _load_version_from_db(self, version: int) -> List[Node]:
        """Load all trajectories for a version from database"""
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, parent_id, achievements_json, value, ticks 
                    FROM programs WHERE version = %s
                """,
                    (version,),
                )
                rows = cur.fetchall()

        # Build node tree
        nodes = {}
        roots = []
        for id, parent_id, achievements, value, ticks in rows:
            node = Node(
                id=id,
                parent_id=parent_id,
                metrics={"value": value or 0, "ticks": ticks or 0},
                static_achievements=achievements.get("static", {}),
                dynamic_achievements=achievements.get("dynamic", {}),
                children=[],
            )
            nodes[id] = node

        # Connect nodes
        for node in nodes.values():
            if node.parent_id is None:
                roots.append(node)
            elif node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)

        return roots

    def _calculate_gdp(self, root: Node) -> float:
        """Calculate GDP for a trajectory using either method"""
        if not self.use_value_gdp:
            """Calculate final GDP for a trajectory"""
            total = 0
            stack = [root]
            while stack:
                node = stack.pop()
                total += node.metrics["value"]
                stack.extend(node.children)
            return total

        total_value = 0
        stack = [root]

        # Track achievements across the entire trajectory
        all_achievements = defaultdict(int)

        while stack:
            node = stack.pop()

            # Add static achievements
            for item, quantity in node.static_achievements.items():
                all_achievements[item] += quantity

            # Add dynamic achievements
            for item, quantity in node.dynamic_achievements.items():
                all_achievements[item] += quantity

            stack.extend(node.children)

        # Calculate total value based on achievements
        print("\nValue-based GDP calculation:")
        for item, quantity in all_achievements.items():
            item_value = self.value_calculator.get_value(item)
            contribution = item_value * quantity
            total_value += contribution
            print(f"  {item}: {quantity} x {item_value:.2f} = {contribution:.2f}")

        print(f"Total value-based GDP: {total_value}")
        return total_value

    def _process_achievements(self, version: int):
        """Process achievements with correct tick accumulation"""
        print(f"\nProcessing achievements for version {version}")

        with open("recipes.jsonl", "r") as f:
            recipes = {r["name"]: r for r in map(json.loads, f)}

        seen = set()
        version_achievements = []

        for root in self.versions[version]["nodes"]:
            # Initialize path tracking for cumulative calculations
            current_path = []
            stack = [(root, 0, [])]  # (node, depth, path_to_node)

            while stack:
                node, depth, path = stack.pop()

                # Update current path and cumulative ticks
                current_path = path + [node]

                # Calculate cumulative ticks for the current path
                path_ticks = sum(n.metrics["ticks"] for n in current_path)

                # Process achievements
                for achievements_dict, is_dynamic in [
                    (node.static_achievements, False),
                    (node.dynamic_achievements, True),
                ]:
                    for item, quantity in achievements_dict.items():
                        if item not in seen:
                            print(f"\nProcessing achievement: {item}")
                            print(f"Original ticks: {path_ticks}, depth: {depth}")

                            version_achievements.append(
                                Achievement(
                                    depth=depth,
                                    ticks=path_ticks,
                                    item_name=item,
                                    ingredients=self._count_ingredients(
                                        recipes.get(item, {})
                                    ),
                                    is_dynamic=is_dynamic,
                                )
                            )
                            seen.add(item)

                # Add children to stack with their paths
                for child in reversed(node.children):
                    stack.append((child, depth + 1, current_path))

        self.achievements[version] = version_achievements
        print(f"Total achievements processed for version {version}: {len(seen)}")

    def _count_ingredients(self, recipe: Dict) -> int:
        """Count total unique ingredients in recipe"""
        seen = set()
        if not recipe:
            return 1

        def traverse(item):
            seen.add(item["name"])
            for ingredient in item.get("ingredients", []):
                traverse(ingredient)

        traverse(recipe)
        return len(seen) - 1

    def _prepare_icon(self, item_name: str):
        """Prepare achievement icon for visualization with size limits"""
        src = os.path.join(self.icons_path, f"{item_name}.png")
        dst = f"icons/{item_name}.png"

        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs("icons", exist_ok=True)
            with Image.open(src) as img:
                # Get the first frame if it's an animated image
                if hasattr(img, "n_frames"):
                    img.seek(0)

                # Extract square tile from top-left
                size = min(img.width, img.height)
                tile = img.crop((0, 0, size, size))

                # Resize if too large (max 256x256)
                if size > 256:
                    tile = tile.resize((256, 256), Image.Resampling.LANCZOS)

                # Convert to RGBA if needed
                if tile.mode != "RGBA":
                    tile = tile.convert("RGBA")

                tile.save(dst, format="PNG")

    def weighted_percentile(self, values, weights, q):
        """Calculate weighted percentile for confidence intervals"""
        order = np.argsort(values)
        values = np.array(values)[order]
        weights = np.array(weights)[order]

        cumsum = np.cumsum(weights)
        cumsum = cumsum / cumsum[-1]  # Normalize

        return np.interp(q / 100, cumsum, values)

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
        edge_width = 3
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

    def _get_step_at_ticks(self, version, target_ticks):
        """Find the step number at which a version reaches the target ticks"""
        if target_ticks <= 0 or np.isinf(target_ticks) or np.isnan(target_ticks):
            return None

        nodes = self.versions[version]["nodes"]
        min_step = float("inf")

        for root in nodes:
            current_ticks = 0
            stack = [(root, 0, 0)]  # (node, step, accumulated_ticks)

            while stack:
                node, step, prev_ticks = stack.pop()
                current_ticks = prev_ticks + node.metrics["ticks"]

                if current_ticks >= target_ticks:
                    min_step = min(min_step, step)
                    break

                for child in node.children:
                    stack.append((child, step + 1, current_ticks))

        return min_step if min_step != float("inf") else None

    # After plotting both charts but before saving, add the connection lines
    def add_connecting_lines(self, ax1, ax2, step=990):
        # Get the data coordinates
        y_min, y_max = ax2.get_ylim()

        # Convert between axes coordinates
        fig = ax1.get_figure()

        # Get the display coordinates for connecting points
        ax1_bbox = ax1.get_position()
        ax2_bbox = ax2.get_position()

        # Right edge of first plot, left edge of second plot in figure coordinates
        x1 = ax1_bbox.x1
        x2 = ax2_bbox.x0

        # Convert data y-coordinates to figure coordinates
        y1_min = ax1.transData.transform([[0, y_min]])[0, 1]
        y1_min = fig.transFigure.inverted().transform([[0, y1_min]])[0, 1]

        y1_max = ax1.transData.transform([[0, y_max]])[0, 1]
        y1_max = fig.transFigure.inverted().transform([[0, y1_max]])[0, 1]

        y2_min = ax2.transData.transform([[0, y_min]])[0, 1]
        y2_min = fig.transFigure.inverted().transform([[0, y2_min]])[0, 1]

        y2_max = ax2.transData.transform([[0, y_max]])[0, 1]
        y2_max = fig.transFigure.inverted().transform([[0, y2_max]])[0, 1]

        # Create filled polygon
        polygon = plt.Polygon(
            [[x1, y1_min], [x2, y2_min], [x2, y2_max], [x1, y1_max]],
            transform=fig.transFigure,
            facecolor="gray",
            alpha=0.15,
            edgecolor="#404040",
            linestyle="--",
            linewidth=1,
        )
        fig.add_artist(polygon)

    def add_adjacent_connecting_lines(self, ax1, ax2):
        """Add connecting lines between two adjacent axes"""
        # Get the data coordinates
        y1_min, y1_max = ax1.get_ylim()
        y2_min, y2_max = ax2.get_ylim()

        # Get the display coordinates for connecting points
        fig = ax1.get_figure()
        ax1_bbox = ax1.get_position()
        ax2_bbox = ax2.get_position()

        # Right edge of first plot, left edge of second plot in figure coordinates
        x1 = ax1_bbox.x1
        x2 = ax2_bbox.x0

        # Convert data y-coordinates to figure coordinates
        y1_min = ax1.transData.transform([[0, y1_min]])[0, 1]
        y1_min = fig.transFigure.inverted().transform([[0, y1_min]])[0, 1]

        y1_max = ax1.transData.transform([[0, y1_max]])[0, 1]
        y1_max = fig.transFigure.inverted().transform([[0, y1_max]])[0, 1]

        y2_min = ax2.transData.transform([[0, y2_min]])[0, 1]
        y2_min = fig.transFigure.inverted().transform([[0, y2_min]])[0, 1]

        y2_max = ax2.transData.transform([[0, y2_max]])[0, 1]
        y2_max = fig.transFigure.inverted().transform([[0, y2_max]])[0, 1]

        # Create filled polygon
        polygon = plt.Polygon(
            [[x1, y1_min], [x2, y2_min], [x2, y2_max], [x1, y1_max]],
            transform=fig.transFigure,
            facecolor="gray",
            alpha=0.15,
            edgecolor="#404040",
            linestyle="--",
            linewidth=1,
        )
        fig.add_artist(polygon)

    def export_split_visualization(self, output_file: str, max_depth: int = 4990):
        """Export a visualization with main progression chart, final GDP scatter plot, and final time plot"""
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["savefig.dpi"] = 300

        # Create figure with three subplots
        fig = plt.figure(figsize=(14, 5))

        # Create three axes with specific width ratios and three rows
        # First row for plots, second for metric labels, third for 'Final' label
        # gs = plt.GridSpec(3, 3, height_ratios=[1, 0.1, 0.1], width_ratios=[15, 1, 1], wspace=0.1, hspace=0)
        gs = plt.GridSpec(
            3,
            3,
            height_ratios=[0.85, 0.075, 0.075],
            width_ratios=[15, 1, 1],
            wspace=0.12,
            hspace=0.2,
        )
        ax1 = fig.add_subplot(gs[0, 0])  # Main progression plot
        ax2 = fig.add_subplot(gs[0, 1])  # Final GDP scatter plot
        ax3 = fig.add_subplot(gs[0, 2])  # Final time scatter plot

        # Create hidden axes for the metric labels
        ax_reward_label = fig.add_subplot(gs[1, 1])
        ax_time_label = fig.add_subplot(gs[1, 2])

        # Create a hidden axis for the shared 'Final' label
        ax_shared = fig.add_subplot(gs[2, 1:])

        # Hide all axes for labels
        ax_reward_label.axis("off")
        ax_time_label.axis("off")
        ax_shared.axis("off")

        # Configure main progression plot
        ax1.set_xscale("log", base=self.x_base)
        ax1.set_yscale("log", base=self.y_base)

        if self.x_axis == "ticks":
            ax1.set_xlim(1e3, 1e8)
            ax1.set_xlabel("Ticks", fontsize=12)
        else:
            ax1.set_xlim(100, 5e3)
            ax1.set_xlabel("Steps", fontsize=12)
        ax1.set_ylim(1e3, 4e5)

        # Create main y-label with two parts
        ax1.set_ylabel("Reward\nCumulative Production Score", fontsize=12, labelpad=10)

        # Get the ylabel text object
        ylabel = ax1.yaxis.label

        # Get the text content
        lines = ylabel.get_text().split("\n")

        # Create two separate text objects
        ax1.set_ylabel(lines[0], fontsize=12, labelpad=20)
        subtitle = ax1.text(  # noqa
            -0.05,
            0.5,
            lines[1],
            transform=ax1.transAxes,
            rotation=90,
            ha="center",
            va="center",
            fontsize=9,
        )

        # Store final values for scatter plots
        final_values = []
        final_cis = []
        final_minutes = []
        final_minutes_cis = []
        colors = []

        ticks_per_unit = 60 * 60 * 60

        # Plot progression lines
        # used_positions = {}
        # for idx, (version, data) in enumerate(self.versions.items()):
        #     color = self.colors[idx % len(self.colors)]
        #     colors.append(color)
        #     stats = self._calculate_statistics(data['nodes'], max_depth)
        #
        #     # Plot main line and confidence interval
        #     x_coords = sorted(stats.keys())
        #     means = [stats[x]['mean'] for x in x_coords]
        #     ci_lower = [stats[x]['ci_lower'] for x in x_coords]
        #     ci_upper = [stats[x]['ci_upper'] for x in x_coords]
        #
        #     ax1.plot(x_coords, means, color=color, label=data['label'], linewidth=1.5)
        #     ax1.fill_between(x_coords, ci_lower, ci_upper, color=color, alpha=0.2)
        #
        #     # Calculate final values and minutes at target step
        #     target_step = 990
        #     if means:
        #         if self.x_axis == "steps":
        #             target_idx = next((idx for idx, x in enumerate(x_coords) if x >= target_step), -1)
        #         else:
        #             target_idx = next((idx for idx, x in enumerate(x_coords) if x >= target_step), -1)
        #
        #         if target_idx != -1:
        #             final_values.append(means[target_idx])
        #             final_cis.append((ci_lower[target_idx], ci_upper[target_idx]))
        #         else:
        #             final_values.append(means[-1])
        #             final_cis.append((ci_lower[-1], ci_upper[-1]))
        used_positions = {}
        for idx, (version, data) in enumerate(self.versions.items()):
            color = self.colors[idx % len(self.colors)]
            colors.append(color)
            stats = self._calculate_statistics(data["nodes"], max_depth)

            # Plot main line and standard error bands
            x_coords = sorted(stats.keys())
            means = [stats[x]["mean"] for x in x_coords]
            sem_lower = [stats[x]["sem_lower"] for x in x_coords]
            sem_upper = [stats[x]["sem_upper"] for x in x_coords]

            ax1.plot(x_coords, means, color=color, label=data["label"], linewidth=1.5)
            ax1.fill_between(x_coords, sem_lower, sem_upper, color=color, alpha=0.2)

            # Calculate final values and standard errors at target step
            target_step = 4990
            if means:
                if self.x_axis == "steps":
                    target_idx = next(
                        (idx for idx, x in enumerate(x_coords) if x >= target_step), -1
                    )
                else:
                    target_idx = next(
                        (idx for idx, x in enumerate(x_coords) if x >= target_step), -1
                    )

                if target_idx != -1:
                    final_values.append(means[target_idx])
                    final_cis.append((sem_lower[target_idx], sem_upper[target_idx]))
                else:
                    final_values.append(means[-1])
                    final_cis.append((sem_lower[-1], sem_upper[-1]))

                # Calculate final ticks statistics and convert to minutes
                final_ticks_stats = self._calculate_final_ticks_statistics(
                    data["nodes"], target_step
                )
                final_minutes.append(
                    final_ticks_stats["median"] / ticks_per_unit
                )  # Convert to hours
                final_minutes_cis.append(
                    (
                        final_ticks_stats["ci_lower"] / ticks_per_unit,
                        final_ticks_stats["ci_upper"] / ticks_per_unit,
                    )
                )

            # Process and plot achievements
            achievements_by_depth = defaultdict(list)
            for achievement in self.achievements[version]:
                if self.x_axis == "ticks":
                    x_coord = achievement.ticks
                    bucket = round(np.log(x_coord) / np.log(self.x_base) * 10) / 10
                else:
                    x_coord = achievement.depth
                    bucket = x_coord

                if x_coord > 0:
                    achievements_by_depth[bucket].append(achievement)

            positions = self.organize_achievement_positions(
                achievements_by_depth, stats, ax1, idx, used_positions
            )

            for (item_name, orig_x), (x, y) in positions.items():
                if x > 0 and y > 0:
                    x_min, x_max = ax1.get_xlim()
                    y_min, y_max = ax1.get_ylim()
                    if x_min <= x <= x_max and y_min <= y <= y_max:
                        self._add_achievement_icon(ax1, item_name, x, y, color)

        # Configure main plot grid and legend
        ax1.grid(True, which="major", linestyle="-", color="gray", alpha=0.2)
        ax1.grid(True, which="minor", linestyle="--", color="gray", alpha=0.1)
        ax1.tick_params(axis="both", which="major", labelsize=9)
        ax1.tick_params(axis="both", which="minor", labelsize=7)
        ax1.set_axisbelow(True)
        ax1.legend(loc="lower right", fontsize=10)

        # Configure GDP scatter plot
        x_margin = 0.5
        ax2.set_xlim(-x_margin, len(final_values) - 1 + x_margin)

        for i, (value, (ci_lower, ci_upper), color) in enumerate(
            zip(final_values, final_cis, colors)
        ):
            ax2.vlines(i, ci_lower, ci_upper, color=color, alpha=0.5)
            ax2.scatter(i, value, color=color, s=50, zorder=5)

        # Configure GDP plot settings
        # ax2.set_xticks(x_pos)
        # ax2.set_xticklabels([''] * len(x_pos))
        ax2.set_xticks([])

        ax2.set_yscale("log", base=self.y_base)
        ax2.yaxis.set_label_position("right")
        ax2.yaxis.tick_right()
        ax2.yaxis.set_minor_locator(LogLocator(base=10, subs="all"))
        ax2.grid(True, which="major", axis="y", linestyle="-", color="gray", alpha=0.2)
        ax2.grid(True, which="minor", axis="y", linestyle="--", color="gray", alpha=0.1)
        ax2.tick_params(axis="y", which="major", labelsize=8)  # Add this line

        # Configure time scatter plot
        ax3.set_xlim(-x_margin, len(final_minutes) - 1 + x_margin)

        for i, (value, (ci_lower, ci_upper), color) in enumerate(
            zip(final_minutes, final_minutes_cis, colors)
        ):
            ax3.vlines(i, ci_lower, ci_upper, color=color, alpha=0.5)
            ax3.scatter(i, value, color=color, s=50, zorder=5)

        # Configure time plot settings
        # ax3.set_xticks(x_pos)
        # ax3.set_xticklabels([''] * len(x_pos))
        ax3.set_xticks([])
        ax3.set_yscale("log", base=10)
        ax3.yaxis.set_label_position("right")
        ax3.yaxis.tick_right()
        ax3.yaxis.set_minor_locator(LogLocator(base=10, subs="all"))
        ax3.grid(True, which="major", axis="y", linestyle="-", color="gray", alpha=0.2)
        ax3.grid(True, which="minor", axis="y", linestyle="--", color="gray", alpha=0.1)
        ax3.tick_params(axis="y", which="major", labelsize=8)  # Add this line

        # For reward plot (ax2)
        # y2_min = min(ci[0] for ci in final_cis) * 0.9  # Add some padding
        # y2_max = max(ci[1] for ci in final_cis) * 1.1
        # ax2.set_ylim(y2_min, y2_max)
        # #ax2.set_yticks([y2_min, y2_max])
        # ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x / 1000):,}k'))
        #
        # # For time plot (ax3)
        # y3_min = min(ci[0] for ci in final_minutes_cis) * 0.9
        # y3_max = max(ci[1] for ci in final_minutes_cis) * 1.1
        # ax3.set_ylim(y3_min, y3_max)
        # #ax3.set_yticks([y3_min, y3_max])
        # ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

        # For reward plot (ax2)
        y2_min = min(ci[0] for ci in final_cis)
        y2_max = max(ci[1] for ci in final_cis)
        ax2.set_ylim(min(0, y2_min * 0.9), y2_max * 1.1)
        # Instead of setting specific tick values, show only min and max rounded values
        # ax2.yaxis.set_major_locator(plt.FixedLocator([y2_min, y2_max]))
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{int(x / 1000):,}k")
        )
        ax2.yaxis.set_minor_locator(plt.NullLocator())

        # For time plot (ax3)
        y3_min = min(ci[0] for ci in final_minutes_cis)
        y3_max = max(ci[1] for ci in final_minutes_cis)
        ax3.set_ylim(min(0, y3_min * 0.9), y3_max * 1.1)
        # Use FixedLocator instead of set_yticks
        # ax3.yaxis.set_major_locator(plt.FixedLocator([y3_min, y3_max]))
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}"))
        ax3.yaxis.set_minor_locator(plt.NullLocator())

        # Add metric labels between charts and 'Final' label
        ax_reward_label.text(0.5, 1.4, "Reward", ha="center", va="center", fontsize=10)
        ax_time_label.text(
            0.5, 1.4, "Elapsed (hrs)", ha="center", va="center", fontsize=10
        )

        # Add shared 'Final' label under both plots
        ax_shared.text(0.5, 2.4, "Final", ha="center", va="center", fontsize=12)

        # Add connecting lines between plots
        self.add_connecting_lines(ax1, ax2)
        self.add_adjacent_connecting_lines(ax2, ax3)

        # Save the figure
        plt.savefig(output_file, bbox_inches="tight", pad_inches=0.1, dpi=300)
        plt.close()

    def _calculate_final_ticks_statistics(
        self, roots: List[Node], target_step: int
    ) -> Dict:
        """Calculate statistics for final ticks at target step"""
        final_ticks = []

        for root in roots:
            stack = [(root, 0, 0)]  # (node, step, accumulated_ticks)

            path_ticks = []
            while stack:
                node, step, prev_ticks = stack.pop()

                if step == target_step:
                    path_ticks.append(prev_ticks + node.metrics["ticks"])
                    continue

                if step < target_step:
                    for child in node.children:
                        stack.append(
                            (child, step + 1, prev_ticks + node.metrics["ticks"])
                        )

            if path_ticks:
                final_ticks.append(np.median(path_ticks))

        if final_ticks:
            return {
                "median": np.median(final_ticks),
                "ci_lower": np.percentile(final_ticks, 2.5),
                "ci_upper": np.percentile(final_ticks, 97.5),
            }
        return {"median": 0, "ci_lower": 0, "ci_upper": 0}

    def _calculate_statistics(self, roots: List[Node], max_depth: int) -> Dict:
        """Calculate statistics with standard error of mean instead of CI"""
        values_by_x = defaultdict(list)

        # Collect raw data points
        for root in roots:
            values_by_x[0].append(0)
            stack = [
                (root, 0, 0, 0, defaultdict(int))
            ]  # (node, depth, prev_ticks, prev_value, achievements)

            while stack:
                node, depth, prev_ticks, prev_value, prev_achievements = stack.pop()
                if depth > max_depth:
                    continue

                # Create a copy of previous achievements
                current_achievements = prev_achievements.copy()

                # Add this node's achievements
                for item, quantity in node.static_achievements.items():
                    current_achievements[item] += quantity
                for item, quantity in node.dynamic_achievements.items():
                    current_achievements[item] += quantity

                # Calculate current value based on GDP method
                if self.use_value_gdp:
                    # Calculate total value based on all achievements up to this point
                    current_value = 0
                    for item, quantity in current_achievements.items():
                        item_value = self.value_calculator.get_value(item)
                        current_value += item_value * quantity
                else:
                    current_value = prev_value + node.metrics["value"]

                # Calculate x coordinate
                ticks = prev_ticks + node.metrics["ticks"]
                x_coord = ticks if self.x_axis == "ticks" else depth

                values_by_x[x_coord].append(current_value)

                # Add children to stack with updated achievements
                for child in node.children:
                    stack.append(
                        (child, depth + 1, ticks, current_value, current_achievements)
                    )

        # Calculate statistics
        stats = {0: {"mean": 0, "sem_lower": 0, "sem_upper": 0, "std": 0}}
        x_coords = sorted(x for x in values_by_x.keys() if x > 0)

        if self.x_axis == "ticks":
            # Create evaluation points using custom base
            eval_points = np.logspace(
                np.log(min(x_coords)) / np.log(self.x_base),
                np.log(max(x_coords)) / np.log(self.x_base),
                500,
                base=self.x_base,
            )

            # Calculate smoothed statistics with SEM
            window = 0.1  # log-space window size
            for x in eval_points:
                nearby_values = []
                for orig_x, values in values_by_x.items():
                    if orig_x > 0:
                        log_diff = abs(
                            np.log(x) / np.log(self.x_base)
                            - np.log(orig_x) / np.log(self.x_base)
                        )
                        if log_diff < window:
                            weight = np.exp(-((log_diff / window) ** 2))
                            nearby_values.extend((v, weight) for v in values)

                if nearby_values:
                    values, weights = zip(*nearby_values)
                    mean = np.average(values, weights=weights)
                    weighted_var = np.average(
                        (np.array(values) - mean) ** 2, weights=weights
                    )
                    # Calculate weighted SEM
                    n_effective = (np.sum(weights) ** 2) / np.sum(
                        np.array(weights) ** 2
                    )
                    sem = np.sqrt(weighted_var / n_effective)

                    stats[x] = {
                        "mean": mean,
                        "std": np.sqrt(weighted_var),
                        "sem_lower": mean - sem,
                        "sem_upper": mean + sem,
                    }
        else:
            # For steps, use direct statistics
            for x in x_coords:
                values = values_by_x[x]
                if values:
                    mean = np.mean(values)
                    std = np.std(values)
                    sem = std / np.sqrt(len(values))  # Standard Error of Mean
                    stats[x] = {
                        "mean": mean,
                        "std": std,
                        "sem_lower": mean - sem,
                        "sem_upper": mean + sem,
                    }

        # Ensure monotonicity
        prev_stats = {"mean": 0, "sem_lower": 0, "sem_upper": 0, "std": 0}
        for x in sorted(stats.keys()):
            stats[x] = {
                "mean": max(stats[x]["mean"], prev_stats["mean"]),
                "sem_lower": max(stats[x]["sem_lower"], prev_stats["sem_lower"]),
                "sem_upper": max(stats[x]["sem_upper"], prev_stats["sem_upper"]),
                "std": stats[x]["std"],
            }
            prev_stats = stats[x]

        return stats

    def _calculate_statistics_ci(self, roots: List[Node], max_depth: int) -> Dict:
        """Calculate statistics with cumulative achievement tracking"""
        values_by_x = defaultdict(list)

        # Collect raw data points
        for root in roots:
            values_by_x[0].append(0)
            stack = [
                (root, 0, 0, 0, defaultdict(int))
            ]  # (node, depth, prev_ticks, prev_value, achievements)

            while stack:
                node, depth, prev_ticks, prev_value, prev_achievements = stack.pop()
                if depth > max_depth:
                    continue

                # Create a copy of previous achievements
                current_achievements = prev_achievements.copy()

                # Add this node's achievements
                for item, quantity in node.static_achievements.items():
                    current_achievements[item] += quantity
                for item, quantity in node.dynamic_achievements.items():
                    current_achievements[item] += quantity

                # Calculate current value based on GDP method
                if self.use_value_gdp:
                    # Calculate total value based on all achievements up to this point
                    current_value = 0
                    for item, quantity in current_achievements.items():
                        item_value = self.value_calculator.get_value(item)
                        current_value += item_value * quantity
                else:
                    current_value = prev_value + node.metrics["value"]

                # Calculate x coordinate
                ticks = prev_ticks + node.metrics["ticks"]
                x_coord = ticks if self.x_axis == "ticks" else depth

                values_by_x[x_coord].append(current_value)

                # Add children to stack with updated achievements
                for child in node.children:
                    stack.append(
                        (child, depth + 1, ticks, current_value, current_achievements)
                    )

        # Calculate statistics
        stats = {0: {"mean": 0, "ci_lower": 0, "ci_upper": 0, "std": 0}}
        x_coords = sorted(x for x in values_by_x.keys() if x > 0)

        if self.x_axis == "ticks":
            # Create evaluation points using custom base
            eval_points = np.logspace(
                np.log(min(x_coords)) / np.log(self.x_base),
                np.log(max(x_coords)) / np.log(self.x_base),
                500,
                base=self.x_base,
            )

            # Calculate smoothed statistics
            window = 0.1  # log-space window size
            for x in eval_points:
                nearby_values = []
                for orig_x, values in values_by_x.items():
                    if orig_x > 0:
                        log_diff = abs(
                            np.log(x) / np.log(self.x_base)
                            - np.log(orig_x) / np.log(self.x_base)
                        )
                        if log_diff < window:
                            weight = np.exp(-((log_diff / window) ** 2))
                            nearby_values.extend((v, weight) for v in values)

                if nearby_values:
                    values, weights = zip(*nearby_values)
                    stats[x] = {
                        "mean": np.average(values, weights=weights),
                        "std": np.std(values),
                        "ci_lower": self.weighted_percentile(values, weights, 2.5),
                        "ci_upper": self.weighted_percentile(values, weights, 97.5),
                    }
        else:
            # For steps, use direct statistics
            for x in x_coords:
                values = values_by_x[x]
                if values:
                    stats[x] = {
                        "mean": np.mean(values),
                        "std": np.std(values),
                        "ci_lower": np.percentile(values, 2.5),
                        "ci_upper": np.percentile(values, 97.5),
                    }

        # Ensure monotonicity
        prev_stats = {"mean": 0, "ci_lower": 0, "ci_upper": 0, "std": 0}
        for x in sorted(stats.keys()):
            stats[x] = {
                "mean": max(stats[x]["mean"], prev_stats["mean"]),
                "ci_lower": max(stats[x]["ci_lower"], prev_stats["ci_lower"]),
                "ci_upper": max(stats[x]["ci_upper"], prev_stats["ci_upper"]),
                "std": stats[x]["std"],
            }
            prev_stats = stats[x]

        return stats

    def _add_achievement_icon(self, ax, item_name: str, x: float, y: float, color: str):
        """Add achievement icon with background circle"""
        try:
            self._prepare_icon(item_name)
            icon_path = f"icons/{item_name}.png"
            if not os.path.exists(icon_path):
                return

            # Add background circle
            circle_img = self.create_circle_background(color)
            circle_box = OffsetImage(circle_img, zoom=0.2)
            circle_box.image.axes = ax

            ab_circle = AnnotationBbox(
                circle_box, (x, y), frameon=False, box_alignment=(0.5, 0.5), pad=0
            )
            ax.add_artist(ab_circle)

            # Add icon
            icon = plt.imread(icon_path)
            icon_box = OffsetImage(icon, zoom=0.10)
            ab = AnnotationBbox(icon_box, (x, y), frameon=False)
            ax.add_artist(ab)
        except Exception as e:
            print(f"Failed to add icon for {item_name}: {e}")


async def main():
    # Example usage
    db_client = PostgresDBClient(
        max_conversation_length=40,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )

    icons_path = "/data/icons/early_icons"

    for x_axis in ["steps", "ticks"]:
        viz = ProgressionVisualizerWithTicks(
            db_client,
            icons_path,
            x_axis,
            use_log_scale=x_axis != "ticks",
            use_value_gdp=False,
            recipes_file="/data/recipes/recipes.jsonl",
        )

        # Configure versions to plot
        version_groups = {
            "Deepseek-v3": [555, 556, 557, 558],
            "GPT-4o-Mini": [548, 575, 576, 577, 578],
            "LLaMA-70B": [550, 599, 600, 601, 602],
            "Gemini-2": [595, 596, 597, 598, 805, 806, 807, 808],
            "GPT-4o": [
                551,
                552,
                553,
                554,
                564,
                797,
                798,
                799,
                800,
            ],  # Multiple GPT-4 versions
            "Claude-3.5": [
                559,
                560,
                561,
                562,
                574,
                801,
                802,
                803,
                804,
            ],  # Multiple Claude versions
            "Claude-3.7": [2223, 2226, 2224, 2225],  # Multiple Claude versions
            "o3-mini-high": [2229, 2227, 2228, 2230],
            # "LLaMA-70B": [488],  # Single version
            # "GPT-4-Mini": [505],
            # "o3-mini": [508]
        }

        labels = {
            "Claude-3.7": "Claude-3.7",
            "Claude-3.5": "Claude-3.5",
            "o3-mini-high": "o3-mini-high",
            "GPT-4o": "GPT-4o",
            "LLaMA-70B": "LLaMA-70B",
            "GPT-4o-Mini": "GPT-4o-Mini",
            "o3-mini": "o3-mini",
            "Deepseek-v3": "Deepseek-v3",
            "Gemini-2": "Gemini-2",
        }

        # Generate visualization
        viz.load_data(version_groups, labels)
        # viz.export_visualization(f"progression_{x_axis}.png", reference_version=492)
        viz.export_split_visualization(f"progression_{x_axis}_split_ticks.png")
        # Generate new achievement stack visualization
        # viz.export_achievement_frequency(f"achievement_stack_{x_axis}.png")


if __name__ == "__main__":
    asyncio.run(main())
