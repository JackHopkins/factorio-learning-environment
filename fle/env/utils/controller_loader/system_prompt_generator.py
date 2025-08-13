from pathlib import Path

from fle.env.utils.controller_loader.code_analyzer import CodeAnalyzer
from fle.env.utils.controller_loader.manual_generator import ManualGenerator
from fle.env.utils.controller_loader.schema_generator import SchemaGenerator
from fle.env.utils.controller_loader.type_definition_processor import (
    TypeDefinitionProcessor,
)


class SystemPromptGenerator:
    """Generates system prompts for the Factorio environment."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.tool_path = self.base_path / "tools" / "agent"

    def generate(self, num_agents: int = 1,  agent_idx: int = 0) -> str:
        # Generate schema
        schema_generator = SchemaGenerator(str(self.tool_path))
        schema = schema_generator.generate_schema(with_docstring=True).replace(
            "temp_module.", ""
        )
        # Load and process type definitions
        type_defs = TypeDefinitionProcessor.load_and_clean_definitions(
            str(self.base_path / "game_types.py")
        )

        # Load and process entity definitions
        entity_defs = CodeAnalyzer.parse_file_for_structure(
            str(self.base_path / "entities.py")
        )

        # Load and process the manuals (agent.md files)
        manual_defs = ManualGenerator.generate_manual(str(self.base_path / "tools"))
        multiagent_str = ""

        if num_agents > 1:
            player_idx = agent_idx + 1
            multiagent_str = (
                f"## MULTIAGENT INSTRUCTIONS\n"
                f"You are Agent {player_idx} out of {num_agents} agent(s) in the game. "
                f"Follow your specific instructions given to you by the task."
                f"Use the send_message() tool regularly to communicate with other agents about your current activities and any challenges you encounter. "
                f"Start each program with a send_message() call to explain what you are doing. "
                f"End each program with a send_message() call to confirm your actions. If your program errors out prior to send_message() being called, the message will not be sent. "
            )

        if multiagent_str:
            manual_defs += f"\n\n{multiagent_str}"
        # Combine all parts into final prompt
        return (
            f"```types\n{type_defs}\n{entity_defs}\n```\n"
            f"```methods\n{schema}\n```"
            f"Here is the manual for the tools available to you\n\n{manual_defs}"
        )

    def manual(self, *args):
        try:
            return ManualGenerator.generate_manual(
                str(self.base_path / "tools")
                + ("/agent/" if args else "")
                + str("/".join(args))
            )
        except:
            return ManualGenerator.generate_manual(
                str(self.base_path / "tools")
                + ("/admin/" if args else "")
                + str("/".join(args))
            )

    def types(self):
        return TypeDefinitionProcessor.load_and_clean_definitions(
            str(self.base_path / "game_types.py")
        )

    def schema(self):
        schema_generator = SchemaGenerator(str(self.tool_path))
        return schema_generator.generate_schema(with_docstring=True).replace(
            "temp_module.", ""
        )

    def entities(self):
        return CodeAnalyzer.parse_file_for_structure(
            str(self.base_path / "entities.py")
        )
