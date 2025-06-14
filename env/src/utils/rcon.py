import os
import re
from glob import glob
from itertools import chain
from pathlib import Path
from typing import List
from typing_extensions import deprecated

from timeit import default_timer as timer
from slpp import slpp as lua

import io
import contextlib


def _load_script(filename):
    with open(filename, "r", encoding="utf-8") as file:
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
                if filename.endswith(".lua"):
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
    return list(
        chain.from_iterable(
            glob(os.path.join(x[0], "*.lua")) for x in os.walk(init_dir)
        )
    )


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
    try:
        init = [init for init in inits if init.endswith(filename + ".lua")][0]
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
                parts.append(value.replace("!!", '"').strip())
            else:
                parts.append(value)
        else:
            pruned[key] = value

    if parts:
        pruned = parts
    return pruned


class LuaConversionError(Exception):
    """Custom exception for Lua conversion errors"""

    pass


def _check_output_for_errors(command, response, output):
    """Check captured stdout for known Lua parsing errors"""
    ERRORS = {
        "unexp_end_string": "Unexpected end of string while parsing Lua string.",
        "unexp_end_table": "Unexpected end of table while parsing Lua string.",
        "mfnumber_minus": "Malformed number (no digits after initial minus).",
        "mfnumber_dec_point": "Malformed number (no digits after decimal point).",
        "mfnumber_sci": "Malformed number (bad scientific format).",
    }

    for error_key, error_msg in ERRORS.items():
        if error_msg in output:
            raise LuaConversionError(
                f"Lua parsing error: {error_msg} for command:\n'{command}' with response:\n'{response}'"
            )


def _lua2python(command, response, *parameters, trace=False, start=0):
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        if not response:
            return None, (timer() - start)

        try:
            # Handle the case where response is a complete table
            if response.strip().startswith("{") and response.strip().endswith("}"):
                output = lua.decode(response)
            else:
                # Handle the case where we need to extract the last line
                splitted = response.split("\n")[-1]
                if "[string" in splitted:
                    splitted = re.sub(r"\[string[^\]]*\]", "", splitted)
                output = lua.decode(splitted)

            if isinstance(output, dict) and "b" in output:
                output["b"] = _remove_numerical_keys(output["b"])

            return output, (timer() - start)

        except Exception as e:
            if trace:
                print(f"Parsing error: {str(e)}")
            return None, (timer() - start)


@deprecated("Doesn't handle nested structures that well")
def _lua2python_old(command, response, *parameters, trace=False, start=0):
    # Capture stdout using StringIO
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        if trace:
            print(command, parameters, response)

        if response:
            if trace:
                print(f"success: {command}")
            end = timer()

            if response[0] != "{":
                splitted = response.split("\n")[-1]

                if "[string" in splitted:
                    a, b = splitted.split("[string")
                    splitted = a + '["' + b.replace('"', "!!")
                    splitted = re.sub(r",\s*}\s*$", "", splitted) + '"]}'

                try:
                    output = lua.decode(splitted)
                except Exception:
                    # Capture any decode errors
                    output = None
            else:
                try:
                    output = lua.decode(response)
                except Exception:
                    # Capture any decode errors
                    output = None

            if trace:
                print(
                    "{hbar}\nCOMMAND: {command}\nPARAMETERS: {parameters}\n\n{response}\n\nOUTPUT:{output}".format(
                        hbar="-" * 100,
                        command=command,
                        parameters=parameters,
                        response=response,
                        output=output,
                    )
                )

            # Check captured stdout for errors
            captured_output = stdout.getvalue()
            _check_output_for_errors(command, response, captured_output)

            # remove numerical keys
            if isinstance(output, dict) and "b" in output:
                pruned = _remove_numerical_keys(output["b"])
                output["b"] = pruned

            return output, (end - start)
        else:
            if trace:
                print(f"failure: {command} \t")
            end = timer()

            try:
                return lua.decode(response), (end - start)
            except Exception:
                # Check captured stdout for errors before returning None
                captured_output = stdout.getvalue()
                _check_output_for_errors(command, response, captured_output)
                return None, (end - start)
