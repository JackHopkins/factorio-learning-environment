from pathlib import Path

from utils.controller_loader.code_analyzer import CodeAnalyzer
from utils.controller_loader.manual_generator import ManualGenerator
from utils.controller_loader.schema_generator import SchemaGenerator
from utils.controller_loader.type_definition_processor import TypeDefinitionProcessor
import tiktoken

class SystemPromptGenerator:
    """Generates system prompts for the Factorio environment."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.tool_path = self.base_path / "tools" / "agent"

    def generate(self) -> str:
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        # Generate schema
        schema_generator = SchemaGenerator(str(self.tool_path))
        schema = schema_generator.generate_schema(with_docstring=True).replace("temp_module.", "")
        schema_tokens= encoding.encode(schema)
        print(f"Schema tokens: {len(schema_tokens)}")
        # Load and process type definitions
        type_defs = TypeDefinitionProcessor.load_and_clean_definitions(
            str(self.base_path / "game_types.py")
        )

        # Load and process entity definitions
        entity_defs = CodeAnalyzer.parse_file_for_structure(
            str(self.base_path / "entities.py")
        )

        # Load and process the manuals (agent.md files)
        manual_defs = ManualGenerator.generate_manual(
            str(self.base_path / "tools")
        )
        type_def_tokens = encoding.encode(type_defs)
        entity_def_tokens = encoding.encode(entity_defs)
        manual_def_tokens = encoding.encode(manual_defs)
        print(f"Type def tokens: {len(type_def_tokens)}")
        print(f"Entity def tokens: {len(entity_def_tokens)}")
        print(f"Manual def tokens: {len(manual_def_tokens)}")
        # Combine all parts into final prompt
        return (
            f"```types\n{type_defs}\n{entity_defs}\n```\n"
            f"```methods\n{schema}\n```"
            f"{manual_defs}"
        )
