import importlib.util
from typing import Optional, Any


class ModuleLoader:
    """Handles loading Python modules from file paths."""

    @staticmethod
    def from_path(path: str) -> Optional[Any]:
        """Load and return a module from the given path."""
        spec = importlib.util.spec_from_file_location("temp_module", path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
