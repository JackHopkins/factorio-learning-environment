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

load_dotenv()

def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class FactorioLLMSampler:
    def __init__(self, model: str = "claude-3-5-sonnet-20240620"): #"gpt-4o"): #
        self.model = model
        self.llm_factory = LLMFactory(model)
        self.api_schema = self._get_base_api_schema_prompt()
        self.objective_context = []
        self.token_count = 0
        self.cost = 0

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

            try:
                self.token_count += response.usage.input_tokens + response.usage.output_tokens
                self.cost += response.usage.input_tokens * 0.0000003 + response.usage.output_tokens * 0.0000015
            except:
                self.token_count += response.usage.total_tokens
                self.cost += response.usage.prompt_tokens * 0.0000003 + response.usage.completion_tokens * 0.0000015

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

    def generate_objective(self) -> str:
        system_prompt = "You are an AI assistant creating beginner objectives for a Factorio game curriculum. Generate a single, clear objective for the next task in the game."
        curriculum_examples = '\n'.join([
            "Mine 100 iron ore into your inventory",
            "Gather resources and smelt 10 iron plates in a stone furnace",
            "Chop down trees and make a wooden chest to store items",
        ])
        context = "\n".join(self.objective_context)
        interstitial = ", set objectives that do one thing at a time"
        if context:
            interstitial += f", considering the following context of previous objectives:\n\n{context}\n"
        user_message = f"Generate a new objective for the Factorio curriculum{interstitial}\nEnsure the new objective is different from these. Example objectives:\n{curriculum_examples}"
        new_objective = self._call_api(system_prompt, user_message)
        self.objective_context.append(new_objective)
        if len(self.objective_context) > 5:
            self.objective_context.pop(0)
        return new_objective

    def generate_plan(self, objective):
        system_prompt = f"You are an AI assistant creating a plan for a Factorio game objective."
        user_message = f"How would you achieve the following?: '{objective}'"
        return self._call_api(system_prompt, user_message)

    def generate_policy_snippet(self, objective: str, steps: str) -> str:
        system_prompt = (
            f"You are an AI agent creating Python snippets to achieve Factorio game objectives. "
            f"Here is the API you can use:\n{self.api_schema}\n"
            f"Write a Python snippet that achieves the objective and includes assertions to verify the result. "
            f"The snippet should be a series of commands, not a function. "
            f"Use assert statements to check if the objective has been met. "
            f"Print assigned variable values for debugging. "
            f"Ensure that failed assertions return the most relevant error message possible to help with correction. "
            f"Only write in python in ``` blocks. "
            f"Ensure appropriate error handling without using try-catch blocks. "
            f"Do not include any example usage or function calls in your response."
        )
        user_message = (
            f"Write a Python snippet to achieve the objective: '{objective}'. "
            f"Here are the steps to achieve the objective:\n{steps}\n"
            f"Include assertions to verify that the objective has been met."
        )
        response = self._call_api(system_prompt, user_message)
        try:
            program = response.replace('```python', '```')
            program = program.split('```')[1]
            return program
        except:
            return response

    def generate_snippet_name(self, objective: str) -> str:
        system_prompt = f"You are an AI assistant creating Python snippet names for Factorio game objectives."
        user_message = (f"Provide a name for a snippet to achieve the objective: '{objective}'. "
                        f"Only write between ``` blocks. "
                        f"e.g '```place_furnace_next_to_coal```'")
        response = self._call_api(system_prompt, user_message, temperature=0)
        parsed = response.split('```')[1].replace(' ', '_').lower().strip()
        return parsed

    def correct_policy_snippet(self, objective: str, original_snippet: str,
                               error_message: str, correction_history: List[Dict[str, str]]) -> str:
        system_prompt = (
            f"You are an AI assistant correcting Python snippets for Factorio game objectives. "
            f"The snippet should use this API: \n{self.api_schema}\n"
            f"Only write in python in ``` blocks. "
            f"Ensure appropriate error handling without using try-catch blocks. "
            f"Include assertions to verify that the objective has been met."
        )

        history_str = "\n\n".join([
            f"Attempt {i + 1}:\nSnippet:\n```python\n{attempt['snippet']}\n```\nError: {attempt['error']}"
            for i, attempt in enumerate(correction_history)
        ])

        user_message = (
            f"The following snippet for the objective '{objective}' has failed. "
            f"Here's the history of attempts and errors:\n\n{history_str}\n\n"
            f"Please correct the snippet to fix these errors and achieve the objective. "
            f"Consider all previous attempts and their errors when making your correction."
        )
        return self._call_api(system_prompt, user_message)

    def stream_curriculum(self, objectives: List[str]):
        # for _ in range(num_objectives):
        #     objective = self.generate_objective()
        for objective in objectives:
            name = self.generate_snippet_name(objective)
            steps = self.generate_plan(objective)
            snippet = self.generate_policy_snippet(objective, steps)
            yield {
                "objective": objective,
                "snippet": snippet,
                "steps": steps,
                "snippet_name": name,
            }

if __name__ == "__main__":
    sampler = FactorioLLMSampler()

    inventory = {
        'iron-plate': 50,
        'coal': 50,
        'copper-plate': 50,
        'iron-chest': 2,
        'burner-mining-drill': 3,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 9,
        'transport-belt': 50,
        'boiler': 1,
        'burner-inserter': 32,
        'pipe': 15,
        'steam-engine': 1,
        'small-electric-pole': 10
    }
    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)

    # Load objectives from file
    objectives_file = "objectives.txt"
    if os.path.exists(objectives_file):
        objectives = sampler.load_objectives(objectives_file)
    else:
        print(f"Objectives file '{objectives_file}' not found. Please create it and add objectives.")
        exit(1)

    while objectives:
        for objective in objectives.copy():
            curriculum_item = next(sampler.stream_curriculum([objective]))
            snippet_name = curriculum_item['snippet_name']
            existing_state = sampler.load_existing_state(snippet_name)

            if existing_state:
                print(f"Resuming work on existing objective: {existing_state['objective']}")
                curriculum_item = existing_state
                correction_history = existing_state.get("corrections", [])
                with open(f"../skills/_{snippet_name}/snippet.py", "r") as f:
                    curriculum_item['snippet'] = f.read()
            else:
                correction_history = []

            print(f"Objective: {curriculum_item['objective']}")
            print("Snippet name: " + snippet_name)
            print("Plan:")
            print(curriculum_item["steps"])
            print("Snippet:")
            print(curriculum_item['snippet'])
            print("\n" + "=" * 50 + "\n")

            if not is_valid_python(curriculum_item['snippet']):
                continue

            snippet = curriculum_item['snippet']

            max_attempts = 6
            snippet_passed = False

            for attempt in range(max_attempts):
                instance._reset(**instance.initial_inventory if isinstance(instance.initial_inventory, dict) else instance.initial_inventory.__dict__)

                try:
                    score, goal, result = instance.eval_with_error(snippet, timeout=20)

                    if 'error' in result.lower() or 'assertion' in result.lower():
                        raise Exception(result)

                    snippet_passed = True
                    break
                except Exception as e:
                    correction_history.append({"snippet": snippet, "error": str(e)})
                    if attempt < max_attempts - 1:
                        print(f"{snippet_name} - Snippet failed on attempt {attempt + 1}. `{str(result)}` Attempting to correct...")
                        corrected_snippet = sampler.correct_policy_snippet(
                            curriculum_item['objective'],
                            snippet,
                            str(result),
                            correction_history
                        )
                        corrected_snippet = corrected_snippet.split("```")[1].lstrip('python\n')
                        snippet = textwrap.dedent(corrected_snippet)
                    else:
                        print(f"{snippet_name} - Snippet failed after {max_attempts} attempts. Moving to next objective.")

            # Save results and update files
            folder_name = snippet_name if snippet_passed else f"_{snippet_name}"
            folder_path = f"../skills/{folder_name.strip()}"
            os.makedirs(folder_path, exist_ok=True)

            with open(f"{folder_path}/snippet.py", "w") as f:
                f.write(snippet)

            details = {
                "instruction": objective,
                "objective": curriculum_item['objective'],
                "steps": curriculum_item['steps'],
                "corrections": correction_history,
                "token_count": sampler.token_count,
                "cost": sampler.cost,
                "snippet_passed": snippet_passed
            }
            with open(f"{folder_path}/details.json", "w") as f:
                json.dump(details, f, indent=2)

            if snippet_passed:
                print(f"Successfully wrote snippet file for objective: {curriculum_item['objective']}")
                # Remove the completed objective from objectives.txt
                sampler.remove_objective(objectives_file, objective)
            else:
                print(f"Failed to generate a working snippet for objective: {curriculum_item['objective']}")

            sampler.token_count = 0
            sampler.cost = 0

        if objectives:
            print("Completed a full cycle. Starting over with remaining objectives.")
        else:
            print("All objectives have been completed. Exiting the program.")

    print("All objectives have been completed. The program will now exit.")