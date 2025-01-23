import ast
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


class FactorioBottomUpSkillGenerator:
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

    def generate_skill(self, objective: str, base_skills: List[Dict], inventory) -> str:
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

    def verify_skill(self, implementation: str, inventory: Dict[str, int]) -> Tuple[bool, str]:
        try:
            self.factorio_instance.set_inventory(**inventory)
            score, goal, result = self.factorio_instance.eval_with_error(implementation, timeout=20)
            if 'error' in result.lower() or 'assertion' in result.lower():
                return False, result
            return True, result
        except Exception as e:
            return False, str(e)

    def repair_skill(self, implementation: str, error_message: str, objective: str, entities) -> str:
        repair_prompt = f"""
        The following implementation failed:

        ```python
        {implementation}
        ```

        Error message: {error_message}
        
         {("Game entities:" + repr(entities)) if entities else ""}

        Objective: {objective}

        Please fix the implementation to achieve the objective and handle the error.
        Your response should only include the corrected Python code, nothing else.
        """

        messages = [
            {"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": repair_prompt}
        ]
        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        result = response.content[0].text
        result = result.replace("```python", "").replace("```", "").strip()
        result = result.replace("reset()", "")
        return result

    def save_skill(self, name: str, implementation: str, description: str, dependencies: List[str], signature: str,
                   attempt: int, version="v1.3"):
        cursor = self.conn.cursor()
        embedding = self.get_embedding(signature)
        implementation_model = self.llm_factory.model
        cursor.execute("""
            INSERT INTO public.skills (name, implementation, description, embedding, dependencies, version, embedding_model, 
            implementation_model, signature, attempt)
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
        """, (name, implementation, description, embedding, dependencies, version, "text-embedding-3-small",
              implementation_model, signature, attempt))
        self.conn.commit()

    def parse_implementation(self, implementation: str) -> Tuple[str, str, str, str, List[str]]:
        implementation = implementation.replace("```python", "").replace("```", "").strip()
        try:
            tree = ast.parse(implementation)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_def = ast.unparse(node)
                    visitor = FunctionVisitor()
                    visitor.visit(node)

                    function_name = visitor.function_name
                    description = visitor.description
                    dependencies = list(visitor.dependencies)
                    signature = visitor.signature

                    # Filter out controller names and the function itself from dependencies
                    dependencies = [dep for dep in dependencies if
                                    dep != function_name and dep not in self.controller_names]

                    return function_name, function_def, description, signature, dependencies

            raise ValueError("No function definition found in the generated code.")
        except Exception as e:
            print(f"Error parsing implementation: {e}")
            return None

    def generate_and_save_skill(self) -> Tuple[bool, str]:
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
        print(f"Generated objective: {objective}")
        self.logger.log(f"Generated objective: {objective}")

        # Generate new skill
        implementation = self.generate_skill(objective, base_skills, inventory)
        self.logger.log(implementation)

        # Verify and repair if needed
        max_repair_attempts = 16
        current_attempt = 0
        for attempt in range(max_repair_attempts):
            success, result = self.verify_skill(implementation, inventory)
            if success:
                self.logger.log(f"\nImplementation succeeded on attempt {attempt + 1}")
                break
            print(f"\nAttempt {attempt + 1} failed:")
            print(f"Error: {result}")

            self.logger.log(f"\nAttempt {attempt + 1} failed:")
            self.logger.log(f"Error: {result}")

            if attempt < max_repair_attempts - 1:
                try:
                    entities = self.factorio_instance.get_entities()
                except Exception as e:
                    entities = []
                    self.logger.log(f"Failed to get entities: {str(e)}")
                self.logger.log(f"Game state: {repr(entities)}")
                implementation = self.repair_skill(implementation, result, objective, entities)
                self.logger.log("\nRepaired implementation:")
                self.logger.log(implementation)
                self.factorio_instance.reset()
            else:
                return False, f"Skill failed after {max_repair_attempts} repair attempts"

            current_attempt += 1

        # Parse and save the working implementation
        parsed_result = self.parse_implementation(implementation)
        if not parsed_result:
            return False, "Failed to parse implementation"

        function_name, function_def, description, signature, dependencies = parsed_result

        # Save the new skill
        try:
            self.save_skill(
                name=function_name,
                implementation=function_def,
                description=description,
                dependencies=dependencies,
                signature=signature,
                attempt=current_attempt
            )
            return True, f"Successfully generated and saved skill: {function_name}"
        except Exception as e:
            return False, f"Failed to save skill: {str(e)}"


if __name__ == "__main__":
    generator = FactorioBottomUpSkillGenerator()
    num_skills_to_generate = 10

    print(f"Generating {num_skills_to_generate} new skills using bottom-up approach...")

    for i in range(num_skills_to_generate):
        print(f"\nGenerating skill {i + 1}/{num_skills_to_generate}")
        success, message = generator.generate_and_save_skill()
        print(message)
        print("=" * 50)

    print("\nSkill generation complete!")