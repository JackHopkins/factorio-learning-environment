import ast
import os
import textwrap
from dataclasses import dataclass
from typing import List, Dict
from typing import Tuple

import psycopg2
import yaml
from dotenv import load_dotenv
from openai import OpenAI

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from skills.db_test_loader import TestInfo
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

@dataclass
class Objective:
    objective: str
    starting_inventory: Dict[str, int]

class TailRecursiveSkillGenerator:
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
        self.factorio_instance = FactorioInstance(address='localhost', bounding_box=200, tcp_port=27015, fast=True)
        self.factorio_instance.speed(10)
        self.implementation_stack = []  # Stack to track recursive implementations

    def calculate_inventory_difference(self, starting_inventory: Dict[str, int], final_inventory: Dict[str, int]) -> \
    Dict[str, int]:
        """Calculate the net difference between starting and final inventories"""
        difference = {}
        all_items = set(starting_inventory.keys()) | set(final_inventory.keys())

        for item in all_items:
            start_count = starting_inventory.get(item, 0)
            final_count = final_inventory.get(item, 0)
            diff = final_count - start_count
            if diff != 0:  # Only include items that changed
                difference[item] = diff

        return difference

    def can_afford_dependencies(self, required_items: Dict[str, int], available_inventory: Dict[str, int]) -> bool:
        """Check if the available inventory can support the required items"""
        for item, count in required_items.items():
            if count < 0:  # Items consumed
                if item not in available_inventory or available_inventory[item] < abs(count):
                    return False
        return True

    def load_objectives(self, file_path: str) -> List[Objective]:
        """Load objectives and their starting inventories from YAML file"""
        with open(file_path, 'r') as f:
            objectives_data = yaml.safe_load(f)
            return [Objective(**obj) for obj in objectives_data]

    def remove_objective(self, file_path: str, objective: str):
        with open(file_path, 'r') as f:
            objectives_data = yaml.safe_load(f)
        objectives_data = [obj for obj in objectives_data if obj['objective'] != objective]
        with open(file_path, 'w') as f:
            yaml.dump(objectives_data, f)

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

    def should_generate_dependency(self, error_message: str, current_objective: str) -> Tuple[bool, str]:
        """
        Determines whether to repair the current implementation or generate a dependency objective.
        Returns (should_generate_dependency, suggested_dependency_objective).
        """
        prompt = f"""
        Analyze this Factorio implementation error and determine if it indicates a missing dependency that should be handled first:

        Error message: {error_message}
        Current objective: {current_objective}

        Consider:
        1. Does the error suggest missing resources/items/buildings?
        2. Is this a logical prerequisite that should be handled first?
        3. Is this a simple implementation error that could be fixed by rewriting the code?

        Respond with either:
        - "False" if this is a code-level error that should be fixed by rewriting the implementation
        - "True: <specific dependency objective>" if this indicates a missing dependency that should be handled first

        Response:"""

        messages = [
            #{"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=200)
        result = response.content[0].text.strip()

        if result.startswith("True:"):
            return True, result[5:].strip()
        return False, ""

    def generate_dependency_objective(self, error_message: str, current_objective: str) -> str:
        """
        Generates a specific dependency objective based on the error message.
        """
        prompt = f"""
        Based on this Factorio implementation error, generate a specific objective for obtaining the missing dependency:

        Error message: {error_message}
        Current objective: {current_objective}

        Generate a clear, specific objective for obtaining the missing prerequisite.
        Your response should be a single line stating the objective, nothing else.
        Example: "Create an assembly machine and ensure it has power"
        """

        messages = [
            #{"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=100)
        return response.content[0].text.strip()

    def combine_implementations(self, dependency_impl: str, main_impl: str) -> str:
        """
        Combines dependency implementation with the main implementation.
        """
        prompt = f"""
        Combine these two Factorio implementation snippets into a single coherent implementation:

        Dependency implementation:
        {dependency_impl}

        Main implementation:
        {main_impl}

        Create a single implementation that:
        1. Executes the dependency implementation first
        2. Then executes the main implementation
        3. Maintains proper error handling and assertions
        4. Follows a logical flow

        Your response should only include the combined Python code, nothing else.
        """

        messages = [
           # {"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        return response.content[0].text.strip()

    def generate_function(self, objective: Objective, similar_functions: List[Dict], parent_context: str = "") -> str:
        context = "\n\n".join([f"```{func['name']}\n\"\"\"{func['description']}\"\"\"\n\n{func['implementation']}\n```" for func in similar_functions])
        parent_implementation = f"Parent implementation: \n```{parent_context}\n```" if parent_context else ""
        prompt = \
f"""
Objective: {objective.objective}
Starting inventory: {repr(objective.starting_inventory)}

Relevant existing functions for reference:
{context}

{parent_implementation}
Write a Python snippet to achieve the given objective. 
Include assertions for self-validation, and use code from the provided existing implementation if necessary.
Pay close attention to dependencies such as intermediate resources or buildings that may be required to achieve the objective.
Analyze which methods were called in the existing functions and how they can be adapted to achieve the current objective.
After considering your solution, output Python code wrapped in '```python' <-> '```'.
Only write Python code outside of a function, like a REPL or script, not a full function definition.
"""

        messages = [
            {"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": prompt}]
        response = self.llm_factory.call(
            messages=messages,
            max_tokens=2000,
        )

        return response.content[0].text

    def verify_skill(self, implementation: str) -> Tuple[bool, str]:
        try:

            score, goal, result = self.factorio_instance.eval_with_error(implementation, timeout=90)
            if 'error' in result.lower() or 'assertion' in result.lower():
                return False, result
            return True, result
        except Exception as e:
            if isinstance(e, TimeoutError) or type(e) is TimeoutError:
                return False, "Evaluation timed out after 90 seconds"
            # if e is `TimeoutError()` catch it and return a message
            return False, str(e)

    def repair_function(self, function_def: str, error_message: str, similar_functions, objective: str) -> str:
        context = "\n\n".join(
            [f"```{func['name']}\n\"\"\"{func['description']}\"\"\"\n\n{func['implementation']}\n```" for func in
             similar_functions])

        repair_prompt = \
f"""
The following snippet failed to achieve its objective:

```python
{function_def}
```

Error message: {error_message}

Objective: {objective}

Please modify the code to fix the error and achieve the objective.
Your response should only include the Python code for the corrected snippet, nothing else.

Here are some examples of similar snippets for reference:
{context}
"""

        messages = [
            #{"role": "system", "content": self._get_base_api_schema_prompt()},
            {"role": "user", "content": repair_prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        return response.content[0].text

    def get_embedding(self, text: str) -> List[float]:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    # def find_similar_functions(self, query: Objective, n: int = 5) -> List[Dict]:
    #     cursor = self.conn.cursor()
    #     query_embedding = self.get_embedding(query.objective)
    #     cursor.execute("""
    #         SELECT name, implementation, description, signature
    #         FROM public.skills
    #         WHERE version = 'v1.1'
    #         ORDER BY embedding <-> %s::vector
    #         LIMIT %s
    #     """, (query_embedding, n))
    #     return [{"name": row[0].replace("\"", ""), "implementation": row[1], "description": row[2], "signature": row[3]} for row in
    #             cursor.fetchall()]
    def find_similar_functions(self, query: Objective, n: int = 5) -> List[Dict]:
        """Find similar functions that are achievable with current inventory"""
        cursor = self.conn.cursor()
        query_embedding = self.get_embedding(query.objective)

        # First, get more candidates than needed since we'll filter some out
        cursor.execute("""
            SELECT name, implementation, description, signature, dependencies
            FROM public.skills
            WHERE version = 'v1.1'
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (query_embedding, n * 2))  # Get 2x candidates

        candidates = []
        for row in cursor.fetchall():
            name, implementation, description, signature, dependencies_str = row

            # Parse dependencies string back into dictionary
            try:
                required_items = ast.literal_eval(dependencies_str) if dependencies_str else {}
            except (ValueError, SyntaxError):
                continue  # Skip if dependencies can't be parsed

            # Check if we can afford this function's dependencies
            if self.can_afford_dependencies(required_items, query.starting_inventory):
                candidates.append({
                    "name": name.replace("\"", ""),
                    "implementation": implementation,
                    "description": description,
                    "signature": signature
                })
            else:
                print(f"Skipping function '{name}' due to unaffordable dependencies: {required_items}")

            if len(candidates) >= n:  # Stop once we have enough viable candidates
                break

        return candidates

    def save_function(self,
                      name: str,
                      implementation: str,
                      description: str,
                      starting_inventory: Dict[str, int],
                      signature: str,
                      version="v1.0"):
        cursor = self.conn.cursor()
        embedding = self.get_embedding(signature)
        implementation_model = self.llm_factory.model
        inventory_str = repr(starting_inventory)
        cursor.execute("""
            INSERT INTO public.skills (name, implementation, description, embedding, dependencies, version, embedding_model, implementation_model, signature)
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s)
        """, (name, implementation, description, embedding, inventory_str, version, "text-embedding-3-small",
              implementation_model, signature))
        self.conn.commit()

    def generate_summary(self, test_info: TestInfo) -> str:
        """Generate a summary of what the test does using the LLM."""
        prompt = f"""
        Please analyze this snippet and provide a clear, concise docstring of the objective that this code achieves.
        Focus on the high-level purpose and key functionality being tested.
        e.g "Build/place steam engine before attempting to connect with pipes"

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

        response = self.llm_factory.call(messages=messages, max_tokens=200)
        return response.content[0].text.strip().strip('`"\' ')

    def implement_skill(self, objective: Objective, parent_context: str = "", depth: int = 0) -> str:
        if depth > 5:  # Prevent infinite recursion
            print(f"Maximum recursion depth reached for objective: {objective}")
            return None

        # Initialize Factorio instance with starting inventory
        self.factorio_instance = FactorioInstance(
            address='localhost',
            bounding_box=200,
            tcp_port=27015,
            fast=True,
            inventory=objective.starting_inventory
        )
        self.factorio_instance.speed(10)

        # Store initial inventory state
        initial_inventory = dict(objective.starting_inventory)

        similar_functions = self.find_similar_functions(objective, n=3)
        implementation = self.generate_function(objective, similar_functions, parent_context)
        original_objective = objective.objective  # Store original objective for combined implementation naming

        max_repair_attempts = 8
        for attempt in range(max_repair_attempts):
            implementation = implementation.split("```python")[1].split("```")[0].strip()
            self.factorio_instance.reset()
            self.factorio_instance.set_inventory(**objective.starting_inventory)
            score, _ = self.factorio_instance.score()
            success, result = self.verify_skill(implementation)
            final_score, _ = self.factorio_instance.score()
            if success and final_score > score:
                # Get final inventory state and calculate difference
                final_inventory = self.factorio_instance.inspect_inventory().__dict__
                inventory_diff = self.calculate_inventory_difference(initial_inventory, final_inventory)
                self._save_implementation(implementation,
                                          objective.objective,
                                          # starting_inventory=objective.starting_inventory,
                                          inventory_difference=inventory_diff)
                break

            if attempt < max_repair_attempts - 1:
                # Check if we should generate a dependency objective
                should_generate_dep, suggested_objective = self.should_generate_dependency(result, objective.objective)

                # Dependency generation is disabled for now
                #should_generate_dep = False

                if should_generate_dep:
                    print(f"Detected missing dependency. Generating dependency objective...")
                    if not suggested_objective:
                        suggested_objective = self.generate_dependency_objective(result, objective.objective)

                    print(f"Implementing dependency: {suggested_objective}")

                    current_inventory = self.factorio_instance.inspect_inventory().__dict__
                    dependency_implementation = self.implement_skill(
                        Objective(objective=suggested_objective, starting_inventory=current_inventory),
                        parent_context=implementation,
                        depth=depth + 2
                    )

                    if dependency_implementation:
                        print(f"Successfully implemented dependency: {suggested_objective}. Combining implementation with {objective}...")
                        implementation = self.combine_implementations(dependency_implementation, implementation)
                        # Verify the combined implementation
                        self.factorio_instance.set_inventory(**objective.starting_inventory)
                        success, result = self.verify_skill(implementation)
                        print(f"Combined implementation verification result: {success}"
                              f"\nVerification output: {result}")

                        if success:
                            final_inventory = self.factorio_instance.inspect_inventory().__dict__
                            inventory_difference = self.calculate_inventory_difference(initial_inventory,
                                                                                       final_inventory)
                            # Save the combined implementation with a special name/description
                            combined_name = f"combined_{original_objective.split()[0].lower()}_with_dependencies"
                            combined_description = f"Combined implementation that achieves: {original_objective} " \
                                                   f"with prerequisite: {suggested_objective}"
                            self._save_implementation(implementation,
                                                      combined_name,
                                                      combined_description,
                                                      inventory_difference=inventory_difference)
                            break
                    else:
                        print("Failed to implement dependency.")

                # If we shouldn't generate a dependency or if dependency implementation failed,
                # fall back to regular repair
                print(f"Attempting regular repair (attempt {attempt + 1})...")
                implementation = self.repair_function(implementation, result, similar_functions, objective.objective)
            else:
                print(f"Function failed after {max_repair_attempts} repair attempts.")
                return None

        return implementation

    def _save_implementation(self,
                             implementation: str,
                             objective_or_name: str,
                             custom_description: str = None,
                             inventory_difference: Dict[str, int] = None) -> None:
    ##starting_inventory: Dict[str, int] = None) -> None:
        """Helper method to save implementations to the database"""
        name = (objective_or_name.split("\n\n")[0].lower()
                .replace(" ", "_")
                .replace(":", "")
                .replace("(", "")
                .replace(")", "")
                .replace("/", "_")
                .replace("\"", ""))

        if custom_description:
            docstring = custom_description
        else:
            docstring = self.generate_summary(TestInfo(name=name, source=implementation))

        self.save_function(
            name=name,
            implementation=implementation,
            description=docstring,
            starting_inventory=inventory_difference or {},
            signature=f"{name}(game) -> None:\n    \"\"\"{docstring}\"\"\"",
            version="v1.1"
        )


if __name__ == "__main__":
    generator = TailRecursiveSkillGenerator()

    objectives_file = "objectives.yaml"
    if os.path.exists(objectives_file):
        objectives = generator.load_objectives(objectives_file)
    else:
        print(f"Objectives file '{objectives_file}' not found. Please create it with objectives and inventories.")
        exit(1)

    for obj in objectives:
        print(f"Implementing skill for objective: {obj.objective}")
        print(f"Starting inventory: {obj.starting_inventory}")

        new_skill = generator.implement_skill(obj)
        if new_skill:
            print("Successfully implemented skill:")
            print(new_skill)
            # delete objective from file
            generator.remove_objective(objectives_file, obj.objective)
        else:
            print(f"Failed to implement skill for objective: {obj.objective}")
        print("\n" + "=" * 50 + "\n")

    print("All objectives have been processed. The program will now exit.")