import atexit
import contextlib
import enum
import functools
import importlib
import inspect
import json
import os
import shutil
import signal
import threading
import time
import traceback
import types
from concurrent.futures import TimeoutError
from pathlib import Path
from timeit import default_timer as timer
from typing_extensions import Optional, List, Dict, Any, Tuple
import uuid

from dotenv import load_dotenv
from slpp import slpp as lua

from fle.env.entities import BoundingBox
from fle.env.utils.camera import Camera

from fle.env.lua_manager import LuaScriptManager
from fle.env.namespace import FactorioNamespace
from fle.env.utils.rcon import _lua2python, _get_dir
from fle.commons.models.research_state import ResearchState
from factorio_rcon import RCONClient
from fle.commons.models.game_state import GameState
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.env.game_types import PrototypeJSONEncoder

# Add Lua syntax validation
try:
    from luaparser import ast as lua_ast

    LUAPARSER_AVAILABLE = True
except ImportError:
    LUAPARSER_AVAILABLE = False
    print("WARNING: luaparser not available. Install with: pip install luaparser")

CHUNK_SIZE = 32
MAX_SAMPLES = 5000

load_dotenv()

NONE = "nil"

global var
var = {}


class DirectionInternal(enum.Enum):
    UP = NORTH = 0
    RIGHT = EAST = 2
    DOWN = SOUTH = 4
    LEFT = WEST = 6

    @classmethod
    def opposite(cls, direction):
        return cls((direction.value + 4) % 8)

    @classmethod
    def next_clockwise(cls, direction):
        return cls((direction.value + 2) % 8)

    @classmethod
    def next_counterclockwise(cls, direction):
        return cls((direction.value - 2) % 8)

    @classmethod
    def to_factorio_direction(cls, direction):
        return direction.value // 2

    @classmethod
    def from_factorio_direction(cls, direction):
        return direction.value * 2


class FactorioTransaction:
    def __init__(self):
        self.commands: List[
            Tuple[str, List[Any], bool]
        ] = []  # (command, parameters, is_raw)

    def add_command(self, command: str, *parameters, raw=False):
        self.commands.append((command, list(parameters), raw))

    def clear(self):
        self.commands.clear()

    def get_commands(self):
        return self.commands


class BatchManager:
    def __init__(self, instance, grace_period=5, rcon_connection=None, manager_id=0):
        self.instance = instance
        self.is_active = False
        self.scheduled_commands = []
        self.current_batch_id = None
        self.grace_period = grace_period  # Default 5 tick grace period
        self.rcon_connection = rcon_connection  # Store the RCON connection
        self.manager_id = manager_id  # Store the manager ID

        # Add connection validation
        self.connection_healthy = False
        self.last_error = None
        self._validate_connection()

        # Generate unique sequence ID per Python script run
        import uuid

        self.sequence_id = f"seq_{uuid.uuid4()}"

    def _validate_connection(self):
        """Validate that the RCON connection is working properly."""
        if not self.rcon_connection:
            self.connection_healthy = True
            return

        try:
            # Test basic connectivity
            self.rcon_connection.send_command(
                "/sc rcon.print('health_check_" + str(self.manager_id) + "')"
            )

            # Test if we can access global actions
            self.rcon_connection.send_command("/sc rcon.print(type(global.actions))")

            # Test if we can create a sequence
            self.rcon_connection.send_command(
                f'/sc rcon.print("sequence_test_manager_{self.manager_id}")'
            )

            self.connection_healthy = True

        except Exception as e:
            self.connection_healthy = False
            self.last_error = str(e)
            print(
                f"❌ BatchManager {self.manager_id}: Connection validation failed: {e}"
            )

    def get_health_status(self):
        """Get the health status of this batch manager."""
        return {
            "manager_id": self.manager_id,
            "connection_healthy": self.connection_healthy,
            "last_error": self.last_error,
            "is_active": self.is_active,
            "current_batch_id": self.current_batch_id,
            "has_dedicated_connection": self.rcon_connection is not None,
        }

    def activate(self):
        """Enable batch mode for all tools."""
        self.is_active = True
        # Clear any existing commands
        self.scheduled_commands.clear()
        self.current_batch_id = None
        # Set this batch manager on all tools
        for namespace in self.instance.namespaces:
            for tool_name in self.instance.controllers:
                controller = self.instance.controllers[tool_name]
                controller.set_batch_manager(self)

    def deactivate(self):
        """Disable batch mode."""
        self.is_active = False
        self.scheduled_commands.clear()
        self.current_batch_id = None
        for namespace in self.instance.namespaces:
            for tool_name in self.instance.controllers:
                controller = self.instance.controllers[tool_name]
                controller.set_batch_manager(None)

    def add_tool_command(self, tick: int, tool_name: str, player_index: int, *args):
        """Add a processed tool command to the batch."""
        if not self.is_active:
            raise RuntimeError("BatchManager not activated - call activate() first")

        # Store command with all necessary info for later submission
        # Add player_index to front since Lua functions expect it as first parameter
        parameters = [player_index] + list(args)
        self.scheduled_commands.append(
            {"tick": tick, "command": tool_name, "parameters": parameters, "raw": False}
        )
        return {"batched": True, "tick": tick, "tool": tool_name}

    def reset_sequence(self, grace_period=None):
        """Reset the batch sequence to start fresh timing with optional grace period."""
        if grace_period is None:
            grace_period = self.grace_period

        self.instance.begin_transaction()
        self.instance.add_command("/sc global.actions.reset_sequence()", raw=True)
        result = self.instance.execute_transaction()

        # Store the grace period for this sequence
        self.grace_period = grace_period
        return result

    def emergency_cleanup(self):
        """Emergency cleanup method to clear all server-side memory and queued actions.

        This method is designed to be called during KeyboardInterrupt or error conditions
        to ensure that no scheduled commands continue running on the server.
        """
        cleanup_results = {}
        rcon_client = self.rcon_connection or self.instance.rcon_client

        try:
            # Clear local state first
            self.scheduled_commands.clear()
            old_batch_id = self.current_batch_id
            self.current_batch_id = None

            print(
                f"   📝 Manager {self.manager_id}: Clearing local state (batch_id: {old_batch_id})"
            )

            # Reset the sequence to clear all scheduled commands for this manager's sequence
            print(
                f"   🔄 Manager {self.manager_id}: Resetting sequence {self.sequence_id}"
            )
            reset_cmd = (
                f'/sc global.actions.register_sequence_start("{self.sequence_id}", 0)'
            )
            rcon_client.send_command(reset_cmd)

            # Use the new clear_sequence_commands function to precisely clear this sequence's commands
            clear_sequence_cmd = (
                f'/sc global.actions.clear_sequence_commands("{self.sequence_id}")'
            )
            rcon_client.send_command(clear_sequence_cmd)

            # Force reset sequence to clear any remaining scheduled commands
            reset_sequence_cmd = "/sc global.actions.reset_sequence()"
            rcon_client.send_command(reset_sequence_cmd)

            cleanup_results["sequence_reset"] = "success"
            print(f"   ✅ Manager {self.manager_id}: Sequence reset completed")

        except Exception as e:
            cleanup_results["sequence_reset"] = f"error: {str(e)}"
            print(f"   ❌ Manager {self.manager_id}: Failed to reset sequence: {e}")

        try:
            # Clear batch results for this specific batch if it exists
            if old_batch_id:
                clear_specific_cmd = (
                    f'/sc global.actions.clear_batch_results("{old_batch_id}")'
                )
                rcon_client.send_command(clear_specific_cmd)
                print(
                    f"   🗑️ Manager {self.manager_id}: Cleared results for batch {old_batch_id}"
                )

            # Clear all batch results to free server memory
            clear_all_cmd = "/sc global.actions.clear_batch_results()"
            rcon_client.send_command(clear_all_cmd)

            cleanup_results["batch_results_cleared"] = "success"
            print(f"   🧹 Manager {self.manager_id}: All batch results cleared")

        except Exception as e:
            cleanup_results["batch_results_cleared"] = f"error: {str(e)}"
            print(
                f"   ❌ Manager {self.manager_id}: Failed to clear batch results: {e}"
            )

        try:
            # Deactivate batch mode to ensure tools don't add more commands
            self.deactivate()
            cleanup_results["deactivated"] = "success"
            print(f"   🛑 Manager {self.manager_id}: Batch mode deactivated")

        except Exception as e:
            cleanup_results["deactivated"] = f"error: {str(e)}"
            print(f"   ❌ Manager {self.manager_id}: Failed to deactivate: {e}")

        return cleanup_results

    def submit_batch(self):
        """Submit all batched commands to the server and return batch info."""
        if not self.scheduled_commands:
            return {}

        # Check connection health before submission
        if not self.connection_healthy:
            print(
                f"❌ Manager {self.manager_id}: Refusing to submit - connection unhealthy: {self.last_error}"
            )
            return {"error": "Connection unhealthy", "last_error": self.last_error}

        # Use the dedicated RCON connection for this batch manager
        rcon_client = self.rcon_connection or self.instance.rcon_client

        # Store the total number of commands for completion tracking
        total_commands = len(self.scheduled_commands)

        # Store metadata before clearing for debugging purposes
        self.last_batch_metadata = {
            "commands": self.scheduled_commands.copy(),
            "total_count": total_commands,
        }

        # CRITICAL: Sort commands by tick before submitting to ensure Lua indices
        # match the expected sorted order from Python side
        self.scheduled_commands.sort(key=lambda x: x["tick"])

        # Submit the batch directly to the server
        import json

        batch_json = json.dumps(self.scheduled_commands, cls=PrototypeJSONEncoder)

        # Validate the JSON as a Lua string
        escaped_batch_json = batch_json.replace('"', '\\"')

        try:
            # Register sequence start with grace period using our unique sequence ID
            sequence_cmd = f'/sc global.actions.register_sequence_start("{self.sequence_id}", {self.grace_period})'
            rcon_client.send_command(sequence_cmd)

            # Submit the batch - let Lua generate the batch_id
            lua_command = (
                f'/sc global.actions.submit_scheduled_batch("{escaped_batch_json}")'
            )
            is_valid, validation_msg = validate_lua_syntax(lua_command)
            if not is_valid:
                print(
                    f"❌ Manager {self.manager_id}: Lua validation failed: {validation_msg}"
                )

            submit_result_raw = rcon_client.send_command(lua_command)
            submit_result = _lua2python("submit_batch", submit_result_raw)

        except Exception as e:
            print(f"❌ Manager {self.manager_id}: Exception during submission: {e}")
            return {"error": str(e)}

        # Extract batch_id from submission result
        batch_id_from_result = None
        if isinstance(submit_result, tuple) and len(submit_result) >= 1:
            response_data = submit_result[0]
            if isinstance(response_data, dict) and "batch_id" in response_data:
                batch_id_from_result = response_data["batch_id"]
            else:
                print(
                    f"❌ Manager {self.manager_id}: No batch_id found in response data"
                )
        else:
            print(
                f"❌ Manager {self.manager_id}: Unexpected result format: {type(submit_result)}"
            )

        if not batch_id_from_result:
            print(f"❌ Manager {self.manager_id}: Failed to get batch_id from server")
            return {"error": "Failed to get batch_id"}

        self.current_batch_id = batch_id_from_result
        self.expected_command_count = total_commands

        # Clear the batch
        self.scheduled_commands.clear()

        return {"batch_id": batch_id_from_result, "submitted": True}

    def wait_for_batch_completion(self, timeout_seconds=30):
        """Wait for the batch to complete and return results."""
        if not self.current_batch_id:
            raise RuntimeError("No active batch to wait for")

        import time

        rcon_client = self.rcon_connection or self.instance.rcon_client

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # Check batch status using dedicated RCON connection
            result_raw = rcon_client.send_command(
                f'/sc global.actions.get_batch_results("{self.current_batch_id}")'
            )
            result = _lua2python("get_batch_results", result_raw)

            # Extract batch results
            batch_results = None
            if isinstance(result, tuple) and len(result) >= 1:
                response_data = result[0]
                if isinstance(response_data, dict) and "completed" in response_data:
                    batch_results = response_data

            if batch_results and batch_results.get("completed"):
                # Clean up server-side results
                rcon_client.send_command(
                    f'/sc global.actions.clear_batch_results("{self.current_batch_id}")'
                )

                self.current_batch_id = None
                return batch_results["results"]

            time.sleep(0.1)  # Wait before checking again

        raise TimeoutError(f"Batch did not complete within {timeout_seconds} seconds")

    def submit_batch_and_wait(self, timeout_seconds=30):
        """Submit batch and wait for completion, returning all results."""
        self.submit_batch()
        return self.wait_for_batch_completion(timeout_seconds)

    def submit_batch_and_stream(self, timeout_seconds=30, poll_interval=0.1):
        """Submit batch and yield results as they become available.

        Args:
            timeout_seconds: Maximum time to wait for batch completion
            poll_interval: How often to check for new results (in seconds)

        Yields:
            dict: Individual command results as they complete

        Each yielded result contains:
        - command_index: The index of the command in the batch
        - command: The command name
        - success: Whether the command succeeded
        - result: The command result or error message
        - tick: The game tick when the command was executed
        """
        if not self.scheduled_commands:
            return

        # Submit the batch
        submit_result = self.submit_batch()

        if "error" in submit_result:
            print(
                f"❌ Manager {self.manager_id}: Batch submission failed: {submit_result}"
            )
            return

        if not self.current_batch_id:
            print(f"❌ Manager {self.manager_id}: No current batch ID after submission")
            return

        import time

        rcon_client = self.rcon_connection or self.instance.rcon_client

        start_time = time.time()
        yielded_results = set()  # Track which results we've already yielded
        poll_count = 0

        try:
            while time.time() - start_time < timeout_seconds:
                poll_count += 1
                # Check batch status using dedicated RCON connection
                status_cmd = (
                    f'/sc global.actions.get_batch_results("{self.current_batch_id}")'
                )

                try:
                    result_raw = rcon_client.send_command(status_cmd)
                    result = _lua2python("get_batch_results", result_raw)

                except Exception as e:
                    print(
                        f"❌ Manager {self.manager_id}: Poll {poll_count} failed: {e}"
                    )
                    time.sleep(poll_interval)
                    continue

                # Process responses
                if isinstance(result, tuple) and len(result) >= 1:
                    response_data = result[0]

                    # Handle proper Lua table response format
                    if isinstance(response_data, dict):
                        batch_id_from_response = response_data.get("batch_id")
                        if batch_id_from_response != self.current_batch_id:
                            time.sleep(poll_interval)
                            continue

                        # Process results
                        batch_results_data = response_data.get("results", {})
                        is_complete = response_data.get("completed", False)
                        sequence_start_tick = response_data.get(
                            "sequence_start_tick", 0
                        )

                        # Yield new results - handle both numeric and string keys
                        new_results_count = 0
                        num_commands = 0
                        for cmd_index_key, cmd_result in batch_results_data.items():
                            try:
                                # Convert key to integer (Lua arrays start at 1, Python at 0)
                                if isinstance(cmd_index_key, str):
                                    command_index = (
                                        int(cmd_index_key) - 1
                                    )  # Convert 1-based to 0-based
                                elif isinstance(cmd_index_key, int):
                                    command_index = (
                                        cmd_index_key - 1
                                    )  # Convert 1-based to 0-based
                                else:
                                    print(
                                        f"❌ Manager {self.manager_id}: Unexpected command index type: {type(cmd_index_key)}"
                                    )
                                    continue

                                num_commands += 1
                                if command_index not in yielded_results:
                                    yielded_results.add(command_index)
                                    new_results_count += 1

                                    # Calculate sequence-relative tick: game_tick - sequence_start_tick
                                    game_tick = cmd_result.get("game_tick", 0)
                                    sequence_relative_tick = (
                                        game_tick - sequence_start_tick
                                        if sequence_start_tick > 0
                                        else game_tick
                                    )

                                    result_dict = {
                                        "command_index": command_index,
                                        "command": cmd_result.get("command", "unknown"),
                                        "success": cmd_result.get("success", False),
                                        "result": cmd_result.get("result"),
                                        "tick": sequence_relative_tick,
                                        "planned_tick": cmd_result.get(
                                            "planned_tick", "?"
                                        ),  # Pass through planned_tick from Lua
                                    }

                                    yield result_dict

                            except (ValueError, TypeError) as e:
                                print(
                                    f"❌ Manager {self.manager_id}: Failed to parse command index {cmd_index_key}: {e}"
                                )
                        print(
                            f"POLL {poll_count} - num_commands: {num_commands}, new_results: {new_results_count}"
                        )
                        # Check if batch is complete
                        if is_complete:
                            # Clean up using dedicated RCON connection
                            try:
                                rcon_client.send_command(
                                    f'/sc global.actions.clear_batch_results("{self.current_batch_id}")'
                                )
                                print(f"POLL {poll_count} - CLEANED UP")
                            except Exception as e:
                                print(
                                    f"❌ Manager {self.manager_id}: Cleanup failed: {e}"
                                )

                            self.current_batch_id = None
                            return
                    else:
                        print(f"POLL {poll_count} - NO RESULTS, result: {result}")
                else:
                    print(
                        f"POLL {poll_count} - NO RESULTS, type(result): {type(result)}, len(result): {len(result)}"
                    )

                time.sleep(poll_interval)

            print(
                f"❌ Manager {self.manager_id}: Timeout after {timeout_seconds}s ({poll_count} polls)"
            )
            raise TimeoutError(
                f"Batch did not complete within {timeout_seconds} seconds"
            )

        except Exception as e:
            print(f"❌ Manager {self.manager_id}: Exception in streaming: {e}")
            # Clean up on error
            if self.current_batch_id:
                try:
                    rcon_client.send_command(
                        f'/sc global.actions.clear_batch_results("{self.current_batch_id}")'
                    )
                except:
                    pass  # Best effort cleanup
                self.current_batch_id = None
            raise


class FactorioInstance:
    namespace_class = FactorioNamespace
    _cleanup_registered = False  # Only register cleanup once per process

    def __init__(
        self,
        address=None,
        fast=False,
        tcp_port=27000,
        inventory=None,
        cache_scripts=True,
        all_technologies_researched=True,
        peaceful=True,
        num_agents=1,
        regenerate="map",
        batch_grace_period=5,  # New parameter
        max_concurrent_batches=1,  # New parameter for concurrency
        **kwargs,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.num_agents = num_agents
        self.persistent_vars = {}
        self.tcp_port = tcp_port
        self.max_concurrent_batches = max_concurrent_batches

        # Create multiple RCON connections for concurrent batch processing
        self.rcon_connections = []
        self.batch_managers = []

        # Primary connection for main operations
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.rcon_connections.append(self.rcon_client)

        # Create additional connections for concurrent batch processing
        for i in range(max_concurrent_batches - 1):
            try:
                additional_rcon = self.connect_to_server(address, tcp_port)[0]
                self.rcon_connections.append(additional_rcon)
            except Exception as e:
                print(f"❌ Could not create additional RCON connection {i + 2}: {e}")
                break

        # Test all connections
        for i, conn in enumerate(self.rcon_connections):
            try:
                conn.send_command("/sc rcon.print('test_connection_" + str(i) + "')")
            except Exception as e:
                print(f"❌ RCON connection {i} test failed: {e}")

        print(
            f"Created {len(self.rcon_connections)} RCON connection(s) for batch processing"
        )

        self.all_technologies_researched = all_technologies_researched
        self.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0
        self._is_initialised = False
        self.regenerate = regenerate

        self.peaceful = peaceful
        self.namespaces = [self.namespace_class(self, i) for i in range(num_agents)]

        self.lua_script_manager = LuaScriptManager(self.rcon_client, cache_scripts)
        self.script_dict = {
            **self.lua_script_manager.lib_scripts,
            **self.lua_script_manager.tool_scripts,
        }

        # Initialize hooks as dictionaries to organize callbacks by tool name
        self.pre_tool_hooks = {}
        self.post_tool_hooks = {}

        # Load the python controllers that correspond to the Lua scripts
        self.setup_tools(self.lua_script_manager)

        # Initialize multiple batch managers - one per RCON connection
        for i, rcon_conn in enumerate(self.rcon_connections):
            batch_manager = BatchManager(
                self, batch_grace_period, rcon_connection=rcon_conn, manager_id=i
            )
            self.batch_managers.append(batch_manager)

        # Primary batch manager for backward compatibility
        self.batch_manager = (
            self.batch_managers[0]
            if self.batch_managers
            else BatchManager(self, batch_grace_period)
        )

        # Print health summary
        print("Batch Manager Health Summary:")
        for manager in self.batch_managers:
            status = manager.get_health_status()
            health_status = (
                "✅ Healthy" if status["connection_healthy"] else "❌ Unhealthy"
            )
            print(f"   Manager {status['manager_id']}: {health_status}")

        if inventory is None:
            inventory = {}
        self.initial_inventory = inventory
        self.initialise(fast)
        self.initial_score = 0
        try:
            self.first_namespace.score()
        except Exception:
            # Invalidate cache if there is an error
            self.lua_script_manager = LuaScriptManager(self.rcon_client, False)
            self.script_dict = {
                **self.lua_script_manager.lib_scripts,
                **self.lua_script_manager.tool_scripts,
            }
            self.setup_tools(self.lua_script_manager)
            self.initialise(fast)

        self.initial_score, goal = self.first_namespace.score()
        # Register the cleanup method to be called on exit (only once per process)
        if not FactorioInstance._cleanup_registered:
            atexit.register(self.cleanup)
            FactorioInstance._cleanup_registered = True

    @property
    def namespace(self):
        if len(self.namespaces) == 1:
            return self.namespaces[0]
        else:
            raise ValueError("Can only use .namespace for single-agent instances")

    @property
    def first_namespace(
        self,
    ) -> Optional[FactorioNamespace]:  # Add this property if used
        return self.namespaces[0] if self.namespaces else None

    @property
    def is_multiagent(self):
        return self.num_agents > 1

    def reset(self, game_state: Optional[GameState] = None):
        # Reset the namespace (clear variables, functions etc)
        assert not game_state or len(game_state.inventories) == self.num_agents, (
            "Game state must have the same number of inventories as num_agents"
        )

        for namespace in self.namespaces:
            namespace.reset()

        if not game_state:
            # Reset the game instance
            inventories = [self.initial_inventory] * self.num_agents
            self._reset(inventories)
            # Reset the technologies
            if not self.all_technologies_researched:
                self.first_namespace._load_research_state(
                    ResearchState(
                        technologies={},
                        research_progress=0,
                        current_research=None,
                        research_queue=[],
                        progress={},
                    )
                )
        else:
            # Reset the game instance with the correct player's inventory and messages if multiagent
            self._reset(game_state.inventories)

            # Load entities into the game
            self.first_namespace._load_entity_state(
                game_state.entities, decompress=True
            )

            # Load research state into the game
            self.first_namespace._load_research_state(game_state.research)

            # Load messages for each agent
            if game_state.agent_messages:
                for i in range(self.num_agents):
                    if i < len(game_state.agent_messages):
                        self.namespaces[i].load_messages(game_state.agent_messages[i])

            # Reset elapsed ticks
            self._reset_elapsed_ticks()

            # Load variables / functions from game state
            for i in range(self.num_agents):
                self.namespaces[i].load(game_state.namespaces[i])

        try:
            self.initial_score, _ = self.first_namespace.score()
        except Exception:
            self.initial_score = 0

        # Clear renderings
        self.begin_transaction()
        self.add_command("/sc rendering.clear()", raw=True)
        self.execute_transaction()

    def set_inventory(self, inventory: Dict[str, Any], agent_idx: int = 0):
        self.begin_transaction()
        self.add_command("clear_inventory", agent_idx + 1)
        self.execute_transaction()
        # print("RCON output:", result)
        self.begin_transaction()
        # kwargs dict to json
        inventory_items = {k: v for k, v in inventory.items()}
        inventory_items_json = json.dumps(inventory_items)
        player_idx = agent_idx + 1
        self.add_command(
            f"/sc global.actions.initialise_inventory({player_idx}, '{inventory_items_json}')",
            raw=True,
        )

        self.execute_transaction()

    def speed(self, speed):
        self.rcon_client.send_command(f"/sc game.speed = {speed}")
        self._speed = speed

    def get_speed(self):
        return self._speed

    def get_elapsed_ticks(self):
        response = self.rcon_client.send_command(
            "/sc rcon.print(global.elapsed_ticks or 0)"
        )
        if not response:
            return 0
        return int(response)

    def get_system_prompt(self, agent_idx: int = 0) -> str:
        """
        Get the system prompt for the Factorio environment.
        This includes all the available actions, objects, and entities that the agent can interact with.
        We get the system prompt by loading the schema, definitions, and entity definitions from their source files.
        These are converted to their signatures - leaving out the implementations.
        :return:
        """
        execution_path = Path(os.path.dirname(os.path.realpath(__file__)))
        generator = SystemPromptGenerator(str(execution_path))
        multiagent_str = ""
        if self.num_agents > 1:
            player_idx = agent_idx + 1
            multiagent_str = (
                f"## MULTIAGENT INSTRUCTIONS\n"
                f"You are Agent {player_idx} out of {self.num_agents} agent(s) in the game. "
                f"Follow your specific instructions given to you by the task."
                f"Use the send_message() tool regularly to communicate with other agents about your current activities and any challenges you encounter. "
                f"Start each program with a send_message() call to explain what you are doing. "
                f"End each program with a send_message() call to confirm your actions. If your program errors out prior to send_message() being called, the message will not be sent. "
            )
        return generator.generate(multiagent_str)

    def connect_to_server(self, address, tcp_port):
        try:
            rcon_client = RCONClient(address, tcp_port, "factorio")  #'quai2eeha3Lae7v')
            address = address
        except ConnectionError as e:
            print(e)
            rcon_client = RCONClient("localhost", tcp_port, "factorio")
            address = "localhost"

        try:
            rcon_client.connect()
            player_count = rcon_client.send_command("/sc rcon.print(#game.players)")
            if int(player_count) == 0:
                print(
                    "WARNING: LuaPlayer hasn't been initialised into the game. Entity placement behavior _may_ be incorrect for boilers and pumps."
                )

        except Exception as e:
            raise ConnectionError(
                f"Could not connect to {address} at tcp/{tcp_port}: \n{e.args[0]}"
            )

        print(f"Connected to {address} client at tcp/{tcp_port}.")
        return rcon_client, address

    def setup_tools(self, lua_script_manager):
        """
        Load Python controllers from valid tool directories (those containing both client.py and server.lua)
        """
        tool_dir = _get_dir("tools")
        self.controllers = {}

        def snake_to_camel(snake_str):
            return "".join(word.capitalize() for word in snake_str.split("_"))

        # Create a function that wraps a tool's call method to execute hooks
        def create_hook_wrapper(tool_name, original_callable):
            from functools import wraps

            @wraps(original_callable)
            def wrapper(*args, **kwargs):
                # Execute pre-tool hooks
                try:
                    self.execute_pre_tool_hooks(
                        tool_name, original_callable, *args, **kwargs
                    )
                except Exception as e:
                    print(f"Error in pre-tool hook for {tool_name}: {e}")

                # Execute the original callable
                result = original_callable(*args, **kwargs)

                # Execute post-tool hooks
                try:
                    self.execute_post_tool_hooks(tool_name, original_callable, result)
                except Exception as e:
                    print(f"Error in post-tool hook for {tool_name}: {e}")

                return result

            return wrapper

        # Walk through all subdirectories
        for dirpath, _, filenames in os.walk(tool_dir):
            # Skip the root directory
            if dirpath == tool_dir:
                continue

            # Check if this is a valid tool directory
            server_file = os.path.join(dirpath, "server.lua")
            client_file = os.path.join(dirpath, "client.py")

            if os.path.isfile(server_file) and os.path.isfile(client_file):
                # Get the tool name from the directory
                tool_name = os.path.basename(dirpath)

                directory_name = Path(dirpath).parent.name
                # Load the Python module
                module_spec = importlib.util.spec_from_file_location(
                    tool_name,
                    client_file,
                    # str(Path(client_file))
                )
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)

                class_name = snake_to_camel(tool_name)

                # Handle special case renames
                if tool_name == "place_entity":
                    class_name = "PlaceObject"
                if tool_name == "score":
                    class_name = "Reward"

                try:
                    for i in range(self.num_agents):
                        # Get and instantiate the controller class
                        callable_class = getattr(module, class_name)
                        callable_instance = callable_class(
                            lua_script_manager, self.namespaces[i]
                        )

                        # Create a wrapper that will execute hooks
                        wrapped_instance = create_hook_wrapper(
                            tool_name.lower(), callable_instance
                        )

                        # Store the controller and add it to namespace
                        self.controllers[tool_name.lower()] = callable_instance

                        if directory_name == "admin":
                            # If this is an admin method, we hide it in the namespace by adding a shebang
                            setattr(
                                self.namespaces[i],
                                f"_{tool_name.lower()}",
                                wrapped_instance,
                            )
                        else:
                            setattr(
                                self.namespaces[i], tool_name.lower(), wrapped_instance
                            )

                except Exception as e:
                    raise Exception(
                        f"Could not instantiate {class_name} from {client_file}. {e}"
                    )

    def eval_with_error(self, expr, agent_idx=0, timeout=60):
        """Evaluate an expression with a timeout, and return the result without error handling"""

        def handler(signum, frame):
            raise TimeoutError()

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)

        try:
            return self.namespaces[agent_idx].eval_with_timeout(expr)
        finally:
            signal.alarm(0)

    def eval(self, expr, agent_idx=0, timeout=60):
        "Evaluate several lines of input, returning the result of the last line with a timeout"
        try:
            return self.eval_with_error(expr, agent_idx, timeout)
        except TimeoutError:
            return -1, "", "Error: Evaluation timed out"
        except Exception as e:
            message = e.args[0].replace("\\n", "")
            return -1, "", f"{message}".strip()

    def _get_command(self, command, parameters=[], measured=True):
        prefix = "/sc " if not measured else "/command "
        if command in self.script_dict:
            script = prefix + self.script_dict[command]
            for index in range(len(parameters)):
                script = script.replace(
                    f"arg{index + 1}", lua.encode(parameters[index])
                )
        else:
            script = command
        return script

    def calculate_optimal_zoom(self, bounds: BoundingBox, resolution="1920x1080"):
        """
        Calculate the optimal zoom level to fit the factory in the screenshot.

        Args:
            bounds (BoundingBox): Factory bounds containing width and height
            resolution (str): Screenshot resolution in format "WIDTHxHEIGHT"

        Returns:
            float: Optimal zoom level
        """
        if not bounds:
            return 1

        # Parse resolution
        width, height = map(int, resolution.split("x"))
        aspect_ratio = width / height

        # Get factory dimensions
        factory_width = bounds.width()
        factory_height = bounds.height()

        # Base tiles visible at zoom level 1
        # These values are approximate for Factorio's zoom levels
        BASE_VISIBLE_HEIGHT = 25  # tiles visible vertically at zoom 1
        BASE_VISIBLE_WIDTH = BASE_VISIBLE_HEIGHT * aspect_ratio

        # Calculate required zoom based on both dimensions
        zoom_by_width = BASE_VISIBLE_WIDTH / factory_width
        zoom_by_height = BASE_VISIBLE_HEIGHT / factory_height

        # Use the smaller zoom to ensure entire factory is visible
        optimal_zoom = min(zoom_by_width, zoom_by_height)

        # Add padding (20% margin)
        optimal_zoom *= 0.8

        # Clamp zoom to reasonable values
        # Factorio's min and max zoom levels
        MIN_ZOOM = 0.1
        MAX_ZOOM = 4.0

        optimal_zoom = max(MIN_ZOOM, min(MAX_ZOOM, optimal_zoom))

        return round(optimal_zoom, 2)

    def screenshot(
        self,
        script_output_path,
        resolution="1920x1080",
        save_path=None,
        zoom=None,
        center_on_factory=False,
    ):
        """
        Take a screenshot in game and optionally save it to a specific location.

        This does nothing in headless mode.

        Args:
            resolution (str, optional): Screenshot resolution (e.g., "1920x1080")
            save_path (str, optional): Path where to save the screenshot copy
            zoom (float, optional): Zoom level for the screenshot (e.g., 0.5 for zoomed out, 2.0 for zoomed in)

        Returns:
            str: Path to the saved screenshot, or None if failed
        """
        # Clear rendering
        camera: Camera = self.first_namespace._get_factory_centroid()
        POS_STRING = ""
        if camera:
            centroid = camera.position
            POS_STRING = (
                ", position={x=" + str(centroid.x) + ", y=" + str(centroid.y) + "}"
            )

        self.rcon_client.send_command("/sc rendering.clear()")

        # # Calculate optimal zoom if not specified
        # if zoom is None:
        #     zoom = self.calculate_optimal_zoom(bounds, resolution)

        command = (
            "/sc game.take_screenshot({player=1, zoom="
            + str(camera.zoom)
            + ", show_entity_info=true, hide_clouds=true, hide_fog=true "
            + POS_STRING
            + "})"
        )
        self.rcon_client.send_command(command)
        time.sleep(1)
        # if not response:
        #     return None

        # Wait for the screenshot file to appear and get its path
        screenshot_path = self._get_latest_screenshot(
            script_output_path=script_output_path
        )
        if not screenshot_path:
            print("Screenshot file not found")
            return None

        # If save_path is provided, copy the screenshot there
        if save_path:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

                # Copy the file
                shutil.copy2(screenshot_path, save_path)
                return save_path
            except Exception as e:
                print(f"Failed to copy screenshot: {e}")
                return screenshot_path

        return screenshot_path

    def _get_latest_screenshot(self, script_output_path, max_wait=2):
        """
        Get the path to the latest screenshot in the script-output directory.
        Waits up to max_wait seconds for the file to appear.
        """
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Get list of screenshot files
                screenshots = [
                    f
                    for f in os.listdir(script_output_path)
                    if f.endswith(".png") and f.startswith("screenshot")
                ]

                if screenshots:
                    # Sort by modification time to get the latest
                    latest = max(
                        screenshots,
                        key=lambda x: os.path.getmtime(
                            os.path.join(script_output_path, x)
                        ),
                    )
                    return os.path.join(script_output_path, latest)
            except Exception as e:
                print(f"Error checking for screenshots: {e}")

            time.sleep(0.5)  # Wait before checking again

        return None

    def _send(self, command, *parameters, trace=False) -> List[str]:
        """
        Send a Lua command to the underlying Factorio instance
        """
        start = timer()
        script = self._get_command(command, parameters=list(parameters), measured=False)
        lua_response = self.rcon_client.send_command(script)
        # self.add_command(command, *parameters)
        # response = self._execute_transaction()
        # print(lua_response)
        return _lua2python(command, lua_response, start=start)

    def _reset_static_achievement_counters(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.add_command(
            "/sc global.crafted_items = {}; global.harvested_items = {}", raw=True
        )
        self.execute_transaction()

    def _reset_elapsed_ticks(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.add_command("/sc global.elapsed_ticks = 0", raw=True)
        self.execute_transaction()

    def _reset(self, inventories: List[Dict[str, Any]]):
        self.begin_transaction()
        if self.regenerate == "resources":
            regenerate_func = "global.actions.regenerate_resources(1)"
        elif self.regenerate == "map":
            regenerate_func = "global.actions.regenerate_map(1)"
        else:
            raise ValueError(f"Invalid regenerate value: {self.regenerate}")

        self.add_command(
            f"/sc global.alerts = {{}}; game.reset_game_state(); global.actions.reset_production_stats(); {regenerate_func}",
            raw=True,
        )
        # self.add_command('/sc script.on_nth_tick(nil)', raw=True) # Remove all dangling event handlers

        self.execute_transaction()

        self.begin_transaction()
        self.add_command("/sc global.actions.clear_walking_queue()", raw=True)
        for i in range(self.num_agents):
            player_index = i + 1
            self.add_command(
                f"/sc global.actions.clear_entities({player_index})", raw=True
            )
            inventory_items = {k: v for k, v in inventories[i].items()}
            inventory_items_json = json.dumps(inventory_items)
            self.add_command(
                f"/sc global.actions.initialise_inventory({player_index}, '{inventory_items_json}')",
                raw=True,
            )

        if self.all_technologies_researched:
            self.add_command(
                "/sc global.agent_characters[1].force.research_all_technologies()",
                raw=True,
            )
        self.execute_transaction()
        # self.clear_entities()
        self._reset_static_achievement_counters()
        self._reset_elapsed_ticks()

    def _execute_transaction(self) -> Dict[str, Any]:
        start = timer()
        rcon_commands = {}
        for idx, (command, parameters, is_raw) in enumerate(
            self.current_transaction.get_commands()
        ):
            if is_raw:
                rcon_commands[f"{idx}_{command}"] = command
            else:
                script = self._get_command(
                    command, parameters=parameters, measured=False
                )
                rcon_commands[f"{idx}_{command}"] = script

        lua_responses = self.rcon_client.send_commands(rcon_commands)

        results = {}
        for command, response in lua_responses.items():
            results[command] = _lua2python(command, response, start=start)

        self.current_transaction.clear()
        return results

    def begin_transaction(self):
        if not hasattr(self, "current_transaction"):
            self.current_transaction = FactorioTransaction()
        elif self.current_transaction:
            self.current_transaction.clear()
        else:
            self.current_transaction = FactorioTransaction()

    def add_command(self, command: str, *parameters, raw=False):
        if not hasattr(self, "current_transaction"):
            self.begin_transaction()
        self.current_transaction.add_command(command, *parameters, raw=raw)

    def execute_transaction(self) -> Dict[str, Any]:
        return self._execute_transaction()

    def initialise(self, fast=True):
        self.begin_transaction()
        self.add_command("/sc global.alerts = {}", raw=True)
        self.add_command("/sc global.elapsed_ticks = 0", raw=True)
        self.add_command(
            "/sc global.fast = {}".format("true" if fast else "false"), raw=True
        )
        self.execute_transaction()

        # Create characters for all agents
        self._create_agent_game_characters()

        init_scripts = [
            "initialise",
            "clear_entities",
            "alerts",
            "util",
            "priority_queue",
            "connection_points",
            "recipe_fluid_connection_mappings",
            "serialize",
            "production_score",
            "initialise_inventory",
            "scheduled_batch",  # Add the new batch scheduler
        ]
        if self.peaceful:
            init_scripts.append("enemies")
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)

        inventories = [self.initial_inventory] * self.num_agents
        self._reset(inventories)
        self.first_namespace._clear_collision_boxes()

    def _create_agent_game_characters(self):
        """Create Factorio characters for all agents in the game."""
        # Create characters in Factorio
        self.begin_transaction()
        color_logic = ""
        if self.num_agents > 1:
            color_logic = "if i==1 then char.color={r=0,g=1,b=0,a=1} elseif i==2 then char.color={r=0,g=0,b=1,a=1} end;"

        self.add_command(
            f'/sc global.agent_characters = {{}}; for _,c in pairs(game.surfaces[1].find_entities_filtered{{type="character"}}) do if c then c.destroy() end end; for i=1,{self.num_agents} do local char = game.surfaces[1].create_entity{{name="character",position={{x=0,y=(i-1)*2}},force=game.forces.player}}; {color_logic} global.agent_characters[i]=char end',
            raw=True,
        )
        self.add_command("/sc player = global.agent_characters[1]", raw=True)
        self.execute_transaction()

    def get_warnings(self, seconds=10):
        """
        Get all alerts that have been raised before the last n seconds
        :param seconds: The number of seconds to look back
        :return:
        """
        start = timer()
        command = f"/silent-command rcon.print(dump(global.get_alerts({seconds})))"
        lua_response = self.rcon_client.send_command(command)
        # print(lua_response)
        alert_dict, duration = _lua2python("alerts", lua_response, start=start)
        if isinstance(alert_dict, dict):
            alerts = list(alert_dict.values())
            alert_strings = []
            for alert in alerts:
                issues = ", ".join(
                    [al.replace("_", " ") for al in list(alert["issues"].values())]
                )
                alert_strings.append(
                    f"{alert['entity_name']} at {tuple(alert['position'].values())}: {issues}"
                )

            return alert_strings
        else:
            return []

    def _prepare_callable(self, value):
        if callable(value):
            if inspect.ismethod(value) or inspect.isfunction(value):
                # For methods and functions, bind them to the instance
                return value.__get__(self, self.__class__)
            elif hasattr(value, "__call__"):
                # For objects with a __call__ method (like your controllers)
                return lambda *args, **kwargs: value(*args, **kwargs)
            else:
                # For other callables, return as is
                return value
        else:
            # For non-callable attributes, return as is
            return value

    def create_factorio_namespace(self):
        namespace = {}

        def add_to_namespace(name, value):
            if isinstance(value, enum.EnumMeta):
                # For enums, add the enum itself and all its members
                namespace[name] = value
                for member_name, member_value in value.__members__.items():
                    namespace[f"{name}.{member_name}"] = member_value
            elif inspect.ismodule(value) and value.__name__.startswith("factorio_"):
                # For Factorio-related modules, add the module and its attributes
                namespace[name] = value
                for attr_name, attr_value in inspect.getmembers(value):
                    if not attr_name.startswith("_"):
                        namespace[f"{name}.{attr_name}"] = attr_value
            elif isinstance(value, type):
                # For classes, add the class itself
                namespace[name] = value
            else:
                # For other values, add them directly
                namespace[name] = value

        # Add all public instance attributes and methods
        for name, value in vars(self).items():
            if not name.startswith("_"):
                add_to_namespace(name, value)

        # Add dynamically loaded controllers
        for name, controller in self.controllers.items():
            namespace[name] = self._prepare_callable(controller)

        # Add all class-level attributes
        for name, value in vars(self.__class__).items():
            if not name.startswith("_") and name not in namespace:
                add_to_namespace(name, value)

        # Add all global variables from the module where FactorioInstance is defined
        module_globals = inspect.getmodule(self.__class__).__dict__
        for name, value in module_globals.items():
            if not name.startswith("_") and name not in namespace:
                add_to_namespace(name, value)

        return types.SimpleNamespace(**namespace)

    def run_func_in_factorio_env(self, func):
        """
        This decorator allows a function to be run in the Factorio environment, with access to all Factorio objects
        :param func:
        :return:
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            factorio_ns = self.create_factorio_namespace()

            # Create a new function with the Factorio namespace as its globals
            new_globals = {**func.__globals__, **vars(factorio_ns)}
            new_func = types.FunctionType(
                func.__code__,
                new_globals,
                func.__name__,
                func.__defaults__,
                func.__closure__,
            )

            return new_func(*args, **kwargs)

        return wrapper

    def run_snippet_file_in_factorio_env(self, file_path, clean=True):
        """
        Execute a Python file in the Factorio environment, with access to all Factorio objects and support for
        debugging and breakpoints
        :param file_path:
        :return:
        """
        factorio_ns = self.create_factorio_namespace()

        # Prepare the globals for the snippet execution
        snippet_globals = {
            "__name__": "__main__",
            "__file__": file_path,
            **vars(factorio_ns),
        }
        try:
            # Execute the file directly
            with open(file_path, "r") as file:
                code = compile(file.read(), file_path, "exec")
                exec(code, snippet_globals)
        except Exception as e:
            print(f"Error executing file {file_path}: {e}")
            traceback.print_exc()
            raise e
        finally:
            # Ensure cleanup is performed
            if clean:
                self.cleanup()

    def register_post_tool_hook(self, tool_name, callback=None):
        """
        Register a hook to be called after a specific tool is executed.
        Can be used as a regular function or as a decorator.

        Args:
            tool_name (str): Name of the tool to hook into
            callback (callable, optional): Function to call after the tool is executed.
                                          Will receive the tool instance and the result as arguments.

        Returns:
            If used as a regular function (with callback provided), returns the callback.
            If used as a decorator (without callback), returns a decorator function.
        """
        # When used as a decorator without parentheses: @register_post_tool_hook
        if tool_name is not None and callback is None and callable(tool_name):
            callback = tool_name
            tool_name = callback.__name__
            if not hasattr(self, "post_tool_hooks"):
                self.post_tool_hooks = {}
            if tool_name not in self.post_tool_hooks:
                self.post_tool_hooks[tool_name] = []
            self.post_tool_hooks[tool_name].append(callback)
            return callback

        # When used as a decorator with arguments: @register_post_tool_hook("tool_name")
        if callback is None:

            def decorator(func):
                if not hasattr(self, "post_tool_hooks"):
                    self.post_tool_hooks = {}
                if tool_name not in self.post_tool_hooks:
                    self.post_tool_hooks[tool_name] = []
                self.post_tool_hooks[tool_name].append(func)
                return func

            return decorator

        # When used as a regular function: register_post_tool_hook("tool_name", callback_func)
        if not callable(callback):
            raise TypeError("Callback must be callable")

        if not hasattr(self, "post_tool_hooks"):
            self.post_tool_hooks = {}
        if tool_name not in self.post_tool_hooks:
            self.post_tool_hooks[tool_name] = []

        self.post_tool_hooks[tool_name].append(callback)
        return callback

    def register_pre_tool_hook(self, tool_name, callback=None):
        """
        Register a hook to be called before a specific tool is executed.
        Can be used as a regular function or as a decorator.

        Args:
            tool_name (str): Name of the tool to hook into
            callback (callable, optional): Function to call before the tool is executed.
                                          Will receive the tool instance and the arguments as parameters.

        Returns:
            If used as a regular function (with callback provided), returns the callback.
            If used as a decorator (without callback), returns a decorator function.
        """
        # When used as a decorator without parentheses: @register_pre_tool_hook
        if tool_name is not None and callback is None and callable(tool_name):
            callback = tool_name
            tool_name = callback.__name__
            if not hasattr(self, "pre_tool_hooks"):
                self.pre_tool_hooks = {}
            if tool_name not in self.pre_tool_hooks:
                self.pre_tool_hooks[tool_name] = []
            self.pre_tool_hooks[tool_name].append(callback)
            return callback

        # When used as a decorator with arguments: @register_pre_tool_hook("tool_name")
        if callback is None:

            def decorator(func):
                if not hasattr(self, "pre_tool_hooks"):
                    self.pre_tool_hooks = {}
                if tool_name not in self.pre_tool_hooks:
                    self.pre_tool_hooks[tool_name] = []
                self.pre_tool_hooks[tool_name].append(func)
                return func

            return decorator

        # When used as a regular function: register_pre_tool_hook("tool_name", callback_func)
        if not callable(callback):
            raise TypeError("Callback must be callable")

        if not hasattr(self, "pre_tool_hooks"):
            self.pre_tool_hooks = {}
        if tool_name not in self.pre_tool_hooks:
            self.pre_tool_hooks[tool_name] = []

        self.pre_tool_hooks[tool_name].append(callback)
        return callback

    def execute_post_tool_hooks(self, tool_name, tool_instance, result):
        """
        Execute all hooks registered for a tool after it has been executed.

        Args:
            tool_name (str): Name of the tool
            tool_instance: The tool instance that was executed
            result: The result of the tool execution
        """
        if tool_name in self.post_tool_hooks:
            for callback in self.post_tool_hooks[tool_name]:
                try:
                    callback(tool_instance, result)
                except Exception as e:
                    print(f"Error in post-tool hook for {tool_name}: {e}")

    def execute_pre_tool_hooks(self, tool_name, tool_instance, *args, **kwargs):
        """
        Execute all hooks registered for a tool before it is executed.

        Args:
            tool_name (str): Name of the tool
            tool_instance: The tool instance to be executed
            *args, **kwargs: The arguments passed to the tool
        """
        if tool_name in self.pre_tool_hooks:
            for callback in self.pre_tool_hooks[tool_name]:
                try:
                    callback(tool_instance, *args, **kwargs)
                except Exception as e:
                    print(f"Error in pre-tool hook for {tool_name}: {e}")

    def get_available_batch_manager(self):
        """Get an available batch manager for concurrent processing."""
        # Find a batch manager that's not currently active
        for manager in self.batch_managers:
            if not manager.is_active or not manager.current_batch_id:
                return manager

        # If all are busy, return the first one (will queue)
        return self.batch_managers[0] if self.batch_managers else self.batch_manager

    def cleanup(self):
        # Close all RCON connections
        if hasattr(self, "rcon_client") and self.rcon_client:
            self.rcon_client.close()

        # Close additional RCON connections
        if hasattr(self, "rcon_connections"):
            for rcon_conn in self.rcon_connections[1:]:  # Skip the primary one
                try:
                    if rcon_conn:
                        rcon_conn.close()
                except Exception as e:
                    print(f"Error closing RCON connection: {e}")

        self.post_tool_hooks = {}
        self.pre_tool_hooks = {}

        # Join all non-daemon threads
        for thread in threading.enumerate():
            if (
                thread != threading.current_thread()
                and thread.is_alive()
                and not thread.daemon
            ):
                try:
                    thread.join(timeout=5)  # Wait up to 5 seconds for each thread
                except Exception as e:
                    print(f"Error joining thread {thread.name}: {e}")


def validate_lua_syntax(lua_code: str) -> Tuple[bool, str]:
    """Validate Lua syntax using luaparser if available"""
    if not LUAPARSER_AVAILABLE:
        return True, "luaparser not available - skipping validation"

    try:
        lua_code = lua_code.replace("/sc", "").replace("/c", "").strip()
        with contextlib.redirect_stdout(None):
            lua_ast.parse(lua_code)
        return True, "Valid Lua syntax"
    except Exception as e:
        return False, f"Lua syntax error: {str(e)}"
