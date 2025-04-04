import os


class ExamplesGenerator:
    """Generates a string of examples from all markdown files in the examples directory."""

    @staticmethod
    def generate_examples(folder_path) -> str:
        """Generate schema from all Python files in the folder."""
        agent_example_path = os.path.join(folder_path, "examples")
        # get all the examples in tool_paths
        example_files = [
            f for f in os.listdir(agent_example_path) if os.path.isfile(os.path.join(agent_example_path, f))
        ]
        examples = "Here are examples of how to use the API for various objectives in Factorio\n\n"
        for file_path in example_files:
            file_path = os.path.join(agent_example_path, file_path)
            with open(file_path, "r") as f:
                    examples += f.read()
                    examples += "\n\n"
        return examples
