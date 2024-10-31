import os
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, Set, Optional, List, Tuple
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from skills.composition.factorio_graph_generator import Objective
from utilities.controller_loader import load_schema, load_definitions

load_dotenv()
client = OpenAI()

guidelines = """
1. When referencing the graph, place any new entities in square brackets
2. Connect entities according to the connection type. You can the use `connect_entities` method to connect entities that have been placed.
    a) To connect two entities with belts, use the `connect_entities` method after they have been placed - don't place belts using `place_entity`.
3. Include exhaustive assertions (with informative error_messages) at each step to verify the operation succeeded and that entities are connected:
   a) For fluid connections, verify the fluid box.
   b) Verify the status of all entities. It is very important to verify that all are working (or normal for passive entities like belts).
4. Don't catch any exception, let the code fail if the operation is not successful.
5. Do not craft anything, use only what is in your inventory
6. When using asserts, ensure that you get the entity from the game state first, by using `get_entity` or `get_entities` - otherwise the state will be stale.
7. When calling methods, ensure that all arguments are on the same line.
"""

@dataclass
class EntityNode:
    name: str
    prototype: str
    position: Optional[dict] = None
    entity_reference: Optional[dict] = None


class FactorioGraphExecutor:
    def __init__(self, factorio_instance, llm_factory, implementation_dao):
        self.factorio = factorio_instance
        self.implementation_dao = implementation_dao
        self.llm_factory = llm_factory
        self.entities: Dict[str, EntityNode] = {}
        self.api_schema = self._get_base_api_schema_prompt()

    def _extract_error_line(self, error_message: str) -> Optional[int]:
        """Extract the line number from an error message"""
        try:
            if "Line" in error_message:
                # Extract line number from messages like "Line 54: assert..."
                line_match = re.search(r"Line (\d+):", error_message)
                if line_match:
                    return int(line_match.group(1))
            return None
        except Exception:
            return None

    def _calculate_progress(self, error_line: Optional[int], total_lines: int) -> float:
        """Calculate the proportion of code that executed successfully"""
        if error_line is None:
            return 0.0
        return error_line / total_lines if total_lines > 0 else 0.0

    def _progress(self, error_message, implementation):
        error_line = self._extract_error_line(error_message)
        progress = self._calculate_progress(error_line, len(implementation.splitlines()))
        return progress

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
        dedented = textwrap.dedent(brief.strip())
        return dedented
    def generate_implementation(self, graph: str, objective: str, context: str = "") -> str:
        """Generate implementation code for a graph line using LLM"""
        # Skip comments and empty lines
        if graph.strip().startswith('%') or not graph.strip():
            return ""

        # Find similar functions for context
        similar_functions = self.implementation_dao.find_similar_functions(objective)
        context_examples = "\n\n".join([
            f"```python\n# {func['description']}\n{func['implementation']}\n```"
            for func in similar_functions
        ])

        prompt = \
f"""
Generate Python code to implement this Factorio graph line using the game API:

Graph: 
```mermaid
{graph}
```

Current context:
{context}

Previously created entities: {list(self.entities.keys())}

The code should:
{guidelines}

Similar implementations for reference:
{context_examples}

Output only a Python snippet or script, no explanations or function definitions.
"""
        dedented = textwrap.dedent(prompt.strip())

        messages = [
            {"role": "system", "content": self.api_schema},
            {"role": "user", "content": dedented}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=1000)
        implementation = response.content[0].text.strip()
        implementation = implementation.split("```python")[1].split("```")[0].strip()
        return implementation

    def verify_implementation(self, implementation: str) -> Tuple[bool, str, int, float]:
        """Execute and verify an implementation"""
        try:
            initial_score, _ = self.factorio.score()
            result = self.factorio.eval_with_error(implementation)

            if 'error' in str(result).lower() or 'assertion' in str(result).lower():
                progress = self._progress(str(result), implementation)
                return False, str(result), 0, progress

            self.factorio.sleep(5)
            final_score, _ = self.factorio.score()
            if final_score <= 0: # This means the implementation did not progress the game state
                return False, "Implementation did not generate any score, something isn't connected right", final_score - initial_score, 0.0

            return True, "", final_score - initial_score, 1.0

        except Exception as e:
            progress = self._progress(str(e), implementation)
            return False, str(e), 0, progress

    def repair_implementation(self, implementation: str, error_message: str, graph: str, entities: list) -> str:
        """Repair failed implementation using LLM"""
        similar_functions = self.implementation_dao.find_similar_functions(error_message)
        context = "\n\n".join(
            [f"```{func['name']}\n\"\"\"{func['description']}\"\"\"\n\n{func['implementation']}\n```"
             for func in similar_functions]
        )

        relevant_snippets = self.implementation_dao.get_snippets_with_correct_invocation(error_message)
        contextual_snippets = "\n\n".join(
            [f"```python\n{snippet}\n```" for snippet in relevant_snippets]
        )
        def indent(text):
            return textwrap.indent(text, "        ")

        repair_prompt = f"""
        The following Factorio implementation snippet failed:
        
        Architecture:
        ```mermaid
        {indent(graph)}
        ```
        ===
        
        Implementation:
        ```python
        {indent(implementation)}
        ```
        ===

        Error message: 
        ```
        {indent(error_message.strip())}
        ```
        ===
        
        Game entities:
        ```
        {repr(entities)}
        ```
        ===
        
        Examples using this function correctly:
        {contextual_snippets}
        ===
        
        Please modify the code to fix the error and achieve the objective. For successful repair, follow these guidelines:
        {indent(guidelines)}
        
        Focus on the entity that caused the error and ensure it is correctly placed, oriented and connected.
         
        Orientation and off-by-one errors are common issues.
        
        Your response should only include the Python code for the corrected snippet, and reasoning through comments.
        """

        repair_prompt = textwrap.dedent(repair_prompt)
        system = f"You are an effective Python debugger and Factorio expert wrote some implementations that may help your repair: \n{context}"
        messages = [
            {"role": "system", "content": system}, #self.api_schema},
            {"role": "user", "content": repair_prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        implementation = response.content[0].text.strip()
        implementation = implementation.split("```python")[1].split("```")[0].strip()
        return implementation


    def execute_graph(self, graph: str, objective: Objective, max_repair_attempts=12) -> Tuple[str, Dict[str, int], int, int]:
        """Execute a Mermaid graph in Python"""
        try:
            # Generate implementation code
            implementation = self.generate_implementation(graph, objective.objective)

            # Track progress history
            progress_history = []
            no_progress = 0
            max_no_progress_attempts = 4  # Maximum attempts without progress improvement

            for attempt in range(max_repair_attempts):
                print(f"Attempt {attempt + 1}:")

                # Reset game state for this attempt
                self.factorio.reset()
                self.factorio.set_inventory(**objective.starting_inventory)
                current_inventory = self.factorio.inspect_inventory().__dict__
                assert current_inventory == objective.starting_inventory

                # Verify implementation
                success, error_message, score, progress = self.verify_implementation(implementation)
                progress_history.append(progress)

                if success:
                    print("Success!")
                    final_inventory = self.factorio.inspect_inventory().__dict__
                    return implementation, final_inventory, attempt + 1, score

                # Check if we're making progress
                if len(progress_history) >= 2:
                    if progress_history[-1] <= progress_history[-2]:
                        no_progress += 1

                # Decide whether to continue repairs
                if no_progress >= max_no_progress_attempts:
                    print(f"No progress made in last {max_no_progress_attempts} attempts. Stopping repairs.")
                    raise Exception(f"Repair attempts stalled at {progress:.2%} completion")

                # Repair if not successful
                if attempt < max_repair_attempts - 1:
                    print(f"Repair attempt {attempt + 1}. Error: {error_message}")
                    print(f"Progress history: {[f'{p:.2%}' for p in progress_history]}")
                    entities = self.factorio.get_entities()
                    implementation = self.repair_implementation(implementation, error_message, graph, entities)
                else:
                    print(f"Failed to implement line after {max_repair_attempts} attempts")
                    print(f"Final progress: {progress:.2%}")
                    raise Exception(f"Failed to implement line after {max_repair_attempts} attempts")

        except Exception as e:
            print(f"Failed to execute graph\b '{graph}': {str(e)}")
            raise e
