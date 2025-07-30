import asyncio
import threading
from contextlib import contextmanager
from time import time as timer

from factorio_rcon import RCONClient
from slpp import slpp as lua
from typing_extensions import Any, Dict, List, Tuple

from fle.env.run_envs import PlatformConfig
from fle.env.lua_manager import LuaScriptManager, ToolHookRegistry
from fle.env.namespace import FactorioNamespace
from fle.env.utils.rcon import _lua2python

PLATFORM_CONFIG = PlatformConfig()

class FactorioTransaction:
    def __init__(self, server):
        self.server = server
        self.commands: List[Tuple[str, List[Any], bool]] = (
            []
        )  # (command, parameters, is_raw)

    def add_command(self, command: str, *parameters, raw=False):
        self.commands.append((command, list(parameters), raw))

    def clear(self):
        self.commands.clear()

    def get_commands(self):
        return self.commands

    def execute(self) -> Dict[str, Any]:
        """Execute all commands in this transaction"""
        start = timer()
        rcon_commands = {}

        for idx, (command, parameters, is_raw) in enumerate(self.commands):
            if is_raw:
                rcon_commands[f"{idx}_{command}"] = command
            else:
                script = self.server._get_command(
                    command, parameters=parameters, measured=False
                )
                rcon_commands[f"{idx}_{command}"] = script

        lua_responses = self.server.rcon_client.send_commands(rcon_commands)

        results = {}
        for command, response in lua_responses.items():
            results[command] = _lua2python(command, response, start=start)

        self.clear()
        return results

    @contextmanager
    def __enter__(self):
        """Context manager entry - clear any existing commands"""
        self.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - execute the transaction"""
        if exc_type is None:  # Only execute if no exception occurred
            self.execute()


class FactorioServer:
    def __init__(self, address, tcp_port = PLATFORM_CONFIG.rcon_port, cache_scripts=True):
        self.rcon_client, self.address = self.connect_to_server(address, tcp_port)
        self.cache_scripts = cache_scripts
        self.tool_hook_registry = ToolHookRegistry()
        # Initialize Lua script manager and script dictionary
        self.lua_script_manager = LuaScriptManager(
            self.rcon_client, self.tool_hook_registry, cache_scripts
        )
        self.script_dict = {
            **self.lua_script_manager.lib_scripts,
            **self.lua_script_manager.tool_scripts,
        }

    def ensure_rcon_client(self):
        if not self.rcon_client:
            self.rcon_client = RCONClient(self.address, self.tcp_port, PLATFORM_CONFIG.factorio_password)
        return self.rcon_client

    def run_rcon_print(self, command: str):
        return self.rcon_client.send_command(f"/sc rcon.print({command})")

    def send_command(self, command: str):
        return self.rcon_client.send_command(command)

    def load_init_into_game(self, init_scripts):
        if type(init_scripts) == str:
            init_scripts = [init_scripts]
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)

    def load_tool_into_game(self, name):
        self.lua_script_manager.load_tool_into_game(name)

    def connect_to_server(self, address, tcp_port):
        try:
            rcon_client = RCONClient(address, tcp_port, PLATFORM_CONFIG.factorio_password)
            address = address
        except ConnectionError as e:
            print(e)
            rcon_client = RCONClient("localhost", tcp_port, PLATFORM_CONFIG.factorio_password)
            address = "localhost"

        print(f"Connected to {address} client at tcp/{tcp_port}.")
        return rcon_client, address

    def _get_command(self, command, parameters=[], measured=True):
        prefix = "/sc " if not measured else "/command "
        if command in self.script_dict:
            script = prefix + self.script_dict[command]
            for index in range(len(parameters)):
                script = script.replace(
                    f"arg{index + 1}", lua.encode(parameters[index])
                )
        else:
            script = command
        return script

    @contextmanager
    def transaction(self):
        """Context manager for executing transactions"""
        tx = FactorioTransaction(self)
        try:
            yield tx
        except:
            # On error, do not execute queued commands
            raise
        else:
            # Only execute if no exception occurred
            tx.execute()

    def register_controllers(
        self, namespaces: List[FactorioNamespace], invalidate_cache: bool = False
    ):
        """
        Load Python controllers from valid tool directories (delegated).
        """
        self.lua_script_manager.register_controllers(self, namespaces, invalidate_cache)

    def cleanup(self):
        # Close the RCON connection
        if hasattr(self, "rcon_client") and self.rcon_client:
            self.rcon_client.close()

        self.tool_hook_registry = ToolHookRegistry()

        # Join all non-daemon threads
        for thread in threading.enumerate():
            if (
                thread != threading.current_thread()
                and thread.is_alive()
                and not thread.daemon
            ):
                try:
                    thread.join(timeout=5)  # Wait up to 5 seconds for each thread
                except Exception as e:
                    print(f"Error joining thread {thread.name}: {e}")

