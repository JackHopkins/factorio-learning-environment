import json
import os
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
import psycopg2


@dataclass
class Config:
    model: str = "gpt-4o"
    temperature: float = 0.9


class BlueprintMetadataGenerator:
    def __init__(self):
        load_dotenv()
        self.config = Config()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conn = psycopg2.connect(
            host="factorio.cwqst41cfhhd.us-east-1.rds.amazonaws.com",
            port="5432",
            dbname="factorio",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),
        )

    def get_embedding(self, text: str) -> list:
        """Get embedding for text using OpenAI's API"""
        response = self.openai_client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def save_to_db(
        self,
        code: str,
        file_path: str,
        objective: str,
        docstring: str,
        inventory: Dict[str, int],
        model: str,
    ) -> None:
        """Save the analysis results to the skills table"""
        cursor = self.conn.cursor()

        # Generate name from file path
        name = str(Path(file_path)).split("/")[-2]

        # Create signature from name and docstring
        signature = f'{name}(game) -> None:\n    """{docstring}"""'

        # Get embedding for the objective
        embedding = self.get_embedding(objective)

        try:
            cursor.execute(
                """
                INSERT INTO public.skills 
                (name, implementation, description, embedding, dependencies, version, embedding_model, implementation_model, signature, meta)
                VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
            """,
                (
                    name,
                    code,
                    docstring,
                    embedding,
                    repr(inventory),  # Store inventory as dependencies
                    "v1.4",
                    "text-embedding-3-small",
                    model,
                    signature,
                    json.dumps(
                        {"objective": {"plan": docstring, "objective": objective}}
                    ),
                ),
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error saving to database: {e}")
            self.conn.rollback()
        finally:
            cursor.close()

    def analyze_file(self, file_path: Path) -> Dict[str, str]:
        """Analyzes a Factorio build file and generates objective and docstring."""

        print(f"Analyzing file: {file_path}")
        # Read the file content
        with open(file_path, "r") as f:
            content = f.read()

        # Parent directory
        parent_dir = file_path.parent

        # Blueprint name
        blueprint_name = parent_dir.stem

        # Blueprint directory
        blueprint_dir = parent_dir.parent.parent / "blueprints"

        # Get inventory from blueprint JSON
        inventory = {}
        for root, _, files in os.walk(blueprint_dir):
            if "decoded" in root:
                continue
            for file in files:
                if file.endswith(".json") and file.startswith(blueprint_name):
                    blueprint_path = Path(root) / file
                    with open(blueprint_path, "r") as f:
                        blueprint_json = f.read()
                        blueprint = json.loads(blueprint_json)
                        try:
                            if "blueprint" in blueprint:
                                blueprint = blueprint["blueprint"]
                            entities = blueprint["entities"]
                            for entity in entities:
                                name = entity["name"]
                                inventory[name] = inventory.get(name, 0) + 1
                        except Exception as e:
                            print(e)
                        break

        # Generate the objective
        objective = self._generate_objective(content, blueprint_name)

        # Generate the docstring
        docstring = self._generate_docstring(content, objective, blueprint_name).strip()

        # Model used
        filename = file_path.stem

        model = "".join(filename).split("_")[1]

        # Save results to database
        self.save_to_db(content, str(file_path), objective, docstring, inventory, model)

        return {
            "file": str(file_path),
            "objective": objective,
            "docstring": docstring,
            "inventory": inventory,
        }

    def _generate_objective(self, content: str, filename: str) -> str:
        """Generates a specific objective for the build file."""
        prompt = f"""Analyze this Factorio build file named '{filename}' and provide a one-sentence specific objective:

{content}

Generate a clear, specific objective statement that describes what this build creates. Format:
Objective: <one short sentence>

e.g `I need to construct a stone mining facility using a single burner mining drill, delivering the mined stone to a stone furnace situated far from the extraction point`
"""

        response = self.openai_client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=128,
        )

        return response.choices[0].message.content.split("Objective: ")[-1].strip()

    def _generate_docstring(self, content: str, objective: str, filename: str) -> str:
        """Generates a detailed docstring with build logic."""
        prompt = f"""Given this Factorio build file '{filename}' and its objective:

Objective: {objective}

Content:
{content}

Generate a detailed description that explains the logical reasoning and implementation steps required to build this structure. 
Focus on the high-level approach and key considerations. 
Do not mention Factorio.

Format like this example:

'''
I will create a 23x8 steam power facility with dual rows of steam engines fed by a central coal belt. 
Each row will consist of 4 steam engines and 2 boilers arranged symmetrically around the fuel line, 
with electrical infrastructure and lighting. Components will be placed relative to an origin point 
using a helper function for precise positioning.
'''"""

        response = self.openai_client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=512,
        )

        return response.choices[0].message.content.strip().strip("'")


def analyze_factorio_builds(builds_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Analyzes all Factorio build files in the specified directory and its subdirectories.
    Returns a dictionary of analysis results keyed by file path.
    """
    analyzer = BlueprintMetadataGenerator()
    results = {}

    # Walk through directory looking for .py files
    for root, _, files in os.walk(builds_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                try:
                    results[str(file_path)] = analyzer.analyze_file(file_path)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {str(e)}")

    return results


def main():
    load_dotenv()
    # Execution directory
    exec_dir = Path(__file__).parent
    # Directory containing Factorio build files
    # builds_dir = exec_dir / "refactor"
    builds_dir = exec_dir / "full"

    # Analyze all build files
    results = analyze_factorio_builds(builds_dir)

    # Print results
    for file_path, analysis in results.items():
        print(f"\nFile: {file_path}")
        print(f"Objective: {analysis['objective']}")
        print(f"Docstring:\n{analysis['docstring']}")
        print(f"Inventory: {analysis['inventory']}")


if __name__ == "__main__":
    main()
