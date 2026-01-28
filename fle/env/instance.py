import atexit
import datetime
import enum
import os
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
import time
from pathlib import Path
from timeit import default_timer as timer
from typing import Dict

from typing_extensions import Optional
import uuid

from dotenv import load_dotenv

from fle.env.lua_manager import LuaScriptManager
from fle.env.namespace import FactorioNamespace
from fle.env.utils.rcon import _lua2python
from fle.commons.models.research_state import ResearchState
from factorio_rcon import RCONClient
from fle.commons.models.game_state import GameState
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.cluster.run_envs import START_RCON_PORT, RCON_PASSWORD

CHUNK_SIZE = 32
MAX_SAMPLES = 5000

load_dotenv()

NONE = "nil"

global var
var = {}


class GameControl:
    """Handles game speed and pause/unpause functionality"""

    def __init__(
        self,
        rcon_client,
        render_message_tool,
        reset_speed: float = 10,
        reset_paused: bool = False,
    ):
        self.rcon_client = rcon_client
        self._speed = 1.0
        self._is_paused = False
        self.reset_speed = reset_speed
        self.reset_paused = reset_paused
        self.render_message_tool = render_message_tool

    def _render_pause_message(self, message: str):
        """Safely render a pause/unpause message using render_message tool"""
        try:
            # Use the render_message tool (prefixed with underscore)
            if self.render_message_tool:
                self.render_message_tool(message)
        except Exception as e:
            # If render_message fails, fall back to console print
            print(f"Could not render message '{message}': {e}")

    def set_speed(self, speed: float):
        """Set game speed (only affects speed when unpaused)"""
        if speed <= 0:
            raise ValueError("Speed must be greater than 0")
        self._speed = speed
        if not self._is_paused:  # Only apply if not paused
            self.rcon_client.send_command(f"/sc game.speed = {speed}")

    def get_speed(self) -> float:
        """Get current speed setting (regardless of pause state)"""
        return self._speed

    def pause(self):
        """Pause the game (preserves speed setting)"""
        if not self._is_paused:
            self._is_paused = True
            self.rcon_client.send_command("/sc game.tick_paused = true")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self._render_pause_message(f"[{timestamp}] Game paused")

    def unpause(self):
        """Unpause the game (restores previous speed)"""
        if self._is_paused:
            self._is_paused = False
            self.rcon_client.send_command("/sc game.tick_paused = false")
            self.rcon_client.send_command(f"/sc game.speed = {self._speed}")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self._render_pause_message(
                f"[{timestamp}] Game unpaused (speed: {self._speed}x)"
            )

    def is_paused(self) -> bool:
        """Check if game is currently paused"""
        return self._is_paused

    def set_speed_and_unpause(self, speed: float):
        """Set speed and ensure game is unpaused - common use case"""
        self.set_speed(speed)
        self.unpause()

    def pause_at_speed(self, speed: float):
        """Set speed for when unpaused, but pause immediately"""
        self.set_speed(speed)
        self.pause()

    def get_elapsed_ticks(self):
        response = self.rcon_client.send_command(
            "/sc rcon.print(storage.elapsed_ticks or 0)"
        )
        if not response:
            print("WARNING: No response from get_elapsed_ticks")
            return 0
        return int(response)

    def _reset_elapsed_ticks(self):
        """Reset the elapsed ticks counter to 0."""
        self.rcon_client.send_command("/sc storage.elapsed_ticks = 0")

    def reset_to_defaults(self):
        """Reset to the configured default speed and pause state"""
        self.set_speed(self.reset_speed)
        if self.reset_paused:
            self.pause()
        else:
            self.unpause()


class DirectionInternal(enum.Enum):
    # Factorio 2.0 uses 16-direction system
    # Cardinal directions
    UP = NORTH = 0
    RIGHT = EAST = 4
    DOWN = SOUTH = 8
    LEFT = WEST = 12
    # Diagonal directions
    UPRIGHT = NORTHEAST = 2
    DOWNRIGHT = SOUTHEAST = 6
    DOWNLEFT = SOUTHWEST = 10
    UPLEFT = NORTHWEST = 14

    @classmethod
    def opposite(cls, direction):
        return cls((direction.value + 8) % 16)

    @classmethod
    def next_clockwise(cls, direction):
        return cls((direction.value + 4) % 16)

    @classmethod
    def next_counterclockwise(cls, direction):
        return cls((direction.value - 4) % 16)

    @classmethod
    def to_factorio_direction(cls, direction):
        # Factorio 2.0 uses the same values as our Direction enum
        return direction.value

    @classmethod
    def from_factorio_direction(cls, direction):
        # Factorio 2.0 uses the same values as our Direction enum
        return direction.value


class FactorioInstance:
    namespace_class = FactorioNamespace
    _cleanup_registered = False  # Only register cleanup once per process

    def __init__(
        self,
        address="localhost",
        fast=True,
        tcp_port=START_RCON_PORT,
        inventory: Dict = {},
        cache_scripts=True,
        all_technologies_researched=True,
        clear_entities=True,
        peaceful=True,
        num_agents=1,
        reset_speed=10,
        reset_paused=False,
        **kwargs,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.num_agents = num_agents
        self.persistent_vars = {}
        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.fast = fast
        self._ticks_elapsed = 0
        self._is_initialised = False

        self.peaceful = peaceful
        self.namespaces = [self.namespace_class(self, i) for i in range(num_agents)]

        # Create GameControl instance with render_message tool
        render_message_tool = None
        if hasattr(self.first_namespace, "_render_message"):
            render_message_tool = self.first_namespace._render_message
        self.game_control = GameControl(
            self.rcon_client, render_message_tool, reset_speed, reset_paused
        )
        self.game_control.reset_to_defaults()

        self.lua_script_manager = LuaScriptManager(self.rcon_client, cache_scripts)
        self.script_dict = {
            **self.lua_script_manager.lib_scripts,
            **self.lua_script_manager.tool_scripts,
        }

        # Initialize hooks as dictionaries to organize callbacks by tool name
        self.pre_tool_hooks = {}
        self.post_tool_hooks = {}

        # Load the python controllers that correspond to the Lua scripts
        self.lua_script_manager.load_init_into_game("initialise")
        self.lua_script_manager.setup_tools(self)

        if inventory is None:
            inventory = {}
        self.initial_inventory = inventory
        self.initialise(fast, all_technologies_researched, clear_entities)
        self.initial_score = 0
        try:
            self.first_namespace.score()
            # print("Initial score:", self.initial_score)
        except Exception:
            # print(e)
            # Invalidate cache if there is an error
            self.lua_script_manager = LuaScriptManager(self.rcon_client, False)
            self.script_dict = {
                **self.lua_script_manager.lib_scripts,
                **self.lua_script_manager.tool_scripts,
            }
            self.lua_script_manager.setup_tools(self)
            self.initialise(fast, all_technologies_researched, clear_entities)

        self.initial_score, _ = self.first_namespace.score()
        # Register the cleanup method to be called on exit (only once per process)
        if not FactorioInstance._cleanup_registered:
            atexit.register(self.cleanup)
            FactorioInstance._cleanup_registered = True

        self._executor = ThreadPoolExecutor(max_workers=2)

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

    def reset(
        self,
        game_state: Optional[GameState] = None,
        reset_position: bool = False,
        all_technologies_researched: bool = False,
        clear_entities: bool = True,
    ):
        # Ensure RCON connection is healthy before resetting
        # This prevents cascading failures when the connection was broken by a previous test
        self.ensure_connected()

        # Reset the namespace (clear variables, functions etc)
        assert not game_state or len(game_state.inventories) == self.num_agents, (
            "Game state must have the same number of inventories as num_agents"
        )

        for namespace in self.namespaces:
            namespace.reset()

        if not game_state:
            # Reset the game instance
            inventories = [self.initial_inventory] * self.num_agents
            self.first_namespace._reset(
                inventories, reset_position, all_technologies_researched, clear_entities
            )
            # Reset the technologies
            if not all_technologies_researched:
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
            self.first_namespace._reset(
                game_state.inventories,
                reset_position,
                all_technologies_researched,
                clear_entities,
            )

            # Load entities into the game
            self.first_namespace._load_entity_state(
                game_state.entities, decompress=True
            )

            # Load research state into the game
            self.first_namespace._load_research_state(game_state.research)

            # Load messages for each agent
            for i in range(min(self.num_agents, len(game_state.agent_messages))):
                self.namespaces[i].load_messages(game_state.agent_messages[i])

            # Load variables / functions from game state
            for i in range(self.num_agents):
                self.namespaces[i].load(game_state.namespaces[i])

        # Always restore to predictable state
        self.game_control.reset_to_defaults()

        try:
            self.initial_score, _ = self.first_namespace.score()
        except Exception:
            self.initial_score = 0

    def set_speed(self, speed: float):
        """Set game speed (only affects speed when unpaused)"""
        self.game_control.set_speed(speed)

    def get_speed(self) -> float:
        """Get current speed setting (regardless of pause state)"""
        return self.game_control.get_speed()

    def get_elapsed_ticks(self):
        """Get the number of ticks elapsed since the game started"""
        return self.game_control.get_elapsed_ticks()

    def _reset_elapsed_ticks(self):
        """Reset the elapsed ticks counter to 0."""
        self.game_control._reset_elapsed_ticks()

    def pause(self):
        """Pause the game (preserves speed setting)"""
        self.game_control.pause()

    def unpause(self):
        """Unpause the game (restores previous speed)"""
        self.game_control.unpause()

    def set_speed_and_unpause(self, speed: float):
        """Set speed and ensure game is unpaused - common use case"""
        self.game_control.set_speed_and_unpause(speed)

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
        return generator.generate_for_agent(
            agent_idx=agent_idx, num_agents=self.num_agents
        )

    @staticmethod
    def connect_to_server(address, tcp_port):
        try:
            rcon_client = RCONClient(
                address, tcp_port, RCON_PASSWORD
            )  #'quai2eeha3Lae7v')
            address = address
        except ConnectionError as e:
            print(e)
            rcon_client = RCONClient("localhost", tcp_port, RCON_PASSWORD)
            address = "localhost"

        try:
            rcon_client.connect()
            rcon_client.send_command("/sc rcon.print(#game.players)")
            # if int(player_count) == 0:
            #     print(
            #         "WARNING: LuaPlayer hasn't been initialised into the game. Entity placement behavior _may_ be incorrect for boilers and pumps."
            #     )

        except Exception as e:
            raise ConnectionError(
                f"Could not connect to {address} at tcp/{tcp_port}: \n{e.args[0]}"
            )

        print(f"Connected to {address} client at tcp/{tcp_port}.")
        return rcon_client, address

    def __eval_with_error(self, expr, agent_idx=0, timeout=60):
        """Evaluate an expression with a timeout, and return the result without error handling"""

        def handler(signum, frame):
            raise TimeoutError()

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)

        try:
            return self.namespaces[agent_idx].eval_with_timeout(expr)
        finally:
            signal.alarm(0)

    def eval_with_error(self, expr, agent_idx=0, timeout=60):
        """Evaluate an expression with a timeout, and return the result without error handling"""

        # Submit the evaluation to the thread pool
        future = self._executor.submit(
            self.namespaces[agent_idx].eval_with_timeout, expr
        )

        try:
            # Wait for the result with timeout
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            # Cancel the future if it's still running
            future.cancel()
            raise TimeoutError()
        except Exception:
            # Re-raise any other exceptions
            raise

    def eval(self, expr, agent_idx=0, timeout=60):
        "Evaluate several lines of input, returning the result of the last line with a timeout"
        ctime = time.time()
        try:
            response = self.eval_with_error(expr, agent_idx, timeout)
        except TimeoutError:
            # Capture partial output from namespace.logging_results
            partial_output = self._extract_partial_output(agent_idx)
            timeout_msg = f"Error: Evaluation timed out after {timeout}s"
            if partial_output:
                timeout_msg = (
                    f"{partial_output}\n\nError: Evaluation timed out after {timeout}s"
                )
            response = (-1, "", timeout_msg)
        except Exception as e:
            message = e.args[0].replace("\\n", "")
            response = (-1, "", f"{message}".strip())
        ntime = time.time()
        duration = ntime - ctime
        reward, _, result = response

        return reward, duration, result

    def _extract_partial_output(self, agent_idx=0, max_lines=64):
        """Extract partial output from namespace logging_results after a timeout.

        Mirrors the parse_result_into_str logic from namespace.eval_with_timeout.
        """
        try:
            namespace = self.namespaces[agent_idx]
            if (
                not hasattr(namespace, "logging_results")
                or not namespace.logging_results
            ):
                return ""

            result = []
            execution_trace = getattr(namespace, "execution_trace", False)

            for key, values in namespace.logging_results.items():
                if execution_trace:
                    for line_no, value in values:
                        result.append(f"{line_no}: {value}")
                else:
                    for value in values:
                        result.append(f"{key}: {value}")

            if len(result) > max_lines:
                truncated_count = len(result) - max_lines
                result = [f"... {truncated_count} lines truncated ..."] + result[
                    -max_lines:
                ]

            return "\n".join(result)
        except Exception:
            return ""

    def initialise(
        self, fast=True, all_technologies_researched=True, clear_entities=True
    ):
        self.rcon_client.send_command(f"/sc storage.fast = {str(fast).lower()}")
        self.first_namespace._create_agent_characters(self.num_agents)

        init_scripts = [
            "lualib_util",
            "utils",
            "alerts",
            "connection_points",
            "recipe_fluid_connection_mappings",
            "serialize",
        ]
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)

        if self.peaceful:
            self.rcon_client.send_command("/sc storage.utils.remove_enemies()")

        # Generate chunks around origin to enable long-distance pathfinding
        # 4000 tiles in each direction = 125 chunks (each chunk is 32x32 tiles)
        self._generate_chunks(center_x=0, center_y=0, chunk_radius=25)

        inventories = [self.initial_inventory] * self.num_agents

        self.first_namespace._reset(
            inventories,
            reset_position=False,
            all_technologies_researched=all_technologies_researched,
            clear_entities=clear_entities,
        )
        self.first_namespace._clear_collision_boxes()

    def get_warnings(self, seconds=10):
        """
        Get all alerts that have been raised before the last n seconds
        :param seconds: The number of seconds to look back
        :return:
        """
        start = timer()
        lua_response = self.rcon_client.send_command(
            f"/sc rcon.print(dump(storage.get_alerts({seconds})))"
        )
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

    def _generate_chunks(
        self, center_x: int = 0, center_y: int = 0, chunk_radius: int = 25
    ):
        """
        Generate chunks around a position to enable pathfinding in that area.

        Factorio chunks are 32x32 tiles. The pathfinder can only find paths
        through generated chunks. This method requests chunk generation and
        forces immediate generation.

        Args:
            center_x: Center X position (in tiles)
            center_y: Center Y position (in tiles)
            chunk_radius: Radius in chunks (each chunk is 32 tiles)
        """
        # Request chunk generation around the position
        _ = self.rcon_client.send_command(
            f"/silent-command game.surfaces[1].request_to_generate_chunks({{x={center_x}, y={center_y}}}, {chunk_radius})"
        )
        # Force immediate generation of all requested chunks
        _ = self.rcon_client.send_command(
            "/silent-command game.surfaces[1].force_generate_chunk_requests()"
        )
        pass

    def is_rcon_connected(self) -> bool:
        """Check if the RCON client is still connected and healthy."""
        if not hasattr(self, "rcon_client") or self.rcon_client is None:
            return False
        # Check the internal state of the factorio_rcon library
        if self.rcon_client.rcon_socket is None:
            return False
        if self.rcon_client.rcon_failure:
            return False
        return True

    def reconnect(self):
        """Reconnect to the RCON server if the connection has been lost."""
        if self.is_rcon_connected():
            return  # Already connected

        print(
            f"RCON connection lost, attempting to reconnect to {self.address}:{self.tcp_port}..."
        )
        try:
            self.rcon_client.connect()
            print(
                f"Successfully reconnected to RCON server at {self.address}:{self.tcp_port}"
            )
        except Exception as e:
            print(f"Failed to reconnect to RCON server: {e}")
            raise

    def ensure_connected(self):
        """Ensure RCON connection is healthy, reconnecting if necessary."""
        if not self.is_rcon_connected():
            self.reconnect()

    def cleanup(self):
        # Close the RCON connection
        if hasattr(self, "rcon_client") and self.rcon_client:
            self.rcon_client.close()

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

        # Shutdown the executor
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True, cancel_futures=True)
