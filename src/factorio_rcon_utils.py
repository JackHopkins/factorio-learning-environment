import os
import re
from glob import glob
from itertools import chain
from pathlib import Path
from typing import List
from factorio_rcon import AsyncRCONClient
from timeit import default_timer as timer
from slpp import slpp as lua



def _load_scripts(scripts):
    script_dict = {}
    for filename in scripts:
        with open(filename, "r") as file:
            script_string = "".join(file.readlines())
            pruned = Path(filename).name[:-4]
            script_dict[pruned] = script_string
    return script_dict

def _load_actions():
    # get local execution path
    path = os.path.dirname(os.path.realpath(__file__))

    actions = list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(f'{path}/actions')))
    return _load_scripts(actions)

def _load_action(filename):
    # get local execution path
    path = os.path.dirname(os.path.realpath(__file__))

    actions = list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(f'{path}/actions')))
    for action in actions:
        if action.endswith(filename+".lua"):
            with open(action, 'r') as file:
                script = file.read()
                return script

    raise ValueError(f"No action found with the name {filename}")

def _load_init():
    # get local execution path
    path = os.path.dirname(os.path.realpath(__file__))

    init = list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(f'{path}/init')))
    return _load_scripts(init)



def _lua2python(command, response, *parameters, trace=False, start=0):
    if trace:
        print(command, parameters, response)
    if response:
        if trace:
            print(f"success: {command}")
        end = timer()
        splitted = response.split("\n")[-1]

        if "[string" in splitted:
            a, b = splitted.split("[string")
            splitted = a + '[\"' + b.replace('"', '!!').strip(',} ') + "\"]}"

        output = lua.decode(splitted)

        ##output = luadata.unserialize(splitted[-1], encoding="utf-8", multival=False)

        if trace:
            print("{hbar}\nCOMMAND: {command}\nPARAMETERS: {parameters}\n\n{response}\n\nOUTPUT:{output}"
                  .format(hbar="-" * 100, command=command, parameters=parameters, response=response, output=output))

            # Only the last transmission is considered the output - the rest are just messages
        return output, (end - start)
    else:
        if trace:
            print(f"failure: {command} \t")
    end = timer()
    return lua.decode(response), (end - start)

