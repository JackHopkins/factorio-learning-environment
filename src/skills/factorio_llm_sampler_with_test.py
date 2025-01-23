import ast
import json
import os
import textwrap
from typing import List, Dict, Any
from dotenv import load_dotenv

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from utilities.controller_loader import load_schema, load_definitions

load_dotenv()


def is_valid_python(code_string: str) -> bool:
    """
    Check if a string is syntactically valid Python code.

    Args:
    code_string (str): The string containing Python code to validate.

    Returns:
    bool: True if the code is syntactically valid, False otherwise.
    """
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class FactorioLLMSampler:
    def __init__(self, model: str = "claude-3-5-sonnet-20240620"):
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
        entity_definitions = load_definitions(f'{execution_path}/../factorio_types.py')
        brief = f"""
            You have access to the following Game API for use in your Python code:

            Types:
            {entity_definitions}

            Methods:
            ```
            {schema}
            """
        return brief

    def _call_api(self, system_prompt: str, user_message: str, **kwargs) -> str:
        max_tokens = kwargs.get('max_tokens', 1200)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        try:
            response = self.llm_factory.call(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )

            # Update token count
            self.token_count += response.usage.input_tokens + response.usage.output_tokens
            self.cost += response.usage.input_tokens * 0.0000003 + response.usage.output_tokens * 0.0000015

            # Handle different response structures
            if hasattr(response, 'choices'):
                # OpenAI and DeepSeek API
                return response.choices[0].message.content
            elif hasattr(response, 'content'):
                # Anthropic API
                return response.content[0].text
            else:
                raise ValueError("Unexpected response structure")
        except Exception as e:
            print(f"API call failed: {e}")
            raise

    def load_existing_state(self, function_name: str) -> Dict[str, Any]:
        folder_path = f"../skills/_{function_name}"
        if os.path.exists(folder_path):
            with open(f"{folder_path}/details.json", "r") as f:
                details = json.load(f)

            self.token_count = details.get("token_count", 0)
            self.cost = details.get("cost", 0)

            return details
        return None

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
        system_prompt = (
            f"You are an AI assistant creating a plan for a Factorio game objective. "
            # f"\n{self.api_schema}\n"

        )
        user_message = f"How would you achieve the following?: '{objective}'"
        return self._call_api(system_prompt, user_message)

    def generate_verification_function(self, objective: str, function_name: str, steps: str, policy: str) -> str:
        system_prompt = (
            f"You are an AI assistant creating Python verification decorators for functions that fulfil Factorio game objectives. "
            f"The function you need to test is:\n```python\n{policy}\n```\n"
            f"Here is the API you can use to write the test, exposed by the `game` parameter:\n{self.api_schema}\n"
            f"Write a decorator that sets up the initial state, runs the policy, and verifies the output state."
            f"The decorator should take the game instance as a parameter."
            f"Only write in python in ``` blocks"
            "Import: `from factorio_instance import *`"
            "Use `functools.wraps` to preserve the original function's metadata."
            "Do not include any example usage or function calls in your response."
        )

        user_message = (
            f"Design a Python verification decorator to check if the policy fulfils the objective: '{objective}' "
            f"given the desired approach:\n```{steps}```\n"
            f"The decorator should:\n"
            f"1. Set up the initial state (e.g., inventory)\n"
            f"2. Run the policy function\n"
            f"3. Verify the output state (e.g., changes in inventory, placed entities)\n"
            f"4. Raise an exception if the verification fails"
        )
        response = self._call_api(system_prompt, user_message)
        try:
            program = response.replace('```python', '```')
            program = program.split('```')[1]
            return program
        except:
            return response

    def generate_policy_function(self, objective: str, function_name: str, steps: str) -> str:
        system_prompt = (
            f"You are an AI agent creating Python policy functions to achieve Factorio game objectives. "
            f"The function should be named '{function_name}'. \n{self.api_schema}\n"
            f"Only write in python in ``` blocks. "
            f"Ensure the function raises an uncaught exception if something goes wrong at runtime. "
            "Do not use try-catch as it will hide the error message."
            "Include appropriate function parameters with type annotations, instead of constants and magic numbers."
            "Import: `from factorio_instance import *`"
            "Do not include any example usage or function calls in your response."
        )
        user_message = f"Use the API to write a Python policy function to achieve the objective: '{objective}'. Here are the steps to achieve the objective:\n{steps}"
        response = self._call_api(system_prompt, user_message)
        try:
            program = response.replace('```python', '```')
            program = program.split('```')[1]
            return program
        except:
            return response

    def generate_function_name(self, objective: str) -> str:
        system_prompt = f"You are an AI assistant creating Python function names for Factorio game objectives."
        user_message = (f"Provide me with the name for a function to achieve the objective: '{objective}'. "
                        f"Only write between ``` blocks."
                        f"e.g '```place_furnace_next_to_coal```'")
        response = self._call_api(system_prompt, user_message)
        parsed = response.split('```')[1].replace(' ', '_').lower()
        return parsed

    def correct_policy_function(self, objective: str, function_name: str, original_policy: str,
                                error_message: str, correction_history: List[Dict[str, str]]) -> str:
        system_prompt = (
            f"You are an AI assistant correcting Python policy functions for Factorio game objectives. "
            f"The function should be named '{function_name}' and take a 'game' parameter which exposes this API: \n{self.api_schema}\n"
            f"Only write in python in ``` blocks"
            f"Ensure the function raises an uncaught exception if something goes wrong at runtime. "
            "Do not use try-catch as it will hide the error message."
        )

        history_str = "\n\n".join([
            f"Attempt {i + 1}:\nPolicy:\n```python\n{attempt['policy']}\n```\nError: {attempt['error']}"
            for i, attempt in enumerate(correction_history)
        ])

        user_message = (
            f"The following policy function for the objective '{objective}' has failed multiple times. "
            f"Here's the history of attempts and errors:\n\n{history_str}\n\n"
            f"Please correct the policy function to fix these errors and achieve the objective. "
            f"Consider all previous attempts and their errors when making your correction."
        )
        return self._call_api(system_prompt, user_message)

    def correct_test(self, objective: str, correction_history: List[Dict[str, str]]) -> str:
        system_prompt = (
            f"You are an AI assistant correcting Python verification decorators for Factorio game objectives. "
            f"Only write in python in ``` blocks"
            f"The decorator should raise an exception if the verification fails. "
            f"The game API is available for use by passing in the `game` parameter, which exposes: \n\n{self.api_schema}"
        )

        history_str = "\n\n".join([
            f"Attempt {i + 1}:\nDecorator:\n```python\n{attempt['policy']}\n```\nError: {attempt['error']}"
            for i, attempt in enumerate(correction_history)
        ])

        user_message = (
            f"The following verification decorator for the Factorio objective '{objective}' has failed multiple times. "
            f"Here's the history of attempts and errors:\n\n{history_str}\n\n"
            f"Please correct the verification decorator to fix these errors and successfully test the policy function. "
            f"Consider all previous attempts and their errors when making your correction."
            f"Ensure the decorator sets up the initial state, runs the policy, and verifies the output state."
        )
        return self._call_api(system_prompt, user_message)

    def stream_curriculum(self, num_objectives: int = 5):
        for _ in range(num_objectives):
            objective = self.generate_objective()
            name = self.generate_function_name(objective)
            steps = self.generate_plan(objective)
            policy = self.generate_policy_function(objective, name, steps)
            test = self.generate_verification_function(objective, name, steps, policy)
            yield {
                "objective": objective,
                "verification": test,
                "policy": policy,
                "steps": steps,
                "function_name": name,
            }

def extract_steps_from_policy_function(policy: str) -> str:
    """
    Extract the plan steps from a policy function.

    Args:
    policy_string (str): The policy function code.

    Returns:
    str: The plan steps extracted from the policy function.
    """
    policy_string = "\n".join(policy.split("\n")[1:])
    # remove the first \tab character from each line
    policy_string = textwrap.dedent(policy_string)
    #policy_string = policy_string.replace(" game.", " ")

    return policy_string

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
                                tcp_port=27000,
                                fast=True,
                                inventory=inventory)

    for curriculum_item in sampler.stream_curriculum(10):
        function_name = curriculum_item['function_name']
        existing_state = sampler.load_existing_state(function_name)

        if existing_state:
            print(f"Resuming work on existing objective: {existing_state['objective']}")
            curriculum_item = existing_state
            correction_history = existing_state.get("corrections", [])
            with open(f"../skills/_{function_name}/policy.py", "r") as f:
                curriculum_item['policy'] = f.read()
            with open(f"../skills/_{function_name}/test_policy.py", "r") as f:
                curriculum_item['verification'] = f.read()
        else:
            correction_history = []

        print(f"Objective: {curriculum_item['objective']}")
        print("Function name: " + function_name)
        print("Plan:")
        print(curriculum_item["steps"])
        print("Verification function:")
        print(curriculum_item['verification'])
        print("Policy function:")
        print(curriculum_item['policy'])
        print("\n" + "=" * 50 + "\n")

        if not is_valid_python(curriculum_item['verification']) or not is_valid_python(curriculum_item['policy']):
            continue

        policy_string = curriculum_item['policy']
        test_string = curriculum_item['verification']

        max_attempts = 16
        policy_passed = False

        for attempt in range(max_attempts):
            instance._reset(**instance.initial_inventory if isinstance(instance.initial_inventory, dict) else instance.initial_inventory.__dict__)

            try:
                combined_code = f"{test_string}\n\n{policy_string}\n\n{function_name}(instance)"
                score, goal, result = instance.eval_with_error(combined_code, timeout=10)

                if 'error' in result.lower():
                    raise Exception(result)

                policy_passed = True
                break
            except Exception as e:
                correction_history.append({"policy": combined_code, "error": str(e)})
                if attempt < max_attempts - 1:
                    print(f"Policy or verification failed on attempt {attempt + 1}. `{str(result)}` Attempting to correct...")
                    if 'decorator' in str(e).lower():
                        corrected_test = sampler.correct_test(curriculum_item['objective'], correction_history)
                        corrected_test = corrected_test.split("```")[1].lstrip('python\n')
                        test_string = corrected_test
                    else:
                        corrected_policy = sampler.correct_policy_function(
                            curriculum_item['objective'],
                            function_name,
                            policy_string,
                            str(result),
                            correction_history
                        )
                        corrected_policy = corrected_policy.split("```")[1].lstrip('python\n')
                        policy_string = textwrap.dedent("\n".join(corrected_policy.split("\n")[1:]))
                else:
                    print(f"Policy and verification failed after {max_attempts} attempts. Moving to next objective.")

        # Save results and update files
        folder_name = function_name if policy_passed else f"_{function_name}"
        folder_path = f"../skills/{folder_name}"
        os.makedirs(folder_path, exist_ok=True)

        with open(f"{folder_path}/test_policy.py", "w") as f:
            f.write("from factorio_instance import *\n" + curriculum_item['verification'])

        with open(f"{folder_path}/policy.py", "w") as f:
            f.write("from factorio_instance import *\n" + curriculum_item['policy'])

        details = {
            "objective": curriculum_item['objective'],
            "steps": curriculum_item['steps'],
            "corrections": correction_history,
            "token_count": sampler.token_count,
            "cost": sampler.cost,
            "policy_passed": policy_passed
        }
        with open(f"{folder_path}/details.json", "w") as f:
            json.dump(details, f, indent=2)

        if policy_passed:
            print(f"Successfully wrote policy and test files for objective: {curriculum_item['objective']}")
        else:
            print(f"Failed to generate a working policy for objective: {curriculum_item['objective']}")

        sampler.token_count = 0
        sampler.cost = 0