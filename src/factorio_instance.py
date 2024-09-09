import ast
import concurrent
import importlib
import os
from enum import Enum
from pathlib import Path
from timeit import default_timer as timer
from typing import List

from dotenv import load_dotenv
from slpp import slpp as lua

from src.factorio_rcon_utils import _load_actions, _load_init, _lua2python
from src.rcon.factorio_rcon import RCONClient
from factorio_types import Prototype, Resource
from models.game_state import GameState
from vocabulary import Vocabulary

from factorio_entities import *

CHUNK_SIZE = 32
MAX_SAMPLES = 5000

load_dotenv()

PLAYER = 1
NONE = 'nil'

global var
var = {}

class Direction(Enum):
    """
    Factorio directions (for some reason they are different from the cardinal directions)
    North - 0
    Northeast - 1
    East - 2
    Southeast - 3
    South - 4
    Southwest - 5
    West - 6
    Northwest - 7

    -- self.UP, self.ABOVE, self.TOP = 1
        -- self.RIGHT, self.EAST = 4
        -- self.LEFT, self.WEST = 3
        -- self.DOWN, self.BELOW, self.BOTTOM = 2
    """
    UP = NORTH = 0
    RIGHT = EAST = 1
    LEFT = WEST = 3
    DOWN = BELOW = BOTTOM = 2

    # SOUTH = 2
    # NORTH = 0
    # EAST = 1
    # WEST = 3

    # UP = 0
    # RIGHT = 1
    # LEFT = 3
    # DOWN = 2
    #
    # SOUTH = 2
    # NORTH = 0
    # EAST = 1
    # WEST = 3

    # UP = 0
    # RIGHT = 3
    # LEFT = 2
    # DOWN = 1
    # SOUTH = 1
    # NORTH = 0
    # EAST = 2
    # WEST = 3


class FactorioInstance:

    def __init__(self, address=None,
                 vocabulary: Vocabulary = Vocabulary(),
                 bounding_box=20,
                 fast=False,
                 tcp_port=27015, inventory={}):
        self.tcp_port = tcp_port
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)

        self.game_state = GameState().with_default(vocabulary)
        self.game_state.fast = fast

        self.max_sequential_exception_count = 2
        self._sequential_exception_count = 0
        self.actions = _load_actions()

        self.script_dict = {**self.actions, **_load_init()}
        self.initial_inventory = inventory
        self.initialise(**inventory)
        self._load_actions(self.rcon_client, self.game_state)
        self.observe_all()
        self._tasks = []

        self._initial_score, goal = self.score()

        # Available objects that the agent can interact with
        self.Prototype = Prototype
        self.Resource = Resource
        self.Direction = Direction
        self.Position = Position

        # Statically named directions
        self.UP, self.ABOVE, self.TOP = [Direction.UP]*3
        self.RIGHT, self.EAST = [Direction.RIGHT]*2
        self.LEFT, self.WEST = [Direction.LEFT]*2
        self.DOWN, self.BELOW, self.BOTTOM = [Direction.DOWN]*3

        # Available actions that the agent can perform
        self._static_members = [attr for attr in dir(self)
                                if not callable(getattr(self, attr))
                                and not attr.startswith("__")
                                ]



    def reset(self):
        #self.script_dict = {**self.actions, **_load_init()}
        #self.initialise(**inventory)
        for attr in dir(self):
            if not callable(getattr(self, attr)) and attr[0] != "_" and attr not in self._static_members:
                self[attr] = None

        self._reset(**self.initial_inventory if isinstance(self.initial_inventory, dict) else self.initial_inventory.__dict__)
        try:
            self.observe_all()
        except Exception as e:
            print(e)
            pass
        self.game_state._initial_score = 0
        #self.game_state.initial_score, goal = self.score()

    def print(self, arg):
        self.memory.log_observation(str(arg))
        print(arg)

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
            rcon_client.send_command('/c global.actions = {}')

        except Exception as e:
            raise ConnectionError(f"Could not connect to {address} at tcp/{tcp_port}: \n{e.args[0]}")

        print(f"Connected to {address} client at tcp/{tcp_port}.")
        return rcon_client, address

    def _load_actions(self, connection, game_state):
        # Define the directory containing the callable class files
        callable_classes_directory = "controllers"

        # Get the local execution directory
        local_directory = os.path.dirname(os.path.realpath(__file__))

        def snake_to_camel(snake_str):
            return "".join(word.capitalize() for word in snake_str.split("_"))

        # Loop through the files in the directory
        for file in os.listdir(os.path.join(local_directory, callable_classes_directory)):
            # Check if the file is a Python file and does not start with '_'
            if file.endswith(".py") and not file.startswith("_"):
                # Load the module
                module_name = Path(file).stem
                module_spec = importlib.util.spec_from_file_location(module_name,
                                                                     os.path.join(os.path.join(local_directory, callable_classes_directory), file))
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)

                class_name = snake_to_camel(module_name)
                if module_name == "place_entity":
                    class_name = "PlaceObject"
                if module_name == "score":
                    class_name = "Reward"
                # Get the callable class
                callable_class = getattr(module, class_name)

                # Create an instance of the callable class
                try:
                    callable_instance = callable_class(connection, game_state)
                except Exception as e:
                    raise Exception(f"Could not instantiate {class_name}. {e}")
                # Add the instance as a member method
                setattr(self, module_name.lower(), callable_instance)

    def __getitem__(self, key):
        if key not in dir(self) or key.startswith('__'):
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def _eval_with_timeout(self, expr):
        """
        Executes a Python expression with a timeout
        :param expr:
        :return:
        """

        tree = ast.parse(expr)
        results = {}
        for index, node in enumerate(tree.body):
            try:
                if isinstance(node, ast.Expr):
                    compiled = compile(ast.Expression(node.value), 'file', 'eval')
                    response = eval(compiled, {}, self)
                    if response is not True and response:
                        results[index] = response
                        self._sequential_exception_count = 0
                else:
                    compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
                    exec(compiled, {}, self)
                    #results.append("Executed successfully")
            except Exception as e:
                self._sequential_exception_count += 1

                if self._sequential_exception_count == self.max_sequential_exception_count:
                    pass
                    #break

                # parts = list(e.args)
                # sentences = ". ".join([str(part).replace("_", " ") for part in parts])
                # results[index] = f"Error at line {node.end_lineno}: {sentences}"
                # break

                # Get detailed error information
                error_info = {
                    "line_number": node.lineno,
                    "end_line_number": node.end_lineno,
                    "function_name": None,
                    "inputs": None,
                }

                # Extract function name and inputs if available
                if isinstance(node, ast.FunctionDef):
                    error_info["function_name"] = node.name
                    error_info["inputs"] = [arg.arg for arg in node.args.args]
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    error_info["function_name"] = node.func.id
                    error_info["inputs"] = [ast.unparse(arg) for arg in node.args]

                # Format the error message
                error_message = f"Error at lines {error_info['line_number']}-{error_info['end_line_number']}"
                if error_info["function_name"]:
                    error_message += f" in function '{error_info['function_name']}'"
                if error_info["inputs"]:
                    error_message += f" with inputs: {', '.join(error_info['inputs'])}"
                error_message += f": {str(e)}"

                results[index] = error_message
                break

        score, goal = self.score()
        return score, goal, '\n'.join([f"{i}: {str(r)}" for i, r in results.items()])

    def eval_with_error(self, expr, timeout=60):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._eval_with_timeout, expr)
            score, goal, result = future.result(timeout)
            return score, goal, result

    def eval(self, expr, timeout=60):
        "Evaluate several lines of input, returning the result of the last line with a timeout"
        try:
            return self.eval_with_error(expr, timeout)
        except concurrent.futures.TimeoutError:
            return -1, "", "Error: Evaluation timed out"
        except Exception as e:
            trace = e.__traceback__
            return -1, "", f"Error: {str(e)}"

    def run_tasks(self):
        for task in self._tasks:
            try:
                next(task)()
            except StopIteration:
                self.observe()

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
        start = timer()
        script = self._get_command(command, parameters=list(parameters), measured=False)
        lua_response = self.rcon_client.send_command(script)
        # print(lua_response)
        return _lua2python(command, lua_response, start=start)

    def comment(self, comment: str, *args):
        # game.players[1].print({"","[img=entity/character][color=orange]",{"engineer-title"},": [/color]",{"think-"..thought}})
        #self.rcon_client.send_command(f'/c game.players[1].print("[img=entity/character][color=orange]" {{"{comment}"}},": ",{args}}})')
        self.rcon_client.send_command(f"[img=entity/character] " + str(comment) + ", ".join(args))

    def _reset(self, **kwargs):
        self._send("/c global.alerts = {}")
        #self._send("/c game.reload_script()")
        self._send('/c game.reset_game_state()')
        self._send('clear_inventory', PLAYER)
        self._send('reset_position', PLAYER, 0, 0)
        #self._send('regenerate_resources', PLAYER)
        self.clear_entities()
        #self.regenerate_resources()
        #self._send('clear_entities', PLAYER)

        for entity, count in kwargs.items():
            self._send('give_item', PLAYER, entity, count)

    def initialise(self, **kwargs):

        self._send('initialise', PLAYER)
        self._send('alerts')
        self._send('util')
        self._send('serialize')
        self._send('production_score')
        # self._send('story')
        # self.factorio_client.send('new_world', PLAYER)
        self._send('clear_inventory', PLAYER)
        self._send('reset_position', PLAYER, 0, 0)

        for entity, count in kwargs.items():
            self._send('give_item', PLAYER, entity, count)

    def get_warnings(self, seconds=10):
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

    def _set_walking(self, walking: bool):
        if walking:
            lua_response = self.rcon_client.send_command(
                '/c game.players[1].character.walking_state = {walking = true, direction = defines.direction.north}')
        else:
            lua_response = self.rcon_client.send_command(
                '/c game.players[1].character.walking_state = {walking = false, direction = defines.direction.north}')
        return lua_response

    def observe_statistics(self):
        """
        At each time t, statistics on the factory are returned
        :return:
        """
        response, execution_time = self._send('observe_performance', PLAYER)
        return response, execution_time

    def observe_position(self):
        """
        At each time t, the agent receives the agent’s current absolute position p.
        :return:
        """
        return self._send('observe_position', PLAYER)

    def observe_nearest_points_of_interest(self):
        """
        At each time t, the agent receives the positions of the nearest points of interest.
        :return:
        """
        return self._send('observe_points_of_interest', PLAYER, 200)

