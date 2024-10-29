import os
import ast
import re
from textwrap import dedent
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import inspect

from skills.top_down_skill_generator import FactorioSkillGenerator


@dataclass
class TestInfo:
    name: str
    source: str
    docstring: Optional[str] = None
    generated_summary: Optional[str] = None
    dependencies: Optional[str] = None


class TestAnalyzer:
    def __init__(self, skill_generator):
        self.skill_generator = skill_generator

    def find_test_files(self, directory: str) -> List[str]:
        """Find all Python files that contain tests in the given directory."""
        test_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        return test_files

    def _extract_dict_content(self, text):
        pattern = r'instance.initial_inventory = ({[^}]*})'
        match = re.search(pattern, text)
        if match:
            string_dict = match.group(0).replace("instance.initial_inventory = ", "")
            try:
                dict_obj = ast.literal_eval(string_dict)
                return repr(dict_obj)
            except Exception as e:
                return None
        return None

    def extract_test_functions(self, file_path: str) -> List[TestInfo]:
        """Extract all test functions from a given file."""
        with open(file_path, 'r') as f:
            content = f.read()

        inventory = self._extract_dict_content(content)
        tree = ast.parse(content)
        test_functions = []

        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and
                    node.name.startswith('test_')):
                # Get the source code for the function
                source = ast.get_source_segment(content, node)

                # Extract existing docstring if present
                docstring = ast.get_docstring(node)

                source = source.replace("game.", "")  # Remove game. prefix from function calls
                source = "\n".join(source.split("\n")[1:])
                source = dedent(source)
                test_functions.append(TestInfo(
                    name=node.name,
                    source=source,
                    docstring=docstring,
                    dependencies=inventory
                ))

        return test_functions

    def generate_summary(self, test_info: TestInfo) -> str:
        """Generate a summary of what the test does using the LLM."""
        prompt = f"""
        Please analyze this test function and provide a clear, concise docstring summary of what it aims to achieve.
        Focus on the high-level purpose and what is ultimately being tested.

        ```python
        {test_info.source}
        ```

        Write only the docstring summary, nothing else. Do not include triple quotes.
        """

        messages = [
            {"role": "system",
             "content": "You are an expert at analyzing Python test code and writing clear, concise documentation."},
            {"role": "user", "content": prompt}
        ]

        response = self.skill_generator.llm_factory.call(messages=messages, max_tokens=200)
        return response.content[0].text.strip().strip('`"\' ')

    def save_to_db(self, test_info: TestInfo):
        """Save the test information and embeddings to the database."""

        self.skill_generator.save_function(
            name=test_info.name,
            implementation=test_info.source,
            description=test_info.generated_summary,
            dependencies=test_info.dependencies,  # Dependencies could be extracted if needed
            signature=f"{test_info.name}(game) -> None:\n    \"\"\"{test_info.generated_summary}\"\"\"",
            version="v1.3"
        )

    def process_directory(self, directory: str):
        """Process all test files in the given directory."""
        test_files = self.find_test_files(directory)

        for file_path in test_files:
            print(f"Processing file: {file_path}")
            test_functions = self.extract_test_functions(file_path)

            for test_info in test_functions:
                print(f"\nAnalyzing test: {test_info.name}")

                # Generate summary if there isn't an existing docstring
                #if not test_info.docstring:
                test_info.generated_summary = self.generate_summary(test_info)
                #else:
                #    test_info.generated_summary = test_info.docstring

                print(f"Generated summary: {test_info.generated_summary}")

                # Save to database
                self.save_to_db(test_info)
                print(f"Saved {test_info.name} to database")


def main():
    # Initialize the FactorioSkillGenerator
    generator = FactorioSkillGenerator()

    # Create the test analyzer
    analyzer = TestAnalyzer(generator)

    # Get current execution directions
    current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    # Process the tests directory
    test_directory = "../tests/functional"
    analyzer.process_directory(test_directory)


if __name__ == "__main__":
    main()