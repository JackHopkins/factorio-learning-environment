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

class FactorioInstance:
    namespace_class = FactorioNamespace
    _cleanup_registered = False  # Only register cleanup once per process

    def __init__(
        self,
        address=None,
        fast=True,
        tcp_port=27000,
        inventory=None,
        cache_scripts=True,
        all_technologies_researched=True,
        clear_entities=True,
        peaceful=True,
        num_agents=1,
        **kwargs,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.num_agents = num_agents
        self.persistent_vars = {}
        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0
        self._is_initialised = False

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
        self.lua_script_manager.load_init_into_game("initialise")
        self.setup_tools(self.lua_script_manager)

        if inventory is None:
            inventory = {}
        self.initial_inventory = inventory
        self.initialise(fast, all_technologies_researched, clear_entities)
        self.initial_score = 0
        try:
            self.first_namespace.score()
            print("Initial score:", self.initial_score)
        except Exception as e:
            print(e)
            # Invalidate cache if there is an error
            self.lua_script_manager = LuaScriptManager(self.rcon_client, False)
            self.script_dict = {
                **self.lua_script_manager.lib_scripts,
                **self.lua_script_manager.tool_scripts,
            }
            self.setup_tools(self.lua_script_manager)
            self.initialise(fast, all_technologies_researched, clear_entities)

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

    def reset(
        self,
        game_state: Optional[GameState] = None,
        reset_position: bool = False,
        all_technologies_researched: bool = True,
        clear_entities: bool = True,
    ):
        # Reset the namespace (clear variables, functions etc)
        assert not game_state or len(game_state.inventories) == self.num_agents, (
            "Game state must have the same number of inventories as num_agents"
        )

        for namespace in self.namespaces:
            namespace.reset()

        if not game_state:
            # Reset the game instance
            inventories = [self.initial_inventory] * self.num_agents
            self.first_namespace._reset(inventories, reset_position, all_technologies_researched, clear_entities)
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
            if game_state.agent_messages:
                for i in range(self.num_agents):
                    if i < len(game_state.agent_messages):
                        self.namespaces[i].load_messages(game_state.agent_messages[i])

            # Load variables / functions from game state
            for i in range(self.num_agents):
                self.namespaces[i].load(game_state.namespaces[i])

        try:
            self.initial_score, _ = self.first_namespace.score()
        except Exception:
            self.initial_score = 0

    def set_speed(self, speed):
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
        return generator.generate_for_agent(
            agent_idx=agent_idx, num_agents=self.num_agents
        )

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

    def initialise(self, fast=True, all_technologies_researched=True, clear_entities=True):
        self.rcon_client.send_command(
            f"/sc global.fast = {str(fast).lower()}"
        )
        self.first_namespace._create_agent_characters(self.num_agents)

        init_scripts = [
            "alerts",
            "util",
            "connection_points",
            "recipe_fluid_connection_mappings",
            "serialize",
        ]
        if self.peaceful:
            init_scripts.append("enemies")
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)

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
        lua_response = self.rcon_client.send_command(f"/sc rcon.print(dump(global.get_alerts({seconds})))")
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
