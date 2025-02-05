from pathlib import Path

from utilities.controller_loader.code_analyzer import CodeAnalyzer
from utilities.controller_loader.schema_generator import SchemaGenerator
from utilities.controller_loader.type_definition_processor import TypeDefinitionProcessor


class SystemPromptGenerator:
    """Generates system prompts for the Factorio environment."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.controllers_path = self.base_path / "controllers"

    def generate(self) -> str:
        """Generate the complete system prompt."""
        # Generate schema
        schema_generator = SchemaGenerator(str(self.controllers_path))
        schema = schema_generator.generate_schema(with_docstring=True).replace("temp_module.", "")

        # Load and process type definitions
        type_defs = TypeDefinitionProcessor.load_and_clean_definitions(
            str(self.base_path / "factorio_types.py")
        )

        # Load and process entity definitions
        entity_defs = CodeAnalyzer.parse_file_for_structure(
            str(self.base_path / "factorio_entities.py")
        )

        # Combine all parts into final prompt
        return (
            f"```types\n{type_defs}\n{entity_defs}\n```\n"
            f"```methods\n{schema}\n```"
        )