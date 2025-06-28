from typing import List, Tuple, Any


class FactorioTransaction:
    def __init__(self):
        self.commands: List[Tuple[str, List[Any], bool]] = []  # (command, parameters, is_raw)

    def add_command(self, command: str, *parameters, raw=False):
        self.commands.append((command, list(parameters), raw))

    def clear(self):
        self.commands.clear()

    def get_commands(self):
        return self.commands