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

class FactorioLLMSampler:
    def __init__(self, prompt_path: str = "prompts", examples_path: str = r"skills/rag_functions", model: str = "claude-3-5-sonnet-20240620"):
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

    def generate_plan_notebook(self, objective: str, 
                                           inventory: Dict[str, int], 
                                           mining_setup: str) -> str:
        specific_prompt_path = f"{self.prompt_path}/prompts_for_notebook"


        user_input = f"Objective: {objective}\n"
        user_input += f"Mining setup: {mining_setup}\n"
        user_input += f"Inventory: {inventory}\n"

        # read in the user_mesasge_planning.md and system_message_planning.md
        with open(f"{specific_prompt_path}/user_message_planning.md", "r") as f:
            user_message_planning = f.read()
        with open(f"{specific_prompt_path}/system_message_planning_substeps.md", "r") as f:
            system_prompt_planning = f.read()

        planning_examples_folder = r"prompts\prompts_for_notebook\planning_examples\rag_functions"
        # get all folders in examples_path
        examples = os.listdir(planning_examples_folder)
        examples_string = ""
        for example in examples:
            # read in the input.md
            with open(f"{planning_examples_folder}/{example}/input.md", "r") as f:
                example_input = f.read()
            examples_string += "USER INPUT\n" + example_input + "\n"
            # read in the plan.md
            with open(f"{planning_examples_folder}/{example}/plan.md", "r") as f:
                example_plan = f.read()
            examples_string += f"\nPLANNING OUTPUT: {example_plan}\n\n"

        user_message_planning = user_message_planning.format(user_input=user_input, examples=examples_string)
        full_output = self._call_api(system_prompt_planning,
                                      user_message_planning, max_tokens = 2048,
                                      model = "claude-3-5-sonnet-20240620",
                                      temperature = 0.5)
        #full_output = "Plan Analysis:\nTo achieve the objective of having one stone furnace in the inventory, we need to consider the following:\n\n1. There is already a stone furnace on the map, which we can use.\n2. Our inventory is currently empty.\n3. We don't need to craft a new stone furnace; we just need to pick up the existing one.\n\nGiven these conditions, our plan will be straightforward. We need to locate the existing stone furnace on the map, move to its position, and then pick it up. After that, we'll verify that the stone furnace is in our inventory.\n\n###START OF PLAN\nSTEP 1: Locate the stone furnace\n- Identify the position of the stone furnace on the map (x=-12.0, y=-12.0)\n\nSTEP 2: Move to the stone furnace\n- Move to the position of the stone furnace (x=-12.0, y=-12.0)\n\nSTEP 3: Pick up the stone furnace\n- Pick up the stone furnace at the current position\n\nSTEP 4: Verify inventory\nOUTPUT CHECK: Check if the stone furnace is now in the inventory\n###END OF PLAN"
        #full_output = "To achieve the objective of crafting an OffshorePump, we need to gather resources and craft the necessary components. Since there are no entities on the map and our inventory is empty, we'll start from scratch by gathering resources.\n\n[PLANNING]\n[STEP] 1: Print recipes. We need to print the recipe for crafting an OffshorePump to understand what materials are required.\n[STEP] 2: Gather resources. Based on the recipe, we need to gather enough copper ore and iron ore to produce at least 3 copper plates and 5 iron plates. Additionally, we must gather coal for smelting these ores into plates. Output check: Ensure that after this step, we have all specified raw materials in our inventory.\n[STEP] 3: Smelt ores into plates. Use a stone furnace (which needs to be crafted if not available) to smelt copper ore into copper plates and iron ore into iron plates. Output check: Verify that after this step, we have at least 3 copper plates and 5 iron plates in our inventory.\n[STEP] 4: Craft the OffshorePump. Use the gathered materials and crafted intermediates to craft one OffshorePump according to its recipe. Output check: Verify that an OffshorePump is now present in our inventory.\n[PLANNING]"
        # get everything between the [PLANNING] tags
        #planning_tag_locations = [m.start() for m in re.finditer("\[PLANNING\]", full_output)]
        #plan = full_output[planning_tag_locations[0]:planning_tag_locations[1]].replace("[PLANNING]", "").strip()
        start_of_plan_location = full_output.find("#START OF PLAN") + len("#START OF PLAN")
        end_of_plan_location = full_output.find("#END OF PLAN")
        plan = full_output[start_of_plan_location:end_of_plan_location].replace("#END OF PLAN", "").strip()
        #
        # split by newlines
        #plan = plan.split("[STEP]")
        plan = plan.split("STEP")
        steps = []
        final_output = {"full_plan": full_output, "plan": plan}
        for plan_step in plan:
            if plan_step == "":
                continue
            plan_step = plan_step.strip()
            steps.append({"step_description": plan_step})
        final_output["steps"] = steps
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

    def generate_step_notebook(self, objective: str, 
                                           inventory: Dict[str, int], 
                                           mining_setup: str,
                                           action_trace: List,
                                           print_trace: List, 
                                           full_plan: str) -> str:
        specific_prompt_path = f"{self.prompt_path}/prompts_for_notebook"


        #user_input = f"Objective: {objective}\n"
        #if mining_setup:
        #    user_input += f"Mining setup: {mining_setup}\n"
        #user_input += f"Inventory: {inventory}\n"
        

        # read in the user_mesasge_planning.md and system_message_planning.md
        with open(f"{specific_prompt_path}/user_message_step_filler.md", "r") as f:
            user_message_steps = f.read()
        with open(f"{specific_prompt_path}/system_message_step_filler.md", "r") as f:
            system_prompt_steps = f.read()

        step_examples_folder = r"skills\notebook_scripts"
        examples_string = self.get_example_string_rag(objective, mining_setup)

        system_prompt_steps = system_prompt_steps.format(entity_definitions=self.entities, schema = self.schema)
        user_message_steps = user_message_steps.format(objective=objective, 
                                                             examples=examples_string,
                                                             print_trace=print_trace,
                                                             full_script=full_plan,
                                                             inventory=inventory,
                                                             mining_setup=mining_setup)
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        output = self._call_api(system_prompt_steps, user_message_steps,
                                max_tokens = 1024, temperature = 0.5,
                                model = "claude-3-5-sonnet-20240620")
        prompt_inputs = {"objective": objective, "inventory": inventory_dict, "mining_setup": mining_setup,
                         "examples": examples_string, "print_trace": print_trace, "full_plan": full_plan}
        return output, prompt_inputs
        #try:
        #    program = response.replace('```python', '```')
        #    program = program.split('```')[1]
        #    return program, plan
        #except:
        #    return response, plan
    
    def correct_policy_snippet(self, objective: str, last_executed_policy: str,
                                error_message: str, action_trace: List[Dict[str, str]],
                                inventory: Dict[str, int], game_logs : list, error_logs: list,
                                mining_setup: str) -> str:
        
        
        specific_prompt_path = f"{self.prompt_path}/prompts_for_notebook"
        # read in user_message.md and system_message.md
        with open(f"{specific_prompt_path}/user_message_correct_filler.md", "r") as f:
            user_message = f.read()
        with open(f"{specific_prompt_path}/system_message_correct_filler.md", "r") as f:
            system_prompt = f.read()
        system_prompt = system_prompt.format(entity_definitions=self.entities, schema = self.schema)

        examples_string = self.get_example_string_rag(objective, mining_setup)
        game_log_string = "\n".join(game_logs)
        error_log_string = "\n".join(error_logs)
        game_log_string = f"Game logs:\n{game_log_string}\n\nError logs:\n{error_log_string}"
        
        user_message = user_message.format(
            objective=objective,
            inventory=inventory,
            working_examples = examples_string,
            last_executed_policy=action_trace,
            script_with_error =  last_executed_policy,
            error_message=error_message,
            game_log = game_log_string,
            mining_setup = mining_setup)
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

    def stream_curriculum(self, objective: Dict,  instance):   
        scenario_starting_inv = copy.deepcopy(objective["starting_inventory"])
        max_attempts = 2
        # First set up the game

        instance.reset()
        instance.initial_inventory = objective["starting_inventory"]
        instance.reset()
        # run the objective starting snippet
        _ = instance.eval_with_error(objective["starting_snippet"], timeout=60)

        objective_str = objective["objective"]
        starting_inventory = instance.inspect_inventory()
        action_trace = ""
        mining_setup = self.get_mining_setup(instance)
        #policy = self.generate_policy_function(objective, inventory = inventory)
        plan_output = self.generate_plan_notebook(objective_str, inventory = starting_inventory, 
                                                               mining_setup = mining_setup)
        #policy = '\ndef craft_offshore_pump():\n    """\n    Objective: We need to craft one offshore pump from scratch as we have no items in our inventory.\n    Mining setup: Currently there are no entities on the map\n    Inventory: We have no items in our inventory\n    """\n    # [PLANNING] To craft an offshore pump, we need:\n    # 1. 2 iron gear wheels (each requires 2 iron plates)\n    # 2. 1 electronic circuit (requires 1 iron plate and 3 copper cables)\n    # 3. 1 pipe (requires 1 iron plate)\n    # In total, we need:\n    # - 6 iron plates (2 for gear wheels, 1 for electronic circuit, 1 for pipe, 2 for the pump itself)\n    # - 3 copper plates (for the electronic circuit)\n    # We also need to mine coal for smelting.\n    # Steps:\n    # 1. Mine iron ore, copper ore, and coal\n    # 2. Craft stone furnaces\n    # 3. Smelt iron and copper plates\n    # 4. Craft iron gear wheels\n    # 5. Craft copper cable\n    # 6. Craft electronic circuit\n    # 7. Craft pipe\n    # 8. Finally, craft the offshore pump\n    # [END OF PLANNING]\n\n    # Step 1: Mine resources\n    iron_position = nearest(Resource.IronOre)\n    move_to(iron_position)\n    harvest_resource(iron_position, 12)  # We need 6 plates, so mine 12 ore to be safe\n    \n    copper_position = nearest(Resource.CopperOre)\n    move_to(copper_position)\n    harvest_resource(copper_position, 6)  # We need 3 plates, so mine 6 ore to be safe\n    \n    coal_position = nearest(Resource.Coal)\n    move_to(coal_position)\n    harvest_resource(coal_position, 10)  # Mine some extra for smelting\n    \n    stone_position = nearest(Resource.Stone)\n    move_to(stone_position)\n    harvest_resource(stone_position, 10)  # For crafting furnaces\n\n    # Step 2: Craft stone furnaces\n    craft_item(Prototype.StoneFurnace, 2)\n    furnace_count = inspect_inventory()[Prototype.StoneFurnace]\n    assert furnace_count >= 2, f"Failed to craft stone furnaces. Expected 2, but got {furnace_count}"\n\n    # Step 3: Smelt iron and copper plates\n    iron_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))\n    copper_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))\n\n    # [SUBFUNCTION]\n    # Name: smelt_ore_with_furnace\n    # Objective: We need to smelt ore into plates with a furnace\n    # Mining setup: We have a furnace on the map that we can use to smelt ores\n    # Inventory: We have enough ore and coal in the inventory to smelt the plates\n    # :param input_coal: The number of coal to insert into the furnace\n    # :param input_ore: The number of ore to insert into the furnace\n    # :param furnace: The furnace entity to use for smelting\n    # :param ore_type: The type of ore to smelt (IronOre or CopperOre)\n    # :param output_plate: The number of plates to extract from the furnace\n    # :return: None as the plates will be in inventory\n    # [END OF SUBFUNCTION]\n    smelt_ore_with_furnace(input_coal=5, input_ore=12, furnace=iron_furnace, ore_type=Prototype.IronOre, output_plate=6)\n    smelt_ore_with_furnace(input_coal=5, input_ore=6, furnace=copper_furnace, ore_type=Prototype.CopperOre, output_plate=3)\n\n    # Step 4: Craft iron gear wheels\n    craft_item(Prototype.IronGearWheel, 2)\n    gear_count = inspect_inventory()[Prototype.IronGearWheel]\n    assert gear_count >= 2, f"Failed to craft iron gear wheels. Expected 2, but got {gear_count}"\n\n    # Step 5: Craft copper cable\n    craft_item(Prototype.CopperCable, 3)\n    cable_count = inspect_inventory()[Prototype.CopperCable]\n    assert cable_count >= 3, f"Failed to craft copper cable. Expected 3, but got {cable_count}"\n\n    # Step 6: Craft electronic circuit\n    craft_item(Prototype.ElectronicCircuit, 1)\n    circuit_count = inspect_inventory()[Prototype.ElectronicCircuit]\n    assert circuit_count >= 1, f"Failed to craft electronic circuit. Expected 1, but got {circuit_count}"\n\n    # Step 7: Craft pipe\n    craft_item(Prototype.Pipe, 1)\n    pipe_count = inspect_inventory()[Prototype.Pipe]\n    assert pipe_count >= 1, f"Failed to craft pipe. Expected 1, but got {pipe_count}"\n\n    # Step 8: Craft offshore pump\n    craft_item(Prototype.OffshorePump, 1)\n    pump_count = inspect_inventory()[Prototype.OffshorePump]\n    assert pump_count >= 1, f"Failed to craft offshore pump. Expected 1, but got {pump_count}"\n\n    print("Successfully crafted one offshore pump!")\n'
            
        full_script = f'from factorio_instance import *\n\n"""\nMain Objective: {objective_str}\n"""\n\n'
        # fill out the full script
        for idx, plan in enumerate(plan_output["steps"]):
            full_script += '\n\n"""\n'
            full_script += f"Step {plan['step_description']}\n"
            full_script += '"""\n'
            full_script += f'# Placeholder {idx + 1}'
                

        full_plan = plan_output["full_plan"]
        print_trace = []
        for plan_idx, plan in enumerate(plan_output["steps"]):
                
            step_description = plan["step_description"]
            current_inventory = instance.inspect_inventory()
            mining_setup = self.get_mining_setup(instance)
            plan["full_script_tries"] = []
            
            step_description = f"Placeholder {step_description}"
            step_script, prompt_inputs = self.generate_step_notebook(objective = step_description, 
                                                      inventory = current_inventory, 
                                                      mining_setup = mining_setup, 
                                                      action_trace=action_trace, 
                                                      print_trace=print_trace, 
                                                      full_plan=full_script)
            plan["full_script_tries"].append({"prompt_inputs": prompt_inputs, "output": step_script})
            try:
                program = step_script.split('```python')[1]
                program = program.split('```')[0]
                program.replace('```', '')
            except:
                program = step_script
                

            output_list, result = self.eval_program_with_result_trace(instance, program)
            errored = False
            if "error" in result.lower():
                errored = True
                for i in range(max_attempts):
                    print(f"Error in step {step_description}. Attempt {i+1}. Error: {result}")
                    step_script = self.correct_policy_snippet(objective=step_description, 
                                                              last_executed_policy=program, 
                                                              error_message = result, 
                                                              action_trace=full_script, 
                                                              inventory=current_inventory, 
                                                              game_logs = print_trace, 
                                                              error_logs=output_list,
                                                              mining_setup=mining_setup)
                    plan["full_script_tries"].append(step_script)
                    try:
                        program = step_script.split('```python')[1]
                        program = program.split('```')[0]
                        program.replace('```', '')
                    except:
                        program = step_script

                    instance.reset()
                    instance.initial_inventory = objective["starting_inventory"]        
                    instance.reset()
                    _ = instance.eval_with_error(objective["starting_snippet"], timeout=60)
                    _ = instance.eval_with_error(action_trace, timeout=60)
                    output_list, result = self.eval_program_with_result_trace(instance, program)
                    if "error" not in result.lower():
                        errored = False
                        break

            if errored:
                print(f"Failed to repair step {step_description}")
                break
            full_script = full_script.replace(f"# Placeholder {plan_idx + 1}",f"# Inventory at the start of step {current_inventory}\n#Step Execution\n{program}")
            print_trace += output_list
            action_trace += f"\n#[STEP SEPARATOR]\n\n{program}"
            plan["final_step_program"] = program
        
        
        starting_inv_dict = {}
        for item in scenario_starting_inv:
            if isinstance(item, tuple):
                item = item[0]
                starting_inv_dict[item[0]] = scenario_starting_inv[item]
            else:
                starting_inv_dict[item] = scenario_starting_inv[item]
        yield {
            "plan_output": plan_output["steps"],
            "objective": objective_str,
            "mining_setup": mining_setup,
            "starting_inventory": starting_inv_dict,
            "full_plan": full_plan,
            "full_script": full_script,
            "full_snippet": action_trace,
            "errored": errored,
            "name": objective["name"],
            "scenario_starting_inv": scenario_starting_inv
        }

def save_gold_skills_into_db():
    db = SkillsDB()
    db.delete_all_skills()
    skills = db.get_all_skills()
    names = [skill['name'] for skill in skills]
    examples_folder = r"skills\notebook_scripts_rag"
    # get all folders in examples_path
    examples = os.listdir(examples_folder)
    for example in examples:
        if example.startswith("exclude"):
            continue
        # read in details
        folder_path = f"{examples_folder}/{example}"
        with open(f"{folder_path}/details.json", "r") as f:
            details = json.load(f)
        # read in the snippet
        with open(f"{folder_path}/snippet.py", "r") as f:
            snippet = f.read()
        
        name = "N/A"
        if name in names:
            continue
        implementation = f"Planning\n{details['planning']}\n\nCode snippet\n```python{snippet}```"
        # get the signature, that is the step description
        mining_setup_string = "There are no entities on the map" if "[" not in details["mining_setup"] else "There are useable entities on the map"
        signature = f"Objective: {details['step']}\nMining setup: {mining_setup_string}"
        description = f'Step description: {details["step"]}\nInventory: {details["inventory"]}\nMining setup: {details["mining_setup"]}'
        dependencies = []
        implementation_model = "gold_standard"
        db.save_function(name = name, 
                    description = description, 
                    implementation = implementation, 
                    dependencies = dependencies, 
                    implementation_model = implementation_model,
                    signature = signature)

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
    folder_path = r"skills\rag_skills\_create_electric_coal_mine"
    #evaluate_a_skill(folder_path)
    #main()
    save_gold_skills_into_db()

    sampler = FactorioLLMSampler(model = "gpt-4o")
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

# put down a chest at origin
chest = place_entity(Prototype.IronChest, position=Position(x=0, y=0))

# place a stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))
# put coal into furnace
furnace = insert_item(Prototype.Coal, furnace, 5)

print(furnace.fuel.get(Prototype.Coal))

"""

    try:
        score, goal, result = instance.eval_with_error(test_string, timeout=60)
    except Exception as e:
        print(f"Error: {e}")
    # Load objectives from file
    #objectives_file = "skills\objectives_rag.txt"
    #if os.path.exists(objectives_file):
    #    objectives = sampler.load_objectives(objectives_file)
    #else:
    #    print(f"Objectives file '{objectives_file}' not found. Please create it and add objectives.")
    #    exit(1)    

    starting_scenario_name = "one_chest_with_random_inv_on_map"
    objective_group = "Group_4_craft_hard"
    starting_scenarios_folder = f"skills\data_scenarios\starting_scenarios\{starting_scenario_name}"
    objectives_folder = f"skills\data_scenarios\objectives\{objective_group}"
    #read in details.json
    with open(f"{objectives_folder}/details.json", "r") as f:
        details = json.load(f)
    
    # read in starting_snippet.py from starting_scenarios_folder
    with open(f"{starting_scenarios_folder}/starting_snippet.py", "r") as f:
        starting_snippet = f.read()
    
    # read in details from details.json from starting_scenarios_folder
    with open(f"{starting_scenarios_folder}/details.json", "r") as f:
        starting_details = json.load(f)
    objectives = details["objectives"]

    for obj_idx, objective in enumerate(objectives):
            snippet_name = objective["name"]
            save_folder_path =  f"skills/notebook_skills/{objective_group}/{starting_scenario_name}/{snippet_name.strip()}"
            if os.path.exists(save_folder_path):
                print(f"Objective {snippet_name} has already been completed. Skipping.")
                continue
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
            
            if "inventory" in objective:
                additional_inv = objective["inventory"]
                for key, value in additional_inv.items():
                    if key in starting_inventory:
                        starting_inventory[key] += value
                    else:
                        starting_inventory[key] = value
            # remove all items that have a value of 0
            starting_inventory = {k: v for k, v in starting_inventory.items() if v != 0}
            objective["starting_inventory"] = starting_inventory
            objective["starting_snippet"] = starting_snippet
            curriculum_item = next(sampler.stream_curriculum(objective, instance))
            
            snippet_name = curriculum_item["name"]
            snippet_passed = not curriculum_item["errored"]
            snippet = curriculum_item["full_script"]
            
            # Save results and update files
            folder_name = snippet_name if snippet_passed else f"_{snippet_name}"
            folder_path = f"skills/notebook_skills/{objective_group}/{starting_scenario_name}/{folder_name.strip()}"
            # check if the folder existss
            if os.path.exists(folder_path):
                # start adding numbers to the folder name
                i = 1
                new_folder_path = f"{folder_path}_{i}"
                while os.path.exists(new_folder_path):
                    i += 1
                    new_folder_path = f"{folder_path}_{i}"
                folder_path = new_folder_path
            
            os.makedirs(folder_path, exist_ok=True)
            with open(f"{folder_path}/full_snippet.py", "w") as f:
                f.write(snippet)

            curriculum_item["starting_scenario"] = starting_scenario_name
            curriculum_item["objective_group"] = objective_group
            with open(f"{folder_path}/curriculum_item.json", "w") as f:
                json.dump(curriculum_item, f, indent=2)

            sampler.token_count = 0
            sampler.cost = 0

    print("All objectives have been completed. The program will now exit.")
