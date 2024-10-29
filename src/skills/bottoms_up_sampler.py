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
import re
from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from utilities.controller_loader import load_schema, load_definitions
import numpy as np
import io
load_dotenv()
import time
from skills_db import SkillsDB
import copy
def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class BottomsUpSkillSampler:
    def __init__(self, prompt_path: str = "prompts/bottoms_up_prompts", examples_path: str = r"skills/rag_functions", model: str = "claude-3-5-sonnet-20240620"):
        self.model = model
        self.llm_factory = LLMFactory(model)
        self.api_schema, self.entities = self._get_base_api_schema_prompt()
        self.objective_context = []
        self.token_count = 0
        self.cost = 0
        self.prompt_path = prompt_path
        self.examples_path = examples_path
        self.skills_db = SkillsDB()

    def _get_base_api_schema_prompt(self):
        execution_path = os.path.dirname(os.path.realpath(__file__))
        folder_path = f'{execution_path}/../controllers'
        self.schema = load_schema(folder_path)
        type_definitions = load_definitions(f'{execution_path}/../factorio_types.py')
        self.entity_definitions = load_definitions(f'{execution_path}/../factorio_entities.py')
        brief = f"""
You have access to the following Game API for use in your Python code:

Entities:
{self.entity_definitions}

            Methods:
            ```
            {self.schema}
            """
        return brief, self.entity_definitions

    def _call_api(self, system_prompt: str, user_message: str, **kwargs) -> str:
        max_tokens = kwargs.get('max_tokens', 4096)
        temperature = kwargs.get('temperature', 0.3)
        model_to_use = kwargs.get('model', self.model)
        # delete the temperature and max_tokens from kwargs
        if "max_tokens" in kwargs:
            del kwargs['max_tokens']
        if "temperature" in kwargs:
            del kwargs['temperature']
        if "model" in kwargs:
            del kwargs['model']
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        try:
            max_tries = 5
            for i in range(max_tries):
                try:
                    response = self.llm_factory.call(
                        model=model_to_use,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    )
                    break
                except Exception as e:
                    if i == max_tries - 1:
                        raise e
                    print(f"API call failed: {e}")
                    time.sleep(2**i)

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


    def generate_verification_function(self, objective: str) -> str:
        specific_prompt_path = f"{self.prompt_path}/outcome_test"
        # read in user_message.md and system_message.md
        with open(f"{specific_prompt_path}/user_message.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message.md", "r") as f:
            system_prompt = f.read()
        system_prompt = system_prompt.format(api_schema=self.api_schema)
        user_message = user_message.format(objective=objective)
        response = self._call_api(system_prompt, user_message)
        try:
            program = response.replace('```python', '```')
            program = program.split('```')[1]

            return program
        except:
            return response

    def generate_objectives(self, curriculum: str, 
                                           mining_setup: str) -> str:
        specific_prompt_path = f"{self.prompt_path}/objective_generation"


        user_input = f"{curriculum['objective']}\n"
        if curriculum['objective_gen_instructions']:
            user_input += f"Extra generation instructions: {curriculum['objective_gen_instructions']}\n"
        #user_input += f"Mining setup: {mining_setup}\n"

        # read in the user_mesasge_planning.md and system_message_planning.md
        with open(f"{specific_prompt_path}/user_message.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message.md", "r") as f:
            system_prompt = f.read()

        examples_folder = f"{self.prompt_path}/objective_generation/examples"
        # get all folders in examples_path
        examples = os.listdir(examples_folder)
        examples_string = ""
        for example in examples:
            # read in the input.md
            with open(f"{examples_folder}/{example}/input.md", "r") as f:
                example_input = f.read()
            examples_string += "USER INPUT\n" + example_input + "\n"
            # read in the plan.md
            with open(f"{examples_folder}/{example}/output.md", "r") as f:
                example_output = f.read()
            examples_string += f"\nOUTPUT: {example_output}\n\n"

        user_message = user_message.format(user_input=user_input, examples=examples_string)
        full_output = self._call_api(system_prompt,
                                      user_message, max_tokens = 2048,
                                      model = "claude-3-5-sonnet-20240620",
                                      temperature = 1)
        start_of_objectives_location = full_output.find("###START OF OBJECTIVES") + len("###START OF OBJECTIVES")
        end_of_objectives_location = full_output.find("###END OF OBJECTIVES")
        objectives = full_output[start_of_objectives_location:end_of_objectives_location].replace("###END OF OBJECTIVES", "").strip()
        #
        # split by newlines
        objectives = objectives.split("\n")
        final_output = [{"objective": obj, "implementation_tries": []} for obj in objectives if obj]
        return final_output

    def get_example_string_from_folder(self, step_examples_folder: str) -> str:
        # get all folders in examples_path
        examples = os.listdir(step_examples_folder)
        examples_string = ""
        for example in examples:
            # read in the snippet.py
            with open(f"{step_examples_folder}/{example}/snippet.py", "r") as f:
                example_output = f.read()
            
            # read in the details.json
            with open(f"{step_examples_folder}/{example}/details.json", "r") as f:
                details = json.load(f)
        
            example_objective = details["step"]
            example_inventory = details["inventory"]
            example_input = f"Objective: {example_objective}\nInventory: {example_inventory}\n"
            examples_string += "USER INPUT\n" + example_input + "\n"
            # split everything by '[PLANNING]\n"""'
            example_outputs_split = example_output.split('[PLANNING]\n"""')
            example_code = example_outputs_split[1] 
            example_plan = example_outputs_split[0].replace("[PLANNING]", "").replace('"""', "").strip()
            examples_string += f"\nSTEP OUTPUT:\nPLANNING\n{example_plan}\nCode snippet ```python{example_code}```\n\n"
        return examples_string
    
    def get_example_string_rag(self, step_description: str, mining_setup) -> str:
        mining_rag_string = "There are no entities on the map" if "[" not in mining_setup else "There are useable entities on the map"
        rag_str = f"Objective: {step_description}\nMining setup: {mining_rag_string}\n"
        examples = self.skills_db.find_similar_functions(rag_str, n = 3)

        examples_string = ""
        for example in examples:
        
            examples_string += "USER INPUT\n" + example['description'] + "\n"
            # split everything by '[PLANNING]\n"""'
            examples_string += f"\nOUTPUT:\n{example['implementation']}\n\n"
        return examples_string

    def generate_implementation(self, input_objective: str, 
                                           curriculum: dict, 
                                           mining_setup: str
                                                            ) -> str:
        specific_prompt_path = f"{self.prompt_path}/implementation_generation"


        #user_input = f"Objective: {objective}\n"
        #if mining_setup:
        #    user_input += f"Mining setup: {mining_setup}\n"
        #user_input += f"Inventory: {inventory}\n"
        

        # read in the user_mesasge_planning.md and system_message_planning.md
        with open(f"{specific_prompt_path}/user_message.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message.md", "r") as f:
            system_prompt = f.read()

        user_message = user_message.format(ground_truth_objective=curriculum["objective"], 
                                                             reference_mining_setup=mining_setup,
                                                             implementation=curriculum["implementation"],
                                                             input_objective=input_objective,
                                                             input_mining_setup=mining_setup)
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        
        output = self._call_api(system_prompt, user_message,
                                max_tokens = 2048, temperature = 0.5,
                                model = "claude-3-5-sonnet-20240620")
        prompt_inputs = {"curriculum": curriculum, "input_objective": input_objective, "mining_setup": mining_setup}
        return output, prompt_inputs
        #try:
        #    program = response.replace('```python', '```')
        #    program = program.split('```')[1]
        #    return program, plan
        #except:
        #    return response, plan

    def synthesise_objective_and_implementation(self,
                                           curriculum: dict, 
                                           mining_setup: str
                                                            ) -> str:
        specific_prompt_path = f"{self.prompt_path}/skill_generator"
        user_input = f"{curriculum['objective']}\n"
        if curriculum['objective_gen_instructions']:
            user_input += f"Extra generation instructions: {curriculum['objective_gen_instructions']}\n"

        #user_input = f"Objective: {objective}\n"
        #if mining_setup:
        #    user_input += f"Mining setup: {mining_setup}\n"
        #user_input += f"Inventory: {inventory}\n"
        

        # read in the user_mesasge_planning.md and system_message_planning.md
        with open(f"{specific_prompt_path}/user_message.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message.md", "r") as f:
            system_prompt = f.read()

        user_message = user_message.format(ground_truth_objective=user_input, 
                                                             reference_mining_setup=mining_setup,
                                                             implementation=curriculum["implementation"])
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        
        output = self._call_api(system_prompt, user_message,
                                max_tokens = 2048, temperature = 1,
                                model = "claude-3-5-sonnet-20240620")
        prompt_inputs = {"curriculum": curriculum, "mining_setup": mining_setup}
        return output, prompt_inputs
        #try:
        #    program = response.replace('```python', '```')
        #    program = program.split('```')[1]
        #    return program, plan
        #except:
        #    return response, plan
    
    def correct_implementation_snippet(self, 
                                        input_objective: str, 
                                        last_executed_policy: str,
                                        error_message: str, 
                                        curriculum: List[Dict[str, str]],
                                        logs : list, 
                                        mining_setup: str,
                                        mining_setup_during_error
                                        ) -> str:
        
        
        specific_prompt_path = f"{self.prompt_path}/implementation_reflection"
        # read in user_message.md and system_message.md
        with open(f"{specific_prompt_path}/user_message.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message.md", "r") as f:
            system_prompt = f.read()
        system_prompt = system_prompt.format(entity_definitions=self.entities, schema = self.schema)

        game_log_string = "\n".join(logs)
        game_log_string = f"Game logs:\n{game_log_string}\n\nError logs:\n{error_message}"
        
        user_message = user_message.format(
            reference_objective=curriculum["objective"],
            reference_implementation=curriculum["implementation"],
            objective = input_objective,
            script_with_error =  last_executed_policy,
            error_message=error_message,
            game_log = game_log_string,
            mining_setup = mining_setup,
            mining_setup_during_error = mining_setup_during_error)
        return self._call_api(system_prompt, user_message, max_tokens = 2048,
                              model = "claude-3-5-sonnet-20240620"
                              )


    def eval_program_with_print_capture(self, instance, program):
        # Create a StringIO object to capture the output
        captured_output = io.StringIO()
        # Save the current stdout so we can revert back later
        sys_stdout = sys.stdout
        # Redirect stdout to the StringIO object
        sys.stdout = captured_output
        # evaluate the step
        try:
            score, goal, result = instance.eval_with_error(program, timeout=60)
        except Exception as e:
            result = f"error: {str(e)}"
        captured_output.seek(0)  # Go to the start of StringIO to read from beginning
        output_list = captured_output.read().splitlines()
        # Revert sys.stdout to its original state
        sys.stdout = sys_stdout
        return output_list, result


    def eval_program_with_result_trace(self, instance, program):
        # evaluate the step
        try:
            score, goal, result = instance.eval_with_error(program, timeout=60)
        except Exception as e:
            result = f"error: {str(e)}"
        # split result by newlines
        output_list = result.splitlines()
        return output_list, result
    
    def get_mining_setup(self, instance):
        mining_setup = instance.get_entities()
        if len(mining_setup) == 0:
            mining_setup = "There are no entities on the map"
        else:
            mining_setup = f"The following entities are on the map and can be used: {mining_setup}"
        return mining_setup

    def stream_curriculum(self, curriculum: Dict,  instance):   
        scenario_starting_inv = copy.deepcopy(curriculum["starting_inventory"])
        max_attempts = 0
        # First set up the game

        instance.reset()
        instance.initial_inventory = curriculum["starting_inventory"]
        instance.reset()
        ## run the objective starting snippet
        _ = instance.eval_with_error(curriculum["starting_snippet"], timeout=60)

        starting_inventory = instance.inspect_inventory()
        mining_setup = self.get_mining_setup(instance)
        objectives_output = self.generate_objectives(curriculum, 
                                                               mining_setup = mining_setup)
        for objective in objectives_output:

            instance.reset()
            instance.initial_inventory = curriculum["starting_inventory"]
            instance.reset()
            ## run the objective starting snippet
            _ = instance.eval_with_error(curriculum["starting_snippet"], timeout=60)
        
            step_script, prompt_inputs = self.generate_implementation(input_objective= objective["objective"], 
                                                      curriculum= curriculum, 
                                                      mining_setup=mining_setup)
            objective["implementation_tries"].append({"prompt_inputs": prompt_inputs, "output": step_script})
            try:
                program = step_script.split('```python')[1]
                program = program.split('```')[0]
                program.replace('```', '')
            except:
                program = step_script
                

            output_list, result = self.eval_program_with_result_trace(instance, program)
            errored = False if "error" not in result.lower() else True
            if "error" in result.lower():
                errored = True
                for i in range(max_attempts):
                    print(f"Error in step {objective}. Attempt {i+1}. Error: {result}")
                    mining_setup_during_error = self.get_mining_setup(instance)
                    step_script = self.correct_implementation_snippet(input_objective= objective["objective"], 
                                                              curriculum= curriculum, 
                                                              mining_setup=mining_setup, 
                                                              last_executed_policy=program, 
                                                              error_message = result, 
                                                              logs = output_list,
                                                              mining_setup_during_error = mining_setup_during_error)
                                                              
                    objective["implementation_tries"].append({"error_message": result, "output": step_script})
                    try:
                        program = step_script.split("ERROR CORRECTION")[-1]
                        program = program.split('```python')[1]
                        program = program.split('```')[0]
                        program.replace('```', '')
                    except:
                        program = step_script

                    instance.reset()
                    instance.initial_inventory = curriculum["starting_inventory"]        
                    instance.reset()
                    _ = instance.eval_with_error(curriculum["starting_snippet"], timeout=60)
                    output_list, result = self.eval_program_with_result_trace(instance, program)
                    if "error" not in result.lower():
                        errored = False
                        break
            
            objective["final_implementation"] = program
            if errored:
                print(f"Failed to repair step {objective['objective']}")
                objective["success"] = False
            else: 
                objective["success"] = True
        
        
        starting_inv_dict = {}
        for item in scenario_starting_inv:
            if isinstance(item, tuple):
                item = item[0]
                starting_inv_dict[item[0]] = scenario_starting_inv[item]
            else:
                starting_inv_dict[item] = scenario_starting_inv[item]
        
        return objectives_output
    
    def curriculum_bottom_up(self, curriculum: Dict,  instance):   
        scenario_starting_inv = copy.deepcopy(curriculum["starting_inventory"])
        max_attempts = 1
        # First set up the game

        instance.reset()
        instance.initial_inventory = curriculum["starting_inventory"]
        instance.reset()
        ## run the objective starting snippet
        _ = instance.eval_with_error(curriculum["starting_snippet"], timeout=60)

        starting_inventory = instance.inspect_inventory()
        mining_setup = self.get_mining_setup(instance)
        objective_output, prompt_inputs = self.synthesise_objective_and_implementation(curriculum, 
                                                               mining_setup = mining_setup)

        
        #objective["implementation_tries"].append({"prompt_inputs": prompt_inputs, "output": objective_output})
        try:
            program = objective_output.split('```python')[1]
            program = program.split('```')[0]
            program.replace('```', '')
        except:
            program = objective_output
                

        output_list, result = self.eval_program_with_result_trace(instance, program)
        errored = False
        if "error" in result.lower():
                errored = True
                for i in range(max_attempts):
                    print(f"Error in step {objective}. Attempt {i+1}. Error: {result}")
                    mining_setup_during_error = self.get_mining_setup(instance)
                    step_script = self.correct_implementation_snippet(input_objective= objective["objective"], 
                                                              curriculum= curriculum, 
                                                              mining_setup=mining_setup, 
                                                              last_executed_policy=program, 
                                                              error_message = result, 
                                                              logs = output_list,
                                                              mining_setup_during_error = mining_setup_during_error)
                                                              
                    objective["implementation_tries"].append({"error_message": result, "output": step_script})
                    try:
                        program = step_script.split("ERROR CORRECTION")[-1]
                        program = program.split('```python')[1]
                        program = program.split('```')[0]
                        program.replace('```', '')
                    except:
                        program = step_script

                    instance.reset()
                    instance.initial_inventory = curriculum["starting_inventory"]        
                    instance.reset()
                    _ = instance.eval_with_error(curriculum["starting_snippet"], timeout=60)
                    output_list, result = self.eval_program_with_result_trace(instance, program)
                    if "error" not in result.lower():
                        errored = False
                        break
            
        objective["final_implementation"] = program
        if errored:
            print(f"Failed to repair step {objective['objective']}")
            objective["success"] = False
        else: 
            objective["success"] = True
        
        
        starting_inv_dict = {}
        for item in scenario_starting_inv:
            if isinstance(item, tuple):
                item = item[0]
                starting_inv_dict[item[0]] = scenario_starting_inv[item]
            else:
                starting_inv_dict[item] = scenario_starting_inv[item]
        
        return objectives_output

def save_synth_skills_into_db():
    db = SkillsDB()
    
    skills_folder = r"skills\expanded_skills"
    all_skills_from_db = db.get_all_skills()
    # get all folders in examples_path
    all_skills = os.listdir(skills_folder)
    names = [skill["name"] for skill in all_skills_from_db if "mart_expansion" in skill["version"]]
    for skill_group in all_skills:
        skill_group_folder = f"{skills_folder}/{skill_group}"
        # get all folders in skill_group_folder
        starting_scenarios = os.listdir(skill_group_folder)
        for starting_scenario in starting_scenarios:
            # get all folders in starting_scenario
            starting_scenario_folder = f"{skill_group_folder}/{starting_scenario}"
            # get all folders in starting_scenario_folder
            expanded_skills = os.listdir(starting_scenario_folder)
            for expanded_skill in expanded_skills:
                if "false" in expanded_skill.lower():
                    continue
                full_path = f"{starting_scenario_folder}/{expanded_skill}"
                # read in the implementation
                with open(f"{full_path}/implementation.py", "r") as f:
                    implementation = f.read()
                # read in objective.json
                with open(f"{full_path}/objective.json", "r") as f:
                    objective = json.load(f)
                # read in curriculum_item.json
                with open(f"{full_path}/curriculum_item.json", "r") as f:
                    curriculum = json.load(f)
                name = f"{skill_group}_{starting_scenario}_{expanded_skill}"
                if name in names:
                    continue
                # create the description
                description = f'Objective: {objective["objective"]}\nStarting Inventory: {curriculum["starting_inventory"]}'
                signature = description
                dependencies = []
                implementation_model = "expanded_synthetic"
                version = "mart_expansion_v1"
    

                db.save_function(name = name, 
                            description = description, 
                            implementation = implementation, 
                            dependencies = dependencies, 
                            implementation_model = implementation_model,
                            signature = signature,
                            version = version)

def evaluate_a_skill(folder_path):
    # readinthe full_snippet.py
    with open(f"{folder_path}/full_snippet.py", "r") as f:
        full_snippet = f.read()
    
    # read in the details.json
    with open(f"{folder_path}/details.json", "r") as f:
        details = json.load(f)

    inventory = details["inventory"]
    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)

    # evaluate the skill
    score, goal, result = instance.eval_with_error(full_snippet, timeout=240)
    print(result)


if __name__ == "__main__":
    #evaluate_a_skill(folder_path)
    #main()
    #save_synth_skills_into_db()

    sampler = BottomsUpSkillSampler(model = "gpt-4o")
    #sampler = FactorioLLMSampler()

    inventory = {
        'iron-plate': 50,
        'coal': 100,
        'copper-plate': 50,
        'iron-chest': 2,
        'burner-mining-drill': 3,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 9,
        'transport-belt': 500,
        'boiler': 1,
        'burner-inserter': 32,
        'pipe': 15,
        'steam-engine': 1,
        'small-electric-pole': 10,
        "wooden-chest": 1,
        "iron-ore": 20,
        "offshore-pump": 1
    }

    #inventory = {
    #    'iron-plate': 20,
    #    'coal': 20,
    #    'copper-plate': 20,
    #    'stone-furnace': 3,
    #    'iron-ore':10
    #}
    #inventory = {}
    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)


    test_string = """


from factorio_instance import *

# Find the nearest copper ore patch
copper_ore_position = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch to place the burner mining drills
# move to the center of the patch, the place where the drills will be placed
move_to(copper_ore_position.bounding_box.center)
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the first burner mining drill on the copper ore patch
# place it at the center of the patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position.bounding_box.center)
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to fuel the first burner mining drill
# Also get a updated fueled_drill variable to refresh the drill variable with the updated fuel level
fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
coal_inserted = fueled_drill.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the burner mining drill")


"""

    #try:
    #    score, goal, result = instance.eval_with_error(test_string, timeout=60)
    #except Exception as e:
    #    print(f"Error: {e}")
    # Load objectives from file
    #objectives_file = "skills\objectives_rag.txt"
    #if os.path.exists(objectives_file):
    #    objectives = sampler.load_objectives(objectives_file)
    #else:
    #    print(f"Objectives file '{objectives_file}' not found. Please create it and add objectives.")
    #    exit(1)    
    
    starting_objective_folder = r"skills\ground_truth_skills\put_down_electricity_gen"
    #read in curriculum_item.jsom
    with open(f"{starting_objective_folder}/curriculum_item.json", "r") as f:
        curriculum = json.load(f)
    
    # read in starting_snippet.py from starting_scenarios_folder
    with open(f"{starting_objective_folder}/full_snippet.py", "r") as f:
        implementation = f.read()

    curriculum["implementation"] = implementation
    starting_scenario_folder = f"skills\data_scenarios\starting_scenarios\{curriculum['starting_scenario']}" 
    snippet_name = curriculum["objective_group"]
    
    # read in the details.json from the starting_scenario_folder
    with open(f"{starting_scenario_folder}/details.json", "r") as f:
        starting_details = json.load(f)
    
    # read in the starting_snippet.py from the starting_scenario_folder
    with open(f"{starting_scenario_folder}/starting_snippet.py", "r") as f:
        starting_snippet = f.read()

    starting_inventory = copy.deepcopy(starting_details["fixed_inventory"])
    random_inventory = starting_details["random_inventory"]
    for key, value in random_inventory.items():
        # get a 0 or a 1 to add this item to the inventory
        if np.random.randint(0, 2) == 1:
            starting_inventory[key] = np.random.randint(value[0], value[1]+1)
    
    if "additional_inventory_for_starting_scenario" in starting_details:
        additional_inv = starting_details["additional_inventory_for_starting_scenario"]
        for key, value in additional_inv.items():
            if key in starting_inventory:
                starting_inventory[key] += value
            else:
                starting_inventory[key] = value
    
    if "inventory" in curriculum:
        additional_inv = curriculum["inventory"]
        for key, value in additional_inv.items():
            if key in starting_inventory:
                starting_inventory[key] += value
            else:
                starting_inventory[key] = value
    # remove all items that have a value of 0
    starting_inventory = {k: v for k, v in starting_inventory.items() if v != 0}
    curriculum["starting_inventory"] = starting_inventory
    curriculum["starting_snippet"] = starting_snippet
    completed_objectives = sampler.stream_curriculum(curriculum, instance)
            
    save_folder_path = f"skills\expanded_skills\{snippet_name}\{curriculum['starting_scenario']}"
    # create the folder if it does not exist
    os.makedirs(save_folder_path, exist_ok=True)
    for objective in completed_objectives:
        # get the nr of files in the folder
        nr_files = len(os.listdir(save_folder_path))
        # create the folder
        folder_path = f"{save_folder_path}/{nr_files}_{objective['success']}"

        os.makedirs(folder_path, exist_ok=True)
        # write the ground truth snippet
        with open(f"{folder_path}/reference_snippet.py", "w") as f:
            f.write(curriculum["implementation"])
        # write the curriculum_item.json
        with open(f"{folder_path}/curriculum_item.json", "w") as f:
            json.dump(curriculum, f, indent=2)
        
        # write the implementation if it exists
        if "final_implementation" in objective:
            with open(f"{folder_path}/implementation.py", "w") as f:
                f.write(objective["final_implementation"])
            # remove the final_implementation from the objective
            del objective["final_implementation"]
        # write the objective
        with open(f"{folder_path}/objective.json", "w") as f:
            json.dump(objective, f, indent=2)

        
    print("All objectives have been completed. The program will now exit.")
