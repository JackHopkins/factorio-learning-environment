import os
import sys
import time
from typing import List, Tuple, Dict, Any, Union

from slpp import slpp as lua, ParseError
from timeit import default_timer as timer

from factorio_entities import Position, Entity
from factorio_rcon_utils import _lua2python, _load_action

COMMAND = "/silent-command"

class Controller:

    def __init__(self, lua_script_manager: 'FactorioLuaScriptManager', game_state: 'FactorioInstance', *args, **kwargs):
        self.connection = lua_script_manager.rcon_client
        self.game_state = game_state
        self.name = self.camel_to_snake(self.__class__.__name__)
        self.lua_script_manager = lua_script_manager
    def clean_response(self, response):
        cleaned_response = {}
        for key, value in response.items():
            if isinstance(value, dict):
                # if not value:
                #    continue
                if 1 in value.keys():

                    if 'inventory' in key:
                        cleaned_response[key] = {}
                        values = list(value.values())
                        for val in values:
                            cleaned_response[key][val['name']] = val['count']
                    else:
                        cleaned_response[key] = []
                        for sub_key, sub_value in value.items():
                            cleaned_response[key].append(sub_value)
                else:
                    cleaned_response[key] = value
            else:
                cleaned_response[key] = value
        return cleaned_response

    def camel_to_snake(self, camel_str):
        snake_str = ""
        for index, char in enumerate(camel_str):
            if char.isupper():
                if index != 0:
                    snake_str += "_"
                snake_str += char.lower()
            else:
                snake_str += char
        return snake_str


    def _get_command(self, command, parameters=[], measured=True):
        if command in self.script_dict:
            script = f'{COMMAND} '+ self.script_dict[command]
            for index in range(len(parameters)):
                script = script.replace(f"arg{index + 1}", lua.encode(parameters[index]))
        else:
            script = command
        return script

    def execute(self, *args) -> Tuple[Dict, Any]:
        try:
            start = time.time()
            parameters = [lua.encode(arg) for arg in args]
            #parameters.append(lua.encode(arg.dict()))
            #parameters = [lua.encode(arg) for arg in args]
            invocation = f"pcall(global.actions.{self.name}{(', ' if parameters else '') + ','.join(parameters)})"
            wrapped = f"{COMMAND} a, b = {invocation}; rcon.print(dump({{a=a, b=b}}))"
            lua_response = self.connection.send_command(wrapped)
            parsed, elapsed = _lua2python(invocation, lua_response, start=start)
            if not parsed['a'] and 'b' in parsed and isinstance(parsed['b'], str):
                parsed['b'] = parsed['b'].replace("!!", "\"")
            if not 'b' in parsed:
                return {}, elapsed
        except ParseError as e:
            # If a non-string gets passed back from the Lua script, it will raise a ParseError
            # Split by `["b"] = ` and take the second part, which is the returned value
            try:
                parts = lua_response.split('["b"] = ')
                return parts[1][:-2], -1
            except IndexError:
                return e.args[0], -1
            return lua_response, -1
        except TypeError as e:
            return lua_response, -1
        except Exception as e:
            return lua_response, -1
        return parsed['b'], elapsed

    def send(self, command, *parameters, trace=False) -> List[str]:
        start = timer()
        script = self._get_command(command, parameters=list(parameters), measured=False)
        lua_response = self.connection.send_command(script)
        # print(lua_response)
        return _lua2python(command, lua_response, start=start)

