import atexit
import enum
import functools
import importlib
import inspect
import json
import os
import shutil
import signal
import sys
import threading
import time
import traceback
import types
from concurrent.futures import TimeoutError
from pathlib import Path
from timeit import default_timer as timer
from typing_extensions import deprecated

from dotenv import load_dotenv
from slpp import slpp as lua

from entities import *
from lua_manager import LuaScriptManager
from namespace import FactorioNamespace
from utils.rcon import _lua2python, _get_dir
from transaction import FactorioTransaction
from models.research_state import ResearchState
from rcon.factorio_rcon import RCONClient
from eval.open.model.game_state import GameState
from utils.controller_loader.system_prompt_generator import SystemPromptGenerator

CHUNK_SIZE = 32
MAX_SAMPLES = 5000

load_dotenv()

PLAYER = 1
NONE = 'nil'

global var
var = {}

class Direction(Enum):
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

    def __init__(self,
                 address=None,
                 fast=False,
                 tcp_port=27000,
                 inventory={},
                 cache_scripts=True,
                 all_technologies_researched=True,
                 peaceful=True,
                 **kwargs
                 ):

        self.persistent_vars = {}

        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.all_technologies_researched = all_technologies_researched
        #self.game_state = ObservationState().with_default(vocabulary)
        self.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0

        self.peaceful = peaceful
        self.namespace = FactorioNamespace(self)

        self.lua_script_manager = LuaScriptManager(self.rcon_client, cache_scripts)
        self.script_dict = {**self.lua_script_manager.lib_scripts, **self.lua_script_manager.tool_scripts}

        # Load the python controllers that correspond to the Lua scripts
        self.setup_tools(self.lua_script_manager)#, self.game_state)

        self.initial_inventory = inventory
        self.initialise(fast, **inventory)
        self.initial_score = 0

        try:
            self.namespace.score()
        except Exception as e:
            # Invalidate cache if there is an error
            self.lua_script_manager = LuaScriptManager(self.rcon_client, False)
            self.script_dict = {**self.lua_script_manager.lib_scripts, **self.lua_script_manager.tool_scripts}
            self.setup_tools(self.lua_script_manager)
            self.initialise(fast, **inventory)

        self._tasks = []

        self.initial_score, goal = self.namespace.score()

        # Register the cleanup method to be called on exit
        atexit.register(self.cleanup)

    def reset(self, game_state: Optional[GameState] = None):
        # Reset the namespace (clear variables, functions etc)
        self.namespace.reset()

        if not game_state:
            # Reset the game instance
            self._reset(**self.initial_inventory if isinstance(self.initial_inventory,
                                                               dict) else self.initial_inventory.__dict__)
            # Reset the technologies
            if not self.all_technologies_researched:
                self.namespace._load_research_state(ResearchState(
                    technologies={},
                    research_progress=0,
                    current_research=None,
                    research_queue=[]
                ))
        else:
            # Reset the game instance
            self._reset(**dict(game_state.inventory))

            # Load entities into the game
            self.namespace._load_entity_state(game_state.entities, decompress=True)

            # Load research state into the game
            self.namespace._load_research_state(game_state.research)

            # Reset elapsed ticks
            self._reset_elapsed_ticks()

            # Load variables / functions from game state
            self.namespace.load(game_state)

        # try:
        #     self.namespace.observe_all()
        # except Exception as e:
        #     print(e)
        #     pass

        try:
            self.initial_score, goal = self.namespace.score()
        except Exception as e:
            self.initial_score, goal = 0, None

        # Clear renderings
        self.begin_transaction()
        self.add_command('/c rendering.clear()', raw=True)
        self.execute_transaction()


    def set_inventory(self, **kwargs):
        self.begin_transaction()
        self.add_command('clear_inventory', PLAYER)
        self.execute_transaction()

        self.begin_transaction()
        # kwargs dict to json
        inventory_items = {k: v for k, v in kwargs.items()}
        inventory_items_json = json.dumps(inventory_items)
        self.add_command(f"/c global.actions.initialise_inventory({PLAYER}, '{inventory_items_json}')", raw=True)

        self.execute_transaction()

    def speed(self, speed):
        response = self.rcon_client.send_command(f'/c game.speed = {speed}')
        self._speed = speed

    def get_elapsed_ticks(self):
        response = self.rcon_client.send_command(f'/c rcon.print(global.elapsed_ticks or 0)')
        if not response: return 0
        return int(response)

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the Factorio environment.
        This includes all the available actions, objects, and entities that the agent can interact with.
        We get the system prompt by loading the schema, definitions, and entity definitions from their source files.
        These are converted to their signatures - leaving out the implementations.
        :return:
        """
        execution_path = Path(os.path.dirname(os.path.realpath(__file__)))
        generator = SystemPromptGenerator(str(execution_path))
        return generator.generate()

    def connect_to_server(self, address, tcp_port):
        try:
            rcon_client = RCONClient(address, tcp_port, 'factorio') #'quai2eeha3Lae7v')
            address = address
        except ConnectionError as e:
            print(e)
            rcon_client = RCONClient('localhost', tcp_port, 'factorio')
            address = 'localhost'

        try:
            rcon_client.connect()
            player_exists = rcon_client.send_command('/c rcon.print(game.players[1].position)')
            if not player_exists:
                raise Exception(
                    "Player hasn't been initialised into the game. Please log in once to make this node operational.")
            #rcon_client.send_command('/c global = {}')
            #rcon_client.send_command('/c global.actions = {}')

        except Exception as e:
            raise ConnectionError(f"Could not connect to {address} at tcp/{tcp_port}: \n{e.args[0]}")

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
                    client_file
                    #str(Path(client_file))
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
                    # Get and instantiate the controller class
                    callable_class = getattr(module, class_name)
                    callable_instance = callable_class(lua_script_manager, self.namespace)

                    # Store the controller and add it to namespace
                    self.controllers[tool_name.lower()] = callable_instance

                    if directory_name == 'admin':
                        # If this is an admin method, we hide it in the namespace by adding a shebang
                        setattr(self.namespace, f"_{tool_name.lower()}", callable_instance)
                    else:
                        setattr(self.namespace, tool_name.lower(), callable_instance)

                except Exception as e:
                    raise Exception(f"Could not instantiate {class_name} from {client_file}. {e}")

    def eval_with_error(self, expr, timeout=60):
        """ Evaluate an expression with a timeout, and return the result without error handling"""
        # with ThreadPoolExecutor(max_workers=1) as executor:
        #     future = executor.submit(self._eval_with_timeout, expr)
        #     score, goal, result = future.result(timeout)
        #     return score, goal, result
        def handler(signum, frame):
            raise TimeoutError()

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)

        try:
            return self.namespace.eval_with_timeout(expr)
        finally:
            signal.alarm(0)


    def eval(self, expr, timeout=60):
        "Evaluate several lines of input, returning the result of the last line with a timeout"
        try:
            return self.eval_with_error(expr, timeout)
        except TimeoutError:
            return -1, "", "Error: Evaluation timed out"
        except Exception as e:
            trace = e.__traceback__
            message = e.args[0].replace('\\n', '')
            return -1, "", f"{message}".strip()

    def _get_command(self, command, parameters=[], measured=True):
        prefix = "/c " if not measured else '/command '
        if command in self.script_dict:
            script = prefix + self.script_dict[command]
            for index in range(len(parameters)):
                script = script.replace(f"arg{index + 1}", lua.encode(parameters[index]))
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
        width, height = map(int, resolution.split('x'))
        aspect_ratio = width / height

        # Get factory dimensions
        factory_width = bounds.width()
        factory_height = bounds.height()
        factory_aspect_ratio = factory_width / factory_height

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

    def screenshot(self, resolution="1920x1080", save_path=None, zoom=None, center_on_factory=False, script_output_path="/Users/jackhopkins/Library/Application Support/factorio/script-output"):
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
        bounds: BoundingBox = self.namespace._get_factory_centroid()
        POS_STRING = ""
        if bounds:
            centroid = bounds.center()
            POS_STRING = ", position={x="+str(centroid.x)+", y="+str(centroid.y)+"}"

        self.rcon_client.send_command("/c rendering.clear()")

        # Calculate optimal zoom if not specified
        if zoom is None:
            zoom = self.calculate_optimal_zoom(bounds, resolution)

        command = "/c game.take_screenshot({player=1, zoom="+str(zoom)+", show_entity_info=true, hide_clouds=true, hide_fog=true "+POS_STRING+"})"
        response = self.rcon_client.send_command(command)
        time.sleep(1)
        # if not response:
        #     return None

        # Wait for the screenshot file to appear and get its path
        screenshot_path = self._get_latest_screenshot(script_output_path=script_output_path)
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
                screenshots = [f for f in os.listdir(script_output_path)
                               if f.endswith('.png') and f.startswith('screenshot')]

                if screenshots:
                    # Sort by modification time to get the latest
                    latest = max(screenshots,
                                 key=lambda x: os.path.getmtime(os.path.join(script_output_path, x)))
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
        #self.add_command(command, *parameters)
        #response = self._execute_transaction()
        # print(lua_response)
        return _lua2python(command, lua_response, start=start)

    # def comment(self, comment: str, *args):
    #     """
    #     Send a comment to the Factorio game console
    #     :param comment:
    #     :param args:
    #     :return:
    #     """
    #     # game.players[1].print({"","[img=entity/character][color=orange]",{"engineer-title"},": [/color]",{"think-"..thought}})
    #     #self.rcon_client.send_command(f'/c game.players[1].print("[img=entity/character][color=orange]" {{"{comment}"}},": ",{args}}})')
    #     self.rcon_client.send_command(f"[img=entity/character] " + str(comment) + ", ".join(args))

    def _reset_static_achievement_counters(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.add_command('/c global.crafted_items = {}', raw=True)
        self.add_command('/c global.harvested_items = {}', raw=True)
        self.execute_transaction()

    def _reset_elapsed_ticks(self):
        """
        This resets the cached production flows that we track for achievements and diversity sampling.
        """
        self.add_command('/c global.elapsed_ticks = 0', raw=True)
        self.execute_transaction()

    def _reset(self, **kwargs):

        self.begin_transaction()
        self.add_command('/c global.alerts = {}', raw=True)
        self.add_command('/c game.reset_game_state()', raw=True)
        self.add_command('/c global.actions.reset_production_stats()', raw=True)
        self.add_command(f'/c global.actions.regenerate_resources({PLAYER})', raw=True)
        #self.add_command('/c script.on_nth_tick(nil)', raw=True) # Remove all dangling event handlers
        self.add_command('clear_inventory', PLAYER)
        self.add_command('reset_position', PLAYER, 0, 0)

        self.execute_transaction()

        self.begin_transaction()
        self.add_command('/c global.actions.clear_walking_queue()', raw=True)
        self.add_command(f'/c global.actions.clear_entities({PLAYER})', raw=True)

        # kwargs dict to json
        inventory_items = {k: v for k, v in kwargs.items()}
        inventory_items_json = json.dumps(inventory_items)
        self.add_command(f"/c global.actions.initialise_inventory({PLAYER}, '{inventory_items_json}')", raw=True)

        if self.all_technologies_researched:
            self.add_command("/c game.players[1].force.research_all_technologies()", raw=True)
        self.execute_transaction()
        #self.clear_entities()
        self._reset_static_achievement_counters()
        self._reset_elapsed_ticks()

    def _execute_transaction(self) -> Dict[str, Any]:
        start = timer()
        rcon_commands = {}
        for idx, (command, parameters, is_raw) in enumerate(self.current_transaction.get_commands()):
            if is_raw:
                rcon_commands[f"{idx}_{command}"] = command
            else:
                script = self._get_command(command, parameters=parameters, measured=False)
                rcon_commands[f"{idx}_{command}"] = script

        lua_responses = self.rcon_client.send_commands(rcon_commands)

        results = {}
        for command, response in lua_responses.items():
            results[command] = _lua2python(command, response, start=start)

        self.current_transaction.clear()
        return results

    def begin_transaction(self):
        if not hasattr(self, 'current_transaction'):
            self.current_transaction = FactorioTransaction()
        elif self.current_transaction:
            self.current_transaction.clear()
        else:
            self.current_transaction = FactorioTransaction()

    def add_command(self, command: str, *parameters, raw=False):
        if not hasattr(self, 'current_transaction'):
            self.begin_transaction()
        self.current_transaction.add_command(command, *parameters, raw=raw)

    def execute_transaction(self) -> Dict[str, Any]:
        return self._execute_transaction()

    def initialise(self, fast=True, **kwargs):

        self.begin_transaction()
        self.add_command('/c global.alerts = {}', raw=True)
        self.add_command('/c global.elapsed_ticks = 0', raw=True)
        self.add_command('/c global.fast = {}'.format('true' if fast else 'false'), raw=True)
        #self.add_command('/c script.on_nth_tick(nil)', raw=True)

        # Peaceful mode
        # self.add_command('/c game.map_settings.enemy_expansion.enabled = false', raw=True)
        # self.add_command('/c game.map_settings.enemy_evolution.enabled = false', raw=True)
        # self.add_command('/c game.forces.enemy.kill_all_units()', raw=True)
        if self.peaceful:
            self.lua_script_manager.load_init_into_game('enemies')


        self.add_command(f'/c player = game.players[{PLAYER}]', raw=True)
        self.execute_transaction()

        self.lua_script_manager.load_init_into_game('initialise')
        self.lua_script_manager.load_init_into_game('clear_entities')
        self.lua_script_manager.load_init_into_game('alerts')
        self.lua_script_manager.load_init_into_game('util')
        self.lua_script_manager.load_init_into_game('priority_queue')
        self.lua_script_manager.load_init_into_game('connection_points')
        self.lua_script_manager.load_init_into_game('recipe_fluid_connection_mappings')
        self.lua_script_manager.load_init_into_game('serialize')
        self.lua_script_manager.load_init_into_game('production_score')
        self.lua_script_manager.load_init_into_game('initialise_inventory')

        self._reset(**kwargs)

        self.namespace._clear_collision_boxes()

    def get_warnings(self, seconds=10):
        """
        Get all alerts that have been raised before the last n seconds
        :param seconds: The number of seconds to look back
        :return:
        """
        start = timer()
        command = f'/silent-command rcon.print(dump(global.get_alerts({seconds})))'
        lua_response = self.rcon_client.send_command(command)
        # print(lua_response)
        alert_dict, duration = _lua2python('alerts', lua_response, start=start)
        if isinstance(alert_dict, dict):
            alerts = list(alert_dict.values())
            alert_strings = []
            for alert in alerts:
                issues = ", ".join([al.replace("_", " ") for al in list(alert['issues'].values())])
                alert_strings.append(f"{alert['entity_name']} at {tuple(alert['position'].values())}: {issues}")

            return alert_strings
        else:
            return []

    def _prepare_callable(self, value):
        if callable(value):
            if inspect.ismethod(value) or inspect.isfunction(value):
                # For methods and functions, bind them to the instance
                return value.__get__(self, self.__class__)
            elif hasattr(value, '__call__'):
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
            elif inspect.ismodule(value) and value.__name__.startswith('factorio_'):
                # For Factorio-related modules, add the module and its attributes
                namespace[name] = value
                for attr_name, attr_value in inspect.getmembers(value):
                    if not attr_name.startswith('_'):
                        namespace[f"{name}.{attr_name}"] = attr_value
            elif isinstance(value, type):
                # For classes, add the class itself
                namespace[name] = value
            else:
                # For other values, add them directly
                namespace[name] = value

        # Add all public instance attributes and methods
        for name, value in vars(self).items():
            if not name.startswith('_'):
                add_to_namespace(name, value)

        # Add dynamically loaded controllers
        for name, controller in self.controllers.items():
            namespace[name] = self._prepare_callable(controller)

        # Add all class-level attributes
        for name, value in vars(self.__class__).items():
            if not name.startswith('_') and name not in namespace:
                add_to_namespace(name, value)

        # Add all global variables from the module where FactorioInstance is defined
        module_globals = inspect.getmodule(self.__class__).__dict__
        for name, value in module_globals.items():
            if not name.startswith('_') and name not in namespace:
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
            new_func = types.FunctionType(func.__code__, new_globals, func.__name__, func.__defaults__,
                                          func.__closure__)

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
            '__name__': '__main__',
            '__file__': file_path,
            **vars(factorio_ns)
        }
        try:
            # Execute the file directly
            with open(file_path, 'r') as file:
                code = compile(file.read(), file_path, 'exec')
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
        # Close the RCON connection
        if hasattr(self, 'rcon_client') and self.rcon_client:
            self.rcon_client.close()

        # Join all non-daemon threads
        for thread in threading.enumerate():
            if thread != threading.current_thread() and thread.is_alive() and not thread.daemon:
                try:
                    thread.join(timeout=5)  # Wait up to 5 seconds for each thread
                except Exception as e:
                    print(f"Error joining thread {thread.name}: {e}")

        sys.exit(0)