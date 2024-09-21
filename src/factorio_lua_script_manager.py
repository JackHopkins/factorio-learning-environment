import hashlib
import json
from pathlib import Path

from factorio_rcon_utils import _load_init, _get_action_dir, _get_init_dir, _get_action_names, _load_script, \
    _get_init_names, _load_action
from src.rcon.factorio_rcon import RCONClient

class FactorioLuaScriptManager:
    def __init__(self,
                 rcon_client: RCONClient,
                 cache_scripts: bool = False):
        self.rcon_client = rcon_client
        self.cache_scripts = cache_scripts
        if not cache_scripts:
            self._clear_game_checksums(rcon_client)
        self.action_directory = _get_action_dir()
        self.init_directory = _get_init_dir()
        if cache_scripts:
            self.init_action_checksums()
            self.game_checksums = self._get_game_checksums(rcon_client)
        self.action_scripts = self.get_actions_to_load()
        self.init_scripts = self.get_inits_to_load()

    def init_action_checksums(self):
        checksum_init_script = _load_init("checksum")
        response = self.rcon_client.send_command("/c "+checksum_init_script)
        return response

    def load_action_into_game(self, name):
        if name not in self.action_scripts:
            # attempt to load the script from the filesystem
            script = _load_action(name)
            self.action_scripts[name] = script

        script = self.action_scripts[name]
        if self.cache_scripts:
            checksum = self.calculate_checksum(script)
            if name in self.game_checksums and self.game_checksums[name] == checksum:
                return
            self.update_game_checksum(self.rcon_client, name, checksum)

        self.rcon_client.send_command(f'/c ' + script)

    def load_init_into_game(self, name):
        if name not in self.init_scripts:
            # attempt to load the script from the filesystem
            script = _load_init(name)
            self.init_scripts[name] = script

        script = self.init_scripts[name]
        if self.cache_scripts:
            checksum = self.calculate_checksum(script)
            if name in self.game_checksums and self.game_checksums[name] == checksum:
                return
            self.update_game_checksum(self.rcon_client, name, checksum)

        self.rcon_client.send_command(f'/c ' + script)


    def calculate_checksum(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def get_actions_to_load(self):
        scripts_to_load = {}
        script_names = _get_action_names()
        for script_file in script_names:
            name, content = _load_script(script_file)

            if self.cache_scripts:
                checksum = self.calculate_checksum(content)
                if (name not in self.game_checksums or
                    self.game_checksums[name] != checksum):
                    scripts_to_load[name] = content
            else:
                scripts_to_load[name] = content

        return scripts_to_load

    def get_inits_to_load(self):
        scripts_to_load = {}
        for filename in _get_init_names():
            name, content = _load_script(filename)
            if self.cache_scripts:
                checksum = self.calculate_checksum(content)

                if (name not in self.game_checksums or
                    self.game_checksums[name] != checksum):
                    scripts_to_load[name] = content
            else:
                scripts_to_load[name] = content

        return scripts_to_load

    def update_game_checksum(self, rcon_client, script_name: str, checksum: str):
        rcon_client.send_command(f"/c global.set_lua_script_checksum('{script_name}', '{checksum}')")

    def _clear_game_checksums(self, rcon_client):
        rcon_client.send_command("/c global.clear_lua_script_checksums()")
    def _get_game_checksums(self, rcon_client):
        response = rcon_client.send_command("/c rcon.print(global.get_lua_script_checksums())")
        return json.loads(response)


