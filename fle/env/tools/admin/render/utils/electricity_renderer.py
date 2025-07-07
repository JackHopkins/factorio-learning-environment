import colorsys
from typing import Dict, Callable
from PIL import ImageDraw

from fle.env.entities import Layer
from fle.env.tools.admin.render.layers.layer_renderer import LayerRenderer


class ElectricityLayerRenderer(LayerRenderer):
    """Renderer for electricity networks, showing coverage areas colored by network ID"""

    @property
    def layer_name(self) -> str:
        return "electricity"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        game_to_img_func: Callable,
        boundaries: Dict[str, float],
        **kwargs,
    ) -> None:
        """Draw electricity network coverage areas on the map"""
        requested_layers = kwargs.get("layers", Layer.ALL)

        # Only proceed if electricity layer is requested
        if Layer.ELECTRICITY not in requested_layers:
            return

        electricity_networks = kwargs.get("electricity_networks", [])
        if not electricity_networks:
            return

        # Dictionary to store network colors by network_id
        network_colors = {}
        network_ids = set()

        # Collect all network IDs first
        for network in electricity_networks:
            if "network_id" in network:
                network_ids.add(network["network_id"])

        # Generate unique colors for each network
        self._assign_network_colors(network_ids, network_colors)

        # Draw the electricity coverage for each pole
        min_x, max_x = boundaries["min_x"], boundaries["max_x"]
        min_y, max_y = boundaries["min_y"], boundaries["max_y"]

        # Set semi-transparency for the shaded areas
        alpha = 100  # 0-255, where 0 is fully transparent and 255 is fully opaque

        for network in electricity_networks:
            if (
                "network_id" not in network
                or "position" not in network
                or "supply_area" not in network
            ):
                continue

            x, y = network["position"].get("x", 0), network["position"].get("y", 0)
            network_id = network["network_id"]
            supply_area = network["supply_area"]

            # Skip poles outside the grid boundaries or with no coverage
            if (
                x < min_x - supply_area
                or x > max_x + supply_area
                or y < min_y - supply_area
                or y > max_y + supply_area
                or supply_area <= 0
            ):
                continue

            # Get color for this network
            base_color = network_colors.get(network_id, (150, 150, 150))
            # Add alpha component for semi-transparency
            color = base_color + (alpha,)

            # Convert to image coordinates
            img_x, img_y = game_to_img_func(x, y)

            # Calculate radius in pixels
            radius_px = supply_area * self.config.style["cell_size"]

            # Draw a semi-transparent circle for the coverage area
            draw.ellipse(
                [
                    img_x - radius_px,
                    img_y - radius_px,
                    img_x + radius_px,
                    img_y + radius_px,
                ],
                fill=color,
                outline=None,
            )

            # Draw small pole indicator at the center
            pole_size = self.config.style["cell_size"] / 4
            draw.rectangle(
                [
                    img_x - pole_size,
                    img_y - pole_size,
                    img_x + pole_size,
                    img_y + pole_size,
                ],
                fill=base_color,
                outline=(0, 0, 0),
            )

    def _assign_network_colors(self, network_ids: set, color_map: Dict) -> None:
        """Generate visually distinct colors for each electricity network"""
        if not network_ids:
            return

        # Use golden ratio to generate visually distinct colors
        golden_ratio = 0.618033988749895
        hue = 0.1  # Starting hue

        # Predefined colors for first few networks for better distinction
        predefined_colors = [
            (55, 126, 184),  # Blue
            (228, 26, 28),  # Red
            (77, 175, 74),  # Green
            (152, 78, 163),  # Purple
            (255, 127, 0),  # Orange
            (166, 86, 40),  # Brown
            (247, 129, 191),  # Pink
            (0, 204, 204),  # Cyan
        ]

        # Sort network IDs for consistent coloring
        sorted_ids = sorted(network_ids)

        # Assign predefined colors for the first few networks
        for i, network_id in enumerate(sorted_ids):
            if i < len(predefined_colors):
                color_map[network_id] = predefined_colors[i]
            else:
                # For additional networks, use the golden ratio method
                hue = (hue + golden_ratio) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 0.9)
                color_map[network_id] = (int(r * 255), int(g * 255), int(b * 255))
