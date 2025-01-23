import atexit
import atexit
import enum
import functools
import importlib
import inspect
import json
import os
import signal
import sys
import threading
import traceback
import types
from concurrent.futures import TimeoutError
from pathlib import Path
from timeit import default_timer as timer

from dotenv import load_dotenv
from slpp import slpp as lua

from factorio_entities import *
from factorio_lua_script_manager import FactorioLuaScriptManager
from factorio_namespace import FactorioNamespace
from factorio_transaction import FactorioTransaction
from models.observation_state import ObservationState
from models.research_state import ResearchState
from search.model.game_state import GameState
from src.factorio_rcon_utils import _lua2python
from src.rcon.factorio_rcon import RCONClient
from utilities.controller_loader import load_schema, load_definitions, parse_file_for_structure
from vocabulary import Vocabulary

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

    def __init__(self, address=None,
                 vocabulary: Vocabulary = Vocabulary(),
                 bounding_box=20,
                 fast=False,
                 tcp_port=27000,
                 inventory={},
                 cache_scripts=True,
                 all_technologies_researched=True,
                 peaceful=True
                 ):

        self.persistent_vars = {}

        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.all_technologies_researched = all_technologies_researched
        self.game_state = ObservationState().with_default(vocabulary)
        self.game_state.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0

        self.peaceful = peaceful
        self.namespace = FactorioNamespace(self)

        self.lua_script_manager = FactorioLuaScriptManager(self.rcon_client, cache_scripts)
        self.script_dict = {**self.lua_script_manager.action_scripts, **self.lua_script_manager.init_scripts}

        # Load the python controllers that correspond to the Lua scripts
        self.setup_controllers(self.lua_script_manager, self.game_state)

        self.initial_inventory = inventory
        self.initialise(fast, **inventory)
        try:
            self.namespace.observe_all()
        except Exception as e:
            # Invalidate cache if there is an error
            self.lua_script_manager = FactorioLuaScriptManager(self.rcon_client, False)
            self.script_dict = {**self.lua_script_manager.action_scripts, **self.lua_script_manager.init_scripts}
            self.setup_controllers(self.lua_script_manager, self.game_state)
            self.initialise(fast, **inventory)

        self._tasks = []

        self._initial_score, goal = self.namespace.score()

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

        try:
            self.namespace.observe_all()
        except Exception as e:
            print(e)
            pass

        try:
            self.game_state.initial_score, goal = self.namespace.score()
        except Exception as e:
            self.game_state.initial_score, goal = 0, None



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
        self.game_state._speed = speed

    def get_elapsed_ticks(self):
        response = self.rcon_client.send_command(f'/c rcon.print(global.elapsed_ticks or 0)')
        if not response: return 0
        return int(response)

    # def log(self, *arg):
    #     """
    #     Shadows the builtin print function,and ensures that whatever is printed is logged in agent memory
    #     """
    #     #if self.memory:
    #     #    self.memory.log_observation(str(arg))
    #     if self.line_value not in self.logging_results:
    #         self.logging_results[self.line_value] = []
    #     self.logging_results[self.line_value].append(repr(arg))
    #
    #     if 'error' in repr(arg).lower():
    #         print(f"\033[93m{self.tcp_port}: {repr(arg)}")
    #     else:
    #         print(f"{self.tcp_port}: {repr(arg)}")
    #     return arg

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the Factorio environment.

        This includes all the available actions, objects, and entities that the agent can interact with.

        We get the system prompt by loading the schema, definitions, and entity definitions from their source files.

        These are converted to their signatures - leaving out the implementations.
        :return:
        """
        execution_path = os.path.dirname(os.path.realpath(__file__))
        folder_path = f'{execution_path}/controllers'
        schema = load_schema(folder_path, with_docstring=True).replace("temp_module.", "")
        type_definitions = load_definitions(f'{execution_path}/factorio_types.py')
        # Filter `import` statements and `from` statements
        type_definitions = "\n".join(list(
            filter(lambda x: not x.startswith("import") and not x.startswith("from") and not x.lstrip().startswith('#'), type_definitions.split("\n"))))
        type_definitions = type_definitions.replace("\n\n\n", "\n").replace("\n\n", "\n").strip()
        # get everything from and including class Prototype(enum.Enum):
        type_definitions = type_definitions[type_definitions.index("class Prototype(enum.Enum"):]
        # entity_definitions = load_definitions(f'{execution_path}/factorio_entities.py')
        entity_definitions = parse_file_for_structure(f'{execution_path}/factorio_entities.py')
        brief = f"```types\n{type_definitions}\n```\n```objects\n{entity_definitions}\n```\n```tools\n{schema}\n```"

        return brief

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

    def setup_controllers(self, lua_script_manager, game_state):
        """
        Here we load all the Python controllers into the namespace, e.g `inspect_inventory(), nearest(), ect`
        @param lua_script_manager:
        @param game_state:
        @return:
        """
        # Define the directory containing the callable class files
        callable_classes_directory = "controllers"

        # Get the local execution directory
        local_directory = os.path.dirname(os.path.realpath(__file__))

        def snake_to_camel(snake_str):
            return "".join(word.capitalize() for word in snake_str.split("_"))

        # Store the callable instances in a dictionary
        self.controllers = {}

        # Loop through the files in the directory
        for file in os.listdir(os.path.join(local_directory, callable_classes_directory)):
            # Check if the file is a Python file and does not start with '_'
            if file.endswith(".py") and not file.startswith("__"):
                # Load the module
                module_name = Path(file).stem
                module_spec = importlib.util.spec_from_file_location(module_name,
                                                                     os.path.join(os.path.join(local_directory, callable_classes_directory), file))
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)

                class_name = snake_to_camel(module_name)

                # We have to rename these because on windows environments it fails silently (for some reason)
                if module_name == "place_entity":
                    class_name = "PlaceObject"
                if module_name == "score":
                    class_name = "Reward"
                # Get the callable class
                callable_class = getattr(module, class_name)

                # Create an instance of the callable class
                try:
                    callable_instance = callable_class(lua_script_manager, game_state)
                    self.controllers[module_name.lower()] = callable_instance
                except Exception as e:
                    raise Exception(f"Could not instantiate {class_name}. {e}")
                # Add the instance as a member method
                setattr(self.namespace, module_name.lower(), callable_instance)
        pass


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

    def comment(self, comment: str, *args):
        """
        Send a comment to the Factorio game console
        :param comment:
        :param args:
        :return:
        """
        # game.players[1].print({"","[img=entity/character][color=orange]",{"engineer-title"},": [/color]",{"think-"..thought}})
        #self.rcon_client.send_command(f'/c game.players[1].print("[img=entity/character][color=orange]" {{"{comment}"}},": ",{args}}})')
        self.rcon_client.send_command(f"[img=entity/character] " + str(comment) + ", ".join(args))

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
        self.lua_script_manager.load_init_into_game('serialize')
        self.lua_script_manager.load_init_into_game('production_score')
        self.lua_script_manager.load_init_into_game('initialise_inventory')

        self._reset(**kwargs)

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