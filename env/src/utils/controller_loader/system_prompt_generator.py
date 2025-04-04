from pathlib import Path

from utils.controller_loader.code_analyzer import CodeAnalyzer
from utils.controller_loader.manual_generator import ManualGenerator
from utils.controller_loader.schema_generator import SchemaGenerator
from utils.controller_loader.examples_generator import ExamplesGenerator
from utils.controller_loader.type_definition_processor import TypeDefinitionProcessor


class SystemPromptGenerator:
    """Generates system prompts for the Factorio environment."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.tool_path = self.base_path / "tools" / "agent"

    def generate(self) -> dict:
        # Generate schema
        schema_generator = SchemaGenerator(str(self.tool_path))
        schema = schema_generator.generate_schema(with_docstring=True).replace("temp_module.", "")

        # Load and process type definitions
        type_defs = TypeDefinitionProcessor.load_and_clean_definitions(
            str(self.base_path / "game_types.py")
        )

        # Load and process entity definitions
        entity_defs = CodeAnalyzer.parse_file_for_structure(
            str(self.base_path / "entities.py")
        )

        # Load and process the manuals (agent.md files)
        agent_manual_defs = ManualGenerator.generate_agent_manual(
            str(self.base_path / "tools")
        )
        # Load and process the RAG manuals (agent.md files)
        rag_manual_defs = ManualGenerator.generate_rag_manual(
            str(self.base_path / "tools")
        )
        examples = ExamplesGenerator.generate_examples(
            str(self.base_path / "tools")
        )
        # Combine all parts into final prompt
        return {
            "type_defs":type_defs,
            "entity_defs":entity_defs,
            "schema": schema,
            "manual_defs": agent_manual_defs,
            "examples": examples,
            "rag_manual_defs": rag_manual_defs,
        }
