import os
import re
from glob import glob
from itertools import chain
from pathlib import Path
from typing import List
from typing_extensions import deprecated

from factorio_rcon import AsyncRCONClient
from timeit import default_timer as timer
from slpp import slpp as lua


def _load_script(filename):
    with open(filename, "r", encoding='utf-8') as file:
        script_string = file.read()
        pruned = Path(filename).name[:-4]
        return pruned, script_string

def _load_scripts(scripts):
    script_dict = {}
    for filename in scripts:
        pruned, script_string = _load_script(filename)
        script_dict[pruned] = script_string
    return script_dict
#
# @deprecated("Moving to tools")
# def _get_action_dir():
#     # get local execution path
#     path = os.path.dirname(os.path.realpath(__file__))
#     return path + "/actions"

def _get_lib_dir():
    # get local execution path
    path = os.path.dirname(Path(os.path.dirname(os.path.realpath(__file__))))
    return path + "/lib"

def _get_dir(name="tools"):
    # get local execution path
    path = os.path.dirname(Path(os.path.dirname(os.path.realpath(__file__))))
    return path + f"/{name}"


def _get_tool_names(name="tools") -> List[str]:
    tool_dir = _get_dir(name)
    lua_files = []

    # Walk through all directories
    for dirpath, _, filenames in os.walk(tool_dir):
        # Skip processing files if this is a valid tool directory
        if dirpath == tool_dir:
            continue

        # First check if this is a valid tool directory
        server_file = os.path.join(dirpath, "server.lua")
        client_file = os.path.join(dirpath, "client.py")

        if os.path.isfile(server_file) and os.path.isfile(client_file):
            # If valid, collect all .lua files in this directory
            for filename in filenames:
                if filename.endswith('.lua'):
                    # Get the relative path from tool_dir
                    full_path = os.path.join(dirpath, filename)
                    lua_files.append(full_path)

    return lua_files

# @deprecated("Moving to tools")
# def _get_action_names() -> List[str]:
#     action_dir = _get_action_dir()
#     return list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(action_dir)))

def _get_lib_names():
    init_dir = _get_lib_dir()
    return list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(init_dir)))

# def _load_action(filename):
#     actions = _get_action_names()
#     try :
#         action = [action for action in actions if action.endswith(filename+".lua")][0]
#         name, script = _load_script(action)
#         return script
#     except IndexError:
#         raise ValueError(f"No action found with the name {filename}")

def _load_lib(filename):
    inits = _get_lib_names()
    try :
        init = [init for init in inits if init.endswith(filename+".lua")][0]
        name, script = _load_script(init)
        return script
    except IndexError:
        raise ValueError(f"No init found with the name {filename}")

def _load_initialisation_scripts():
    return _load_scripts(_get_lib_names())

def _remove_numerical_keys(dictionary):
    pruned = {}
    if not isinstance(dictionary, dict):
        return dictionary
    parts = []
    for key, value in dictionary.items():
        if isinstance(key, int):
            if isinstance(value, dict):
                parts.append(_remove_numerical_keys(value))
            elif isinstance(value, str):
                parts.append(value.replace("!!", "\"").strip())
            else:
                parts.append(value)
        else:
            pruned[key] = value

    if parts:
        pruned = parts
    return pruned

def _lua2python(command, response, *parameters, trace=False, start=0):
    if trace:
        print(command, parameters, response)
    if response:
        if trace:
            print(f"success: {command}")
        end = timer()

        if response[0] != '{':

            splitted = response.split("\n")[-1]

            if "[string" in splitted:
                a, b = splitted.split("[string")
                splitted = a + '[\"' + b.replace('"', '!!')
                # remove trailing ',} '
                splitted = re.sub(r',\s*}\s*$', '', splitted) + "\"]}"

            output = lua.decode(splitted)
        else:
            output = lua.decode(response)

        ##output = luadata.unserialize(splitted[-1], encoding="utf-8", multival=False)

        if trace:
            print("{hbar}\nCOMMAND: {command}\nPARAMETERS: {parameters}\n\n{response}\n\nOUTPUT:{output}"
                  .format(hbar="-" * 100, command=command, parameters=parameters, response=response, output=output))

        # remove numerical keys
        if isinstance(output, dict) and 'b' in output:
            pruned = _remove_numerical_keys(output['b'])
            output['b'] = pruned
            # Only the last transmission is considered the output - the rest are just messages
        return output, (end - start)
    else:
        if trace:
            print(f"failure: {command} \t")
    end = timer()

    try:
        return lua.decode(response), (end - start)
    except Exception as e:
        return None, (end - start)

