import sys
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser\src")
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser")

import ast
import json
import os
import textwrap
from itertools import cycle
from typing import List, Dict, Any
from dotenv import load_dotenv

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from utilities.controller_loader import load_schema, load_definitions
from skills.skills_db import SkillsDB
load_dotenv()

class SkillPostProcessor:
    def __init__(self, model: str = "claude-3-5-sonnet-20240620"): #"gpt-4o"): #
        self.model = model
        self.llm_factory = LLMFactory(model)
        self.api_schema = self._get_base_api_schema_prompt()
        self.skills_db = SkillsDB()

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

    def _call_api(self, system_prompt: str, user_message: str, **kwargs) -> str:
        max_tokens = kwargs.get('max_tokens', 2000)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        try:
            response = self.llm_factory.call(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )

            if hasattr(response, 'choices'):
                return response.choices[0].message.content
            elif hasattr(response, 'content'):
                return response.content[0].text
            else:
                raise ValueError("Unexpected response structure")
        except Exception as e:
            print(f"API call failed: {e}")
            raise

    def load_existing_state(self, snippet_name: str) -> Dict[str, Any]:
        folder_path = f"../skills/_{snippet_name}"
        if os.path.exists(folder_path):
            with open(f"{folder_path}/details.json", "r") as f:
                details = json.load(f)
            self.token_count = details.get("token_count", 0)
            self.cost = details.get("cost", 0)
            return details
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

    def get_objective_examples(self, examples_folder):
        example_string = ""
        for example_folder in os.listdir(examples_folder):
            # read in details.json
            with open(os.path.join(examples_folder, example_folder, "details.json"), "r") as f:
                details = json.load(f)
            # read in snippet.py

            with open(os.path.join(examples_folder, example_folder, "snippet.py"), "r") as f:
                snippet = f.read()
            
            example_string += f"###USER INPUT EXAMPLE\n\nDESCRIPTION\n{details['description']}\n\nINVENTORY REQUIREMENTS\n{details['dependencies']}\n\nNAME\n{details['name']}\n\nIMPLEMENTATION\n{snippet}\n\n"
            example_string += f'###OUTPUT EXAMPLE\n\n#OBJECTIVE\n{details["objective"]}\n#OBJECTIVE\n\n'
        return example_string
    def generate_objective(self, skill) -> str:
        prompt_folder = r"prompts\postprocessing_objectives"
        #read in system_prompt.md
        with open(os.path.join(prompt_folder, "system_prompt.md"), "r") as f:
            system_prompt = f.read()

        #read in user_message.md
        with open(os.path.join(prompt_folder, "user_message.md"), "r") as f:
            user_message = f.read()
        
        examples_folder = f"prompts/postprocessing_objectives/examples"

        examples_string = self.get_objective_examples(examples_folder)
        user_message = user_message.format(examples = examples_string,
                                           name = skill["name"],
                                           implementation = skill["implementation"],
                                           description = skill["description"],
                                           dependencies = skill["dependencies"])
        objective = self._call_api(system_prompt, user_message)
        # assert atleast 2 #OBJECTIVE is in objective
        if objective.count("#OBJECTIVE") != 2:
            raise ValueError("Objective is not formatted correctly")
        # get the string between the two #OBJECTIVE
        objective = objective.split("#OBJECTIVE")[1].strip()
        return objective



if __name__ == "__main__":
    post_processor = SkillPostProcessor()
