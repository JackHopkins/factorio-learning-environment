import asyncio
import json
import pickle
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal

import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from matplotlib import image as mpimg

from search.db_client import DBClient
from search.independent_runs.value_calculator import ValueCalculator

load_dotenv()

@dataclass
class Node:
    """Represents a node in the MCTS tree"""
    id: int
    parent_id: Optional[int]
    metrics: Dict  # Contains 'value', 'ticks'
    static_achievements: Dict[str, int]
    dynamic_achievements: Dict[str, int]
    children: List['Node']

    def to_dict(self):
        """Convert Node to dictionary for caching"""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'metrics': self.metrics,
            'static_achievements': self.static_achievements,
            'dynamic_achievements': self.dynamic_achievements,
            'children_ids': [child.id for child in self.children]
        }

    @staticmethod
    def from_dict(data: Dict, nodes_dict: Dict[int, 'Node']):
        """Create Node from dictionary and populate children from nodes_dict"""
        node = Node(
            id=data['id'],
            parent_id=data['parent_id'],
            metrics=data['metrics'],
            static_achievements=data['static_achievements'],
            dynamic_achievements=data['dynamic_achievements'],
            children=[]
        )
        node.children = [nodes_dict[child_id] for child_id in data['children_ids']]
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

from matplotlib.legend_handler import HandlerBase
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os


class IconColorHandler(HandlerBase):
    """Custom handler to create legend entries with both color patches and icons"""

    def __init__(self, item_name, color, alpha=0.7):
        self.item_name = item_name
        self.color = color
        self.alpha = alpha
        super().__init__()

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        artists = []

        # Create the color rectangle
        rect = patches.Rectangle(
            xy=(0, 0),
            width=width * 0.6,  # Make color patch smaller to leave room for icon
            height=height,
            facecolor=self.color,
            alpha=self.alpha,
            transform=trans
        )
        artists.append(rect)

        # Try to add the icon
        try:
            icon_path = f"icons/{self.item_name}.png"
            if os.path.exists(icon_path):
                # Load and create icon as image
                img = mpimg.imread(icon_path)
                icon = plt.imshow(img,
                                  extent=[width * 0.7, width * 0.7 + height, 0, height],
                                  transform=trans,
                                  aspect='equal',
                                  clip_on=True)
                artists.append(icon)
        except Exception as e:
            print(f"Failed to add icon for {self.item_name}: {e}")

        return artists


def create_custom_legend_with_icons(ax, sorted_items, item_complexities, colors, fontsize, stacked):
    """Create a custom legend by manually placing elements"""


    # Create a new axes for the legend
    legend_bbox = ax.get_position()
    legend_ax = ax.figure.add_axes([
        legend_bbox.x1 + 0.01,  # x position
        legend_bbox.y0,  # y position
        0.1,  # width
        legend_bbox.height  # height
    ])
    legend_ax.axis('off')  # Hide axes

    # Title
    legend_ax.text(0, 0.95, 'Items',# (sorted by complexity)',
                   fontsize=fontsize-2, transform=legend_ax.transAxes)

    # Use full height of legend for spacing
    num_items = len(sorted_items)
    y_spacing = 1 / (num_items+1)  # Remove the +1 to use more space

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
            transform=legend_ax.transAxes
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
                    (0.2, y_pos + y_spacing * 0.35),  # Adjusted position for new spacing
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

class ProgressionVisualizer:
    """Creates publication-quality visualizations of agent progression"""

    VERTICAL_SPACING_PIXELS = 12
    HORIZONTAL_OFFSET_PIXELS = 0

    def __init__(self, db_client, icons_path: str, x_axis: Literal["steps", "ticks"] = "steps",
                 cache_file: str = "viz_cache.pkl", x_base: float = 10, y_base: float = 10, use_value_gdp=False,
                 recipes_file="recipes.jsonl", use_log_scale: bool = True):  # Added use_log_scale parameter
        self.db_client = db_client
        self.icons_path = icons_path
        self.x_axis = x_axis
        self.cache_file = cache_file
        self.x_base = x_base
        self.y_base = y_base
        self.versions = {}
        self.achievements = defaultdict(list)

        # versions = {
        #     492: "Claude",
        #     490: "GPT-4",
        #
        #     505: "GPT-4-Mini",
        #     488: "LLaMA-70B",
        #
        # }
        self.colors = ['#228833', '#CCBB44',  '#EE6677', '#4477AA' ]
        #self.colors = ['#4477AA', '#EE6677', '#228833', '#CCBB44']
        self.use_value_gdp = use_value_gdp
        self.value_calculator = ValueCalculator(recipes_file) if use_value_gdp else None
        self.use_log_scale = use_log_scale  # Store the scale preference

    def _serialize_version_data(self):
        """Convert version data to cacheable format"""
        serialized = {}
        for version, data in self.versions.items():
            nodes_dict = {}
            for root in data['nodes']:
                stack = [root]
                while stack:
                    node = stack.pop()
                    nodes_dict[node.id] = node.to_dict()
                    stack.extend(node.children)

            serialized[version] = {
                'nodes_dict': nodes_dict,
                'root_ids': [root.id for root in data['nodes']],
                'label': data['label']
            }
        return serialized

    def _deserialize_version_data(self, serialized):
        """Restore version data from cached format"""
        for version, data in serialized.items():
            # First create all Node objects without children
            nodes_dict = {}
            for node_id, node_data in data['nodes_dict'].items():
                nodes_dict[node_id] = Node(
                    id=node_data['id'],
                    parent_id=node_data['parent_id'],
                    metrics=node_data['metrics'],
                    static_achievements=node_data['static_achievements'],
                    dynamic_achievements=node_data['dynamic_achievements'],
                    children=[]
                )

            # Then populate children
            for node_id, node_data in data['nodes_dict'].items():
                nodes_dict[node_id].children = [nodes_dict[child_id] for child_id in node_data['children_ids']]

            self.versions[version] = {
                'nodes': [nodes_dict[root_id] for root_id in data['root_ids']],
                'label': data['label']
            }

    def load_data(self, versions: List[int], labels: Dict[int, str]):
        """Load and process data for multiple versions, using cache if available"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if cached_data.get('versions') == versions:
                        self._deserialize_version_data(cached_data['data'])
                        self.achievements = cached_data['achievements']
                        return
            except Exception as e:
                print(f"Error loading cache: {e}")
                os.remove(self.cache_file)

        for version in versions:
            print(f"\nLoading version {version}")
            nodes = self._load_version_from_db(version)
            if nodes:
                gdps = [self._calculate_gdp(root) for root in nodes]
                self.versions[version] = {
                    'nodes': nodes,
                    'label': f"{labels[version]}"# (~GDP: {np.mean(gdps):.1f})"
                }
                self._process_achievements(version)


        # Cache the loaded data
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'versions': versions,
                    'data': self._serialize_version_data(),
                    'achievements': self.achievements
                }, f)
        except Exception as e:
            print(f"Error saving cache: {e}")



    def _load_version_from_db(self, version: int) -> List[Node]:
        """Load all trajectories for a version from database"""
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, parent_id, achievements_json, value, ticks 
                    FROM programs WHERE version = %s
                """, (version,))
                rows = cur.fetchall()

        # Build node tree
        nodes = {}
        roots = []
        for id, parent_id, achievements, value, ticks in rows:
            node = Node(
                id=id,
                parent_id=parent_id,
                metrics={'value': value or 0, 'ticks': ticks or 0},
                static_achievements=achievements.get('static', {}),
                dynamic_achievements=achievements.get('dynamic', {}),
                children=[]
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
                total += node.metrics['value']
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

        with open('recipes.jsonl', 'r') as f:
            recipes = {r['name']: r for r in map(json.loads, f)}

        seen = set()
        version_achievements = []

        for root in self.versions[version]['nodes']:
            # Initialize path tracking for cumulative calculations
            cumulative_ticks = 0
            current_path = []
            stack = [(root, 0, [])]  # (node, depth, path_to_node)

            while stack:
                node, depth, path = stack.pop()

                # Update current path and cumulative ticks
                current_path = path + [node]

                # Calculate cumulative ticks for the current path
                path_ticks = sum(n.metrics['ticks'] for n in current_path)

                # Process achievements
                for achievements_dict, is_dynamic in [(node.static_achievements, False),
                                                      (node.dynamic_achievements, True)]:
                    for item, quantity in achievements_dict.items():
                        if item not in seen:
                            print(f"\nProcessing achievement: {item}")
                            print(f"Original ticks: {path_ticks}, depth: {depth}")

                            version_achievements.append(Achievement(
                                depth=depth,
                                ticks=path_ticks,
                                item_name=item,
                                ingredients=self._count_ingredients(recipes.get(item, {})),
                                is_dynamic=is_dynamic
                            ))
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
            seen.add(item['name'])
            for ingredient in item.get('ingredients', []):
                traverse(ingredient)

        traverse(recipe)
        return len(seen) - 1

    def add_complexity_brackets(self, fig, icon_ax, achievements, x_positions, complexities, fontsize=12):
        bracket_ax = fig.add_axes(icon_ax.get_position())
        bracket_ax.set_xlim(icon_ax.get_xlim())
        bracket_ax.set_ylim(0, 1)
        bracket_ax.axis('off')

        current_complexity = None
        start_x = None
        for i, (achievement, x) in enumerate(zip(achievements, x_positions)):
            complexity = complexities.get(achievement, 0)
            if complexity != current_complexity:
                if current_complexity is not None:
                    self.draw_bracket(bracket_ax, start_x, x_positions[i - 1], current_complexity, fontsize)
                current_complexity = complexity
                start_x = x

        # Draw the last bracket
        if current_complexity is not None:
            self.draw_bracket(bracket_ax, start_x, x_positions[-1], current_complexity, fontsize)

    def draw_bracket(self, ax, start_x, end_x, complexity, fontsize=12):
        mid_x = (start_x + end_x) / 2
        bracket_height = 0.4
        text_height = -0.4  # Adjust this value to position the text lower if needed

        # Draw the bracket
        ax.plot([start_x, start_x, end_x, end_x],
                [0, -bracket_height, -bracket_height, 0],
                color='black', linewidth=1)

        # Add the complexity text
        ax.text(mid_x, text_height, f'{complexity}',
                ha='center', va='top', fontsize=fontsize-2,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))

        # Extend the y-axis limit to show the full bracket and text
        ax.set_ylim(min(ax.get_ylim()[0], text_height - 0.1), ax.get_ylim()[1])

    def export_combined_visualization(self, output_file: str, versions: List[int],
                                      achievement_params: dict = None,
                                      production_params: dict = None,
                                      layout: Literal["side-by-side", "stacked"] = "stacked"):
        """
        Create a combined visualization with achievement stack and production volumes.

        Args:
            output_file: Path to save the output figure
            versions: List of version numbers to plot
            achievement_params: Dictionary of parameters for achievement visualization
            production_params: Dictionary of parameters for production volumes visualization
            layout: Either "side-by-side" or "stacked" layout
        """
        # Set default parameters if not provided
        if achievement_params is None:
            achievement_params = {
                'render_complexity': False,
                'minimum_complexity': 2
            }

        if production_params is None:
            production_params = {
                'step_size': 50,
                'step_proportion': 0.9,
                'show_fractions': False,
                'use_log_scale': False,
                'min_total_volume': 1e-6,
                'min_complexity': 2,
                'cumulative': True,
                'groupby_complexity': False,
                'unified_y_axis': True,
                'chart_type': 'line'
            }

        # Set figure parameters
        plt.rcParams['figure.dpi'] = 150
        plt.rcParams['savefig.dpi'] = 300

        # Create figure with layout-dependent size
        if layout == "side-by-side":
            fig = plt.figure(figsize=(16, 8))
            # Create side-by-side grid
            gs = fig.add_gridspec(2, 3, width_ratios=[2, 1, 1],
                                  height_ratios=[1, 1],
                                  left=0.05, right=0.95,
                                  bottom=0.1, top=0.9,
                                  wspace=0.15, hspace=0.2)

            # Create axes for achievement stack (spans both rows)
            achievement_ax = fig.add_subplot(gs[:, 0])
            icon_ax = fig.add_axes(achievement_ax.get_position())
            icon_ax.set_position([achievement_ax.get_position().x0,
                                  achievement_ax.get_position().y0 - 0.05,
                                  achievement_ax.get_position().width,
                                  0.05])

            # Create axes for production volumes (2x2 grid)
            production_axes = [
                fig.add_subplot(gs[0, 1]),  # top left
                fig.add_subplot(gs[0, 2]),  # top right
                fig.add_subplot(gs[1, 1]),  # bottom left
                fig.add_subplot(gs[1, 2])  # bottom right
            ]

        else:  # stacked layout
            fig = plt.figure(figsize=(16, 6))
            # Create stacked grid
            gs = fig.add_gridspec(2, 4, height_ratios=[0.6, 0.6],
                                  left=0.05, right=0.95,
                                  bottom=0.1, top=0.9,
                                  wspace=0.15, hspace=0.25)

            # Create axes for achievement stack (spans all columns in first row)
            achievement_ax = fig.add_subplot(gs[0, :])
            icon_ax = fig.add_axes(achievement_ax.get_position())
            icon_ax.set_position([achievement_ax.get_position().x0,
                                  achievement_ax.get_position().y0 - 0.05,
                                  achievement_ax.get_position().width,
                                  0.05])

            # Create axes for production volumes (1x4 grid in second row)
            production_axes = [
                fig.add_subplot(gs[1, 0]),  # left
                fig.add_subplot(gs[1, 1]),  # middle-left
                fig.add_subplot(gs[1, 2]),  # middle-right
                fig.add_subplot(gs[1, 3])  # right
            ]

        # Plot achievement stack
        self._plot_achievement_stack(achievement_ax, icon_ax, versions,layout=layout, **achievement_params)

        # Plot production volumes
        self._plot_production_volumes(production_axes, versions, layout=layout, **production_params)

        # Save figure
        plt.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close()

    def _plot_achievement_stack(self, ax, icon_ax, versions, render_complexity=False, minimum_complexity=2, fontsize=16, layout="stacked"):
        """Helper method to plot achievement stack on given axes"""
        from collections import defaultdict

        # Define raw resources that should appear first
        RAW_RESOURCES = {'coal', 'copper-ore', 'iron-ore', 'water', 'stone', 'wood'}

        # Get achievement counts and complexities
        model_achievement_counts = {}
        all_achievements = set()
        achievement_complexities = {}

        # Count total occurrences of each achievement across all runs
        for version in versions:
            counts = defaultdict(int)

            # For each root node (representing a run)
            for root in self.versions[version]['nodes']:
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

            model_achievement_counts[version] = counts

            # Get complexities
            for achievement in self.achievements[version]:
                if achievement.item_name in RAW_RESOURCES:
                    achievement_complexities[achievement.item_name] = 0
                else:
                    achievement_complexities[achievement.item_name] = achievement.ingredients

        # Filter achievements based on minimum complexity
        if minimum_complexity > 0:
            filtered_achievements = {item for item in all_achievements
                                     if achievement_complexities.get(item, 0) >= minimum_complexity}
            all_achievements = filtered_achievements
            for version in model_achievement_counts:
                filtered_counts = {item: count for item, count in model_achievement_counts[version].items()
                                   if item in filtered_achievements}
                model_achievement_counts[version] = filtered_counts

        # Sort achievements
        def sort_key(item):
            if item in RAW_RESOURCES and achievement_complexities.get(item, 0) < minimum_complexity:
                return (0, item)
            return (1, achievement_complexities.get(item, 0), item)

        sorted_achievements = sorted(all_achievements, key=sort_key)

        # Calculate x positions for achievements
        x_positions = np.arange(len(sorted_achievements))
        bar_width = 0.2

        # Plot bars for each model
        for idx, (version, counts) in enumerate(model_achievement_counts.items()):
            color = self.colors[idx % len(self.colors)]
            x_offset = (idx - (len(versions) - 1) / 2) * bar_width

            heights = [counts.get(ach, 0) for ach in sorted_achievements]
            nonzero_mask = np.array(heights) > 0
            if any(nonzero_mask):
                ax.bar(x_positions + x_offset,
                       heights,
                       bar_width, color=color, alpha=0.7,
                       label=self.versions[version]['label'])

        # Add separator after raw resources
        raw_resources_shown = len([r for r in RAW_RESOURCES if r in sorted_achievements])
        if raw_resources_shown > 0:
            ax.axvline(raw_resources_shown - 0.5, color='gray', linestyle='-', alpha=0.5)

        # Add separators between complexity groups
        prev_complexity = None
        for i, ach in enumerate(sorted_achievements[raw_resources_shown:], raw_resources_shown):
            complexity = achievement_complexities.get(ach, 0)
            if prev_complexity is not None and complexity != prev_complexity:
                ax.axvline(i - 0.5, color='gray', linestyle='--', alpha=0.3)
            prev_complexity = complexity

        # Configure main axes
        ax.set_yscale('log')

        ax.set_ylabel('Item Production', fontsize=fontsize-2)  # increase from default
        #ax.set_xlabel('Item Complexity', fontsize=fontsize)
        ax.tick_params(axis='both', which='major', labelsize=fontsize-2)  # increase tick label size

        ax.set_xticks([])
        ax.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_ylim(bottom=0.9)

        # Calculate the exact x-axis limits based on data and bar width
        num_versions = len(versions)
        total_width = bar_width * num_versions * 1.1
        x_min = -total_width / 2
        x_max = len(sorted_achievements) - 1 + total_width / 2
        ax.set_xlim(x_min, x_max)

        # Configure and populate icon axis
        icon_ax.set_xlim(ax.get_xlim())
        icon_ax.set_ylim(0, 1)
        icon_ax.axis('off')

        # Add icons
        for x, achievement in zip(x_positions, sorted_achievements):
            try:
                icon_path = f"icons/{achievement}.png"
                if os.path.exists(icon_path):
                    icon = plt.imread(icon_path)

                    # Create a circular mask
                    height, width = icon.shape[:2]
                    height+=1
                    width+=1
                    center = (width // 2, height // 2)
                    radius = min(width, height) // 2
                    Y, X = np.ogrid[:height, :width]
                    dist_from_center = np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)
                    circular_mask = dist_from_center <= radius

                    # Create background array with circular mask
                    bg = np.zeros((height, width, 4))
                    bg[circular_mask] = [1, 1, 1, 0.7]  # White with alpha

                    # Create background annotation box with circular background
                    bg_box = OffsetImage(bg, zoom=0.25)
                    bg_box.image.axes = icon_ax

                    bg_ab = AnnotationBbox(
                        bg_box,
                        (x, 0.95 if layout == 'stacked' else 0.5),
                        frameon=False,
                        box_alignment=(0.5, 0.5),
                        zorder=2  # Below the icon
                    )
                    icon_ax.add_artist(bg_ab)

                    # Create icon annotation box
                    icon_box = OffsetImage(icon, zoom=0.25)
                    ab = AnnotationBbox(
                        icon_box,
                        (x, 0.95 if layout == 'stacked' else 0.5),
                        frameon=False,
                        box_alignment=(0.5, 0.5),
                        zorder=3  # Above the background
                    )
                    icon_ax.add_artist(ab)
            except Exception as e:
                print(f"Failed to add icon for {achievement}: {e}")

        # Add complexity brackets
        self.add_complexity_brackets(ax.figure, icon_ax, sorted_achievements, x_positions, achievement_complexities, fontsize)

        # Add legend
        #ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left')


    def _plot_production_volumes(self, axes, versions, step_size=25, step_proportion=0.9,
                                 show_fractions=False, use_log_scale=False,
                                 min_total_volume=1e-6, min_complexity=2,
                                 cumulative=True, groupby_complexity=False,
                                 unified_y_axis=True, chart_type='line', fontsize=16, layout="stacked"):
        """Helper method to plot production volumes on given axes"""
        from collections import namedtuple
        StackItem = namedtuple('StackItem', ['node', 'step'])

        # Collect all items across all versions
        all_items = set()
        for version in versions:
            if version not in self.versions:
                print(f"Version {version} not found in data")
                continue

            for root in self.versions[version]['nodes']:
                stack = [StackItem(node=root, step=0)]
                while stack:
                    current = stack.pop()
                    all_items.update(current.node.static_achievements.keys())
                    all_items.update(current.node.dynamic_achievements.keys())
                    for child in current.node.children:
                        stack.append(StackItem(node=child, step=current.step + 1))

        # Remove water and steam
        all_items = {item for item in all_items if item not in ('water', 'steam')}

        # Get complexities for all items
        item_complexities = {}
        for version in versions:
            for achievement in self.achievements[version]:
                if achievement.item_name in all_items:
                    item_complexities[achievement.item_name] = achievement.ingredients

        # Filter and sort items by complexity
        sorted_items = sorted(
            [item for item in all_items if item_complexities.get(item, 0) >= min_complexity],
            key=lambda x: item_complexities.get(x, 0)
        )

        if not sorted_items:
            print(f"No items found with complexity >= {min_complexity}")
            return

        # Group items by complexity if requested
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

        # Track global y-axis limits
        global_ymin = float('inf')
        global_ymax = float('-inf')

        # Process each version
        for ax_idx, version in enumerate(versions):
            if version not in self.versions:
                continue

            # Initialize production tracking
            production_by_step = defaultdict(lambda: defaultdict(int))
            num_trajectories = len(self.versions[version]['nodes'])

            # Get all possible steps
            all_steps = set()
            for root in self.versions[version]['nodes']:
                stack = [StackItem(node=root, step=0)]
                while stack:
                    current = stack.pop()
                    step_bucket = (current.step // step_size) * step_size
                    all_steps.add(step_bucket)
                    for child in current.node.children:
                        stack.append(StackItem(node=child, step=current.step + 1))
            all_steps = sorted(all_steps)

            if cumulative:
                # Initialize tracking for cumulative values
                max_cumulative_by_step = defaultdict(lambda: defaultdict(int))

                # Process each root node
                for root in self.versions[version]['nodes']:
                    # Track cumulative values for this trajectory
                    trajectory_cumulative = defaultdict(int)
                    stack = [StackItem(node=root, step=0)]

                    while stack:
                        current = stack.pop()
                        step_bucket = (current.step // step_size) * step_size

                        # Update cumulative totals with static achievements
                        for item, quantity in current.node.static_achievements.items():
                            if item in sorted_items:
                                trajectory_cumulative[item] += quantity

                        # Update cumulative totals with dynamic achievements
                        for item, quantity in current.node.dynamic_achievements.items():
                            if item in sorted_items:
                                trajectory_cumulative[item] += quantity

                        # Update max cumulative values for current and future step buckets
                        for item in trajectory_cumulative:
                            total = trajectory_cumulative[item]
                            # Update current step bucket
                            max_cumulative_by_step[step_bucket][item] = max(
                                max_cumulative_by_step[step_bucket][item],
                                total
                            )

                            # Update all future step buckets
                            for future_step in range(step_bucket + step_size, max(all_steps) + step_size, step_size):
                                max_cumulative_by_step[future_step][item] = max(
                                    max_cumulative_by_step[future_step][item],
                                    total
                                )

                        # Add children to stack
                        for child in current.node.children:
                            stack.append(StackItem(node=child, step=current.step + 1))

                # Use the max cumulative values for production
                production_by_step = max_cumulative_by_step

            else:
                # Non-cumulative logic
                for root in self.versions[version]['nodes']:
                    stack = [StackItem(node=root, step=0)]
                    while stack:
                        current = stack.pop()
                        step_bucket = (current.step // step_size) * step_size

                        for item, quantity in current.node.static_achievements.items():
                            if item in sorted_items:
                                production_by_step[step_bucket][item] += quantity

                        for item, quantity in current.node.dynamic_achievements.items():
                            if item in sorted_items:
                                production_by_step[step_bucket][item] += quantity

                        for child in current.node.children:
                            stack.append(StackItem(node=child, step=current.step + 1))

                # Average if not cumulative
                if not cumulative:
                    for step in production_by_step:
                        for item in production_by_step[step]:
                            production_by_step[step][item] /= num_trajectories

            # Process values for plotting
            processed_values = {}
            raw_values = {}

            if groupby_complexity:
                for complexity in complexity_groups:
                    values = np.zeros(len(all_steps))
                    raw_group_values = np.zeros(len(all_steps))
                    for item in complexity_groups[complexity]:
                        item_values = [production_by_step[step].get(item, 0) for step in all_steps]
                        values += item_values
                        raw_group_values += item_values
                    processed_values[complexity] = values
                    raw_values[complexity] = raw_group_values
            else:
                for item in sorted_items:
                    values = [production_by_step[step].get(item, 0) for step in all_steps]
                    raw_values[item] = values.copy()
                    processed_values[item] = values

                if show_fractions:
                    totals = np.zeros(len(all_steps))
                    for key in processed_values:
                        totals += processed_values[key]

                    for key in processed_values:
                        values = np.array(processed_values[key])
                        values = np.where(totals > min_total_volume,
                                          values / np.maximum(totals, min_total_volume),
                                          0)
                        processed_values[key] = values
                elif use_log_scale:
                    for key in processed_values:
                        processed_values[key] = [np.log10(v + 1) for v in processed_values[key]]

                    # Get current axis
                ax = axes[ax_idx]
                ax.set_aspect(aspect='auto')

                if groupby_complexity:
                    values_for_stack = [processed_values[complexity] for complexity in unique_complexities]
                    labels = [f"Complexity {complexity}" for complexity in unique_complexities]
                    colors = [complexity_colors[complexity] for complexity in unique_complexities]
                else:
                    values_for_stack = [processed_values[item] for item in sorted_items]
                    labels = [f"{item} (complexity: {item_complexities[item]})" for item in sorted_items]
                    colors = color_map

                # Create the appropriate chart type
                if chart_type.lower() == 'bar':
                    bottom = np.zeros(len(all_steps))
                    for i, (values, color) in enumerate(zip(values_for_stack, colors)):
                        if ax_idx == len(versions) - 1:
                            bar = ax.bar(all_steps, values, bottom=bottom,
                                         label=labels[i], color=color, alpha=0.7,
                                         width=step_size * step_proportion)
                        else:
                            bar = ax.bar(all_steps, values, bottom=bottom,
                                         color=color, alpha=0.7,
                                         width=step_size * step_proportion)
                        bottom += values
                else:  # 'line' chart
                    if ax_idx == len(versions) - 1:
                        stack_plot = ax.stackplot(all_steps, values_for_stack,
                                                  labels=labels,
                                                  colors=colors,
                                                  alpha=0.7)
                    else:
                        stack_plot = ax.stackplot(all_steps, values_for_stack,
                                                  colors=colors,
                                                  alpha=0.7)

                # Update global y-axis limits
                if unified_y_axis:
                    ymin, ymax = ax.get_ylim()
                    global_ymin = min(global_ymin, ymin)
                    global_ymax = 7000  # max(global_ymax, ymax)

                # Position y-axis label based on layout
                if layout == "stacked":
                    if ax_idx == 0:  # First plot in stacked layout
                        if show_fractions:
                            ax.set_ylabel('Fraction of Total Production', fontsize=fontsize)
                        else:
                            y_label = 'Log10(Production Volume + 1)' if use_log_scale else 'Item Production'
                            ax.set_ylabel(y_label, fontsize=fontsize-2)
                    # Show x-axis ticks and labels for all plots in stacked mode
                    ax.tick_params(axis='x', which='both', labelsize=fontsize-2)

                else:  # side-by-side layout
                    if ax_idx in [3]:  # Left side plots
                        ax.yaxis.set_label_position("right")
                        ax.yaxis.set_label_coords(1.05, 0.5)
                        if show_fractions:
                            ax.set_ylabel('Fraction of Total Production', fontsize=fontsize)
                        else:
                            y_label = 'Log10(Production Volume + 1)' if use_log_scale else 'Item Production'
                            ax.set_ylabel(y_label, fontsize=fontsize-2)

                ax.set_xlabel('Step', fontsize=fontsize - 2)

                # Add grid
                ax.grid(True, which='major', linestyle='-', alpha=0.2)
                ax.grid(True, which='minor', linestyle='--', alpha=0.1)

                # Update current axis formatting
                #ax.yaxis.set_major_formatter(formatter)


                # Configure axis ticks for better readability
                #ax.yaxis.set_major_locator(LogLocator(base=10))  # For log scale

                # Set axis limits
                #ax.set_xlim(min(all_steps) - step_size / 2, max(all_steps) + step_size / 2)
                ax.set_xlim(min(all_steps), max(all_steps))
                if show_fractions:
                    ax.set_ylim(0, 1)

        # After all plots are done, set unified y-axis
        if unified_y_axis and not show_fractions:
            for ax in axes:
                ax.set_ylim(0, global_ymax)

        # Now add titles after all axes are finalized
        for ax_idx, (ax, version) in enumerate(zip(axes, versions)):
            if version not in self.versions:
                continue

            # Force matplotlib to update the plot
            ax.figure.canvas.draw()

            # Get the current axis limits after all adjustments
            ylims = ax.get_ylim()
            xlims = ax.get_xlim()

            color = self.colors[ax_idx % len(self.colors)]
            title_text = self.versions[version]["label"]

            # Calculate position for title
            title_x = xlims[0] + (xlims[1] - xlims[0]) * 0.4  # 2% from left edge
            title_y = ylims[1] - (ylims[1] - ylims[0]) * 0.05  # 5% from top

            # Add colored line prefix and title
            ax.text(title_x, title_y+300, '—',
                    color=color,
                    fontsize=fontsize + 16,
                    fontweight='bold',
                    horizontalalignment='right',
                    verticalalignment='top',
                    zorder=10)

            ax.text(title_x + (xlims[1] - xlims[0]) * 0.02, title_y + 0.15,
                    title_text,
                    fontsize=fontsize,
                    horizontalalignment='left',
                    verticalalignment='top',
                    zorder=10)

        # Add legend to the last subplot if needed
        if layout == "stacked":
            if groupby_complexity:
                legend_title = "Complexity Groups"
                # Add white background to complexity groups legend
                legend = axes[-1].legend(title=legend_title,
                                         bbox_to_anchor=(0.02, 0.98),  # Position inside plot
                                         loc='upper left',
                                         fontsize='small',
                                         title_fontsize='medium',
                                         facecolor='white',
                                         edgecolor='lightgray',
                                         framealpha=0.9)
            else:
                # Create legend in first production volume chart
                create_custom_legend_with_icons(axes[-1], sorted_items, item_complexities, colors, fontsize, layout=="stacked")
        else:  # side-by-side layout
            if groupby_complexity:
                legend_title = "Complexity Groups"
                legend = axes[-3].legend(title=legend_title,
                                         bbox_to_anchor=(1.02, 1),
                                         loc='upper left',
                                         fontsize='small',
                                         title_fontsize='medium',
                                         facecolor='white',
                                         edgecolor='lightgray',
                                         framealpha=0.9)
            else:
                create_custom_legend_with_icons(axes[-3], sorted_items, item_complexities, colors, fontsize, layout=="stacked")


async def main():
    # Example usage
    db_client = DBClient(
        max_conversation_length=40,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )

    icons_path = "/data/icons/early_icons"

    for x_axis in ["steps", "ticks"]:
        viz = ProgressionVisualizer(db_client, icons_path, x_axis,
                                    use_log_scale = x_axis != "ticks",
                                    use_value_gdp=False,
                                    recipes_file="/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/recipes/recipes.jsonl")

        # Configure versions to plot
        versions = {
            492: "Claude",
            490: "GPT-4",

            #487: "GPT-4-Mini",
            505: "GPT-4-Mini",
            488: "LLaMA-70B",
            #491: "DeepSeek",

        }

        # Generate visualization
        viz.load_data(list(versions.keys()), versions)

        achievement_params = {
            'render_complexity': False,
            'minimum_complexity': 2
        }
        production_params = {
            'step_size': 50,
            'cumulative': True,
            'show_fractions': False,
            'use_log_scale': False,
            'min_complexity': 2,
            'groupby_complexity': False,
            'unified_y_axis': True,
            'chart_type': 'line'
        }

        viz.export_combined_visualization('combined_analysis_stacked.png', [505, 488, 490, 492],
                                      achievement_params=achievement_params,
                                      production_params=production_params, layout="stacked")
        viz.export_combined_visualization('combined_analysis_side.png', [505, 488, 490, 492],
                                          achievement_params=achievement_params,
                                          production_params=production_params, layout="side-by-side")


if __name__ == "__main__":
    asyncio.run(main())