import inspect
from pathlib import Path
from typing import Any

from utilities.controller_loader.code_analyzer import CodeAnalyzer
from utilities.controller_loader.module_loader import ModuleLoader


class SchemaGenerator:
    """Generates schema from Python files in a directory."""

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

    def _process_class(self, module: Any, file_name: str, with_docstring: bool) -> str:
        """Process a single class to generate its schema entry."""
        schema_entries = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name in ["ObserveAll", "ClearEntities"] or obj.__module__ != module.__name__:
                continue

            if file_name.startswith('_'):
                continue

            call_info = CodeAnalyzer.extract_call_info(obj)
            if not all([call_info.input_types, call_info.output_type, call_info.docstring]):
                continue

            # Clean up signature
            localized_signature = call_info.signature \
                .replace("self, ", "") \
                .replace("factorio_entities.", "") \
                .replace("factorio_instance.", "") \
                .replace("factorio_types.", "")

            docstring_element = f'"""\n{call_info.docstring}\n"""\n\n' if with_docstring else ""
            schema_entry = f'{file_name[:-3]}{localized_signature}\n{docstring_element}'
            schema_entries.append(schema_entry)

        return "".join(schema_entries)

    def generate_schema(self, with_docstring: bool = True) -> str:
        """Generate schema from all Python files in the folder."""
        schema_parts = []

        for python_file in self.folder_path.glob("**/*.py"):
            module = ModuleLoader.from_path(str(python_file))
            if not module:
                continue

            schema_part = self._process_class(module, python_file.name, with_docstring)
            if schema_part:
                schema_parts.append(schema_part)

        return "".join(schema_parts)