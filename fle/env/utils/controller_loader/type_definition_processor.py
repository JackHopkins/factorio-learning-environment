class TypeDefinitionProcessor:
    """Processes Python type definition files."""

    @staticmethod
    def load_and_clean_definitions(file_path: str) -> str:
        """Load and clean type definitions from a file."""
        with open(file_path, "r") as file:
            content = file.read()

        # Filter out imports and comments
        lines = [
            line
            for line in content.split("\n")
            if not (
                line.startswith(("import", "from")) or line.lstrip().startswith("#")
            )
        ]

        cleaned_content = "\n".join(lines)
        cleaned_content = (
            cleaned_content.replace("\n\n\n", "\n").replace("\n\n", "\n").strip()
        )

        # RecipeName is assembled from the complete Prototype registry at import
        # time. Render its concrete members for model-facing type documentation
        # rather than exposing that implementation machinery.
        from fle.env.game_types import RecipeName

        recipe_lines = ["class RecipeName(enum.Enum):"]
        recipe_lines.extend(
            f"    {name} = {member.value!r}"
            for name, member in RecipeName.__members__.items()
        )

        prototype_index = cleaned_content.find("class Prototype(")
        recipe_runtime_index = cleaned_content.find("_RECIPE_NAME_MEMBERS")
        lookup_index = cleaned_content.find("prototype_by_name")
        if min(prototype_index, recipe_runtime_index, lookup_index) < 0:
            return cleaned_content

        prototype_definition = cleaned_content[
            prototype_index:recipe_runtime_index
        ].rstrip()
        remaining_definitions = cleaned_content[lookup_index:]
        return "\n".join(
            [
                *recipe_lines,
                "",
                prototype_definition,
                "",
                remaining_definitions,
            ]
        )
