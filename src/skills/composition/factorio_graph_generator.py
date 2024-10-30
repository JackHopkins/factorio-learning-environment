from dataclasses import dataclass
from typing import List, Dict
from openai import OpenAI
import yaml

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory


@dataclass
class Objective:
    objective: str
    starting_inventory: Dict[str, int]


class FactorioGraphGenerator:
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        self.llm_factory = LLMFactory(model)

    def objective_to_graph(self, objective: Objective) -> str:
        """Convert a Factorio objective into a Mermaid graph showing entity connections"""
        prompt = f"""
        Convert this Factorio objective into a Mermaid graph showing physical connections between entities.

        Objective: {objective.objective}
        Available inventory: {objective.starting_inventory}

        Rules:
        1. Use flowchart TD syntax
        2. Declare new entities with square brackets and a variable name: `entity[Entity Name]`
        3. After an entity is placed, reference it just with its variable name: `entity`
        4. Use specific connection types:
           - pipe: for fluid connections
           - belt: for machine-to-machine or machine-to-inserter transport
           - insert: for inserter-to-machine
           - pickup: for inserter-to-belt
           - pole: for power connections
        5. Include only entities available in the starting inventory
        6. Group related components with comments (%% section name)
        7. Provide a comment above each line with its type, purpose and any relevant information (e.g the type a miner should be mining)

        Example format:
        ```mermaid
        flowchart TD
            %% Coal mining drill
            [Mining Drill]
            
            %% Power setup
            OP[Offshore Pump] -->|pipe| B[Boiler]
        ```
        """

        messages = [
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(messages=messages, max_tokens=2000)
        graph = response.content[0].text

        # Extract just the Mermaid content between ```mermaid and ```
        if "```mermaid" in graph:
            graph = graph.split("```mermaid")[1].split("```")[0].strip()

        return graph

    def load_objectives(self, file_path: str) -> List[Objective]:
        """Load objectives from YAML file"""
        with open(file_path, 'r') as f:
            objectives_data = yaml.safe_load(f)
            return [Objective(**obj) for obj in objectives_data]