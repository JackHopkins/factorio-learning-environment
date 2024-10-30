import os
from dataclasses import dataclass
from textwrap import dedent
from typing import Dict, Set, Optional, List
import ast
import psycopg2
from openai import OpenAI

from skills.composition.factorio_graph_generator import Objective
from skills.composition.composition_utils import load_schema
from skills.db_test_loader import TestInfo
DB_PASSWORD = os.getenv("DB_PASSWORD")


class FactorioImplementationDAO:
    def __init__(self, llm_factory):
        self.llm_factory = llm_factory
        self.conn = psycopg2.connect(
            host="factorio.cwqst41cfhhd.us-east-1.rds.amazonaws.com",
            port="5432",
            dbname="factorio",
            user="postgres",
            password=DB_PASSWORD
        )
        self.client = OpenAI()
        self.controller_names = load_schema("../../controllers")

    def find_similar_functions(self, task_description: str, n: int = 5) -> List[Dict]:
        """Find similar functions from the database with similarity scores"""
        cursor = self.conn.cursor()
        query_embedding = self.get_embedding(task_description)

        # Using PostgreSQL's built-in cosine similarity operator (<#>)
        # Note: We negate it because <#> returns the distance (1 - cosine similarity)
        cursor.execute("""
            SELECT 
                name,
                implementation,
                description,
                signature,
                1 + (embedding <#> %s::vector) as similarity_score
            FROM public.skills
            WHERE version = 'v1.1'
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, 10))

        results = [{
            "name": row[0],
            "implementation": row[1],
            "description": row[2],
            "signature": row[3],
            "similarity": float(row[4])  # Convert Decimal to float
        } for row in cursor.fetchall()]

        return results[-n:]

    def get_snippets_with_correct_invocation(self, error_message: str) -> List[Dict]:
        # We need to get the function name from the error message
        function_name = None
        for controller_name in self.controller_names:
            if controller_name in error_message:
                function_name = controller_name
                break

        if not function_name:
            return []

        snippets = self._find_similar_code_lines(f"{function_name}(")
        relevant_chunks = []
        for snippet in snippets:
            chunks = snippet['implementation'].split("\n\n")
            for chunk in chunks:
                if function_name in chunk:
                    relevant_chunks.append(dedent(chunk))

        return relevant_chunks

    def _find_similar_code_lines(self, code_pattern: str, n: int = 5) -> List[Dict]:
        """Find lines containing specific code patterns using string matching"""
        cursor = self.conn.cursor()

        cursor.execute("""
            WITH implementation_lines AS (
                -- Split implementations into lines and number them
                SELECT 
                    name,
                    implementation,
                    description,
                    line_number,
                    trim(line) as code_line
                FROM (
                    SELECT 
                        name,
                        implementation,
                        description,
                        generate_subscripts(string_to_array(implementation, E'\n'), 1) as line_number,
                        unnest(string_to_array(implementation, E'\n')) as line
                    FROM public.skills
                    WHERE version = 'v1.1'
                ) split_lines
                WHERE 
                    trim(line) != '' AND  -- Skip empty lines
                    trim(line) !~ '^#' AND  -- Skip comments
                    trim(line) LIKE %s  -- Match the code pattern
            )
            SELECT DISTINCT  -- Avoid duplicates
                name,
                implementation,
                description,
                line_number,
                code_line
            FROM implementation_lines
            LIMIT %s
        """, (f'%{code_pattern}%', n))

        return [{
            "name": row[0],
            "implementation": row[1],
            "description": row[2],
            "line_number": row[3],
            "code_line": row[4]
        } for row in cursor.fetchall()]

    def generate_summary(self, implementation: str, graph: str, objective: str) -> str:
        """Generate a comprehensive summary combining code, graph, and objective"""
        prompt = f"""
        Please analyze this Factorio implementation and provide a clear, comprehensive summary.
        Consider all aspects:

        Objective: {objective}

        Graph Structure:
        ```mermaid
        {graph}
        ```

        Implementation:
        ```python
        {implementation}
        ```

        Provide a detailed summary that includes:
        1. The main goal accomplished
        2. Key entities and their relationships
        3. Critical resource dependencies
        4. Notable implementation patterns

        Write a concise but thorough technical summary, focusing on completeness and accuracy.
        """

        messages = [
            {"role": "system", "content": "You are an expert at analyzing code and systems design"},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=500)
        return response.content[0].text.strip()

    def _calculate_inventory_difference(self, starting_inventory: Dict[str, int], final_inventory: Dict[str, int]) -> \
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
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for the text"""
        response = self.client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    def save_execution(self,
                       implementation: str,
                       graph: str,
                       objective: Objective,
                       final_inventory: Dict[str, int],
                       version="v1.1",
                       complexity=-1,
                       attempts=1,
                       score=0) -> None:
        """Save a successful execution to the database"""
        try:
            # Generate name from objective
            name = (objective.objective.split("\n\n")[0].lower()
                    .replace(" ", "_")
                    .replace(":", "")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("/", "_")
                    .replace("\"", ""))

            initial_inventory = dict(objective.starting_inventory)

            # Calculate inventory difference
            inventory_diff = self._calculate_inventory_difference(initial_inventory, final_inventory)

            # Generate comprehensive summary
            summary = self.generate_summary(implementation, graph, objective.objective)

            # Generate embedding from combined information
            embedding_text = f"{objective}\n{summary}\n{implementation}"
            embedding = self.get_embedding(embedding_text)

            # Create signature
            signature = f"{name}(game) -> None:\n    \"\"\"{summary}\"\"\""

            # Save to database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO public.skills (
                    name, implementation, description, embedding, dependencies, 
                    version, embedding_model, implementation_model, signature, attempts, complexity, score
                )
                VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                implementation,
                summary,
                embedding,
                repr(inventory_diff),
                version,
                "text-embedding-3-small",
                self.llm_factory.model,
                signature,
                attempts,
                complexity,
                score
            ))

            self.conn.commit()
            print(f"Successfully saved execution '{name}' to database")

        except Exception as e:
            print(f"Failed to save execution: {str(e)}")
            self.conn.rollback()

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()