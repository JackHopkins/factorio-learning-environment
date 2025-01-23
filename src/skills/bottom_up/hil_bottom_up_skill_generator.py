import ast
import json
import os
import random
import textwrap
from typing import List, Dict, Tuple

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from skills.bottom_up.skill_generation_logger import SkillGenerationLogger
from utilities.controller_loader import load_schema, load_definitions, load_controller_names

load_dotenv()
client = OpenAI()
DB_PASSWORD = os.getenv("DB_PASSWORD")


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.function_name = None
        self.description = None
        self.dependencies = set()
        self.signature = None

    def visit_FunctionDef(self, node):
        self.function_name = node.name
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            self.description = ast.literal_eval(node.body[0].value)

        args = [arg.arg for arg in node.args.args]
        returns = ast.unparse(node.returns) if node.returns else 'None'
        self.signature = f"{self.function_name}({', '.join(args)}) -> {returns}:\n    \"\"\"{self.description}\"\"\""

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.dependencies.add(node.func.id)
        self.generic_visit(node)


class HumanInTheLoopBottomUpSkillGenerator:
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        self.conn = psycopg2.connect(
            host="factorio.cwqst41cfhhd.us-east-1.rds.amazonaws.com",
            port="5432",
            dbname="factorio",
            user="postgres",
            password=DB_PASSWORD
        )
        self.api_schema = self._get_base_api_schema_prompt()
        self.controller_names = load_controller_names(f'{os.path.dirname(os.path.realpath(__file__))}/../controllers')
        self.llm_factory = LLMFactory(model)
        self.factorio_instance = FactorioInstance(address='localhost', bounding_box=200, tcp_port=27000, fast=True)
        self.logger = SkillGenerationLogger()

    def _get_base_api_schema_prompt(self):
        execution_path = os.path.dirname(os.path.realpath(__file__))
        folder_path = f'{execution_path}/../../controllers'
        schema = load_schema(folder_path)
        type_definitions = load_definitions(f'{execution_path}/../../factorio_types.py')
        entity_definitions = load_definitions(f'{execution_path}/../../factorio_entities.py')
        brief = f"""
You have access to the following Game API for use in your Python code:

Entities:
{entity_definitions}

Types:
{type_definitions}

Methods:
```
{schema}
```
"""
        return textwrap.dedent(brief.strip())

    def get_embedding(self, text: str) -> List[float]:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    def get_random_skills(self, n: int = random.randint(1, 3)) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name, implementation, description, signature, dependencies
            FROM public.skills
            WHERE version = 'v1.3'
            ORDER BY RANDOM()
            LIMIT %s
        """, (n,))
        return [{"name": row[0], "implementation": row[1], "description": row[2], "signature": row[3], "dependencies": row[4]
                 } for row in
                cursor.fetchall()]

    def generate_objective(self, skills: List[Dict]) -> str:
        descriptions = [skill["description"] for skill in skills]
        prompt = f"""
        I have the following Factorio game functions with their descriptions:

        {descriptions}

        Based on these functions, generate a new objective that combines or builds upon their capabilities.
        It should be similar in style and complexity to the existing functions.
        The objective should be specific and actionable, starting with "Implement a snippet that..."

        Your response should only include the objective text, nothing else.
        """

        messages = [
            {"role": "user", "content": prompt}
        ]
        response = self.llm_factory.call(messages=messages, max_tokens=200)
        return response.content[0].text.strip()

    def generate_name(self, objective: str) -> str:
        prompt = f"""
        Objective: {objective}
        
        Generate a name for the function that will achieve the given objective.
        
        Your response should only include the function name in snake case, nothing else.
        """

        messages = [
            {"role": "user", "content": prompt}
        ]
        response = self.llm_factory.call(messages=messages, max_tokens=200)
        return response.content[0].text.strip()

    def generate_skill_implementation(self, objective: str, base_skills: List[Dict], inventory) -> str:
        context = "\n\n".join([f"{func['implementation']}" for func in base_skills])
        prompt = f"""
        Objective: {objective}
        
        Inventory: {repr(inventory)}
        
        Base functions to build upon:
        {context}

        Write a Python snippet/script that achieves the given objective by combining the capabilities of the base implementations.
        Include assertions for self-validation where appropriate. Focus on verifying the status of game entities or resources.
        Try to keep the implementation concise, efficient and simple. Don't try to manage too many entities.
        
        Your response should only include Python code, nothing else, wrapped in ```python ````.
        
        Scripts can only run for 60 seconds maximum.
        
        If you intend to place an entity, 
        It should be in script format, not a function definition.
        """

        messages = [
            #{"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}
        ]
        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        implementation = response.content[0].text
        implementation = implementation.replace("```python", "").replace("```", "").strip()
        implementation = implementation.replace("reset()", "")
        return implementation

    def _merge_dicts_max_value(self, dicts: List[Dict[str, int]], multiple=1) -> Dict[str, int]:
        """
        Merge multiple dictionaries of string keys and integer values.
        When keys overlap, keep the entry with the largest integer value.

        Args:
            *dicts: Variable number of Dict[str, int] to merge

        Returns:
            Dict[str, int]: Merged dictionary containing maximum values for each key

        Example:
            >>> d1 = {"a": 1, "b": 5}
            >>> d2 = {"b": 3, "c": 2}
            >>> merge_dicts_max_value(d1, d2)
            {'a': 1, 'b': 5, 'c': 2}
        """
        result = {}
        for d in dicts:
            for key_value in d:
                key, value = key_value.split(":")
                key = key.strip("'")
                value = int(value.strip())
                if key not in result or value > result[key]:
                    result[key] = value

        for key in result:
            result[key] = result[key] * multiple

        return result

    # def verify_skill(self, implementation: str, inventory: Dict[str, int]) -> Tuple[bool, str]:
    #     try:
    #         self.factorio_instance.set_inventory(**inventory)
    #         score, goal, result = self.factorio_instance.eval_with_error(implementation, timeout=20)
    #         if 'error' in result.lower() or 'assertion' in result.lower():
    #             return False, result
    #         return True, result
    #     except Exception as e:
    #         return False, str(e)

    def save_skill(self, name: str, implementation: str, description: str, dependencies: List[str], signature: str,
                   attempts: int, version="v1.3"):
        cursor = self.conn.cursor()
        embedding = self.get_embedding(signature)
        implementation_model = self.llm_factory.model
        cursor.execute("""
            INSERT INTO public.skills (name, implementation, description, embedding, dependencies, version, embedding_model, 
            implementation_model, signature, attempts)
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
        """, (name, implementation, description, embedding, dependencies, version, "text-embedding-3-small",
              implementation_model, signature, attempts))
        self.conn.commit()

    def generate_skill(self) -> Tuple[bool, str]:

        # If there is a `snippet.py` file in the current_skill directory, do not generate a new skill
        if os.path.exists("./current_skill/snippet.py"):
            self.logger.log("Current skill directory is not empty. Skipping skill generation.")
            return False, "Current skill directory is not empty. Skipping skill generation."

        # Get random base skills
        base_skills = self.get_random_skills()
        if not base_skills:
            self.logger.log("ERROR: No base skills found in database")
            return False, "No base skills found in the database"
        self.logger.log("Base skills selected:")
        for skill in base_skills:
            self.logger.log(f"  - {skill['name']}: {skill['description']}")

        inventories = [skill["dependencies"] for skill in base_skills]
        inventory = self._merge_dicts_max_value(inventories, multiple=2)
        self.logger.log(f"Combined inventory requirements: {inventory}")

        # Generate new objective
        objective = self.generate_objective(base_skills)
        name = self.generate_name(objective)
        print(f"Generated objective: {objective}")
        self.logger.log(f"Generated objective: {objective}")

        # Generate new skill
        implementation = self.generate_skill_implementation(objective, base_skills, inventory)
        self.logger.log(implementation)

        # Write to snippet.py in the local directory
        with open("./current_skill/snippet.py", "w") as f:
            # Split objective by sentences and write as comments
            f.write("# " + objective.replace("\n", "\n# ") + "\n\n")
            f.write(implementation)

        # Write details to details.json
        with open("./current_skill/details.json", "w") as f:
            f.write(json.dumps(
                {
                    "name": name,
                    "objective": objective,
                    "base_skills": base_skills,
                    "inventory": inventory
                }, indent=4
            ))
    def iterate_on_skill(self):
        current_attempt = 0
        while True:
            # Wait for the user to run the skill and make corrections
            input("Press Enter to continue...")

            # Execute a snippet file
            try:
                # Load the details.json file and get the inventory
                with open("./current_skill/details.json", "r") as f:
                    details = json.load(f)
                    inventory = details["inventory"]
                    self.factorio_instance.set_inventory(**inventory)
                # Execute a snippet file
                self.factorio_instance.run_snippet_file_in_factorio_env('./current_skill/snippet.py', clean=False)
                break
            except Exception as e:
                # Write error to StdOut
                print(f"\033[91mError running snippet: {e}\033[0m")
                self.factorio_instance.reset()
                current_attempt += 1

        # Load implementation from snippet.py
        with open("./current_skill/snippet.py", "r") as f:
            implementation = f.read()

        with open("./current_skill/details.json", "r") as f:
            details = json.load(f)
            objective = details["objective"]
            name = details["name"]
            signature = f"""{name}() -> None:\n    \"\"\"{objective}\"\"\""""

            # Save the new skill
            try:
                self.save_skill(
                    name=name,
                    implementation=implementation,
                    description=objective,
                    dependencies=repr(inventory),
                    signature=signature,
                    attempts=current_attempt
                )

                return True, f"Successfully generated and saved skill: {function_name}"
            except Exception as e:
                return False, f"Failed to save skill: {str(e)}"


if __name__ == "__main__":
    generator = HumanInTheLoopBottomUpSkillGenerator()
    num_skills_to_generate = 10

    print(f"Generating {num_skills_to_generate} new skills using bottom-up approach...")

    for i in range(num_skills_to_generate):
        print(f"\nGenerating skill {i + 1}/{num_skills_to_generate}")

        generator.generate_skill()
        generator.iterate_on_skill()



    print("\nSkill generation complete!")