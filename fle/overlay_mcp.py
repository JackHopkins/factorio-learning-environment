# Simplified overlay.py modifications for MCP read-only monitoring with warning display

import argparse
import time
import logging
import subprocess
import json
from collections import deque
from datetime import datetime
from queue import Queue
from typing import List, Dict, Set

from nicegui import ui

from fle.overlay import IconManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("factorio_overlay.log")],
)
logger = logging.getLogger(__name__)


class FactorioControlPanel:
    """Minimal control panel for Factorio - MCP read-only monitoring with warning display."""

    def __init__(self, mcp_server: list = None):
        logger.info("Initializing FactorioControlPanel with MCP monitoring")

        self.mcp_server = mcp_server or ["python", "-m", "fle.env.protocols._mcp"]
        self.mcp_bridge = None

        self.update_queue = Queue()
        self.is_monitoring = False

        # Warning buffer and submission tracking
        self.warning_buffer = deque(maxlen=100)  # Keep last 100 warnings for history
        self.displayed_warnings = deque(maxlen=10)  # Keep last 10 warnings for display

        # Track current active warnings from the latest poll
        self.current_active_warnings: Set[int] = (
            set()
        )  # Set of warning hashes currently active

        # Track when we last notified Claude about each warning
        # Format: {hash: last_notification_timestamp}
        self.warning_notification_times: Dict[int, float] = {}
        self.warning_renotification_interval = (
            30  # Re-notify after 30 seconds if still active
        )

        self.last_warning_check = time.time()

        # Warning severity levels
        self.warning_levels = {
            "critical": {"color": "red-500", "icon": "🔴", "priority": 3},
            "error": {"color": "orange-500", "icon": "🟠", "priority": 2},
            "warning": {"color": "yellow-500", "icon": "🟡", "priority": 1},
            "info": {"color": "blue-500", "icon": "🔵", "priority": 0},
        }

        # Initialize icon manager
        self.icon_manager = IconManager()

        # Inventory data
        self.inventory_items = {}

        # Score tracking
        self.last_score = 0

        # Production chart data
        self.production_history = {"timestamps": deque(maxlen=50), "data": {}}
        self.chart = None

        # Production flow tracking
        self.production_samples = deque(
            maxlen=10
        )  # Keep last 10 samples for trend analysis
        self.last_production_notification = {}  # Track last notification time per resource
        self.production_notification_interval = (
            30  # Notify about same resource every 30s
        )
        self.material_change_threshold = 0.1  # 10% change threshold

        # UI elements (will be initialized in create_ui)
        self.coin_icon = None
        self.score_label = None
        self.status_label = None
        self.entities_label = None
        self.tick_label = None
        self.research_label = None
        self.game_view = None
        self.inventory_grid = None
        self.warnings_container = None
        self.warning_count_badge = None
        self.warnings_list = None

        # Auto-start monitoring
        self.auto_start = True

    def send_to_claude_code(self, message: str) -> bool:
        """Send message to Claude Code tmux session (similar to auto_continue.py logic)."""
        try:
            # Check if claude-code tmux session exists
            result = subprocess.run(
                ["tmux", "has-session", "-t", "claude-code"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error("No claude-code tmux session found")
                return False

            logger.info("Found claude-code tmux session")

            # Send the message with carriage return for proper submission
            subprocess.run(
                ["tmux", "send-keys", "-t", "claude-code", message, "C-m"], check=True
            )

            # Send additional C-m for good measure
            subprocess.run(
                ["tmux", "send-keys", "-t", "claude-code", "C-m"], check=True
            )

            logger.info(f"Sent '{message}' to claude-code session")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send to tmux: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to tmux: {e}")
            return False

    def determine_warning_level(self, warning_text: str) -> str:
        """Determine the severity level of a warning based on its content."""
        # text_lower = warning_text.lower()
        #
        # if any(word in text_lower for word in ['critical', 'fatal', 'crash', 'emergency', 'crisis']):
        #     return 'critical'
        # elif any(word in text_lower for word in ['error', 'failed', 'exception', 'invalid', 'falling', 'alert']):
        #     return 'error'
        # elif any(word in text_lower for word in ['warning', 'warn', 'deprecated', 'issue', 'consumption']):
        #     return 'warning'
        # else:
        #     return 'info'
        return "warning"

    def update_active_warnings(self, warnings_list: List[str]):
        """Update the set of currently active warnings from the latest poll."""
        new_active_warnings = {hash(warning) for warning in warnings_list}

        # Find warnings that are no longer active
        removed_warnings = self.current_active_warnings - new_active_warnings

        # Clean up notification times for warnings that are no longer active
        for warning_hash in removed_warnings:
            if warning_hash in self.warning_notification_times:
                del self.warning_notification_times[warning_hash]
                logger.debug(
                    f"Warning {warning_hash} is no longer active, removed from tracking"
                )

        # Update the current active set
        self.current_active_warnings = new_active_warnings

        # Process each active warning
        for warning_text in warnings_list:
            self.process_warning(warning_text, "MCP")

    def process_warning(self, warning_text: str, source: str = "MCP"):
        """Process a warning that is currently active."""
        warning_hash = hash(warning_text)
        current_time = time.time()

        # Add to display buffers
        timestamp = datetime.now()
        level = self.determine_warning_level(warning_text)

        warning_data = {
            "text": warning_text,
            "source": source,
            "timestamp": timestamp,
            "level": level,
            "hash": warning_hash,
        }

        # Add to buffer for display (always update display with current warnings)
        self.warning_buffer.append(warning_data)

        # Check if this warning is already in displayed warnings
        if not any(w["hash"] == warning_hash for w in self.displayed_warnings):
            self.displayed_warnings.append(warning_data)
            logger.info(f"Added new warning to display: {warning_text[:50]}...")

        # Check if we should notify Claude
        should_notify = False

        if warning_hash not in self.warning_notification_times:
            # Never notified about this warning before
            should_notify = True
            logger.info(f"New warning detected: {warning_text[:50]}...")
        else:
            # Check if enough time has passed since last notification
            time_since_last_notification = (
                current_time - self.warning_notification_times[warning_hash]
            )
            if time_since_last_notification >= self.warning_renotification_interval:
                should_notify = True
                logger.info(
                    f"Re-notifying warning after {time_since_last_notification:.0f}s: {warning_text[:50]}..."
                )

        if should_notify:
            self.submit_warning_to_claude(warning_data)
            self.warning_notification_times[warning_hash] = current_time

        # Update the display
        self.update_warnings_display()

    def submit_warning_to_claude(self, warning_data: dict):
        """Submit a warning to Claude Code terminal."""
        warning_text = warning_data["text"]
        source = warning_data["source"]
        timestamp = warning_data["timestamp"].strftime("%H:%M:%S")

        # Format the warning message for Claude
        formatted_message = f"[{timestamp}] {source} Warning: {warning_text}"

        logger.info(f"Submitting warning to Claude: {formatted_message}")

        # Send to Claude Code session
        success = self.send_to_claude_code(formatted_message)

        if success:
            logger.info("Successfully submitted warning to Claude")
        else:
            logger.warning("Failed to submit warning to Claude")

    def update_warnings_display(self):
        """Update the warnings display in the UI."""
        if not self.warnings_list:
            return

        # Clear and rebuild the warnings list
        self.warnings_list.clear()

        with self.warnings_list:
            # Sort warnings by timestamp (newest first) and priority
            sorted_warnings = sorted(
                self.displayed_warnings,
                key=lambda x: (
                    -self.warning_levels[x["level"]]["priority"],
                    x["timestamp"],
                ),
                reverse=True,
            )

            if not sorted_warnings:
                with ui.card().classes("w-full p-2 bg-gray-700 text-gray-400"):
                    ui.label("No warnings").classes("text-xs")
            else:
                for warning in sorted_warnings:
                    level_info = self.warning_levels[warning["level"]]
                    warning_hash = warning["hash"]

                    with ui.card().classes(
                        f"w-full p-2 bg-gray-700 border-l-4 border-{level_info['color']}"
                    ):
                        with ui.row().classes("w-full items-start gap-2"):
                            # Icon
                            ui.label(level_info["icon"]).classes("text-sm")

                            # Content
                            with ui.column().classes("flex-1 gap-1"):
                                # Header with source and time
                                with ui.row().classes(
                                    "w-full justify-between items-center"
                                ):
                                    ui.label(f"{warning['source']}").classes(
                                        f"text-xs font-bold text-{level_info['color']}"
                                    )
                                    ui.label(
                                        warning["timestamp"].strftime("%H:%M:%S")
                                    ).classes("text-xs text-gray-400")

                                # Warning text
                                ui.label(warning["text"]).classes(
                                    "text-xs text-white break-words"
                                )

                                # Show status
                                status_parts = []

                                # Check if warning is still active
                                if warning_hash in self.current_active_warnings:
                                    status_parts.append("🟢 Active")

                                    # Show re-notification timer if applicable
                                    if warning_hash in self.warning_notification_times:
                                        time_since_notification = (
                                            time.time()
                                            - self.warning_notification_times[
                                                warning_hash
                                            ]
                                        )
                                        time_until_renotify = (
                                            self.warning_renotification_interval
                                            - time_since_notification
                                        )
                                        if time_until_renotify > 0:
                                            status_parts.append(
                                                f"Re-notify in {time_until_renotify:.0f}s"
                                            )
                                        else:
                                            status_parts.append("Ready to re-notify")
                                else:
                                    status_parts.append("⚫ Resolved")

                                if status_parts:
                                    ui.label(" | ".join(status_parts)).classes(
                                        "text-xs text-gray-500"
                                    )

        # Update warning count badge
        if self.warning_count_badge:
            active_count = len(self.current_active_warnings)
            if active_count > 0:
                self.warning_count_badge.set_text(str(active_count))
                self.warning_count_badge.classes(remove="hidden")
            else:
                self.warning_count_badge.classes("hidden")

    def clear_warnings(self):
        """Clear all displayed warnings and their notification history."""
        self.displayed_warnings.clear()
        self.current_active_warnings.clear()
        self.warning_notification_times.clear()
        self.update_warnings_display()
        logger.info("Cleared all displayed warnings and notification history")

    def check_for_warnings(self):
        """Check for re-notification of active warnings."""
        current_time = time.time()

        # Only check every 2 seconds to avoid spam
        if current_time - self.last_warning_check < 2.0:
            return

        self.last_warning_check = current_time

        # Check if any active warnings need re-notification
        for warning_hash in self.current_active_warnings:
            if warning_hash in self.warning_notification_times:
                time_since_notification = (
                    current_time - self.warning_notification_times[warning_hash]
                )
                if time_since_notification >= self.warning_renotification_interval:
                    # Find the warning data
                    for warning in self.displayed_warnings:
                        if warning["hash"] == warning_hash:
                            logger.info(
                                f"Re-notifying active warning: {warning['text'][:50]}..."
                            )
                            self.submit_warning_to_claude(warning)
                            self.warning_notification_times[warning_hash] = current_time
                            break

        # Update display to show new timer values
        self.update_warnings_display()

    def analyze_production_flows(self, metrics_data: dict):
        """Analyze production flow changes and generate notifications."""
        if not metrics_data:
            return

        current_time = time.time()
        timestamp = datetime.now()

        # Create a sample with timestamp
        sample = {
            "timestamp": timestamp,
            "time": current_time,
            "input": metrics_data.get("input", {}),
            "output": metrics_data.get("output", {}),
        }

        self.production_samples.append(sample)

        # Need at least 2 samples to calculate rate of change
        if len(self.production_samples) < 2:
            return

        # Calculate rates of change
        oldest_sample = self.production_samples[0]
        latest_sample = self.production_samples[-1]

        time_diff = latest_sample["time"] - oldest_sample["time"]
        if time_diff < 1:  # Avoid division by zero
            return

        # Convert to per-minute rates
        time_diff_minutes = time_diff / 60.0

        production_changes = []
        consumption_changes = []
        critical_changes = []

        # Analyze output changes (production)
        for resource, latest_amount in latest_sample["output"].items():
            old_amount = oldest_sample["output"].get(resource, 0)
            if old_amount == 0:
                continue

            change = latest_amount - old_amount

            if change == 0:
                continue

            rate_per_minute = change / time_diff_minutes

            # Calculate percentage change
            if old_amount > 0:
                percent_change = change / old_amount
            else:
                percent_change = 1.0 if change > 0 else 0

            if abs(percent_change) >= self.material_change_threshold:
                # Check if we should notify about this resource
                last_notified = self.last_production_notification.get(
                    f"output_{resource}", 0
                )
                if (
                    current_time - last_notified
                    >= self.production_notification_interval
                ):
                    if change > 0:
                        production_changes.append(
                            {
                                "resource": resource,
                                "change": change,
                                "percent": percent_change * 100,
                                "rate": rate_per_minute,
                            }
                        )
                    else:
                        # Production decrease is more concerning
                        critical_changes.append(
                            {
                                "resource": resource,
                                "type": "production_decrease",
                                "change": change,
                                "percent": percent_change * 100,
                                "rate": rate_per_minute,
                            }
                        )
                    self.last_production_notification[f"output_{resource}"] = (
                        current_time
                    )

        # Analyze input changes (consumption)
        for resource, latest_amount in latest_sample["input"].items():
            old_amount = oldest_sample["input"].get(resource, 0)
            change = latest_amount - old_amount

            if change == 0:
                continue

            rate_per_minute = change / time_diff_minutes

            # Calculate percentage change
            if old_amount > 0:
                percent_change = change / old_amount
            else:
                percent_change = 1.0 if change > 0 else 0

            if abs(percent_change) >= self.material_change_threshold:
                # Check if we should notify about this resource
                last_notified = self.last_production_notification.get(
                    f"input_{resource}", 0
                )
                if (
                    current_time - last_notified
                    >= self.production_notification_interval
                ):
                    if change > 0:
                        consumption_changes.append(
                            {
                                "resource": resource,
                                "change": change,
                                "percent": percent_change * 100,
                                "rate": rate_per_minute,
                            }
                        )
                    self.last_production_notification[f"input_{resource}"] = (
                        current_time
                    )

        # Check for critical situations (consumption up, production down for same resource)
        for resource in set(latest_sample["input"].keys()) | set(
            latest_sample["output"].keys()
        ):
            input_latest = latest_sample["input"].get(resource, 0)
            input_old = oldest_sample["input"].get(resource, 0)
            output_latest = latest_sample["output"].get(resource, 0)
            output_old = oldest_sample["output"].get(resource, 0)

            input_change = input_latest - input_old
            output_change = output_latest - output_old

            # Critical: consumption increasing while production decreasing
            if input_change > 0 and output_change < 0:
                last_notified = self.last_production_notification.get(
                    f"critical_{resource}", 0
                )
                if (
                    current_time - last_notified
                    >= self.production_notification_interval
                ):
                    critical_changes.append(
                        {
                            "resource": resource,
                            "type": "supply_deficit",
                            "consumption_increase": input_change,
                            "production_decrease": -output_change,
                        }
                    )
                    self.last_production_notification[f"critical_{resource}"] = (
                        current_time
                    )

        # Generate notifications
        for change in production_changes:
            message = f"📈 {change['resource'].replace('-', ' ').title()} production {'increasing' if change['change'] > 0 else 'decreasing'} {abs(change['percent']):.1f}% ({change['rate']:.1f}/min)"
            self.process_warning(message, "Production")

        for change in consumption_changes:
            message = f"⚡ {change['resource'].replace('-', ' ').title()} consumption {'increasing' if change['change'] > 0 else 'decreasing'} {abs(change['percent']):.1f}% ({change['rate']:.1f}/min)"
            self.process_warning(message, "Consumption")

        for change in critical_changes:
            if change["type"] == "production_decrease":
                message = f"⚠️ {change['resource'].replace('-', ' ').title()} production falling {abs(change['percent']):.1f}% ({change['rate']:.1f}/min)"
                self.process_warning(message, "Production Alert")
            elif change["type"] == "supply_deficit":
                message = f"🚨 CRITICAL: {change['resource'].replace('-', ' ').title()} - consumption up +{change['consumption_increase']}, production down -{change['production_decrease']}"
                self.process_warning(message, "Supply Crisis")

    def process_updates(self):
        """Process updates from the MCP bridge."""
        while not self.update_queue.empty():
            update = self.update_queue.get()

            # Check for warnings in the update
            if "warnings" in update and isinstance(update["warnings"], list):
                # Update the active warnings set and process them
                self.update_active_warnings(update["warnings"])

            # Check for error messages that should be treated as warnings
            if "error" in update or "message" in update:
                message = update.get("message", update.get("error", ""))
                if any(
                    keyword in str(message).lower()
                    for keyword in ["warning", "error", "failed", "exception"]
                ):
                    self.process_warning(str(message), "System")

            # Check for metrics data and analyze production flows
            if "metrics" in update and update["metrics"]:
                try:
                    if isinstance(update["metrics"], str):
                        metrics_data = json.loads(update["metrics"])
                    else:
                        metrics_data = update["metrics"]
                    self.analyze_production_flows(metrics_data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Error analyzing metrics: {e}")

            if update["type"] == "state_update":
                # Update inventory
                if "inventory" in update and update["inventory"]:
                    if self.inventory_items != update["inventory"]:
                        self.inventory_items = update["inventory"]
                        self.update_inventory_display()

                # Calculate and display score from inventory
                if "inventory" in update and update["inventory"]:
                    total_value = sum(update["inventory"].values())
                    score_text = f"{total_value:.0f}"
                    if self.score_label:
                        self.score_label.set_content(score_text)

                # Update entity count
                if "entities_count" in update and self.entities_label:
                    self.entities_label.set_text(
                        f"Entities: {update['entities_count']}"
                    )

                # Update position
                if "position" in update and self.tick_label:
                    pos = update["position"]
                    self.tick_label.set_text(
                        f"Pos: ({pos.get('x', 0):.0f}, {pos.get('y', 0):.0f})"
                    )

                # Update game view image if available
                if "image" in update and update["image"] and self.game_view:
                    self.game_view.set_source(update["image"])

                # Update status
                if "status" in update and self.status_label:
                    # Extract key info from status string
                    if "Connected to Factorio server" in str(update["status"]):
                        self.status_label.set_text("🟢 Connected")
                    else:
                        self.status_label.set_text("🟡 " + str(update["status"])[:30])

            elif update["type"] == "init":
                if self.status_label:
                    self.status_label.set_text("🟢 Monitoring Active")

                # Initialize coin icon
                coin_icon_data = self.icon_manager.get_icon_base64("coin")
                if coin_icon_data and self.coin_icon:
                    self.coin_icon.set_source(coin_icon_data)
                elif self.coin_icon:
                    self.coin_icon.classes("hidden")

            elif update["type"] == "error":
                if self.status_label:
                    self.status_label.set_text(
                        f"❌ {update.get('message', 'Error')[:30]}"
                    )
                # Also add as warning
                self.process_warning(update.get("message", "Unknown error"), "System")

    def update_inventory_display(self):
        """Update the inventory grid display with sprite icons."""
        if not self.inventory_grid:
            return

        self.inventory_grid.clear()

        with self.inventory_grid:
            # Sort items by count (descending)
            sorted_items = sorted(
                self.inventory_items.items(), key=lambda x: x[1], reverse=True
            )

            for item_name, count in sorted_items[:20]:  # Show top 20 items
                with ui.card().classes(
                    "w-16 h-16 bg-gray-700 p-1 relative overflow-hidden"
                ):
                    # Try to get sprite icon
                    icon_data = self.icon_manager.get_icon_base64(item_name)

                    if icon_data:
                        # Use actual sprite icon
                        ui.image(icon_data).classes(
                            "absolute inset-0 w-full h-full object-contain p-1"
                        )
                    else:
                        # Fallback to emoji
                        emoji = self.icon_manager.get_emoji_fallback(item_name)
                        ui.label(emoji).classes(
                            "text-2xl absolute top-1 left-1/2 transform -translate-x-1/2"
                        )

                    # Count badge
                    ui.label(str(count)).classes(
                        "text-sm text-white absolute bottom-0 right-1 bg-gray-900 px-1 rounded font-bold"
                    )
                    # Tooltip with item name
                    ui.tooltip(item_name)

    def create_ui(self):
        """Create the MCP monitoring interface with warning display."""
        if hasattr(self, "_ui_created"):
            return
        self._ui_created = True

        # Main container
        with ui.row().classes("w-full h-screen p-4 bg-gray-900 gap-4"):
            # LEFT COLUMN - Stats and inventory
            with ui.column().classes("w-96 flex-shrink-0 gap-2"):
                # Header
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    ui.label("Factorio MCP Monitor").classes(
                        "text-xl font-bold text-center"
                    )
                    self.status_label = ui.label("⚪ Connecting to MCP...").classes(
                        "text-sm text-center mt-2"
                    )

                # Stats
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    ui.label("Statistics").classes("text-sm font-bold")

                    # Score with coin icon
                    with ui.row().classes("items-center gap-1 mt-2"):
                        self.coin_icon = ui.image("").classes("w-4 h-4")
                        self.score_label = ui.html("0").classes("text-lg font-bold")

                    with ui.row().classes("w-full justify-between text-xs mt-2"):
                        self.entities_label = ui.label("Entities: 0")
                        self.tick_label = ui.label("Pos: (0, 0)")

                # Warnings Panel
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    with ui.row().classes("w-full justify-between items-center"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label("⚠️ Warnings").classes("text-sm font-bold")
                            self.warning_count_badge = ui.label("0").classes(
                                "px-2 py-0.5 bg-red-500 text-white text-xs rounded-full hidden"
                            )
                        ui.button("Clear", on_click=self.clear_warnings).classes(
                            "text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600"
                        )

                    # Scrollable warnings list
                    with ui.scroll_area().classes("w-full h-48 mt-2"):
                        self.warnings_list = ui.column().classes("w-full gap-2")

                # Inventory
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    ui.label("Inventory").classes("text-sm font-bold")
                    self.inventory_grid = ui.row().classes(
                        "w-full flex-wrap gap-2 mt-2"
                    )

                # Control buttons
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    with ui.row().classes("w-full gap-2"):
                        ui.button("Reconnect", on_click=self.reconnect_mcp).classes(
                            "flex-1"
                        )
                        ui.button("Stop", on_click=self.stop_monitoring).classes(
                            "flex-1"
                        )
                        # Add test warning button for debugging
                        ui.button(
                            "Test Warning",
                            on_click=lambda: self.process_warning(
                                f"Test warning at {datetime.now().strftime('%H:%M:%S')}",
                                "Test",
                            ),
                        ).classes("flex-1")

                # Warning Settings Info
                with ui.card().classes("w-full bg-gray-800 text-white"):
                    ui.label("⚙️ Warning Settings").classes("text-sm font-bold")
                    ui.label(
                        f"Re-notification interval: {self.warning_renotification_interval}s"
                    ).classes("text-xs text-gray-400 mt-1")
                    ui.label("Only active warnings are re-notified").classes(
                        "text-xs text-gray-400"
                    )
                    ui.label("Resolved warnings are automatically cleaned").classes(
                        "text-xs text-gray-400"
                    )

            # CENTER - Game view
            with ui.column().classes("flex-1"):
                with ui.card().classes("w-full h-full bg-gray-800"):
                    ui.label("Game View").classes("text-sm font-bold text-white mb-2")
                    self.game_view = ui.image().classes("w-full h-full object-contain")
                    # Show placeholder initially
                    self.game_view.set_source(
                        "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iIzMzMyIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjI0IiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+V2FpdGluZyBmb3IgZ2FtZSBkYXRhLi4uPC90ZXh0Pjwvc3ZnPg=="
                    )

            # RIGHT COLUMN - Optional: Live warning feed (for critical warnings)
            with ui.column().classes("w-80 flex-shrink-0 gap-2"):
                with ui.card().classes("w-full bg-gray-800 text-white h-full"):
                    ui.label("🚨 Live Warning Feed").classes("text-sm font-bold mb-2")
                    with ui.scroll_area().classes("w-full flex-1"):
                        self.live_warnings_feed = ui.column().classes("w-full gap-2")

                    # Add notification settings
                    with ui.row().classes("w-full mt-2 pt-2 border-t border-gray-700"):
                        ui.switch("Audio alerts").classes("text-xs")
                        ui.switch("Auto-clear old").classes("text-xs")

        # Set up periodic UI updates
        ui.timer(0.5, self.process_updates)

        # Set up periodic warning checks for re-notification
        ui.timer(2.0, self.check_for_warnings)

        # Auto-clear old warnings from display every 30 seconds
        ui.timer(30.0, self.auto_clear_old_warnings)

        # Auto-start monitoring
        if self.auto_start:
            ui.timer(1.0, lambda: self.start_monitoring(), once=True)

    def auto_clear_old_warnings(self):
        """Automatically remove resolved warnings from display."""
        # Remove warnings that are no longer active from the display
        self.displayed_warnings = deque(
            [
                w
                for w in self.displayed_warnings
                if w["hash"] in self.current_active_warnings
            ],
            maxlen=10,
        )

        self.update_warnings_display()
        logger.info(
            f"Auto-cleaned display, {len(self.current_active_warnings)} warnings remain active"
        )

    def start_monitoring(self):
        """Start monitoring via MCP"""
        if self.is_monitoring:
            return

        logger.info("Starting MCP monitoring")
        self.is_monitoring = True

        if self.status_label:
            self.status_label.set_text("🟡 Connecting to MCP...")

        # Import and create the MCP bridge
        from mcp_dataloader import MCPDataBridge

        self.mcp_bridge = MCPDataBridge(update_queue=self.update_queue)

        try:
            self.mcp_bridge.start()
            logger.info("MCP bridge started successfully")
        except Exception as e:
            logger.error(f"Failed to start MCP bridge: {e}")
            if self.status_label:
                self.status_label.set_text(f"❌ Failed: {str(e)[:30]}")
            self.is_monitoring = False
            # Add as warning
            self.process_warning(f"Failed to start MCP bridge: {e}", "System")

    def reconnect_mcp(self):
        """Reconnect to MCP server"""
        logger.info("Reconnecting to MCP")
        self.stop_monitoring()
        ui.timer(1.0, lambda: self.start_monitoring(), once=True)

    def stop_monitoring(self):
        """Stop monitoring"""
        if not self.is_monitoring:
            return

        logger.info("Stopping MCP monitoring")
        self.is_monitoring = False

        if self.mcp_bridge:
            try:
                self.mcp_bridge.stop()
            except Exception as e:
                logger.error(f"Error stopping MCP bridge: {e}")
            self.mcp_bridge = None

        if self.status_label:
            self.status_label.set_text("⏹️ Stopped")


def main():
    """Main entry point for MCP monitoring panel."""

    logger.info("=== Starting Factorio MCP Monitor ===")

    parser = argparse.ArgumentParser(description="MCP monitoring panel for Factorio")
    parser.add_argument("--port", type=int, default=8080, help="Port for web interface")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host for web interface"
    )
    parser.add_argument(
        "--mcp-server", nargs="+", default=["python", "-m", "fle.env.protocols._mcp"]
    )

    args = parser.parse_args()

    # Create monitoring panel
    panel = FactorioControlPanel(mcp_server=args.mcp_server)

    @ui.page("/")
    def index():
        ui.dark_mode().enable()
        panel.create_ui()

    ui.run(
        host=args.host,
        port=args.port,
        title="Factorio MCP Monitor",
        favicon="👁️",
        dark=True,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
