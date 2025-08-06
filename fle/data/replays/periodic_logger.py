"""
Handles periodic data logging functionality.
"""

import json
from typing import Any, List, Optional
from datetime import datetime

from fle.data.replays.action_converter import ActionConverter


class PeriodicLogger:
    """Handles periodic data logging functionality."""

    def __init__(self, log_file_path: Optional[str], interval: int):
        self.log_file_path = log_file_path
        self.interval = interval
        self.last_logged_tick = 0
        self.enabled = log_file_path is not None and interval > 0

        if self.enabled:
            # Clear any existing log file
            with open(self.log_file_path, "w"):
                pass

    def should_log_at_tick(self, tick: int, min_tick: int = 0) -> bool:
        """Check if we should log at the given tick."""
        if not self.enabled or tick < min_tick:
            return False

        return tick >= self.last_logged_tick + self.interval

    def add_periodic_commands(
        self, batch_info: List, namespace, min_tick: int, max_tick: int
    ):
        """Add periodic logging commands to the batch."""
        if not self.enabled:
            return {}

        periodic_commands = {}
        current_log_tick = self.last_logged_tick + self.interval

        while current_log_tick <= max_tick:
            if current_log_tick >= min_tick:
                try:
                    ActionConverter.execute_tool_call_in_batch(
                        namespace, "inspect_inventory", {}, current_log_tick
                    )
                    command_index = len(batch_info)
                    periodic_commands[command_index] = {
                        "tick": current_log_tick,
                        "type": "inventory",
                    }
                    batch_info.append(
                        {
                            "index": command_index,
                            "func_name": "inspect_inventory",
                            "tick": current_log_tick,
                            "args": {},
                            "is_periodic": True,
                        }
                    )
                except Exception as e:
                    print(
                        f"Error adding periodic logging at tick {current_log_tick}: {e}"
                    )

            current_log_tick += self.interval

        return periodic_commands

    def generate_periodic_commands(self, namespace, min_tick: int, max_tick: int):
        """Generate periodic logging commands without modifying batch_info."""
        if not self.enabled:
            return []

        periodic_commands = []
        current_log_tick = self.last_logged_tick + self.interval

        while current_log_tick <= max_tick:
            if current_log_tick >= min_tick:
                try:
                    ActionConverter.execute_tool_call_in_batch(
                        namespace, "inspect_inventory", {}, current_log_tick
                    )
                    periodic_commands.append(
                        {
                            "func_name": "inspect_inventory",
                            "tick": current_log_tick,
                            "args": {},
                            "is_periodic": True,
                            "periodic_type": "inventory",
                        }
                    )
                except Exception as e:
                    print(
                        f"Error preparing periodic logging at tick {current_log_tick}: {e}"
                    )

            current_log_tick += self.interval

        return periodic_commands

    def log_result(self, tick: int, result_data: Any) -> bool:
        """Log a periodic result and return success status."""
        if not self.enabled:
            return False

        try:
            # Create a serializable version of the inventory data
            def make_serializable(obj, visited=None, depth=0):
                if visited is None:
                    visited = set()
                if depth > 10:  # Prevent infinite recursion
                    return str(obj)

                obj_id = id(obj)
                if obj_id in visited:
                    return f"<circular reference to {type(obj).__name__}>"

                visited.add(obj_id)

                try:
                    if hasattr(obj, "to_dict"):
                        return make_serializable(obj.to_dict(), visited, depth + 1)
                    elif hasattr(obj, "__dict__"):
                        result = {}
                        for key, value in obj.__dict__.items():
                            if not key.startswith("_"):
                                try:
                                    result[key] = make_serializable(
                                        value, visited, depth + 1
                                    )
                                except:
                                    result[key] = str(value)
                        return result
                    elif isinstance(obj, (list, tuple)):
                        return [
                            make_serializable(item, visited, depth + 1) for item in obj
                        ]
                    elif isinstance(obj, dict):
                        return {
                            k: make_serializable(v, visited, depth + 1)
                            for k, v in obj.items()
                        }
                    elif hasattr(obj, "value"):
                        return obj.value
                    else:
                        return obj
                except:
                    return str(obj)
                finally:
                    visited.discard(obj_id)

            serializable_data = make_serializable(result_data)

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tick": tick,
                "inventory": serializable_data,
                "entities": [],
            }

            with open(self.log_file_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

            self.last_logged_tick = tick
            return True
        except Exception as e:
            print(f"Warning: Failed to save periodic data at tick {tick}: {e}")
            return False
