import inspect
import os
from pathlib import Path
from typing import Any

from fle.env.utils.controller_loader.code_analyzer import CodeAnalyzer
from fle.env.utils.controller_loader.module_loader import ModuleLoader


class SchemaGenerator:
    """Generates schema from Python files in a directory."""

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

    def _process_class(self, module: Any, tool_name: str, with_docstring: bool) -> str:
        """Process a single class to generate its schema entry."""
        schema_entries = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                name in ["ObserveAll", "ClearEntities"]
                or obj.__module__ != module.__name__
            ):
                continue

            if tool_name.startswith("_"):
                continue

            call_info = CodeAnalyzer.extract_call_info(obj)
            if not all(
                [call_info.input_types, call_info.output_type, call_info.docstring]
            ):
                continue

            # Clean up signature
            localized_signature = (
                call_info.signature.replace("self, ", "")
                .replace("entities.", "")
                .replace("instance.", "")
                .replace("game_types.", "")
            )

            docstring_element = (
                f'"""\n{call_info.docstring}\n"""\n\n' if with_docstring else ""
            )
            schema_entry = f"{tool_name}{localized_signature}\n{docstring_element}"
            schema_entries.append(schema_entry)

        return "".join(schema_entries)

    def generate_schema(self, with_docstring: bool = True) -> str:
        """Generate schema from all Python files in the folder."""
        schema_parts = []

        for root, tool_dirs, files in os.walk(self.folder_path):
            for tool in tool_dirs:
                if tool == "__pycache__":
                    continue
                python_file = root + "/" + tool + "/client.py"
                module = ModuleLoader.from_path(str(python_file))
                if not module:
                    continue

                schema_part = self._process_class(module, tool, with_docstring)
                if schema_part:
                    schema_parts.append(schema_part)
            break

        return "".join(schema_parts)
