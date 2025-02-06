import re
import os
import ast
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from instance import FactorioInstance
import random
from skills.skill_postprocessor import SkillPostProcessor
from skills.bottoms_up_sampler import eval_program_with_result_trace, get_mining_setup
load_dotenv()
from skills.skills_db import SkillsDB
from skills.get_test_data import get_skills_from_func_tests
def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class SFTDatasetCreator:
    def __init__(self, starting_scenario_folder, finetuning_prompt_path):
        self.skills_db = SkillsDB()
        self.init_starting_scenarios(starting_scenario_folder)
        self.postprocessor = SkillPostProcessor()
        self.starting_scenario_folder = starting_scenario_folder
        self.finetuning_prompt_path = finetuning_prompt_path
    
    def init_starting_scenarios(self, starting_scenario_folder):
        # get all folder names in the starting scenario folder
        self.starting_scenario_names = os.listdir(starting_scenario_folder)

    def read_input_file(self, input_file) -> List[Dict]:
        with open(input_file) as f:
            skills = [json.loads(line) for line in f.readlines()]
        return skills
    
    def read_output_file(self, output_file) -> List[Dict]:
        if os.path.exists(output_file):
            with open(output_file) as f:
                skills = [json.loads(line) for line in f.readlines()]
        else:
            skills = []
        return skills

    def check_if_skill_exists(self, skill, existing_skills) -> bool:
        for existing_skill in existing_skills:
            if existing_skill["name"] == skill["name"] and existing_skill["implementation"] == skill["implementation"]:
                return True
        return False

    def postprocess_skills(self, input_file, output_file) -> Dict:
        # check if the output file exists
        post_processed_skills = self.read_output_file(input_file)
        # read in the skills from the input file
        skills = self.read_input_file(input_file)

        for skill_idx, skill in enumerate(skills):
            print(f"Processing skill {skill_idx}/{len(skills)}")
            exists = self.check_if_skill_exists(skill, post_processed_skills)
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

    def postprocess_skills_with_planning(self, input_file, output_file):
        # check if the output file exists
        post_processed_skills = self.read_output_file(output_file)
        # read in the skills from the input file
        skills = self.read_input_file(input_file)
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27000,
                                fast=True,
                                #cache_scripts=False,
                                inventory={})
        for skill_idx, skill in enumerate(skills):
            print(f"Processing skill {skill_idx}/{len(skills)}")
            exists = self.check_if_skill_exists(skill, post_processed_skills)
            if exists:
                continue
            if "mart" in skill["version"]:
                try:
                    skill = self.backfill_plan(skill, instance)
                except Exception as e:
                    print(f"Error in skill {skill['name']}: {e}")
                    continue
            ## save the skill to the output file
            with open(output_file, "a") as f:
                f.write(json.dumps(skill) + "\n")


    def backfill_plan(self, skill: Dict, instance) -> Dict:
        # We need a objective, starting mining scenario and the starting inventory
        # everything that is over 30 sleeep, put to 30
        if "meta" in skill and "objective" in skill["meta"] and "plan" in skill["meta"]["objective"] and skill["meta"]["objective"]["plan"]:
            skill["initial_plan"] = skill["meta"]["objective"]["plan"]
            return skill
        # get the initial mining setup
        initial_setup_result = self.get_initial_mining_setup(skill, instance) 
        if not initial_setup_result["success"]:
            raise ValueError(f"Error in getting initial mining setup: {initial_setup_result['error']}")

        plan = self.postprocessor.generate_planning(skill, initial_setup_result)
        skill["initial_plan"] = plan
        return skill

    def enchance_skill_with_attributes(self, skill: Dict) -> Dict:
        # We need a objective, starting mining scenario and the starting inventory
        # everything that is over 30 sleeep, put to 30
        if "mart" in skill["version"]:
            if "meta" in skill and skill["meta"]:
                skill["objective"] = skill["meta"]["objective"]["objective"]
                starting_inv = skill["meta"]["curriculum"]["starting_inventory"]
                #starting_inv = eval(skill["meta"]["curriculum"]["starting_inventory"])
                starting_scenario = skill["meta"]["curriculum"]["starting_scenario"]
                # now put them into the skill
                skill["starting_inventory"] = starting_inv
                skill["starting_scenario"] = starting_scenario
                del skill["meta"]["curriculum"]
                del skill["meta"]["objective"]["implementation_tries"]

            else:
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
                if isinstance(item, str):
                    item_split = item.split(":")
                    name = item_split[0].replace("'", "").strip()
                    quantity = item_split[1].replace("-", "").strip()
                    quantity = int(quantity)
                else:
                    name = item[0]
                    quantity = int(item[1])
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
        # if it does, we append to it
        if os.path.exists(output_file):
            # open the file and read in the lines
            with open(output_file) as f:
                existing_skills = f.readlines()
            # get the existing skills
            existing_skills = [json.loads(line) for line in existing_skills]
            # add the new skills to the existing skills
            skills_to_be_saved = []
            for skill in skills:
                exists = False
                for existing_skill in existing_skills:
                    if existing_skill["name"] == skill["name"] and existing_skill["implementation"] == skill["implementation"]:
                        exists = True
                        break
                if not exists:
                    skills_to_be_saved.append(skill)
            # append the new skills to the existing skills
            with open(output_file, "a") as f:
                for skill in skills_to_be_saved:
                    f.write(json.dumps(skill) + "\n")
        else:
            with open(output_file, "w") as f:
                for skill in skills:
                    f.write(json.dumps(skill) + "\n")

    def create_jsonl_dataset_from_db_skills(self, output_file: str, func_test_paths = None) -> None:
            all_skills = self.get_skills_for_sft()
            if func_test_paths:
                skills_from_func_tests = get_skills_from_func_tests(func_test_paths)
                all_skills += skills_from_func_tests
            
            self.skills_db_to_jsonl(all_skills, output_file)

    def try_to_fix_moving_closer_bugs(self, step, instance):
        position_regex = "position=(?:Position\(x=.*?\)|[a-zA-Z_][a-zA-Z0-9_]*(?:\[[0-9]+\])*)"
        new_steps = []
        # split the steps by \n
        lines = step.split("\n")
        for line in lines:
            if "place_entity" in line:
                stripped_line = line.replace(" ", "").strip()
                match = re.search(position_regex, stripped_line)
                if match:
                    print(f"Found: {match.group()}")
                    place_pos = match.group()
                    place_pos = place_pos.replace("position=", "")
                    prefix = line.split("place_entity")[0]
                    new_steps.append(f"# First move to where we want to place the entity\n{prefix}move_to({place_pos})")
        
            new_steps.append(line)
        new_step = "\n".join(new_steps)
        output_list, result = eval_program_with_result_trace(instance, new_step)
        return output_list, result, new_step


    def get_initial_mining_setup(self, skill, instance):
        instance.reset()
        instance.initial_inventory = skill["starting_inventory"]
        instance.reset()
        # here need to run the starting scenario as well
        starting_scenario = skill["starting_scenario"]
        starting_scenario_path = os.path.join(self.starting_scenario_folder, starting_scenario)
        # read in the starting_snippet.py
        with open(f"{starting_scenario_path}\starting_snippet.py") as f:
            starting_scenario_code = f.read()

        output_list, result = eval_program_with_result_trace(instance, starting_scenario_code)
        if "error" in result.lower():
            return {"success": False, "error": result}

        initial_mining_setup = get_mining_setup(instance)
        return {"success": True, "mining_setup": initial_mining_setup}
    
    def get_policy_from_skill(self, skill: Dict, instance) -> Dict:
        traces = []
        
        initial_setup_result = self.get_initial_mining_setup(skill, instance) 
        if not initial_setup_result["success"]:
            return {"success": False, "traces": [], "error_message": initial_setup_result["error"]}

        initial_mining_setup = initial_setup_result["mining_setup"]
        #first_user_message = f"Your starting inventory is {skill['starting_inventory']}. Your initial mining setup is: {initial_mining_setup}. Create a script to achieve the following objective: {skill['objective']}"
        first_user_message = f"Your starting inventory is {skill['starting_inventory']}. Your initial mining setup is: {initial_mining_setup}. Create a useful task that you can carry out in the current game and the python script to achieve the task"
        traces.append({"role": "system", "content": self.system_prompt})
        
        if "initial_plan" in skill:
            plan = "\n" + skill["initial_plan"] + "\n" if skill["initial_plan"] else "\n"
        else:
            plan = "\n"
        if plan != "\n":
            first_user_message += f"\nFirst bring out a thorough step-by-step plan how you can achieve this task and then create the python script to achieve the task."
        assistant_message = f"Sure! The task I will carry out is {skill['objective']}{plan}The policy to achieve this task is \n\n```python\n{skill['implementation']}\n```"
        traces.append({"role": "user", "content": first_user_message})
        traces.append({"role": "assistant", "content": assistant_message})
        return {"success": True, "traces": traces}


    def get_game_trace_from_skill(self, skill: Dict, instance) -> Dict:
        implementation = skill["implementation"]
        # get implementation steps
        implementation_steps_raw = implementation.split("\n\n")
        implementation_steps = []
        # we now need to merge all steps that start with an indentation to the previous step
        for step_idx,step in enumerate(implementation_steps_raw):
            if step.startswith('"""'):
                implementation_steps.append(step)
                continue
            if step.startswith("    "):
                implementation_steps[-1] += "\n" + step
            else:
                implementation_steps.append(step)


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
        with open(f"{starting_scenario_path}\starting_snippet.py") as f:
            starting_scenario_code = f.read()

        output_list, result = eval_program_with_result_trace(instance, starting_scenario_code)
        if "error" in result.lower():
            return {"success": False, "traces": [], "error_message": result}


        initial_mining_setup = get_mining_setup(instance)
        first_user_message = f"Your starting inventory is {skill['starting_inventory']}. Your initial mining setup is: {initial_mining_setup}"
        traces.append({"role": "system", "content": self.system_prompt})
        traces.append({"role": "user", "content": first_user_message})
        for step_idx, implementation_step in enumerate(implementation_steps):
            implementation_step = implementation_step.strip("\n")
            if implementation_step == "from factorio_instance import *":
                continue
            if implementation_step.strip().startswith('"""') and implementation_step.strip().endswith('"""'):
                buffer.append(implementation_step)
                continue
            
            if len(buffer) > 0:
                buffer_str = "\n".join(buffer)
                implementation_step = buffer_str + "\n\n" + implementation_step
            
            if "while " in implementation_step:
                return {"success": False, "traces": [], "error_message": "While loops are not allowed"}
            # eval step
            output_list, result = eval_program_with_result_trace(instance, implementation_step)
            if "error" in result.lower():
                if "Move closer." in result:
                    # try to fix the bug
                    output_list, result, implementation_step = self.try_to_fix_moving_closer_bugs(implementation_step, instance)
                    if "error" in result.lower():
                        return {"success": False, "traces": [], "error_message": result}
                else:
                    return {"success": False,"traces": [], "error_message": result}
            
            assistant_message = f"```python\n{implementation_step}\n```"
            if len(traces) == 1:
                assistant_message = f"I should do the following: {skill['objective']}\n\n First step to achieve the objective is \n\n{assistant_message}"

            traces.append({"role": "assistant", "content": assistant_message})
            user_message = f"Game logs: {output_list}\n\nGame result: {result}"
            traces.append({"role": "user", "content": user_message}) 
            buffer = []
            start = False
        final_message = f"I have achieved the objective: {skill['objective']}\n#COMPLETED"
        traces.append({"role": "assistant", "content": final_message})
        return {"success": True, "traces": traces}
    def init_system_prompt(self, instance):
        api_description = instance.get_system_prompt()
        system_prompt_path = self.finetuning_prompt_path
        # read in the system prompt
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
        self.system_prompt = system_prompt.format(schema=api_description)
        # change all " marks to '
        self.system_prompt.replace('"', "'")
        
    def create_game_traces(self, input_file, success_output_file, 
                           fail_output_file, full_policy = False):
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
                                tcp_port=27000,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)
        self.init_system_prompt(instance)
        for skill in skills:
            exists = False
            # check if the skill is already in the successful or failed traces
            for trace in successful_traces + failed_traces:
                if trace["name"] == skill["name"] and trace["implementation"] == skill["implementation"]:
                    exists = True
                    break
            if exists:
                continue
            if full_policy:
                trace_output = self.get_policy_from_skill(skill, instance)
            else:
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

    def get_skill_from_nb_skills(self, implementation, curriculum_item, override_plan = False):
        objective = curriculum_item["objective"]
        version = "mart_nb"
        description =""
        signature = ""
        plan = curriculum_item["full_plan"]
        plan = plan.replace("\n\n", "\n")
        plan = plan.replace("Plan Analysis:\n", "")
        # remove import from implementation
        implementation = implementation.replace("\n###SEP", "")
        implementation = implementation.replace("\n#Step Execution", "")
        starting_inventory = curriculum_item["starting_inventory"]
        scenario_starting_inv = curriculum_item["scenario_starting_inv"]
        if len(starting_inventory) == 0:
            for item, value in scenario_starting_inv.items():
                if item not in starting_inventory:
                    starting_inventory[item] = 0
                starting_inventory[item] += value
        
        dependencies = [f"'{item}': {value}" for item, value in starting_inventory.items()]
        meta = {"curriculum": curriculum_item, "objective": {"objective": objective, "plan": plan, "implementation_tries": 0}}
        return {"name": curriculum_item["name"], "implementation": implementation, "description": description, 
                "signature": signature, "dependencies": dependencies, "version": version, "starting_inventory": starting_inventory, "objective": objective,
                "starting_scenario": curriculum_item["starting_scenario"], "meta": meta, "initial_plan": plan}



    def get_traces_from_notebook_skills(self, nb_skill_folder, output_file, full_policy = False, override_plan  = False):
        # open the output file to get existing successful traces
        with open(output_file) as f:
            successful_traces = [json.loads(line) for line in f.readlines()]
        # create the game instance
        inventory = {}
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27000,
                                fast=True,
                                #cache_scripts=False,
                                inventory=inventory)
        self.init_system_prompt(instance)
        # get folders in nb_skill_folder
        objective_groups = os.listdir(nb_skill_folder)
        for objective_group in objective_groups:
            objective_group_path = os.path.join(nb_skill_folder, objective_group)
            starting_scenarios = os.listdir(objective_group_path)
            for starting_scenario in starting_scenarios:
                starting_scenario_path = os.path.join(objective_group_path, starting_scenario)
                for skill in os.listdir(starting_scenario_path):
                    if skill.startswith("_"):
                        continue
                    # raed in curriculumt_item.json
                    with open(os.path.join(starting_scenario_path, skill, "curriculum_item.json")) as f:
                        skill_data = json.load(f)
                    # read in full_sniippet.py
                    with open(os.path.join(starting_scenario_path, skill, "full_snippet.py")) as f:
                        full_snippet = f.read()

                    skill = self.get_skill_from_nb_skills(full_snippet, skill_data, override_plan = override_plan)
                    exists = False
                    for trace in successful_traces:
                        if trace["name"] == skill["name"] and trace["implementation"] == skill["implementation"]:
                            exists = True
                            break
                    if exists:
                        continue
                    if full_policy:
                        trace_output = self.get_policy_from_skill(skill, instance)
                    else:
                        trace_output = self.get_game_trace_from_skill(skill, instance)
                    success = trace_output["success"]
                    skill_trace = trace_output["traces"]
                    if success:
                        skill["trace"] = skill_trace
                        with open(output_file, "a") as f:
                            f.write(json.dumps(skill) + "\n")
                    else:
                        raise ValueError(f"Error in {objective_group} {starting_scenario} skill {skill['name']}: {trace_output['error_message']}")

    def create_training_eval_dataset(self, full_dataset_path, training_dataset_path, eval_dataset_path, training_ratio=1):
        with open(full_dataset_path) as f:
            all_skills = [json.loads(line) for line in f.readlines()]
        random.shuffle(all_skills)
        training_skills = all_skills[:int(len(all_skills) * training_ratio)]
        eval_skills = all_skills[int(len(all_skills) * training_ratio):]
        training_skills = [{"messages": skill["trace"]} for skill in training_skills]
        eval_skills = [{"messages": skill["trace"]} for skill in eval_skills]
        with open(training_dataset_path, "w") as f:
            for skill in training_skills:
                f.write(json.dumps(skill) + "\n")
        with open(eval_dataset_path, "w") as f:
            for skill in eval_skills:
                f.write(json.dumps(skill) + "\n")

    def add_system_prompt(self, file):
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27000,
                                fast=True,
                                #cache_scripts=False,
                                inventory={})
        self.init_system_prompt(instance)
        with open(file) as f:
            skills = [json.loads(line) for line in f.readlines()]
        system_prompt_message = {"role": "system", "content": self.system_prompt}
        for skill in skills:
            skill["messages"].insert(0, system_prompt_message)

        # save the skills to file
        with open(file, "w") as f:
            for skill in skills:
                f.write(json.dumps(skill) + "\n")

if __name__ == "__main__":
    starting_scenario_path = r"skills\data_scenarios\starting_scenarios"
    dataloader = SFTDatasetCreator(starting_scenario_path,
                                   #finetuning_prompt_path = r"prompts\bottoms_up_prompts\finetuning_prompts\system_message_policy.md",
                                   finetuning_prompt_path = r"prompts\bottoms_up_prompts\finetuning_prompts\system_message_policy_self_gen.md",
                                   )
    notebook_skill_path = r"datasets/notebook_skills"
    raw_input_jsonl_file = r"datasets\sft_dataset_raw.jsonl"
    postprocessed_input_jsonl_file = r"datasets\sft_dataset_postprocessed.jsonl"
    postprocessed_input_jsonl_file_planning_backfilled = r"datasets\sft_dataset_postprocessed_planning.jsonl"
    successful_output_file = r"datasets\sft_successful_traces.jsonl"
    failed_output_file = r"datasets\sft_failed_traces.jsonl"
    training_dataset_path = r"datasets\sft_training_dataset.jsonl"
    eval_dataset_path = r"datasets\sft_eval_dataset.jsonl"
    successful_output_file_policy = r"datasets\sft_successful_traces_policy_self_gen_v2.jsonl"
    failed_output_file_policy = r"datasets\sft_failed_traces_policy_self_gen_v2.jsonl"
    training_dataset_path_policy = r"datasets\sft_training_dataset_policy_self_gen_v2.jsonl"
    eval_dataset_path_policy = r"datasets\sft_eval_dataset_policy_self_gen.jsonl"
    func_test_paths = [r"tests\functional", r"tests\connect\test_connect_pipes.py",
                       r"tests\connect\test_connect_poles.py",
                       r"tests\connect\test_connect_transport_belts.py",
                       r"tests\connect\test_connect_walls.py"]
    #dataloader.create_jsonl_dataset_from_db_skills(raw_input_jsonl_file,  [])
    #dataloader.postprocess_skills(raw_input_jsonl_file, postprocessed_input_jsonl_file)
    dataloader.create_game_traces(postprocessed_input_jsonl_file_planning_backfilled, successful_output_file_policy, failed_output_file_policy, full_policy = True)
    #dataloader.get_traces_from_notebook_skills(notebook_skill_path, successful_output_file_policy, full_policy=True)
    dataloader.create_training_eval_dataset(successful_output_file_policy, training_dataset_path_policy, eval_dataset_path_policy)
    #dataloader.add_system_prompt(training_dataset_path)
    #dataloader.add_system_prompt(eval_dataset_path)