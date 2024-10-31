import sys
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser\src")
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser")
import os
import ast
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from factorio_instance import FactorioInstance
import random
from skills.skill_postprocessor import SkillPostProcessor
from skills.bottoms_up_sampler import eval_program_with_result_trace, get_mining_setup
load_dotenv()
from skills.skills_db import SkillsDB
from skills.get_test_data import extract_skills_from_test
def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class SFTDatasetCreator:
    def __init__(self, starting_scenario_folder):
        self.skills_db = SkillsDB()
        self.init_starting_scenarios(starting_scenario_folder)
        self.postprocessor = SkillPostProcessor()
        self.starting_scenario_folder = starting_scenario_folder
    
    def init_starting_scenarios(self, starting_scenario_folder):
        # get all folder names in the starting scenario folder
        self.starting_scenario_names = os.listdir(starting_scenario_folder)


    def postprocess_skills(self, input_file, output_file) -> Dict:
        # check if the output file exists
        if os.path.exists(output_file):
            # read in the output jsonl file
            with open(output_file) as f:
                post_processed_skills = [json.loads(line) for line in f.readlines()]
        else:
            post_processed_skills = []

        # read in the input jsonl file
        with open(input_file) as f:
            skills = [json.loads(line) for line in f.readlines()]


        for skill_idx, skill in enumerate(skills):
            print(f"Processing skill {skill_idx}/{len(skills)}")
            exists = False
            # check if the skill is already post processed
            for postprocessed_skill in post_processed_skills:
                if postprocessed_skill["name"] == skill["name"] and postprocessed_skill["implementation"] == skill["implementation"]:
                    exists = True
                    break
            if exists:
                continue
            try:
                skill = self.enchance_skill_with_attributes(skill)
            except Exception as e:
                print(f"Error in skill {skill['name']}: {e}")
                continue
            # save the skill to the output file
            with open(output_file, "a") as f:
                f.write(json.dumps(skill) + "\n")

    def enchance_skill_with_attributes(self, skill: Dict) -> Dict:
        # We need a objective, starting mining scenario and the starting inventory
        # everything that is over 30 sleeep, put to 30
        if "mart" in skill["version"]:
            # first get the objective and the starting inventory from the description
            description = skill["description"]
            # split by Starting Inventory: 
            description_parts = description.split("Starting Inventory: ")
            objective = description_parts[0].replace("Objective: ", "").strip()
            inventory = description_parts[1].split("Scenario:")[0].strip()
            inventory = inventory.replace("\n", "")
            inventory = eval(inventory)
            assert type(inventory) == dict, f"Inventory is not a dict: {inventory}"
            # now we need to get the starting scenario
            # get all starting scenarios that are in the name
            starting_scenarios = [scenario for scenario in self.starting_scenario_names if scenario in skill["name"]]
            # get the one that is longest (heuristic that the shorter ones are subset of longer ones)
            starting_scenario = max(starting_scenarios, key=len)

            # now put them into the skill
            skill["objective"] = objective
            skill["starting_inventory"] = inventory
            skill["starting_scenario"] = starting_scenario
        else:
            starting_scenario = "full_scratch"
            inventory = {}
            for item in skill["dependencies"]:
                item_split = item.split(":")
                name = item_split[0].replace("'", "").strip()
                quantity = item_split[1].replace("-", "").strip()
                quantity = int(quantity)
                if name in ["pipe", "transport-belt", "small-electric-pole"]:
                    # add a random number between 20 to 40
                    quantity += random.randint(20, 40)
                inventory[name] = quantity
            
            objective = self.postprocessor.generate_objective(skill)

            # now put them into the skill
            skill["objective"] = objective
            skill["starting_inventory"] = inventory
            skill["starting_scenario"] = starting_scenario
        return skill


    def get_skills_for_sft(self) -> List[Dict]:
        all_skills = self.skills_db.get_all_skills()
        # remove all skills where implementation starts with def test
        all_skills = [skill for skill in all_skills if not skill["implementation"].startswith("def test")]
        # use only skills where mart in version or version is 'v1.1'
        all_skills = [skill for skill in all_skills if "mart" in skill["version"] or skill["version"] == "v1.1"]
        return all_skills

    def skills_db_to_jsonl(self, skills: List[Dict], output_file: str) -> None:
        # check if the output file exists
        # if it does, raise an error
        if os.path.exists(output_file):
            raise ValueError("Output file already exists")

        with open(output_file, "w") as f:
            for skill in skills:
                f.write(json.dumps(skill) + "\n")

    def create_jsonl_dataset_from_db_skills(self, output_file: str, func_test_folder = None) -> None:
            all_skills = self.get_skills_for_sft()
            if func_test_folder:
                skills_from_func_tests = extract_skills_from_test(func_test_folder)
                all_skills += skills_from_func_tests
            
            self.skills_db_to_jsonl(all_skills, output_file)

    def get_game_trace_from_skill(self, skill: Dict, instance) -> Dict:
        implementation = skill["implementation"]
        implementation_steps = implementation.split("\n\n")
        # if we have a double """ start, remove the first one 
        buffer = []
        traces = []
        start = True
        instance.reset()
        instance.initial_inventory = skill["starting_inventory"]
        instance.reset()
        # here need to run the starting scenario as well
        starting_scenario = skill["starting_scenario"]
        starting_scenario_path = os.path.join(self.starting_scenario_folder, starting_scenario)
        # read in the starting_snippet.py
        with open(starting_scenario_path) as f:
            starting_scenario_code = f.read()

        _ = eval_program_with_result_trace(starting_scenario_code, instance)


        initial_mining_setup = get_mining_setup(instance)
        first_user_message = f"Your starting inventory is {skill['starting_inventory']}. Your initial mining setup is {initial_mining_setup}"
        traces.append({"role": "user", "content": first_user_message})
        for step_idx, implementation_step in enumerate(implementation_steps):
            implementation_step = implementation_step.strip("\n")
            if implementation_step == "from factorio_instance import *":
                continue
            if implementation_step.startswith('"""'):
                buffer.append(implementation_step)
                continue
            
            if len(buffer) > 0:
                if start:
                    buffer_str = buffer[-1]
                else:
                    buffer_str = "\n".join(buffer)
                implementation_step = buffer_str + "\n\n" + implementation_step
            
            # eval step
            output_list, result = eval_program_with_result_trace(implementation_step, instance)
            if "error" in result.lower():
                return {"success": False,"traces": [], "error_message": result}
            
            assistant_message = f"```python\n{implementation_step}\n```"
            if len(traces) == 1:
                assistant_message = f"I should do the following: {skill['objective']}\n\n First step to achieve the objective is \n\n{assistant_message}"
            if step_idx == len(implementation_steps) - 1:
                assistant_message = f"```python\n{implementation_step}\n```"
                assistant_message += f"\n\nI have achieved the objective: {skill['objective']}\n#COMPLETED"
                traces.append({"role": "assistant", "content": assistant_message})
                break

            traces.append({"role": "assistant", "content": assistant_message})
            user_message = f"Game logs: {output_list}\n\nGame result: {result}"
            traces.append({"role": "user", "content": user_message}) 
            buffer = []
            start = False
        return {"success": True, "traces": traces}
    
    def create_game_traces(self, input_file, success_output_file, fail_output_file):
        # read the skills from the input file
        with open(input_file) as f:
            skills = [json.loads(line) for line in f.readlines()]
        # load in the failed and successful traces
        if os.path.exists(success_output_file):
            with open(success_output_file) as f:
                successful_traces = [json.loads(line) for line in f.readlines()]
        else:
            successful_traces = []
            #create the file
            with open(success_output_file, "w") as f:
                pass

        if os.path.exists(fail_output_file):
            with open(fail_output_file) as f:
                failed_traces = [json.loads(line) for line in f.readlines()]
        else:
            failed_traces = []
            # create the file
            with open(fail_output_file, "w") as f:
                pass

        # create the game instance
        inventory = {}
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)
        successful_traces = []
        failed_traces = []
        for skill in skills:
            # check if the skill is already in the successful or failed traces
            for trace in successful_traces + failed_traces:
                if trace["name"] == skill["name"] and trace["implementation"] == skill["implementation"]:
                    continue
            trace_output = self.get_game_trace_from_skill(skill, instance)
            success = trace_output["success"]
            skill_trace = trace_output["traces"]
            if success:
                skill["trace"] = skill_trace
                with open(success_output_file, "a") as f:
                    f.write(json.dumps(skill) + "\n")
            else:
                skill["error_message"] = trace_output["error_message"]
                with open(fail_output_file, "a") as f:
                    f.write(json.dumps(skill) + "\n")
        
if __name__ == "__main__":
    starting_scenario_path = r"skills\data_scenarios\starting_scenarios"
    dataloader = SFTDatasetCreator(starting_scenario_path)
    raw_input_jsonl_file = r"datasets\sft_dataset_raw.jsonl"
    postprocessed_input_jsonl_file = r"datasets\sft_dataset_postprocessed.jsonl"
    successful_output_file = r"datasets\sft_successful_traces.jsonl"
    failed_output_file = r"datasets\sft_failed_traces.jsonl"
    #dataloader.create_jsonl_dataset_from_db_skills(output_jsonl_file)
    #dataloader.postprocess_skills(raw_input_jsonl_file, postprocessed_input_jsonl_file)
    dataloader.create_game_traces(postprocessed_input_jsonl_file, successful_output_file, failed_output_file)