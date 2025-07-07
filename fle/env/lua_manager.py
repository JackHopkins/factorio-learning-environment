import hashlib
import json
import os
from pathlib import Path

from lupa.lua54 import LuaRuntime

from factorio_rcon import RCONClient
from fle.env.utils.rcon import (
    _get_dir,
    _get_lib_dir,
    _get_lib_names,
    _get_tool_names,
    _load_lib,
    _load_script,
)


class LuaScriptManager:
    def __init__(self, rcon_client: RCONClient, cache_scripts: bool = False):
        self.rcon_client = rcon_client
        self.cache_scripts = cache_scripts
        if not cache_scripts:
            self._clear_game_checksums(rcon_client)
        # self.action_directory = _get_action_dir()

        self.lib_directory = _get_lib_dir()
        if cache_scripts:
            self.init_action_checksums()
            self.game_checksums = self._get_game_checksums(rcon_client)

        self.tool_scripts = self.get_tools_to_load()

        self.lib_scripts = self.get_libs_to_load()
        self.lua = LuaRuntime(unpack_returned_tuples=True)

    def init_action_checksums(self):
        checksum_init_script = _load_lib("checksum")
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

    # @deprecated("Using tools")
    # def load_action_into_game(self, name):
    #
    #     if name not in self.action_scripts:
    #         # attempt to load the script from the filesystem
    #         script = _load_action(name)
    #         self.action_scripts[name] = script
    #
    #     script = self.action_scripts[name]
    #     if self.cache_scripts:
    #         checksum = self.calculate_checksum(script)
    #         if name in self.game_checksums and self.game_checksums[name] == checksum:
    #             return
    #         self.update_game_checksum(self.rcon_client, name, checksum)
    #
    #     correct, error = self.check_lua_syntax(script)
    #     if not correct:
    #         raise Exception(f"Syntax error in: {name}: {error}")
    #     print(f"{self.rcon_client.port}: Loading action {name} into game")
    #
    #     result = self.rcon_client.send_command(f'/sc ' + script)

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
                self.update_game_checksum(self.rcon_client, script_name, checksum)

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
            self.update_game_checksum(self.rcon_client, name, checksum)

        self.rcon_client.send_command("/sc " + script)

    def calculate_checksum(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    # @deprecated("Moving to tools")
    # def get_actions_to_load(self):
    #     scripts_to_load = {}
    #     script_names = _get_action_names()
    #     for script_file in script_names:
    #         name, content = _load_script(script_file)
    #
    #         if self.cache_scripts:
    #             checksum = self.calculate_checksum(content)
    #             if (name not in self.game_checksums or
    #                 self.game_checksums[name] != checksum):
    #                 scripts_to_load[name] = content
    #         else:
    #             scripts_to_load[name] = content
    #     return scripts_to_load

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
            f"/sc global.set_lua_script_checksum('{script_name}', '{checksum}')"
        )

    def _clear_game_checksums(self, rcon_client):
        rcon_client.send_command("/sc global.clear_lua_script_checksums()")

    def _get_game_checksums(self, rcon_client):
        response = rcon_client.send_command(
            "/sc rcon.print(global.get_lua_script_checksums())"
        )
        return json.loads(response)
