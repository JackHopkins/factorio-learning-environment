import re
import time
from timeit import default_timer as timer
from typing import List, Tuple, Dict, Any

from slpp import slpp as lua

from fle.env.entities import Direction
from fle.env.lua_manager import LuaScriptManager
from fle.env.namespace import FactorioNamespace
from fle.env.utils.rcon import _lua2python

COMMAND = "/silent-command"


def parse_lua_table(text):
    a = re.search(r'\["a"\]\s*=\s*(true|false)', text)
    b = re.search(r'\["b"\]\s*=\s*(.*?)(?=,\s*})', text, re.DOTALL)

    if not b:
        return {"a": a.group(1) == "true" if a else None, "b": None}

    interim = b.group(1).strip()
    func = re.search(r"interface function\s+([^:]+):", interim)
    error = re.search(r":\d+:\s*(.*?)(?=\s*stack traceback:)", interim, re.DOTALL)
    stack = re.search(r"stack traceback:\s*(.*)", interim, re.DOTALL)
    if not func and not error:
        return interim + " }"

    return {
        "a": a.group(1) == "true" if a else None,
        "b": lua.decode(interim),
        "function_name": func.group(1).strip() if func else None,
        "error_string": error.group(1).strip() if error else None,
        "stack_traceback": stack.group(1).strip() if stack else None,
    }


class Controller:
    def __init__(
        self,
        lua_script_manager: "LuaScriptManager",
        game_state: "FactorioNamespace",
        verbose: bool = True,
        *args,
        **kwargs,
    ):
        # assert isinstance(lua_script_manager, LuaScriptManager), f"Not correct: {type(lua_script_manager)}"
        self.connection = lua_script_manager
        self.game_state = game_state
        self.name = self.camel_to_snake(self.__class__.__name__)
        self.lua_script_manager = lua_script_manager
        self.player_index = (
            game_state.agent_index + 1
        )  # +1 because Factorio is 1-indexed
        self.verbose = verbose

    def clean_response(self, response):
        def is_lua_list(d):
            """Check if dictionary represents a Lua-style list (keys are consecutive numbers from 1)"""
            if not isinstance(d, dict) or not d:
                return False
            keys = set(str(k) for k in d.keys())
            return all(str(i) in keys for i in range(1, len(d) + 1))

        def clean_value(value):
            """Recursively clean a value"""
            if isinstance(value, dict):
                # Handle Lua-style lists
                if is_lua_list(value):
                    # Sort by numeric key and take only the values
                    sorted_items = sorted(value.items(), key=lambda x: int(str(x[0])))
                    return [clean_value(v) for k, v in sorted_items]

                # Handle inventory special case
                if any(isinstance(k, int) for k in value.keys()) and all(
                    isinstance(v, dict) and "name" in v and "count" in v
                    for v in value.values()
                ):
                    cleaned_dict = {}
                    for v in value.values():
                        cleaned_dict[v["name"]] = v["count"]
                    return cleaned_dict

                # Regular dictionary
                return {k: clean_value(v) for k, v in value.items()}

            elif isinstance(value, list):
                return [clean_value(v) for v in value]

            return value

        cleaned_response = {}

        if not hasattr(response, "items"):
            pass

        for key, value in response.items():
            # if key == 'status' and isinstance(value, str):
            # cleaned_response[key] = EntityStatus.from_string(value)
            if key == "direction" and isinstance(value, str):
                cleaned_response[key] = Direction.from_string(value)
            elif not value and key in (
                "warnings",
                "input_connection_points",
                "output_connection_points",
            ):
                cleaned_response[key] = []
            else:
                cleaned_response[key] = clean_value(value)

        return cleaned_response

    def parse_lua_dict(self, d):
        if all(isinstance(k, int) for k in d.keys()):
            # Convert to list if all keys are numeric
            return [self.parse_lua_dict(d[k]) for k in sorted(d.keys())]
        else:
            # Process dictionaries with mixed keys
            new_dict = {}
            last_key = None

            for key in d.keys():
                if isinstance(key, int):
                    if last_key is not None and isinstance(d[key], str):
                        # Concatenate the value to the previous key's value
                        new_dict[last_key] += "-" + d[key]
                else:
                    last_key = key
                    if isinstance(d[key], dict):
                        # Recursively process nested dictionaries
                        new_dict[key] = self.parse_lua_dict(d[key])
                    else:
                        new_dict[key] = d[key]

            return new_dict

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
            script = f"{COMMAND} " + self.script_dict[command]
            for index in range(len(parameters)):
                script = script.replace(
                    f"arg{index + 1}", lua.encode(parameters[index])
                )
        else:
            script = command
        return script

    def get_error_message(self, response):
        try:
            s = str(response)

            # Trim stacktrace early to avoid picking quoted script fragments from the traceback
            if "stack traceback" in s:
                s = s.split("stack traceback", 1)[0]

            # Prefer the last double-quoted substring if present (Factorio often wraps messages in quotes)
            quoted = re.findall(r'"([^"]+)"', s)
            if quoted:
                return quoted[-1].strip()

            # Fallback: take the segment after the last ':' but avoid common noise like 'in main chunk'
            parts = s.split(":")
            if parts:
                candidate = (
                    parts[-1]
                    .replace('"', "")
                    .replace("\\'", "")
                    .replace("'", "")
                    .strip()
                )
                if candidate.lower().startswith("in main chunk") and len(parts) > 1:
                    candidate = (
                        parts[-2]
                        .replace('"', "")
                        .replace("\\'", "")
                        .replace("'", "")
                        .strip()
                    )
                return candidate

            return s
        except Exception:
            return str(response)

    def execute(self, *args) -> Tuple[Dict, Any]:
        try:
            start = time.time()
            parameters = [lua.encode(arg) for arg in args]
            # if self.verbose:
            #     print(f"## {self.name}")
            #     print(f"Python Args: {args}\nLua Parameters: {parameters}")
            response = self.connection.rcon_client.send_command(
                f"/sc rcon.print(remote.interfaces['actions']['{self.name}'])"
            )
            if response == "false":
                print(f"No action found for {self.name}: {response}")
                return {}, "Action not found"
            parameters_str = (", " if parameters else "") + ", ".join(parameters)
            invocation = f"pcall(remote.call, 'actions', '{self.name}'{parameters_str})"
            wrapped = f"{COMMAND} a, b = {invocation}; rcon.print(dump({{a=a, b=b}}))"
            if self.verbose:
                print(f"Wrapped command: {wrapped}")
            lua_response = self.connection.rcon_client.send_command(wrapped)
            if self.verbose:
                print(f"Lua response: {lua_response}")
            if "Error when running interface function" in lua_response:
                parsed = parse_lua_table(lua_response)
                print("🚨 LUA ERROR DETECTED 🚨")
                print("=" * 50)
                if isinstance(parsed, dict) and "error_string" in parsed:
                    print(f"Error Message: {parsed['error_string']}")
                if isinstance(parsed, dict) and "stack_traceback" in parsed:
                    print(f"Stack Trace:\n{parsed['stack_traceback']}")
                else:
                    print(f"Raw Error Response: {lua_response}")
                print("=" * 50)
            else:
                parsed, elapsed = _lua2python(invocation, lua_response, start=start)
            if parsed is None:
                return {}, lua_response  # elapsed

            if not parsed.get("a") and "b" in parsed and isinstance(parsed["b"], str):
                # Return the raw Lua error; callers can extract a precise message if needed
                # if self.verbose:
                #     print(f"Lua error: {self.get_error_message(lua_response)}")
                return parsed["error_string"], lua_response

            return parsed.get("b", {}), lua_response  # elapsed

        except Exception:
            return {}, -1

    def send(self, command, *parameters, trace=False) -> List[str]:
        start = timer()
        script = self._get_command(command, parameters=list(parameters), measured=False)
        lua_response = self.connection.send_command(script)
        # print(lua_response)
        return _lua2python(command, lua_response, start=start)
