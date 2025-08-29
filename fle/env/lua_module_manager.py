import hashlib
import shutil
import os
from pathlib import Path

from lupa.lua54 import LuaRuntime

from factorio_rcon import RCONClient
from fle.env.utils.rcon import (
    _get_mods_dir,
    _get_lib_names,
    _get_tool_names,
    _load_mods,
    _load_script,
)

ROOT_DIR = Path(__file__).parent.parent.parent


def get_control_lua(lib_names, admin_tool_names, agent_tool_names):
    # Ensure 'libs.initialise' is at the top if present
    lib_names = "',\n    '".join(lib_names)
    admin_tool_names = "',\n    '".join(admin_tool_names)
    agent_tool_names = "',\n    '".join(agent_tool_names)

    with open(ROOT_DIR / "fle" / "env" / "control-template.lua", "r") as f:
        template = f.read()
    template = template.replace("{lib_names}", lib_names)
    template = template.replace("{admin_tool_names}", admin_tool_names)
    template = template.replace("{agent_tool_names}", agent_tool_names)
    return template


class LuaModuleManager:
    def __init__(
        self,
        rcon_client: RCONClient,
        cache_scripts: bool = False,
        start_fresh: bool = False,
    ):
        self.rcon_client = rcon_client
        self.cache_scripts = cache_scripts
        # if not cache_scripts:
        #     self._clear_game_checksums(rcon_client)
        # self.action_directory = _get_action_dir()

        self.lib_directory = _get_mods_dir()
        # if cache_scripts:
        #     self.init_action_checksums()
        #     self.game_checksums = self._get_game_checksums(rcon_client)

        # self.tool_scripts = self.get_tools_to_load()
        # self.lib_scripts = self.get_libs_to_load()
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.module_dir = ROOT_DIR / ".fle" / "fle-mod"
        if start_fresh and self.module_dir.exists():
            shutil.rmtree(self.module_dir)

    def build_module(self):
        print(f"Building module to {self.module_dir}")
        self.module_dir.mkdir(parents=True, exist_ok=True)
        tools_dir = self.module_dir / "tools"
        (tools_dir / "agent").mkdir(parents=True, exist_ok=True)
        (tools_dir / "admin").mkdir(parents=True, exist_ok=True)
        libs_dir = self.module_dir / "libs"
        libs_dir.mkdir(parents=True, exist_ok=True)
        control_lua = self.module_dir / "control.lua"
        lib_names = []
        admin_tool_names = []
        agent_tool_names = []
        for lib in _get_lib_names():
            lib = Path(lib)
            lib_name = lib.stem
            # Only copy libs with actual code content (not just comments)
            with open(lib, "r") as f:
                if not any(
                    line.strip() and not line.strip().startswith("--") for line in f
                ):
                    print(f"Skipping {lib_name} because it is empty")
                    continue
                print(f"Copying {lib_name} to {f'{lib_name}.lua'}")
                shutil.copy(lib, libs_dir / f"{lib_name}.lua")
            if lib_name == "initialise":
                lib_names.insert(0, f"libs.{lib_name}")
            else:
                lib_names.append(f"libs.{lib_name}")

        for tool in _get_tool_names():
            tool_type = "agent" if "agent" in tool else "admin"
            tool = Path(tool)
            tool_name = tool.parts[-2]

            with open(tool, "r") as f:
                if not any(
                    line.strip() and not line.strip().startswith("--") for line in f
                ):
                    print(f"Skipping {tool_name} because it is empty")
                    continue
                print(f"Copying {tool_name} to {f'{tool_name}.lua'}")
                shutil.copy(tool, tools_dir / tool_type / f"{tool_name}.lua")
            if tool_type == "admin":
                admin_tool_names.append(f"tools.admin.{tool_name}")
            else:
                agent_tool_names.append(f"tools.agent.{tool_name}")

        with open(control_lua, "w") as f:
            f.write(get_control_lua(lib_names, admin_tool_names, agent_tool_names))

    def prepare_scenario(self, scenario_name: str, copy_module: bool = True):
        scenario_dir = ROOT_DIR / "fle" / "cluster" / "scenarios" / scenario_name
        final_dir = ROOT_DIR / ".fle" / "scenarios" / scenario_name
        final_dir.mkdir(parents=True, exist_ok=True)
        if not scenario_dir.exists():
            raise ValueError(f"Scenario directory does not exist: {scenario_dir}")
        print(f"Copying scenario to {final_dir}")
        shutil.copytree(scenario_dir, final_dir, dirs_exist_ok=True)
        print(f"Copying module to {final_dir}")
        if copy_module:
            self.build_module()
            shutil.copytree(self.module_dir, final_dir, dirs_exist_ok=True)
        print(f"Scenario {scenario_name} prepared")

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

            self.rcon_client.send_command("/sc " + script)
            pass

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

        self.rcon_client.send_command("/sc " + script)

    def calculate_checksum(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()


if __name__ == "__main__":
    manager = LuaModuleManager(rcon_client=None, cache_scripts=False, start_fresh=True)
    manager.prepare_scenario("default_lab_scenario", True)
