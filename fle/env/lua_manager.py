import hashlib
import json
import os
from pathlib import Path
from collections import defaultdict
from lupa.lua54 import LuaRuntime
from contextlib import contextmanager
from factorio_rcon import RCONClient
from fle.env.utils.rcon import (
    _get_dir,
    _get_lib_dir,
    _get_lib_names,
    _get_tool_names,
    _load_lib,
    _load_script,
)

class ToolHookRegistry:
    def __init__(self):
        # Structure: hooks[tool_name]['pre' or 'post'] -> list of callbacks
        self.hooks = defaultdict(lambda: {'pre': [], 'post': []})

    def register(self, tool_name, phase, callback=None):
        """
        Usage:
          @registry.register("mine", "pre")
          def before_mine(tool, *args): ...

          registry.register("mine", "post", callback_fn)
        """
        if callback is None:
            # used as decorator
            def decorator(fn):
                self.hooks[tool_name][phase].append(fn)
                return fn
            return decorator
        else:
            # direct call
            self.hooks[tool_name][phase].append(callback)
            return callback

    def execute(self, tool_name, phase, tool_instance, *args, **kwargs):
        for fn in self.hooks[tool_name][phase]:
            try:
                fn(tool_instance, *args, **kwargs)
            except Exception as e:
                print(f"[HookError] {phase} hook for {tool_name}: {e}")

    @contextmanager
    def around(self, tool_name, tool_instance, *args, **kwargs):
        # run all pre-hooks
        self.execute(tool_name, 'pre', tool_instance, *args, **kwargs)
        try:
            yield
        finally:
            # run all post-hooks
            self.execute(tool_name, 'post', tool_instance, *args, **kwargs)


class LuaScriptManager:
    def __init__(self, rcon_client: RCONClient, cache_scripts: bool = False):
        self.rcon_client = rcon_client
        self.cache_scripts = cache_scripts
        if not cache_scripts:
            self._clear_game_checksums()
        # self.action_directory = _get_action_dir()

        self.lib_directory = _get_lib_dir()
        if cache_scripts:
            self.init_action_checksums()
            self.game_checksums = self._get_game_checksums(rcon_client)

        self.tool_scripts = self.get_tools_to_load()
        self.lib_scripts = self.get_libs_to_load()
        self.lua = LuaRuntime(unpack_returned_tuples=True)


    def update_game_checksum(self, script_name: str, checksum: str):
        self.rcon_client.send_command(
            f"/sc global.set_lua_script_checksum('{script_name}', '{checksum}')"
        )

    def _clear_game_checksums(self):
        self.rcon_client.send_command("/sc global.clear_lua_script_checksums()")

    def _get_game_checksums(self):
        response = self.rcon_client.send_command("/sc rcon.print(global.get_lua_script_checksums())")
        return json.loads(response)

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
        # Find all scripts for this action by checking prefixes
        tool_scripts = [
            key
            for key in self.tool_scripts.keys()
            if key.startswith(f"agent/{name}") or key.startswith(f"admin/{name}")
        ]
        # windows addition
        if len(tool_scripts) == 0:
            tool_scripts = [
                key
                for key in self.tool_scripts.keys()
                if key.startswith(f"agent\\{name}") or key.startswith(f"admin\\{name}")
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
                self.update_game_checksum(script_name, checksum)

            correct, error = self.check_lua_syntax(script)
            if not correct:
                raise Exception(f"Syntax error in: {script_name}: {error}")
            print(f"{self.rcon_client.port}: Loading action {script_name} into game")

            self.rcon_client.send_command("/sc " + script)
            pass

    def load_init_into_game(self, name):
        if name not in self.lib_scripts:
            # attempt to load the script from the filesystem
            script = _load_lib(name)
            self.lib_scripts[name] = script

        script = self.lib_scripts[name]
        if self.cache_scripts:
            checksum = self.calculate_checksum(script)
            if name in self.game_checksums and self.game_checksums[name] == checksum:
                return
            self.update_game_checksum(name, checksum)

        self.rcon_client.send_command("/sc " + script)

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
