import asyncio
import json
import pickle
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal

from matplotlib.legend_handler import HandlerBase
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os

import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from matplotlib import image as mpimg

from fle.commons.db_client import DBClient
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


class IconColorHandler(HandlerBase):
    """Custom handler to create legend entries with both color patches and icons"""

    def __init__(self, item_name, color, alpha=0.7):
        self.item_name = item_name
        self.color = color
        self.alpha = alpha
        super().__init__()

    def create_artists(
        self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans
    ):
        artists = []

        # Create the color rectangle
        rect = patches.Rectangle(
            xy=(0, 0),
            width=width * 0.6,  # Make color patch smaller to leave room for icon
            height=height,
            facecolor=self.color,
            alpha=self.alpha,
            transform=trans,
        )
        artists.append(rect)

        # Try to add the icon
        try:
            icon_path = f"icons/{self.item_name}.png"
            if os.path.exists(icon_path):
                # Load and create icon as image
                img = mpimg.imread(icon_path)
                icon = plt.imshow(
                    img,
                    extent=[width * 0.7, width * 0.7 + height, 0, height],
                    transform=trans,
                    aspect="equal",
                    clip_on=True,
                )
                artists.append(icon)
        except Exception as e:
            print(f"Failed to add icon for {self.item_name}: {e}")

        return artists


def create_custom_legend_with_icons(
    ax, sorted_items, item_complexities, colors, fontsize, stacked
):
    """Create a custom legend by manually placing elements"""

    # Create a new axes for the legend
    legend_bbox = ax.get_position()
    legend_ax = ax.figure.add_axes(
        [
            legend_bbox.x1 + 0.01,  # x position
            legend_bbox.y0 + 0.02,  # y position
            0.2,  # width
            legend_bbox.height * 2.5,  # height
        ]
    )
    legend_ax.axis("off")  # Hide axes

    # Title
    legend_ax.text(
        0,
        0.95,
        "Items",  # (sorted by complexity)',
        fontsize=fontsize - 2,
        transform=legend_ax.transAxes,
    )

    # Use full height of legend for spacing
    num_items = len(sorted_items)
    y_spacing = 1 / (num_items + 1)  # Remove the +1 to use more space

    # Reverse the items and colors for bottom-to-top ordering
    sorted_items_reversed = list(reversed(sorted_items))
    colors_reversed = list(reversed(colors))

    # Add each item
    for idx, (item, color) in enumerate(zip(sorted_items_reversed, colors_reversed)):
        y_pos = 0.9 - idx * y_spacing  # Start from 0.95 instead of 0.9

        # Add color patch
        rect = patches.Rectangle(
            (0, y_pos),
            0.1,
            y_spacing * 0.7,  # Reduced height of color patch for more spacing
            facecolor=color,
            alpha=0.7,
            transform=legend_ax.transAxes,
        )
        legend_ax.add_artist(rect)

        # Try to add icon
        try:
            icon_path = f"icons/{item}.png"
            if os.path.exists(icon_path):
                img = plt.imread(icon_path)
                imagebox = OffsetImage(img, zoom=0.2)

                # Create annotation box with explicit axes reference
                ab = AnnotationBbox(
                    imagebox,
                    (
                        0.2,
                        y_pos + y_spacing * 0.35,
                    ),  # Adjusted position for new spacing
                    xycoords=legend_ax.transAxes,
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                )
                ab.axes = legend_ax  # Set axes explicitly
                legend_ax.add_artist(ab)
        except Exception as e:
            print(f"Failed to add icon for {item}: {e}")

    # Adjust figure to make room for legend
    plt.subplots_adjust(right=0.85)

    return legend_ax


@dataclass
class ModelVersionGroup:
    """Represents a group of versions belonging to the same model"""

    model_name: str
    version_ids: List[int]
    color: str
    label: str


class ProgressionVisualizer:
    """Creates publication-quality visualizations of agent progression"""

    VERTICAL_SPACING_PIXELS = 12
    HORIZONTAL_OFFSET_PIXELS = 0

    def __init__(
        self,
        db_client,
        icons_path: str,
        x_axis: Literal["steps", "ticks"] = "steps",
        cache_file: str = "viz_cache_combined.pkl",
        x_base: float = 10,
        y_base: float = 10,
        use_value_gdp=False,
        recipes_file="recipes.jsonl",
        use_log_scale: bool = True,
    ):
        self.db_client = db_client
        self.icons_path = icons_path
        self.x_axis = x_axis
        self.cache_file = cache_file
        self.x_base = x_base
        self.y_base = y_base
        self.model_groups = {}  # Maps model name to ModelVersionGroup
        self.versions = {}  # Keeps existing version data structure
        self.labels_count = {}
        self.achievements = defaultdict(list)
        # self.colors = ['#228833', '#CCBB44', '#EE6677', '#4477AA']
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
        self.use_log_scale = use_log_scale

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

    def load_data(
        self, model_groups: Dict[str, List[int]], model_labels: Dict[str, str]
    ):
        """
        Load and process data for multiple model groups

        Args:
            model_groups: Dict mapping model names to lists of version IDs
            model_labels: Dict mapping model names to display labels
        """
        print("\nStarting data load process...")

        # First, try to load from cache
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    cached_data = pickle.load(f)
                    # Check if cached groups match current groups
                    if all(
                        [
                            cached_data.get("model_groups")[model].version_ids
                            == model_groups[model]
                            for model in model_groups.keys()
                        ]
                    ):
                        print("Found matching cache data, loading...")
                        self._deserialize_version_data(cached_data["data"])
                        self.achievements = cached_data["achievements"]
                        self.model_groups = cached_data["model_groups"]

                        # Verify loaded data
                        for model_name, group in self.model_groups.items():
                            print(f"\nModel: {model_name}")
                            self.labels_count[model_name] = len(group.version_ids)
                            for version_id in group.version_ids:
                                if version_id in self.versions:
                                    print(
                                        f"  Version {version_id}: {len(self.versions[version_id]['nodes'])} nodes"
                                    )
                                else:
                                    print(f"  Version {version_id}: Not found in data")

                        return
            except Exception as e:
                print(f"Error loading cache: {e}")
                os.remove(self.cache_file)

        print("\nNo valid cache found, loading from database...")

        # Initialize model groups with colors
        for idx, (model_name, version_ids) in enumerate(model_groups.items()):
            color = self.colors[idx % len(self.colors)]
            self.model_groups[model_name] = ModelVersionGroup(
                model_name=model_name,
                version_ids=version_ids,
                color=color,
                label=model_labels[model_name],
            )

        # Load data for each version
        total_versions = sum(
            len(group.version_ids) for group in self.model_groups.values()
        )
        versions_loaded = 0

        for model_name, group in self.model_groups.items():
            print(f"\nLoading data for model: {model_name}")
            for version in group.version_ids:
                print(f"  Loading version {version}...")
                nodes = self._load_version_from_db(version)
                versions_loaded += 1
                print(f"  Progress: {versions_loaded}/{total_versions} versions")

                if nodes:
                    print(f"  Found {len(nodes)} root nodes")
                    self.versions[version] = {
                        "nodes": nodes,
                        "label": f"{group.label} (v{version})",
                    }
                    if group.label not in self.labels_count:
                        self.labels_count[group.label] = 0
                    self.labels_count[group.label] += len(nodes)

                    self._process_achievements(version)
                else:
                    print(f"  No nodes found for version {version}")

        print("\nData loading complete. Summary:")
        for model_name, group in self.model_groups.items():
            print(f"\nModel: {model_name}")
            success_count = sum(1 for v in group.version_ids if v in self.versions)
            print(
                f"Successfully loaded {success_count}/{len(group.version_ids)} versions"
            )

        # Cache the loaded data
        try:
            print("\nSaving to cache...")
            with open(self.cache_file, "wb") as f:
                pickle.dump(
                    {
                        #'model_groups': model_groups,
                        "data": self._serialize_version_data(),
                        "achievements": self.achievements,
                        "model_groups": self.model_groups,
                    },
                    f,
                )
            print("Cache saved successfully")
        except Exception as e:
            print(f"Error saving cache: {e}")

        print("\nAll data loading operations complete")

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

    def add_complexity_brackets(
        self, fig, icon_ax, achievements, x_positions, complexities, fontsize=12
    ):
        bracket_ax = fig.add_axes(icon_ax.get_position())
        bracket_ax.set_xlim(icon_ax.get_xlim())
        bracket_ax.set_ylim(0, 1)
        bracket_ax.axis("off")

        current_complexity = None
        start_x = None
        for i, (achievement, x) in enumerate(zip(achievements, x_positions)):
            complexity = complexities.get(achievement, 0)
            if complexity != current_complexity:
                if current_complexity is not None:
                    self.draw_bracket(
                        bracket_ax,
                        start_x,
                        x_positions[i - 1],
                        current_complexity,
                        fontsize,
                    )
                current_complexity = complexity
                start_x = x

        # Draw the last bracket
        if current_complexity is not None:
            self.draw_bracket(
                bracket_ax, start_x, x_positions[-1], current_complexity, fontsize
            )

    def draw_bracket(self, ax, start_x, end_x, complexity, fontsize=12):
        mid_x = (start_x + end_x) / 2
        bracket_height = 0.4
        text_height = -0.4  # Adjust this value to position the text lower if needed

        # Draw the bracket
        ax.plot(
            [start_x, start_x, end_x, end_x],
            [0, -bracket_height, -bracket_height, 0],
            color="black",
            linewidth=1,
        )

        # Add the complexity text
        ax.text(
            mid_x,
            text_height,
            f"{complexity}",
            ha="center",
            va="top",
            fontsize=fontsize - 2,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.7),
        )

        # Extend the y-axis limit to show the full bracket and text
        ax.set_ylim(min(ax.get_ylim()[0], text_height - 0.1), ax.get_ylim()[1])

    def export_combined_visualization(
        self,
        output_file: str,
        model_names: List[str],
        achievement_params: dict = None,
        production_params: dict = None,
        layout: Literal["side-by-side", "stacked"] = "stacked",
    ):
        """
        Create a combined visualization with achievement stack and production volumes.
        """
        # Set default parameters if not provided
        if achievement_params is None:
            achievement_params = {"render_complexity": False, "minimum_complexity": 2}

        if production_params is None:
            production_params = {
                "step_size": 50,
                "step_proportion": 0.9,
                "show_fractions": False,
                "use_log_scale": False,
                "min_total_volume": 1e-6,
                "min_complexity": 2,
                "cumulative": True,
                "groupby_complexity": False,
                "unified_y_axis": True,
                "chart_type": "line",
            }

        # Set figure parameters
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["savefig.dpi"] = 300

        if layout == "side-by-side":
            # Side-by-side layout with reduced height for production plots
            fig = plt.figure(figsize=(20, 10))  # Reduced height from 12 to 10
            gs = fig.add_gridspec(
                3,
                3,
                width_ratios=[2, 1, 1],
                height_ratios=[
                    1.5,
                    0.75,
                    0.75,
                ],  # Adjusted ratios to reduce production plot height
                left=0.05,
                right=0.95,
                bottom=0.1,
                top=0.9,
                wspace=0.3,
                hspace=0.4,
            )  # Increased spacing

            achievement_ax = fig.add_subplot(gs[:, 0])
            icon_ax = fig.add_axes(achievement_ax.get_position())
            icon_ax.set_position(
                [
                    achievement_ax.get_position().x0,
                    achievement_ax.get_position().y0 - 0.05,
                    achievement_ax.get_position().width,
                    0.05,
                ]
            )

            production_axes = [
                fig.add_subplot(gs[0, 1]),
                fig.add_subplot(gs[0, 2]),
                fig.add_subplot(gs[1, 1]),
                fig.add_subplot(gs[1, 2]),
                fig.add_subplot(gs[2, 1]),
                fig.add_subplot(gs[2, 2]),
            ]

        else:  # stacked layout
            fig = plt.figure(figsize=(16, 10))  # Reduced height from 12 to 10

            # Create a 3-row grid with reduced height for production plots
            gs = fig.add_gridspec(
                3,
                3,
                height_ratios=[
                    1.5,
                    0.75,
                    0.75,
                ],  # Adjusted ratios to reduce production plot height
                left=0.05,
                right=0.95,
                bottom=0.1,
                top=0.9,
                wspace=0.3,
                hspace=0.4,
            )  # Increased spacing

            # Achievement stack spans all columns in first row
            achievement_ax = fig.add_subplot(gs[0, :])
            icon_ax = fig.add_axes(achievement_ax.get_position())
            icon_ax.set_position(
                [
                    achievement_ax.get_position().x0,
                    achievement_ax.get_position().y0 - 0.05,
                    achievement_ax.get_position().width,
                    0.05,
                ]
            )

            # Production plots in 2x3 grid (rows 2 and 3)
            production_axes = [
                fig.add_subplot(gs[1, 0]),  # Top left
                fig.add_subplot(gs[1, 1]),  # Top middle
                fig.add_subplot(gs[1, 2]),  # Top right
                fig.add_subplot(gs[2, 0]),  # Bottom left
                fig.add_subplot(gs[2, 1]),  # Bottom middle
                fig.add_subplot(gs[2, 2]),  # Bottom right
            ]

        # Plot achievement stack
        self._plot_achievement_stack(
            achievement_ax, icon_ax, model_names, layout=layout, **achievement_params
        )

        # Plot production volumes
        self._plot_production_volumes(
            production_axes, model_names, layout=layout, **production_params
        )

        # Save figure
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()

    def _plot_achievement_stack(
        self,
        ax,
        icon_ax,
        model_names,
        render_complexity=False,
        minimum_complexity=2,
        fontsize=16,
        layout="stacked",
    ):
        """Helper method to plot achievement stack on given axes"""
        from collections import defaultdict

        # Define raw resources that should appear first
        RAW_RESOURCES = {"coal", "copper-ore", "iron-ore", "water", "stone", "wood"}

        # Similar to original but using model_groups for aggregation
        model_achievement_counts = defaultdict(dict)
        all_achievements = set()
        achievement_complexities = {}

        # Count achievements across all versions of each model
        for model_name in model_names:
            counts = defaultdict(int)
            group = self.model_groups[model_name]

            for version in group.version_ids:
                if version not in self.versions:
                    continue

                for root in self.versions[version]["nodes"]:
                    run_achievements = defaultdict(int)
                    stack = [root]

                    while stack:
                        node = stack.pop()
                        for item, quantity in node.static_achievements.items():
                            run_achievements[item] += quantity
                        for item, quantity in node.dynamic_achievements.items():
                            run_achievements[item] += quantity
                        stack.extend(node.children)

                    # Add this run's counts to total counts
                    for item, quantity in run_achievements.items():
                        counts[item] += quantity
                        all_achievements.add(item)
                        if item not in model_achievement_counts[model_name]:
                            model_achievement_counts[model_name][item] = 0
                        model_achievement_counts[model_name][item] += quantity

                # Get complexities
                for achievement in self.achievements[version]:
                    if achievement.item_name in RAW_RESOURCES:
                        achievement_complexities[achievement.item_name] = 0
                    else:
                        achievement_complexities[achievement.item_name] = (
                            achievement.ingredients
                        )

        # Filter achievements based on minimum complexity
        if minimum_complexity > 0:
            filtered_achievements = {
                item
                for item in all_achievements
                if achievement_complexities.get(item, 0) >= minimum_complexity
            }
            all_achievements = filtered_achievements
            for version in model_achievement_counts:
                filtered_counts = {
                    item: count
                    for item, count in model_achievement_counts[version].items()
                    if item in filtered_achievements
                }
                model_achievement_counts[version] = filtered_counts

        # Sort achievements
        def sort_key(item):
            if (
                item in RAW_RESOURCES
                and achievement_complexities.get(item, 0) < minimum_complexity
            ):
                return (0, item)
            return (1, achievement_complexities.get(item, 0), item)

        sorted_achievements = sorted(all_achievements, key=sort_key)

        # Calculate x positions for achievements
        x_positions = np.arange(len(sorted_achievements))
        bar_width = 0.15
        spacing_factor = 1

        # Plot bars for each model
        for idx, (version, counts) in enumerate(model_achievement_counts.items()):
            color = self.colors[idx % len(self.colors)]
            x_offset = (idx - (len(model_names) - 1) / 2) * bar_width * spacing_factor

            heights = [counts.get(ach, 0) for ach in sorted_achievements]
            nonzero_mask = np.array(heights) > 0
            if any(nonzero_mask):
                ax.bar(
                    x_positions + x_offset,
                    heights,
                    bar_width,
                    color=color,
                    alpha=0.7,
                    label=version,
                )  # self.versions[version]['label'])

        # Add separator after raw resources
        raw_resources_shown = len(
            [r for r in RAW_RESOURCES if r in sorted_achievements]
        )
        if raw_resources_shown > 0:
            ax.axvline(
                raw_resources_shown - 0.5, color="gray", linestyle="-", alpha=0.5
            )

        # Add separators between complexity groups
        prev_complexity = None
        for i, ach in enumerate(
            sorted_achievements[raw_resources_shown:], raw_resources_shown
        ):
            complexity = achievement_complexities.get(ach, 0)
            if prev_complexity is not None and complexity != prev_complexity:
                ax.axvline(i - 0.5, color="gray", linestyle="--", alpha=0.3)
            prev_complexity = complexity

        # Configure main axes
        ax.set_yscale("log")

        ax.set_ylabel("Item Production", fontsize=fontsize - 2)  # increase from default
        # ax.set_xlabel('Item Complexity', fontsize=fontsize)
        ax.tick_params(
            axis="both", which="major", labelsize=fontsize - 2
        )  # increase tick label size

        ax.set_xticks([])
        ax.grid(True, axis="y", linestyle="--", alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_ylim(bottom=0.9)

        # Calculate the exact x-axis limits based on data and bar width
        num_versions = len(model_names)
        total_width = bar_width * num_versions * 1.1
        x_min = -total_width / 2
        x_max = len(sorted_achievements) - 1 + total_width / 2
        ax.set_xlim(x_min, x_max)

        # Configure and populate icon axis
        icon_ax.set_xlim(ax.get_xlim())
        icon_ax.set_ylim(0, 1)
        icon_ax.axis("off")

        # Add icons
        for x, achievement in zip(x_positions, sorted_achievements):
            try:
                icon_path = f"icons/{achievement}.png"
                if os.path.exists(icon_path):
                    icon = plt.imread(icon_path)

                    # Create a circular mask
                    height, width = icon.shape[:2]
                    height += 1
                    width += 1
                    center = (width // 2, height // 2)
                    radius = min(width, height) // 2
                    Y, X = np.ogrid[:height, :width]
                    dist_from_center = np.sqrt(
                        (X - center[0]) ** 2 + (Y - center[1]) ** 2
                    )
                    circular_mask = dist_from_center <= radius

                    # Create background array with circular mask
                    bg = np.zeros((height, width, 4))
                    bg[circular_mask] = [1, 1, 1, 0.7]  # White with alpha

                    # Create background annotation box with circular background
                    bg_box = OffsetImage(bg, zoom=0.25)
                    bg_box.image.axes = icon_ax

                    bg_ab = AnnotationBbox(
                        bg_box,
                        (x, 0.95 if layout == "stacked" else 0.5),
                        frameon=False,
                        box_alignment=(0.5, 0.5),
                        zorder=2,  # Below the icon
                    )
                    icon_ax.add_artist(bg_ab)

                    # Create icon annotation box
                    icon_box = OffsetImage(icon, zoom=0.25)
                    ab = AnnotationBbox(
                        icon_box,
                        (x, 0.95 if layout == "stacked" else 0.5),
                        frameon=False,
                        box_alignment=(0.5, 0.5),
                        zorder=3,  # Above the background
                    )
                    icon_ax.add_artist(ab)
            except Exception as e:
                print(f"Failed to add icon for {achievement}: {e}")

        # Add complexity brackets
        self.add_complexity_brackets(
            ax.figure,
            icon_ax,
            sorted_achievements,
            x_positions,
            achievement_complexities,
            fontsize,
        )

        # Add legend
        # ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left')

    def _plot_production_volumes(
        self,
        axes,
        model_names,
        step_size=25,
        step_proportion=0.9,
        show_fractions=False,
        use_log_scale=False,
        min_total_volume=1e-6,
        min_complexity=2,
        cumulative=True,
        groupby_complexity=False,
        unified_y_axis=True,
        chart_type="line",
        fontsize=16,
        layout="stacked",
    ):
        """Helper method to plot production volumes on given axes using median values"""
        from collections import namedtuple, defaultdict
        import numpy as np

        StackItem = namedtuple("StackItem", ["node", "step"])

        all_items = set()
        model_versions_found = defaultdict(list)

        # Initial setup remains the same...
        for model_name in model_names:
            if model_name not in self.model_groups:
                print(f"Model {model_name} not found in model_groups")
                continue

            model_group = self.model_groups[model_name]
            for version_id in model_group.version_ids:
                if version_id not in self.versions:
                    print(
                        f"Version {version_id} for model {model_name} not found in data"
                    )
                    continue

                model_versions_found[model_name].append(version_id)
                for root in self.versions[version_id]["nodes"]:
                    stack = [StackItem(node=root, step=0)]
                    while stack:
                        current = stack.pop()
                        all_items.update(current.node.static_achievements.keys())
                        all_items.update(current.node.dynamic_achievements.keys())
                        for child in current.node.children:
                            stack.append(StackItem(node=child, step=current.step + 1))

        # Remove water and steam
        all_items = {item for item in all_items if item not in ("water", "steam")}

        # Get complexities and sort items (same as before)
        item_complexities = {}
        for model_name in model_names:
            if model_name not in model_versions_found:
                continue
            for version in model_versions_found[model_name]:
                if version in self.achievements:
                    for achievement in self.achievements[version]:
                        if achievement.item_name in all_items:
                            item_complexities[achievement.item_name] = (
                                achievement.ingredients
                            )

        sorted_items = sorted(
            [
                item
                for item in all_items
                if item_complexities.get(item, 0) >= min_complexity
            ],
            key=lambda x: item_complexities.get(x, 0),
        )

        if not sorted_items:
            print(f"No items found with complexity >= {min_complexity}")
            return

        # Setup for grouping and colors remains the same...
        if groupby_complexity:
            complexity_groups = {}
            for item in sorted_items:
                complexity = item_complexities[item]
                if complexity not in complexity_groups:
                    complexity_groups[complexity] = []
                complexity_groups[complexity].append(item)

            unique_complexities = sorted(complexity_groups.keys())
            color_map = plt.cm.viridis(np.linspace(0, 1, len(unique_complexities)))
            complexity_colors = dict(zip(unique_complexities, color_map))
        else:
            color_map = plt.cm.viridis(np.linspace(0, 1, len(sorted_items)))

        global_ymin = float("inf")
        global_ymax = float("-inf")

        # Process each model
        for ax_idx, model_name in enumerate(model_names):
            print(f"\nPlotting for axis {ax_idx}, model {model_name}")
            if ax_idx >= len(axes):
                print(f"ERROR: Not enough axes for model {model_name}")
                continue

            model_group = self.model_groups[model_name]

            # Initialize production tracking with lists for calculating medians
            production_by_step = defaultdict(lambda: defaultdict(list))

            # Get all possible steps
            all_steps = set()
            for version in model_group.version_ids:
                if version not in self.versions:
                    continue

                for root in self.versions[version]["nodes"]:
                    stack = [StackItem(node=root, step=0)]
                    while stack:
                        current = stack.pop()
                        step_bucket = (current.step // step_size) * step_size
                        all_steps.add(step_bucket)
                        for child in current.node.children:
                            stack.append(StackItem(node=child, step=current.step + 1))

            all_steps = sorted(all_steps)

            if cumulative:
                # Track cumulative values for each trajectory separately
                for version in model_group.version_ids:
                    if version not in self.versions:
                        continue

                    for root in self.versions[version]["nodes"]:
                        trajectory_cumulative = defaultdict(int)
                        stack = [StackItem(node=root, step=0)]

                        while stack:
                            current = stack.pop()
                            step_bucket = (current.step // step_size) * step_size

                            # Update cumulative totals for this trajectory
                            for achievements_dict in [
                                current.node.static_achievements,
                                current.node.dynamic_achievements,
                            ]:
                                for item, quantity in achievements_dict.items():
                                    if item in sorted_items:
                                        trajectory_cumulative[item] += (
                                            quantity  # / self.labels_count[self.versions[version]['label'].split(" ")[0]]
                                        )

                            # Store the cumulative values for this trajectory at this step
                            for item, total in trajectory_cumulative.items():
                                production_by_step[step_bucket][item].append(total)
                                # Update future steps with the same cumulative value
                                for future_step in range(
                                    step_bucket + step_size,
                                    max(all_steps) + step_size,
                                    step_size,
                                ):
                                    production_by_step[future_step][item].append(total)

                            for child in current.node.children:
                                stack.append(
                                    StackItem(node=child, step=current.step + 1)
                                )

            else:
                # Non-cumulative tracking
                for version in model_group.version_ids:
                    if version not in self.versions:
                        continue

                    for root in self.versions[version]["nodes"]:
                        stack = [StackItem(node=root, step=0)]
                        while stack:
                            current = stack.pop()
                            step_bucket = (current.step // step_size) * step_size

                            step_production = defaultdict(int)
                            for achievements_dict in [
                                current.node.static_achievements,
                                current.node.dynamic_achievements,
                            ]:
                                for item, quantity in achievements_dict.items():
                                    if item in sorted_items:
                                        step_production[item] += (
                                            quantity  # / len(self.versions[version]['nodes'])
                                        )

                            # Store the production values for this trajectory at this step
                            for item, quantity in step_production.items():
                                production_by_step[step_bucket][item].append(quantity)

                            for child in current.node.children:
                                stack.append(
                                    StackItem(node=child, step=current.step + 1)
                                )

            # Calculate median values
            total_values = {}
            for step in all_steps:
                total_values[step] = {}
                for item in sorted_items:
                    values = production_by_step[step][item]
                    if values:
                        # Sum all values instead of taking the mean
                        total_values[step][item] = max(values)  # np.mean(values)
                    else:
                        total_values[step][item] = 0

            # Process values for plotting using median values
            processed_values = {}
            if groupby_complexity:
                for complexity in complexity_groups:
                    values = np.zeros(len(all_steps))
                    for item in complexity_groups[complexity]:
                        item_values = [
                            total_values[step].get(item, 0) for step in all_steps
                        ]
                        values += item_values
                    processed_values[complexity] = values
            else:
                for item in sorted_items:
                    values = [total_values[step].get(item, 0) for step in all_steps]
                    if use_log_scale:
                        values = [np.log10(v + 1) for v in values]
                    processed_values[item] = values

            ax = axes[ax_idx]
            ax.set_aspect("auto")

            def format_large_number(x, pos):
                """Format large numbers with commas for readability"""
                if abs(x) >= 1e6:
                    return f"{int(x / 1e6):,}M"
                elif abs(x) >= 1e3:
                    return f"{int(x / 1e3):,}K"
                else:
                    return f"{int(x):,}"

            # Additionally, to ensure larger numbers don't use scientific notation:
            # ax.ticklabel_format(style='plain', axis='x')

            if groupby_complexity:
                values_for_stack = [
                    processed_values[complexity] for complexity in unique_complexities
                ]
                labels = [
                    f"Complexity {complexity}" for complexity in unique_complexities
                ]
                colors = [
                    complexity_colors[complexity] for complexity in unique_complexities
                ]
            else:
                values_for_stack = [processed_values[item] for item in sorted_items]
                labels = [f"{item}" for item in sorted_items]
                colors = color_map

            if chart_type.lower() == "line":
                stack_plot = ax.stackplot(  # noqa
                    all_steps,
                    values_for_stack,
                    labels=labels if ax_idx == len(model_names) - 1 else [],
                    colors=colors,
                    alpha=0.7,
                )
            else:  # 'bar' chart
                bottom = np.zeros(len(all_steps))
                for values, label, color in zip(values_for_stack, labels, colors):
                    ax.bar(
                        all_steps,
                        values,
                        bottom=bottom,
                        label=label if ax_idx == len(model_names) - 1 else None,
                        color=color,
                        alpha=0.7,
                        width=step_size * step_proportion,
                    )
                    bottom += values

            # Configure axis labels and appearance
            for ax_idx, ax in enumerate(axes):
                # Format axes consistently
                if use_log_scale:
                    ax.set_yscale("log")
                    ax.yaxis.set_major_formatter(plt.LogFormatter(base=10))
                    ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
                    ax.yaxis.set_minor_locator(
                        plt.LogLocator(base=10.0, subs=np.arange(2, 10))
                    )

                ax.set_title("")

                # Update global y-axis limits with this plot's limits
                ymin, ymax = ax.get_ylim()
                global_ymin = min(global_ymin, ymin)
                global_ymax = max(global_ymax, ymax)

                # Set consistent grid style
                ax.grid(True, axis="y", linestyle="--", alpha=0.3)
                ax.set_axisbelow(True)

                ax.xaxis.set_major_formatter(plt.FuncFormatter(format_large_number))
                ax.yaxis.set_major_formatter(plt.FuncFormatter(format_large_number))

                # Ensure x-axis limits are identical
                ax.set_xlim(min(all_steps), max(all_steps))

                # Set labels based on position
                if layout == "stacked":
                    if ax_idx == 0:
                        ax.set_ylabel("Item Production", fontsize=fontsize - 2)
                else:  # side-by-side layout
                    if ax_idx in [0, 2, 4]:
                        ax.set_ylabel("Item Production", fontsize=fontsize - 2)

                ax.set_xlabel("Steps", fontsize=fontsize - 2)

                # Add title with proper positioning
                if ax_idx < len(model_names):
                    title_text = self.model_groups[model_names[ax_idx]].label
                    color = self.model_groups[model_names[ax_idx]].color

                    # Get position for title
                    ax_pos = ax.get_position()
                    title_y = ax_pos.y1 - 0.03  # Move title above the plot

                    # Add colored dash
                    ax.figure.text(
                        ax_pos.x0 + (ax_pos.width * 0.02),
                        title_y,
                        "—",
                        color=color,
                        fontsize=fontsize + 4,  # Reduced from +8
                        fontweight="bold",
                        horizontalalignment="left",
                        verticalalignment="bottom",
                        zorder=10,
                    )

                    # Add title text
                    ax.figure.text(
                        ax_pos.x0 + (ax_pos.width * 0.08),  # Reduced from 0.12
                        title_y + 0.003,
                        title_text,
                        fontsize=fontsize - 4,  # Smaller to avoid overlap
                        horizontalalignment="left",
                        verticalalignment="bottom",
                        zorder=10,
                    )

            # ax.set_xlabel('Step', fontsize=fontsize - 2)
            # ax.tick_params(axis='both', which='major', labelsize=fontsize - 2)
            ax.grid(True, which="major", linestyle="-", alpha=0.2)
            ax.grid(True, which="minor", linestyle="--", alpha=0.1)

            # Set axis limits
            ax.set_xlim(min(all_steps), max(all_steps))
            if show_fractions:
                ax.set_ylim(0, 1)

            # Title placement
            title_text = model_group.label
            color = model_group.color

            # title_y = ylims[1] + (ylims[1] - ylims[0]) * 0.05
            title_y = ax.get_position().y1 - 0.04

            # ax.text(title_x, title_y, '—',
            #         color=color,
            #         fontsize=fontsize + 8,
            #         fontweight='bold',
            #         horizontalalignment='left',
            #         verticalalignment='bottom',
            #         transform=ax.transData,
            #         zorder=10)
            #
            # ax.text(title_x + (xlims[1] - xlims[0]) * 0.05, title_y,
            #         title_text,
            #         fontsize=fontsize - 2,
            #         horizontalalignment='left',
            #         verticalalignment='bottom',
            #         transform=ax.transData,
            #         zorder=10)
            #
            # ax.margins(y=0.2)
            # Place title using figure coordinates instead of data coordinates
            # ax.figure.text(
            #     ax.get_position().x0 + (ax.get_position().width * 0.02),  # x position
            #     title_y,  # y position
            #     '—',
            #     color=color,
            #     fontsize=fontsize + 8,
            #     fontweight='bold',
            #     horizontalalignment='left',
            #     verticalalignment='bottom',
            #     zorder=10
            # )
            #
            # ax.figure.text(
            #     ax.get_position().x0 + (ax.get_position().width * 0.12),  # x position
            #     title_y + 0.005 ,  # y position
            #     title_text,
            #     fontsize=fontsize - 2,
            #     horizontalalignment='left',
            #     verticalalignment='bottom',
            #     zorder=10
            # )

            # Set scientific notation for y-axis when using log scale
            if use_log_scale:
                ax.set_yscale("log")
                ax.yaxis.set_major_formatter(plt.LogFormatter(base=10))

                # Ensure we use standard log ticks
                ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
                ax.yaxis.set_minor_locator(
                    plt.LogLocator(base=10.0, subs=np.arange(2, 10))
                )

            ymin, ymax = ax.get_ylim()
            global_ymin = min(global_ymin, ymin)
            global_ymax = max(global_ymax, ymax)

            ax.margins(y=0.01)

        # After all plots are done, set unified y-axis if requested
        # if unified_y_axis and not show_fractions:
        #     for ax in axes:
        #         ax.set_ylim(0, global_ymax)
        if unified_y_axis and not show_fractions:
            # Add extra space to avoid clipping
            padding = (global_ymax - global_ymin) * 0.1
            for ax in axes:
                ax.set_ylim(global_ymin, global_ymax + padding)

        # Add legend
        if not groupby_complexity:
            if layout == "stacked":
                create_custom_legend_with_icons(
                    axes[-1],
                    sorted_items,
                    item_complexities,
                    colors,
                    fontsize,
                    layout == "stacked",
                )
            else:
                create_custom_legend_with_icons(
                    axes[-3],
                    sorted_items,
                    item_complexities,
                    colors,
                    fontsize,
                    layout == "stacked",
                )


async def main():
    # Example usage
    db_client = DBClient(
        max_conversation_length=40,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )

    icons_path = "/data/icons/early_icons"

    for x_axis in ["steps", "ticks"]:
        viz = ProgressionVisualizer(
            db_client,
            icons_path,
            x_axis,
            use_log_scale=x_axis != "ticks",
            use_value_gdp=False,
            recipes_file="/data/recipes/recipes.jsonl",
        )

        # Configure model groups and their versions
        model_groups = {
            # 'Claude': [492],  # Single version for Claude
            # 'GPT-4': [490],  # Single version for GPT-4
            # 'GPT-4-Mini': [505],  # Using newer version
            # 'LLaMA-70B': [488]
            "Deepseek-v3": [555, 556, 557, 558],
            "GPT-4o-Mini": [548, 575, 576, 577, 578],
            "LLaMA-70B": [550, 600, 601, 602],  # 599
            "Gemini-2": [595, 596, 597, 598, 805, 806, 807, 808],
            "GPT-4o": [551, 552, 553, 554, 564, 797, 798, 799, 800],
            "Claude": [559, 560, 561, 562, 574, 801, 802, 803, 804],
        }

        # Define labels for each model
        model_labels = {
            "Deepseek-v3": "Deepseek-v3",
            "GPT-4o-Mini": "GPT-4-Mini",
            "LLaMA-70B": "LLaMA-70B",
            "Gemini-2": "Gemini-2",
            "GPT-4o": "GPT-4",
            "Claude": "Claude",
        }

        # Load data using new model grouping approach
        viz.load_data(model_groups, model_labels)

        achievement_params = {"render_complexity": False, "minimum_complexity": 2}

        production_params = {
            "step_size": 25,
            "cumulative": True,
            "show_fractions": False,
            "use_log_scale": False,
            "min_complexity": 2,
            "groupby_complexity": False,
            "unified_y_axis": True,
            "chart_type": "line",
        }

        # Generate visualizations using model names instead of version numbers
        model_names = [
            "Deepseek-v3",
            "GPT-4o-Mini",
            "LLaMA-70B",
            "Gemini-2",
            "GPT-4o",
            "Claude",
        ]  # Same order as before

        viz.export_combined_visualization(
            "combined_analysis_stacked.png",
            model_names=model_names,
            achievement_params=achievement_params,
            production_params=production_params,
            layout="stacked",
        )

        viz.export_combined_visualization(
            "combined_analysis_side.png",
            model_names=model_names,
            achievement_params=achievement_params,
            production_params=production_params,
            layout="side-by-side",
        )


if __name__ == "__main__":
    asyncio.run(main())
