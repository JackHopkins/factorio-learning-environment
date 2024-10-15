import psycopg2
from openai import OpenAI
from psycopg2.extras import Json
import openai
from typing import List, Dict, Union, Tuple
import ast
import json
import os
import textwrap
from itertools import cycle
from typing import List, Dict, Any
from dotenv import load_dotenv

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
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

        # Handle more complex return type annotations
        if node.returns:
            returns = ast.unparse(node.returns)
        else:
            returns = 'None'

        self.signature = f"{self.function_name}({', '.join(args)}) -> {returns}:\n    \"\"\"{self.description}\"\"\""

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.dependencies.add(node.func.id)
        self.generic_visit(node)


def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False


class FactorioSkillGenerator:
    def __init__(self, model="claude-3-5-sonnet-20240620"):
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
        self.factorio_instance = FactorioInstance(address='localhost', bounding_box=200, tcp_port=27015, fast=True)

    def _get_base_api_schema_prompt(self):
        execution_path = os.path.dirname(os.path.realpath(__file__))
        folder_path = f'{execution_path}/../controllers'
        schema = load_schema(folder_path)
        type_definitions = load_definitions(f'{execution_path}/../factorio_types.py')
        entity_definitions = load_definitions(f'{execution_path}/../factorio_entities.py')
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
        dedented = textwrap.dedent(brief.strip())
        return dedented

    def get_embedding(self, text: str) -> List[float]:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    def find_similar_functions(self, query: str, n: int = 5) -> List[Dict]:
        cursor = self.conn.cursor()
        query_embedding = self.get_embedding(query)
        cursor.execute("""
            SELECT name, implementation, description, signature
            FROM public.skills
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (query_embedding, n))
        return [{"name": row[0], "implementation": row[1], "description": row[2], "signature": row[3]} for row in
                cursor.fetchall()]

    def generate_function(self, objective: str, similar_functions: List[Dict], parent_context: str = "") -> str:
        context = "\n\n".join([f"{func['implementation']}" for func in similar_functions])
        parent_implementation = f"Parent implementation: {parent_context}\n" if parent_context else ""
        prompt = f"""
        Objective: {objective}

        Similar functions for reference:
        {context}

        {parent_implementation}
        Write a short Python function to achieve the given objective. Include a function signature, docstring, assertions for self-validation, and use any relevant functions from the context. 
        Any sub-goals should be represented by invoking appropriately named function - which we will implement later.
        Your response should only include the Python code, nothing else, wrapped in ```python ````.
        Ensure that all input arguments have type hints, and the function has a return type hint.
        """

        messages = [
            {"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}]
        response = self.llm_factory.call(
            messages=messages,
            max_tokens=1000,
        )

        return response.content[0].text

    def extract_function_definition(self, code_string: str) -> str:
        tree = ast.parse(code_string)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start_line = node.lineno
                end_line = node.body[-1].lineno
                code_lines = code_string.split('\n')
                function_def_lines = code_lines[start_line - 1:end_line]
                return textwrap.dedent('\n'.join(function_def_lines))
        return None

    def save_function(self, name: str, implementation: str, description: str, dependencies: List[str], signature: str):
        cursor = self.conn.cursor()
        embedding = self.get_embedding(signature)
        implementation_model = self.llm_factory.model
        cursor.execute("""
            INSERT INTO public.skills (name, implementation, description, embedding, dependencies, version, embedding_model, implementation_model, signature)
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s)
        """, (name, implementation, description, embedding, dependencies, "v1.0", "text-embedding-3-small",
              implementation_model, signature))
        self.conn.commit()

    def verify_function(self, function_name: str, function_def: str) -> Tuple[bool, str]:
        # Wrap the function in a try-except block to catch any assertions
        wrapped_function = f"\n{function_def}\n{function_name}()"
        try:
            score, goal, result = self.factorio_instance.eval_with_error(wrapped_function, timeout=20)
            if 'error' in result.lower() or 'assertion' in result.lower():
                return False, result
            return True, result
        except Exception as e:
            return False, str(e)

    def repair_function(self, function_def: str, error_message: str, objective: str) -> str:
        repair_prompt = f"""
        The following function failed to achieve its objective:

        ```python
        {function_def}
        ```

        Error message: {error_message}

        Objective: {objective}

        Please modify the function to fix the error and achieve the objective. Ensure that all input arguments have type hints, and the function has a return type hint.
        Your response should only include the Python code for the corrected function, nothing else.
        """

        messages = [
            {"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": repair_prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=1000)
        return response.content[0].text

    def parse_implementation(self, implementation: str) -> Tuple:
        implementation = implementation.replace("```python", "").replace("```", "").strip()
        # Parse the function using AST
        try:
            tree = ast.parse(implementation)

            # Find the first FunctionDef node
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract just this function
                    function_def = ast.unparse(node)

                    visitor = FunctionVisitor()
                    visitor.visit(node)

                    function_name = visitor.function_name
                    description = visitor.description
                    signature = visitor.signature

                    return function_name, function_def, description, signature

            raise ValueError("No function definition found in the generated code.")

        except SyntaxError as e:
            print(f"Error parsing function: {e}")
            print("Function implementation:")
            print(implementation)
            return None
    def implement_skill(self, objective: str, parent_context: str = "") -> str:
        similar_functions = self.find_similar_functions(objective)
        implementation = self.generate_function(objective, similar_functions, parent_context)
        function_name, function_def, description, signature = self.parse_implementation(implementation)

        max_repair_attempts = 4
        for attempt in range(max_repair_attempts):
            success, result = self.verify_function(function_name, function_def)
            if success:
                break
            if attempt < max_repair_attempts - 1:
                print(f"Function failed. Attempting repair (attempt {attempt + 1})...")
                implementation = self.repair_function(implementation, result, objective)
            else:
                print(f"Function failed after {max_repair_attempts} repair attempts.")
                return None

        try:
            tree = ast.parse(implementation)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_def = ast.unparse(node)
                    visitor = FunctionVisitor()
                    visitor.visit(node)
                    function_name = visitor.function_name
                    description = visitor.description
                    dependencies = list(visitor.dependencies - set(func['name'] for func in similar_functions))
                    signature = visitor.signature
                    dependencies = [dep for dep in dependencies if
                                    dep != function_name and dep not in self.controller_names]
                    self.save_function(function_name, function_def, description, dependencies, signature)
                    for dep in dependencies:
                        self.implement_skill(f"Implement the function {dep} for Factorio", parent_context=function_def)
                    return function_def
            raise ValueError("No function definition found in the generated code.")
        except SyntaxError as e:
            print(f"Error parsing function: {e}")
            print("Function implementation:")
            print(implementation)
            return None

    def load_objectives(self, file_path: str) -> List[str]:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def remove_objective(self, file_path: str, objective: str):
        with open(file_path, 'r') as f:
            objectives = f.readlines()
        with open(file_path, 'w') as f:
            for obj in objectives:
                if obj.strip() != objective:
                    f.write(obj)


# Usage
if __name__ == "__main__":
    generator = FactorioSkillGenerator()

    objectives_file = "objectives.txt"
    if os.path.exists(objectives_file):
        objectives = generator.load_objectives(objectives_file)
    else:
        print(f"Objectives file '{objectives_file}' not found. Please create it and add objectives.")
        exit(1)

    for objective in objectives:
        print(f"Implementing skill for objective: {objective}")
        new_skill = generator.implement_skill(objective)
        if new_skill:
            print("Successfully implemented skill:")
            print(new_skill)
            generator.remove_objective(objectives_file, objective)
        else:
            print(f"Failed to implement skill for objective: {objective}")
        print("\n" + "=" * 50 + "\n")

    print("All objectives have been processed. The program will now exit.")