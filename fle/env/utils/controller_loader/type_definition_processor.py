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

        # Extract from Prototype class onwards
        prototype_index = cleaned_content.find("class RecipeName(enum.Enum)")
        return (
            cleaned_content[prototype_index:]
            if prototype_index >= 0
            else cleaned_content
        )
