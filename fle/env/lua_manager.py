import hashlib
import json

import importlib
import os
from pathlib import Path

from lupa.lua54 import LuaRuntime

from factorio_rcon import RCONClient
from fle.env.utils.rcon import (
    _get_dir,
    _get_mods_dir,
    _get_lib_names,
    _get_tool_names,
    _load_mods,
    _load_script,
)


class LuaScriptManager:
    def __init__(self, rcon_client: RCONClient, cache_scripts: bool = False):
        self.rcon_client = rcon_client
        self.cache_scripts = cache_scripts
        if not cache_scripts:
            self._clear_game_checksums(rcon_client)
        # self.action_directory = _get_action_dir()

        self.lib_directory = _get_mods_dir()
        if cache_scripts:
            self.init_action_checksums()
            self.game_checksums = self._get_game_checksums(rcon_client)

        self.tool_scripts = self.get_tools_to_load()

        self.lib_scripts = self.get_libs_to_load()
        self.lua = LuaRuntime(unpack_returned_tuples=True)

    def init_action_checksums(self):
        checksum_init_script = _load_mods("checksum")
        response = self.rcon_client.send_command("/sc " + checksum_init_script)
        return response

    def check_lua_syntax(self, script):
        try:
            self.lua.execute(script)
            return True, None
        except Exception as e:
            if "attempt to index a nil value" in e.args[0]:
                if "global" in e.args[0]:
                    return True, None
            return False, e.args[0]

    def load_tool_into_game(self, name):
        # Select scripts by exact tool directory, not prefix
        tool_dirs = {
            f"agent/{name}",
            f"admin/{name}",
            f"agent\\{name}",
            f"admin\\{name}",
        }
        tool_scripts = [
            key for key in self.tool_scripts.keys() if os.path.dirname(key) in tool_dirs
        ]
        # Sort scripts so server.lua comes last
        tool_scripts.sort(key=lambda x: x.endswith("server.lua"))

        for script_name in tool_scripts:
            if script_name not in self.tool_scripts:
                # attempt to load the script from the filesystem
                script = _load_script(script_name)
                self.tool_scripts[script_name] = script

            script = self.tool_scripts[script_name]
            if self.cache_scripts:
                checksum = self.calculate_checksum(script)
                if (
                    script_name in self.game_checksums
                    and self.game_checksums[script_name] == checksum
                ):
                    continue
                self.update_game_checksum(self.rcon_client, script_name, checksum)
                # Keep local view in sync so later loads skip
                self.game_checksums[script_name] = checksum

            correct, error = self.check_lua_syntax(script)
            if not correct:
                raise Exception(f"Syntax error in: {script_name}: {error}")
            print(f"{self.rcon_client.port}: Loading action {script_name} into game")

            response = self.rcon_client.send_command("/sc " + script)

            if response and "error" in response.lower():
                raise Exception(response)

    def load_init_into_game(self, name):
        if name not in self.lib_scripts:
            # attempt to load the script from the filesystem
            script = _load_mods(name)
            self.lib_scripts[name] = script

        script = self.lib_scripts[name]
        if self.cache_scripts:
            checksum = self.calculate_checksum(script)
            if name in self.game_checksums and self.game_checksums[name] == checksum:
                return
            self.update_game_checksum(self.rcon_client, name, checksum)

        response = self.rcon_client.send_command("/c " + script)

        if response and "error" in response.lower():
            raise Exception(response)

        pass

    def calculate_checksum(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def get_tools_to_load(self):
        scripts_to_load = {}
        lua_files = (
            _get_tool_names()
        )  # This returns all .lua files from previous modification
        tool_dir = _get_dir("tools")
        for lua_file in lua_files:
            # Get the tool name from the directory path
            rel_path = os.path.relpath(lua_file, Path(tool_dir))
            tool_name = os.path.dirname(rel_path)
            script_name = os.path.basename(lua_file)

            # Load the lua script content
            _, content = _load_script(lua_file)

            # Create a unique key combining tool and script name
            script_key = f"{tool_name}/{script_name}" if tool_name else script_name

            if self.cache_scripts:
                checksum = self.calculate_checksum(content)
                if (
                    script_key not in self.game_checksums
                    or self.game_checksums[script_key] != checksum
                ):
                    scripts_to_load[script_key] = content
            else:
                scripts_to_load[script_key] = content

        return scripts_to_load

    def get_libs_to_load(self):
        scripts_to_load = {}
        for filename in _get_lib_names():
            name, content = _load_script(filename)
            if self.cache_scripts:
                checksum = self.calculate_checksum(content)

                if (
                    name not in self.game_checksums
                    or self.game_checksums[name] != checksum
                ):
                    scripts_to_load[name] = content
            else:
                scripts_to_load[name] = content

        return scripts_to_load

    def update_game_checksum(self, rcon_client, script_name: str, checksum: str):
        rcon_client.send_command(
            f"/sc storage.set_lua_script_checksum('{script_name}', '{checksum}')"
        )

    def _clear_game_checksums(self, rcon_client):
        rcon_client.send_command("/sc storage.clear_lua_script_checksums()")

    def _get_game_checksums(self, rcon_client):
        response = rcon_client.send_command(
            "/sc rcon.print(storage.get_lua_script_checksums())"
        )
        return json.loads(response)

    def setup_tools(self, instance):
        """
        Load Python controllers from valid tool directories (those containing both client.py and server.lua)
        """
        tool_dir = _get_dir("tools")
        instance.controllers = {}

        def snake_to_camel(snake_str):
            return "".join(word.capitalize() for word in snake_str.split("_"))

        # Create a function that wraps a tool's call method to execute hooks
        def create_hook_wrapper(tool_name, original_callable):
            from functools import wraps

            @wraps(original_callable)
            def wrapper(*args, **kwargs):
                # Execute pre-tool hooks
                try:
                    self.execute_pre_tool_hooks(
                        instance, tool_name, original_callable, *args, **kwargs
                    )
                except Exception as e:
                    print(f"Error in pre-tool hook for {tool_name}: {e}")

                # Execute the original callable
                result = original_callable(*args, **kwargs)

                # Execute post-tool hooks
                try:
                    self.execute_post_tool_hooks(
                        instance, tool_name, original_callable, result
                    )
                except Exception as e:
                    print(f"Error in post-tool hook for {tool_name}: {e}")

                return result

            return wrapper

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
                    client_file,
                    # str(Path(client_file))
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
                    for i in range(instance.num_agents):
                        # Get and instantiate the controller class
                        callable_class = getattr(module, class_name)
                        callable_instance = callable_class(self, instance.namespaces[i])

                        # Create a wrapper that will execute hooks
                        wrapped_instance = create_hook_wrapper(
                            tool_name.lower(), callable_instance
                        )

                        # Store the controller and add it to namespace
                        instance.controllers[tool_name.lower()] = callable_instance

                        if directory_name == "admin":
                            # If this is an admin method, we hide it in the namespace by adding a shebang
                            setattr(
                                instance.namespaces[i],
                                f"_{tool_name.lower()}",
                                wrapped_instance,
                            )
                        else:
                            setattr(
                                instance.namespaces[i],
                                tool_name.lower(),
                                wrapped_instance,
                            )

                except Exception as e:
                    raise Exception(
                        f"Could not instantiate {class_name} from {client_file}. {e}"
                    )

    @staticmethod
    def register_post_tool_hook(instance, tool_name, callback=None):
        """
        Register a hook to be called after a specific tool is executed.
        Can be used as a regular function or as a decorator.

        Args:
            tool_name (str): Name of the tool to hook into
            callback (callable, optional): Function to call after the tool is executed.
                                          Will receive the tool instance and the result as arguments.

        Returns:
            If used as a regular function (with callback provided), returns the callback.
            If used as a decorator (without callback), returns a decorator function.
        """
        # When used as a decorator without parentheses: @register_post_tool_hook
        if tool_name is not None and callback is None and callable(tool_name):
            callback = tool_name
            tool_name = callback.__name__
            if not hasattr(instance, "post_tool_hooks"):
                instance.post_tool_hooks = {}
            if tool_name not in instance.post_tool_hooks:
                instance.post_tool_hooks[tool_name] = []
            instance.post_tool_hooks[tool_name].append(callback)
            return callback

        # When used as a decorator with arguments: @register_post_tool_hook("tool_name")
        if callback is None:

            def decorator(func):
                if not hasattr(instance, "post_tool_hooks"):
                    instance.post_tool_hooks = {}
                if tool_name not in instance.post_tool_hooks:
                    instance.post_tool_hooks[tool_name] = []
                instance.post_tool_hooks[tool_name].append(func)
                return func

            return decorator

        # When used as a regular function: register_post_tool_hook("tool_name", callback_func)
        if not callable(callback):
            raise TypeError("Callback must be callable")

        if not hasattr(instance, "post_tool_hooks"):
            instance.post_tool_hooks = {}
        if tool_name not in instance.post_tool_hooks:
            instance.post_tool_hooks[tool_name] = []

        instance.post_tool_hooks[tool_name].append(callback)
        return callback

    @staticmethod
    def register_pre_tool_hook(instance, tool_name, callback=None):
        """
        Register a hook to be called before a specific tool is executed.
        Can be used as a regular function or as a decorator.

        Args:
            tool_name (str): Name of the tool to hook into
            callback (callable, optional): Function to call before the tool is executed.
                                          Will receive the tool instance and the arguments as parameters.

        Returns:
            If used as a regular function (with callback provided), returns the callback.
            If used as a decorator (without callback), returns a decorator function.
        """
        # When used as a decorator without parentheses: @register_pre_tool_hook
        if tool_name is not None and callback is None and callable(tool_name):
            callback = tool_name
            tool_name = callback.__name__
            if not hasattr(instance, "pre_tool_hooks"):
                instance.pre_tool_hooks = {}
            if tool_name not in instance.pre_tool_hooks:
                instance.pre_tool_hooks[tool_name] = []
            instance.pre_tool_hooks[tool_name].append(callback)
            return callback

        # When used as a decorator with arguments: @register_pre_tool_hook("tool_name")
        if callback is None:

            def decorator(func):
                if not hasattr(instance, "pre_tool_hooks"):
                    instance.pre_tool_hooks = {}
                if tool_name not in instance.pre_tool_hooks:
                    instance.pre_tool_hooks[tool_name] = []
                instance.pre_tool_hooks[tool_name].append(func)
                return func

            return decorator

        # When used as a regular function: register_pre_tool_hook("tool_name", callback_func)
        if not callable(callback):
            raise TypeError("Callback must be callable")

        if not hasattr(instance, "pre_tool_hooks"):
            instance.pre_tool_hooks = {}
        if tool_name not in instance.pre_tool_hooks:
            instance.pre_tool_hooks[tool_name] = []

        instance.pre_tool_hooks[tool_name].append(callback)
        return callback

    @staticmethod
    def execute_post_tool_hooks(instance, tool_name, tool_instance, result):
        """
        Execute all hooks registered for a tool after it has been executed.

        Args:
            tool_name (str): Name of the tool
            tool_instance: The tool instance that was executed
            result: The result of the tool execution
        """
        if tool_name in instance.post_tool_hooks:
            for callback in instance.post_tool_hooks[tool_name]:
                try:
                    callback(tool_instance, result)
                except Exception as e:
                    print(f"Error in post-tool hook for {tool_name}: {e}")

    @staticmethod
    def execute_pre_tool_hooks(instance, tool_name, tool_instance, *args, **kwargs):
        """
        Execute all hooks registered for a tool before it is executed.

        Args:
            tool_name (str): Name of the tool
            tool_instance: The tool instance to be executed
            *args, **kwargs: The arguments passed to the tool
        """
        if tool_name in instance.pre_tool_hooks:
            for callback in instance.pre_tool_hooks[tool_name]:
                try:
                    callback(tool_instance, *args, **kwargs)
                except Exception as e:
                    print(f"Error in pre-tool hook for {tool_name}: {e}")
