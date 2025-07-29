import atexit
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
from contextlib import contextmanager
from concurrent.futures import TimeoutError
from pathlib import Path
from timeit import default_timer as timer
from typing_extensions import Optional, List, Dict, Any, Tuple
import uuid

from dotenv import load_dotenv
from slpp import slpp as lua

from fle.env.entities import BoundingBox
from fle.env.utils.camera import Camera

from fle.env.lua_manager import LuaScriptManager, ToolHookRegistry
from fle.env.namespace import FactorioNamespace
from fle.env.utils.rcon import _lua2python, _get_dir
from fle.commons.models.research_state import ResearchState
from factorio_rcon import RCONClient
from fle.commons.models.game_state import GameState
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.env.utils.rcon import _load_lib
from collections import defaultdict

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
    def __init__(self, server):
        self.server = server
        self.commands: List[Tuple[str, List[Any], bool]] = []  # (command, parameters, is_raw)

    def add_command(self, command: str, *parameters, raw=False):
        self.commands.append((command, list(parameters), raw))

    def clear(self):
        self.commands.clear()

    def get_commands(self):
        return self.commands

    def execute(self) -> Dict[str, Any]:
        """Execute all commands in this transaction"""
        start = timer()
        rcon_commands = {}
        
        for idx, (command, parameters, is_raw) in enumerate(self.commands):
            if is_raw:
                rcon_commands[f"{idx}_{command}"] = command
            else:
                script = self.server._get_command(command, parameters=parameters, measured=False)
                rcon_commands[f"{idx}_{command}"] = script

        lua_responses = self.server.rcon_client.send_commands(rcon_commands)

        results = {}
        for command, response in lua_responses.items():
            results[command] = _lua2python(command, response, start=start)

        self.clear()
        return results

    @contextmanager
    def __enter__(self):
        """Context manager entry - clear any existing commands"""
        self.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - execute the transaction"""
        if exc_type is None:  # Only execute if no exception occurred
            self.execute()

class FactorioServer:
    def __init__(self, address, tcp_port, cache_scripts=True):
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.cache_scripts = cache_scripts
        self.tool_hook_registry = ToolHookRegistry()
        # Initialize Lua script manager and script dictionary
        self.lua_script_manager = LuaScriptManager(self.rcon_client, cache_scripts)
        self.script_dict = {
            **self.lua_script_manager.lib_scripts,
            **self.lua_script_manager.tool_scripts,
        }
    
    def run_rcon_print(self, command: str):
        return self.rcon_client.send_command(f"/sc rcon.print({command})")
    
    def send_command(self, command: str):
        return self.rcon_client.send_command(command)
    
    def load_init_into_game(self, init_scripts):
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)
    
    def init_action_checksums(self):
        checksum_init_script = _load_lib("checksum")
        response = self.send_command("/sc " + checksum_init_script)
        return response
    
    def connect_to_server(self, address, tcp_port):
        try:
            rcon_client = RCONClient(address, tcp_port, "factorio")
            address = address
        except ConnectionError as e:
            print(e)
            rcon_client = RCONClient("localhost", tcp_port, "factorio")
            address = "localhost"

        print(f"Connected to {address} client at tcp/{tcp_port}.")
        return rcon_client, address

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

    @contextmanager
    def transaction(self):
        """Context manager for backward compatibility"""
        transaction = FactorioTransaction(self)
        with transaction as t:
            yield t

    def register_controllers(self, namespaces: List["FactorioNamespace"], invalidate_cache: bool = False):
        """
        Load Python controllers from valid tool directories (delegated).
        """
        self.lua_script_manager.register_controllers(self, namespaces, invalidate_cache)

    def cleanup(self):
        # Close the RCON connection
        if hasattr(self, "rcon_client") and self.rcon_client:
            self.rcon_client.close()

        self.tool_hook_registry = ToolHookRegistry()

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


class FactorioInstance:
    namespace_class = FactorioNamespace
    _cleanup_registered = False  # Only register cleanup once per process
    namespaces = List[FactorioNamespace]

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
        **kwargs,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.num_agents = num_agents
        self.persistent_vars = {}
        self.tcp_port = tcp_port
        self.server = FactorioServer(address, tcp_port, cache_scripts)
        self.all_technologies_researched = all_technologies_researched
        self.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0
        self._is_initialised = False

        self.peaceful = peaceful
        self.namespaces = [self.namespace_class(self, i) for i in range(num_agents)]


        # Register controllers with the server
        self.server.register_controllers(self.namespaces)

        if inventory is None:
            inventory = {}
        self.initial_inventory = inventory
        self.initialise(fast)
        self.initial_score = 0
        try:
            self.first_namespace.score()
        except Exception:
            # Invalidate cache if there is an error
            self.server.register_controllers(self.namespaces, invalidate_cache=True)
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

    def set_speed(self, speed):
        self.rcon_client.send_command(f"/sc game.speed = {speed}")
        self._speed = speed

    def get_speed(self):
        return self._speed

    def get_elapsed_ticks(self):
        response = self.server.run_rcon_print("global.elapsed_ticks or 0")
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
        return generator.generate(self.num_agents, agent_idx)

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

    def _reset_static_achievement_counters(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.server.add_command(
            "/sc global.crafted_items = {}; global.harvested_items = {}", raw=True
        )
        self.server.execute_transaction()

    def _reset_elapsed_ticks(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.server.add_command("/sc global.elapsed_ticks = 0", raw=True)
        self.server.execute_transaction()

    def _reset(self, inventories: List[Dict[str, Any]]):
        with self.server.transaction() as t:
            t.add_command(
                "/sc global.alerts = {}; game.reset_game_state(); global.actions.reset_production_stats(); global.actions.regenerate_resources(1)",
                raw=True,
            )
            # self.server.add_command('/sc script.on_nth_tick(nil)', raw=True) # Remove all dangling event handlers
            for i in range(self.num_agents):
                player_index = i + 1
                t.add_command(
                    f"/sc global.actions.regenerate_resources({player_index})", raw=True
                )
                # self.server.add_command('clear_inventory', player_index)

        with self.server.transaction() as t:
            t.add_command("/sc global.actions.clear_walking_queue()", raw=True)
            for i in range(self.num_agents):
                player_index = i + 1
                t.add_command(
                    f"/sc global.actions.clear_entities({player_index})", raw=True
                )
                inventory_items = {k: v for k, v in inventories[i].items()}
                inventory_items_json = json.dumps(inventory_items)
                t.add_command(
                    f"/sc global.actions.initialise_inventory({player_index}, '{inventory_items_json}')",
                    raw=True,
                )

            if self.all_technologies_researched:
                t.add_command(
                    "/sc global.agent_characters[1].force.research_all_technologies()",
                    raw=True,
                )
        # self.clear_entities()
        self._reset_static_achievement_counters()
        self._reset_elapsed_ticks()

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
        with self.server.transaction() as t:
            t.add_command("/sc rendering.clear()", raw=True)

    def set_inventory(self, inventory: Dict[str, Any], agent_idx: int = 0):
        with self.server.transaction() as t:
            t.add_command("clear_inventory", agent_idx + 1)

        with self.server.transaction() as t:
            inventory_items = {k: v for k, v in inventory.items()}
            inventory_items_json = json.dumps(inventory_items)
            player_idx = agent_idx + 1
            t.add_command(
                f"/sc global.actions.initialise_inventory({player_idx}, '{inventory_items_json}')",
                raw=True,
            )

    def initialise(self, fast=True):
        with self.server.transaction() as t:
            t.add_command("/sc global.alerts = {}", raw=True)
            t.add_command("/sc global.elapsed_ticks = 0", raw=True)
            t.add_command(
                "/sc global.fast = {}".format("true" if fast else "false"), raw=True
            )

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
        ]
        if self.peaceful:
            init_scripts.append("enemies")
        
        self.server.load_init_into_game(init_scripts)

        inventories = [self.initial_inventory] * self.num_agents
        self._reset(inventories)
        self.first_namespace._clear_collision_boxes()

    def _create_agent_game_characters(self):
        """Create Factorio characters for all agents in the game."""
        # Create characters in Factorio
        with self.server.transaction() as t:
            color_logic = ""
            if self.num_agents > 1:
                color_logic = "if i==1 then char.color={r=0,g=1,b=0,a=1} elseif i==2 then char.color={r=0,g=0,b=1,a=1} end;"

            t.add_command(
                f'/sc global.agent_characters = {{}}; for _,c in pairs(game.surfaces[1].find_entities_filtered{{type="character"}}) do if c then c.destroy() end end; for i=1,{self.num_agents} do local char = game.surfaces[1].create_entity{{name="character",position={{x=0,y=(i-1)*2}},force=game.forces.player}}; {color_logic} global.agent_characters[i]=char end',
                raw=True,
            )
            t.add_command("/sc player = global.agent_characters[1]", raw=True)

    def get_warnings(self, seconds=10):
        """
        Get all alerts that have been raised before the last n seconds
        :param seconds: The number of seconds to look back
        :return:
        """
        start = timer()
        lua_response = self.server.run_rcon_print(f"dump(global.get_alerts({seconds}))")
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

    def cleanup(self):
        self.server.cleanup()
    
    def reset(self, game_state: Optional[GameState] = None):
        self.server.reset(game_state)