import os
import re

from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional, List, Dict
from dataclasses import dataclass
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


@dataclass
class Objective:
    description: str
    children: List["Objective"]
    parent: Optional["Objective"] = None
    completed: bool = False


class ObjectiveTreeGenerator:
    def __init__(
        self,
        api_key: str,
        model: str = "ft:gpt-4o-2024-08-06:paperplane-ai:plans:AcHaA92I",
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_depth = 10  # Prevent infinite recursion
        self.visited_objectives = set()  # Prevent cycles

    def get_sub_objectives(self, objective_text: str) -> List[str]:
        """Query the model for sub-objectives using parent format"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that understands Factorio game objectives and their relationships.",
                    },
                    {"role": "user", "content": f"<parent>{objective_text}</parent>"},
                ],
                temperature=0,
                max_tokens=2048,
            )

            # Parse response into individual objectives
            response_text = response.choices[0].message.content
            objectives = self.extract_objectives(response_text)

            return objectives

        except Exception as e:
            logger.error(f"Error getting sub-objectives for {objective_text}: {e}")
            return []

    def extract_objectives(self, response_text):
        objectives = []
        for line in response_text.split("\n"):
            pattern = r"<([^>]+)>(.*?)</\1>"

            match = re.search(pattern, line)
            if match:
                objectives.append(match.group(2).strip())
        return objectives

    def get_sibling_objectives(self, objective_text: str) -> List[str]:
        """Query the model for sibling objectives"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that understands Factorio game objectives and their relationships.",
                    },
                    {"role": "user", "content": f"<sibling>{objective_text}</sibling>"},
                ],
                temperature=0,
                max_tokens=2048,
            )

            # Parse response into individual objectives
            response_text = response.choices[0].message.content
            objectives = self.extract_objectives(response_text)

            return objectives

        except Exception as e:
            logger.error(f"Error getting sibling objectives for {objective_text}: {e}")
            return []

    def build_tree(
        self, objective_text: str, depth: int = 0, parent: Optional[Objective] = None
    ) -> Optional[Objective]:
        """Recursively build the objective tree"""
        if depth >= self.max_depth:
            logger.warning(f"Max depth reached for objective: {objective_text}")
            return None

        if objective_text in self.visited_objectives:
            logger.warning(f"Cycle detected for objective: {objective_text}")
            return None

        self.visited_objectives.add(objective_text)

        logger.info("\t" * depth + objective_text)

        # Create current objective node
        current = Objective(description=objective_text, children=[], parent=parent)

        # Get sub-objectives
        sub_objectives = self.get_sub_objectives(objective_text)

        # Rate limit to avoid API throttling
        time.sleep(1)

        if len(sub_objectives) == 1:
            sub_objective = sub_objectives[0]
            sub_objectives.extend(self.get_sibling_objectives(sub_objective))

        # Recursively process sub-objectives
        for sub_obj in sub_objectives:
            child = self.build_tree(sub_obj, depth + 1, current)
            if child:
                current.children.append(child)

        return current

    def save_tree(self, root: Objective, file_path: str):
        """Save the objective tree to a file"""

        def objective_to_dict(obj: Objective) -> Dict:
            return {
                "description": obj.description,
                "completed": obj.completed,
                "children": [objective_to_dict(child) for child in obj.children],
            }

        tree_dict = objective_to_dict(root)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tree_dict, f, indent=2)

    def print_tree(self, objective: Objective, level: int = 0):
        """Print the objective tree in a readable format"""
        prefix = "  " * level
        status = "✓" if objective.completed else "○"
        print(f"{prefix}{status} {objective.description}")
        for child in objective.children:
            self.print_tree(child, level + 1)


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    generator = ObjectiveTreeGenerator(api_key=api_key)

    # Generate tree for iron plate factory
    root_objective = "Research automation from scratch"
    tree = generator.build_tree(root_objective)

    # Print the tree
    print("\nGenerated Objective Tree:")
    generator.print_tree(tree)

    # Save the tree
    generator.save_tree(tree, "research_automation.json")


if __name__ == "__main__":
    main()
