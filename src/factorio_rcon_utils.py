import os
import re
from glob import glob
from itertools import chain
from pathlib import Path
from typing import List
from factorio_rcon import AsyncRCONClient
from timeit import default_timer as timer
from slpp import slpp as lua


def _load_script(filename):
    with open(filename, "r") as file:
        script_string = "".join(file.readlines())
        pruned = Path(filename).name[:-4]
        return pruned, script_string

def _load_scripts(scripts):
    script_dict = {}
    for filename in scripts:
        pruned, script_string = _load_script(filename)
        script_dict[pruned] = script_string
    return script_dict

def _get_action_dir():
    # get local execution path
    path = os.path.dirname(os.path.realpath(__file__))
    return path + "/actions"

def _get_init_dir():
    # get local execution path
    path = os.path.dirname(os.path.realpath(__file__))
    return path + "/init"

def _get_action_names() -> List[str]:
    action_dir = _get_action_dir()
    return list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(action_dir)))

def _get_init_names():
    init_dir = _get_init_dir()
    return list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(init_dir)))

def _load_action(filename):
    actions = _get_action_names()
    try :
        action = [action for action in actions if action.endswith(filename+".lua")][0]
        name, script = _load_script(action)
        return script
    except IndexError:
        raise ValueError(f"No action found with the name {filename}")

def _load_init(filename):
    inits = _get_init_names()
    try :
        init = [init for init in inits if init.endswith(filename+".lua")][0]
        name, script = _load_script(init)
        return script
    except IndexError:
        raise ValueError(f"No init found with the name {filename}")

def _load_initialisation_scripts():
    return _load_scripts(_get_init_names())

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
    return lua.decode(response), (end - start)

