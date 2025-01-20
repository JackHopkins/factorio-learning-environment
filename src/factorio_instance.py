import ast
import asyncio
import atexit
import builtins
import enum
import functools
import importlib
import inspect
import json
import os
import pickle
import signal
import sys
import threading
import traceback
import types
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from timeit import default_timer as timer

from dotenv import load_dotenv
from slpp import slpp as lua
from typing_extensions import deprecated

from factorio_namespace import FactorioNamespace
from models.research_state import ResearchState
from search.model.game_state import GameState, wrap_for_serialization, unwrap_after_deserialization, \
    SerializableFunction
from factorio_entities import *
from factorio_lua_script_manager import FactorioLuaScriptManager
from factorio_transaction import FactorioTransaction
from factorio_types import Prototype, Resource, prototype_by_name, Technology
from models.observation_state import ObservationState
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
                 tcp_port=27015,
                 inventory={},
                 cache_scripts=True,
                 all_technologies_researched=True
                 ):

        self.persistent_vars = {}

        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.all_technologies_researched = all_technologies_researched
        self.game_state = ObservationState().with_default(vocabulary)
        self.game_state.fast = fast
        self._speed = 1
        self._ticks_elapsed = 0

        self.namespace = FactorioNamespace(self)

        # self.max_sequential_exception_count = 1
        # self._sequential_exception_count = 0

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
            #self.observe_all()

        self._tasks = []

        self._initial_score, goal = self.namespace.score()

        # # Available objects that the agent can interact with
        # self.Prototype = Prototype
        # self.Resource = Resource
        # self.Direction = Direction
        # self.Position = Position
        # self.EntityStatus = EntityStatus
        # self.BoundingBox = BoundingBox
        # self.BeltGroup = BeltGroup
        # self.Technology = Technology
        # self.Recipe = Recipe
        #
        # self.prototype_by_name = prototype_by_name
        #
        # # Statically named directions
        # self.UP, self.ABOVE, self.TOP = [Direction.UP]*3
        # self.RIGHT, self.EAST = [Direction.RIGHT]*2
        # self.LEFT, self.WEST = [Direction.LEFT]*2
        # self.DOWN, self.BELOW, self.BOTTOM = [Direction.DOWN]*3

        # Available actions that the agent can perform
        # self._static_members = [attr for attr in dir(self)
        #                         if not callable(getattr(self, attr))
        #                         and not attr.startswith("__")]

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
                self._load_research_state(ResearchState(
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
        schema = load_schema(folder_path, with_docstring=False)
        type_definitions = load_definitions(f'{execution_path}/factorio_types.py')
        # Filter `import` statements and `from` statements
        type_definitions = "\n".join(list(
            filter(lambda x: not x.startswith("import") and not x.startswith("from"), type_definitions.split("\n"))))
        type_definitions = type_definitions.replace("\n\n\n", "\n").replace("\n\n", "\n").strip()
        # get everything from and including class Prototype(enum.Enum):
        type_definitions = type_definitions[type_definitions.index("class Prototype(enum.Enum):"):]
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

    # def __getitem__(self, key):
    #     if key not in dir(self) or key.startswith('__'):
    #         raise KeyError(key)
    #     return getattr(self, key)
    #
    # def __setitem__(self, key, value):
    #     setattr(self, key, value)

    # def _extract_error_lines(self, expr, traceback_str):
    #     lines = expr.splitlines()
    #     error_lines = []
    #     for line in traceback_str.splitlines():
    #         if 'File "file", line' in line:
    #             line_num = int(line.split(", line")[1].split(",")[0])
    #             if 1 <= line_num <= len(lines):
    #                 error_lines.append((line_num, lines[line_num - 1].strip()))
    #     return error_lines

    # def _change_print_to_log(self, node):
    #     if isinstance(node, ast.Expr):
    #         # check if its print, if it is, then we route to log
    #         if isinstance(node.value, ast.Call) and isinstance(node.value.func,
    #                                                            ast.Name) and node.value.func.id == 'print':
    #             # change print to log
    #             node.value.func.id = 'log'
    #
    #     elif isinstance(node, ast.If) or isinstance(node, ast.For) or isinstance(node, ast.While):
    #         for subnode_idx, subnode in enumerate(node.body):
    #             node.body[subnode_idx] = self._change_print_to_log(subnode)
    #         for subnode_idx, subnode in enumerate(node.orelse):
    #             node.orelse[subnode_idx] = self._change_print_to_log(subnode)
    #     elif isinstance(node, ast.FunctionDef):
    #         for subnode_idx, subnode in enumerate(node.body):
    #             node.body[subnode_idx] = self._change_print_to_log(subnode)
    #     return node

    # def _eval_with_timeout(self, expr):
    #     """
    #     Executes a Python expression with a timeout and returns the result.
    #     Supports try-except blocks and other compound statements.
    #     """
    #
    #     def parse_result_into_str(data):
    #         result = []
    #         for key, values in data.items():
    #             for value in values:
    #                 result.append(f"{key}: {value}")
    #         return "\n".join(result)
    #
    #     def find_actual_line_number(node, code_lines):
    #         """Find the actual line number in the source code for a given node"""
    #         if not hasattr(node, 'lineno'):
    #             return 0
    #
    #         # Get the node's source code
    #         if isinstance(node, ast.AST):
    #             # For print calls specifically
    #             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
    #                 return node.lineno
    #             # For expressions containing print calls
    #             if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and \
    #                     isinstance(node.value.func, ast.Name) and node.value.func.id == 'print':
    #                 return node.lineno
    #
    #         return node.lineno
    #
    #     def execute_node(node, eval_dict, parent_node=None):
    #         """
    #         Helper function to execute a single AST node
    #         parent_node: The parent AST node, used for context in line number calculation
    #         """
    #         # Set the line number based on the actual position in code
    #         if hasattr(node, 'lineno'):
    #             self.line_value = find_actual_line_number(node, expr.splitlines())
    #
    #         if isinstance(node, ast.FunctionDef):
    #             # For function definitions
    #             wrapped_node = ast.Module([node], type_ignores=[])
    #             compiled = compile(wrapped_node, 'file', 'exec')
    #             exec(compiled, eval_dict)
    #
    #             # Get the newly defined function
    #             func = eval_dict[node.name]
    #
    #             # Create SerializableFunction and bind it immediately
    #             serialized_func = SerializableFunction(func, self)
    #
    #             # Store in persistent vars and as instance attribute
    #             self.persistent_vars[node.name] = serialized_func
    #             setattr(self, node.name, serialized_func)
    #
    #             # Update eval_dict with bound serializable function
    #             eval_dict[node.name] = serialized_func
    #
    #             return True
    #
    #         elif isinstance(node, ast.Assign):
    #             # Store assignments in persistent vars
    #             compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
    #             exec(compiled, eval_dict)
    #
    #             # Get variable names from the assignment
    #             targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
    #             for name in targets:
    #                 if name in eval_dict:
    #                     value = eval_dict[name]
    #                     # Store both original and wrapped version
    #                     self.persistent_vars[name] = wrap_for_serialization(value)
    #                     setattr(self, name, value)
    #                     print(f"{self.tcp_port}: Stored variable {name} - {type(value)}")
    #
    #             return True
    #
    #         elif isinstance(node, ast.Expr):
    #             # For expressions (including function calls)
    #             compiled = compile(ast.Expression(node.value), 'file', 'eval')
    #             response = eval(compiled, eval_dict)
    #             if response is not True and response is not None and not isinstance(node.value, ast.Constant):
    #                 self._sequential_exception_count = 0
    #             self.log(response)
    #             return True
    #
    #         elif isinstance(node, ast.Try):
    #             # Handle try-except blocks
    #             try:
    #                 # Execute the body of the try block
    #                 for n in node.body:
    #                     n = self._change_print_to_log(n)
    #                     execute_node(n, eval_dict, node)
    #             except Exception as e:
    #                 # Find matching except handler
    #                 handled = False
    #                 for handler in node.handlers:
    #                     if handler.type is None or isinstance(e, eval(compile(ast.Expression(handler.type), 'file',
    #                                                                           'eval'), eval_dict)):
    #                         if handler.name:
    #                             eval_dict[handler.name] = e
    #                         # Transform prints to logs in except block
    #                         for n in handler.body:
    #                             n = self._change_print_to_log(n)
    #                             execute_node(n, eval_dict, handler)
    #                         handled = True
    #                         break
    #
    #                 if not handled:
    #                     raise
    #             else:
    #                 # If no exception occurred, execute else block if it exists
    #                 if node.orelse:
    #                     for n in node.orelse:
    #                         n = self._change_print_to_log(n)
    #                         execute_node(n, eval_dict, node)
    #             finally:
    #                 # Execute finally block if it exists
    #                 if node.finalbody:
    #                     for n in node.finalbody:
    #                         n = self._change_print_to_log(n)
    #                         execute_node(n, eval_dict, node)
    #             return True
    #
    #         else:
    #             # For other statements
    #             compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
    #             exec(compiled, eval_dict)
    #             return True
    #
    #     tree = ast.parse(expr)
    #     self.logging_results = {}
    #     self.line_value = 0
    #
    #     # Create the custom dictionary that will also serve as globals
    #     eval_dict = {
    #         # Add built-ins
    #         **{name: getattr(builtins, name) for name in dir(builtins) if not name.startswith('_')},
    #         # Add instance attributes
    #         **{name: getattr(self, name) for name in dir(self) if not name.startswith('_')},
    #         # Add persistent vars
    #         **self.persistent_vars
    #     }
    #
    #     last_successful_state = None
    #     had_error = False
    #
    #     # Execute the expression
    #     for index, node in enumerate(tree.body):
    #         try:
    #             node = self._change_print_to_log(node)
    #             execute_node(node, eval_dict)
    #             last_successful_state = dict(self.persistent_vars)
    #
    #         except Exception as e:
    #             had_error = True
    #             self._sequential_exception_count += 1
    #             error_traceback = traceback.format_exc()
    #             error_lines = self._extract_error_lines(expr, error_traceback)
    #
    #             error_message = ""
    #             if error_lines:
    #                 error_message += "Error occurred in the following lines:\n"
    #                 for line_num, line_content in error_lines:
    #                     error_message += f"  Line {line_num}: {line_content}\n"
    #             error_type = error_traceback.strip().split('\n')[-1]
    #             error_message += f"\n{error_type}"
    #
    #             self.log(error_message)
    #
    #             # Restore the last successful state if available
    #             if last_successful_state is not None:
    #                 self.persistent_vars = last_successful_state.copy()
    #
    #             if self._sequential_exception_count >= self.max_sequential_exception_count:
    #                 break
    #
    #         # Update eval_dict with any new persistent vars
    #         eval_dict.update(self.persistent_vars)
    #
    #     # Get final results
    #     score, goal = self.score()
    #     result_output = parse_result_into_str(self.logging_results)
    #
    #     if had_error:
    #         raise Exception(result_output)
    #
    #     return score, goal, result_output
    #
    # def _eval_with_timeout2(self, expr):
    #     """
    #     Executes a Python expression with a timeout and returns the result
    #     """
    #
    #     def parse_result_into_str(data):
    #         result = []
    #         for key, values in data.items():
    #             for value in values:
    #                 result.append(f"{key}: {value}")
    #         return "\n".join(result)
    #
    #     tree = ast.parse(expr)
    #     self.logging_results = {}
    #     self.line_value = 0
    #
    #     # Create the custom dictionary that will also serve as globals
    #     eval_dict = {
    #         # Add built-ins
    #         **{name: getattr(builtins, name) for name in dir(builtins) if not name.startswith('_')},
    #         # Add instance attributes
    #         **{name: getattr(self, name) for name in dir(self) if not name.startswith('_')},
    #         # Add persistent vars
    #         **self.persistent_vars
    #     }
    #
    #     last_successful_state = None
    #     had_error = False
    #
    #     # Execute the expression
    #     for index, node in enumerate(tree.body):
    #         self.line_value = index
    #         try:
    #             node = self._change_print_to_log(node)
    #
    #             if isinstance(node, ast.FunctionDef):
    #                 # For function definitions
    #                 wrapped_node = ast.Module([node], type_ignores=[])
    #                 compiled = compile(wrapped_node, 'file', 'exec')
    #                 exec(compiled, eval_dict)
    #
    #                 # Get the newly defined function
    #                 func = eval_dict[node.name]
    #
    #                 # Create SerializableFunction and bind it immediately
    #                 serialized_func = SerializableFunction(func, self)
    #
    #                 # Store in persistent vars and as instance attribute
    #                 self.persistent_vars[node.name] = serialized_func
    #                 setattr(self, node.name, serialized_func)
    #
    #                 # Update eval_dict with bound serializable function
    #                 eval_dict[node.name] = serialized_func
    #
    #                 last_successful_state = dict(self.persistent_vars)
    #
    #             elif isinstance(node, ast.Assign):
    #                 # Store assignments in persistent vars
    #                 compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
    #                 exec(compiled, eval_dict)
    #
    #                 # Get variable names from the assignment
    #                 targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
    #                 for name in targets:
    #                     if name in eval_dict:
    #                         value = eval_dict[name]
    #                         # Store both original and wrapped version
    #                         self.persistent_vars[name] = wrap_for_serialization(value)
    #                         setattr(self, name, value)
    #                         print(f"{self.tcp_port}: Stored variable {name} - {type(value)}")
    #
    #                 last_successful_state = dict(self.persistent_vars)
    #
    #             elif isinstance(node, ast.Expr):
    #                 # For expressions (including function calls)
    #                 compiled = compile(ast.Expression(node.value), 'file', 'eval')
    #                 response = eval(compiled, eval_dict)
    #                 if response is not True and response is not None and not isinstance(node.value, ast.Constant):
    #                     self._sequential_exception_count = 0
    #                 #self.log(response)
    #                 last_successful_state = dict(self.persistent_vars)
    #
    #             else:
    #                 # For other statements
    #                 compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
    #                 exec(compiled, eval_dict)
    #                 last_successful_state = dict(self.persistent_vars)
    #
    #         except Exception as e:
    #             had_error = True
    #             self._sequential_exception_count += 1
    #             error_traceback = traceback.format_exc()
    #             error_lines = self._extract_error_lines(expr, error_traceback)
    #
    #             error_message = ""
    #             if error_lines:
    #                 error_message += "Error occurred in the following lines:\n"
    #                 for line_num, line_content in error_lines:
    #                     error_message += f"  Line {line_num}: {line_content}\n"
    #             error_type = error_traceback.strip().split('\n')[-1]
    #             error_message += f"\n{error_type}"
    #
    #             self.log(error_message)
    #
    #             # Restore the last successful state if available
    #             if last_successful_state is not None:
    #                 self.persistent_vars = last_successful_state.copy()
    #
    #             if self._sequential_exception_count >= self.max_sequential_exception_count:
    #                 break
    #
    #         # Update eval_dict with any new persistent vars
    #         eval_dict.update(self.persistent_vars)
    #
    #     # Get final results
    #     score, goal = self.score()
    #     result_output = parse_result_into_str(self.logging_results)
    #
    #     if had_error:
    #         raise Exception(result_output)
    #
    #     return score, goal, result_output

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
        self.add_command('/c game.map_settings.enemy_expansion.enabled = false', raw=True)
        self.add_command('/c game.map_settings.enemy_evolution.enabled = false', raw=True)
        self.add_command('/c game.forces.enemy.kill_all_units()', raw=True)


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