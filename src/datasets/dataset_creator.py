import sys
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser\src")
sys.path.append(r"C:\Users\martb\Documents\paperpclip_max\PaperclipMaximiser")
import os
import ast
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from factorio_instance import FactorioInstance

load_dotenv()
from skills.skills_db import SkillsDB
def is_valid_python(code_string: str) -> bool:
    try:
        ast.parse(code_string)
        return True
    except SyntaxError:
        return False

class SFTDatasetCreator:
    def __init__(self):
        self.skills_db = SkillsDB()
    

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


        post_processed_skill_names = [skill["name"] for skill in post_processed_skills]
        for skill in skills:
            if skill["name"] not in post_processed_skill_names:
                skill = self.enchance_skill_with_attributes(skill)
            
            # save the skill to the output file
            with open(output_file, "a") as f:
                f.write(json.dumps(skill) + "\n")

    def enchance_skill_with_attributes(self, skill: Dict) -> Dict:
        # We need a objective, starting mining scenario and the starting inventory
        # everything that is over 30 sleeep, put to 30
        pass

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

    def create_jsonl_dataset_from_db_skills(self, output_file: str) -> None:
            all_skills = self.get_skills_for_sft()
            self.skills_db_to_jsonl(all_skills, output_file)
    def get_game_trace_from_skill(self, skill: Dict, instance) -> Dict:
        # We need a objective, starting mining setup and the starting inventory
        pass
    def create_game_traces(self, input_file, success_output_file, fail_output_file):
        # read the skills from the input file
        with open(input_file) as f:
            skills = [json.loads(line) for line in f.readlines()]
        
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
            success, skill_trace = self.get_game_trace_from_skill(skill, instance)
            if success:
                successful_traces.append(skill_trace)
            else:
                failed_traces.append(skill_trace)
        with open(success_output_file, "w") as f:
            for skill_trace in successful_traces:
                f.write(json.dumps(skill_trace) + "\n")
        with open(fail_output_file, "w") as f:
            for skill_trace in failed_traces:
                f.write(json.dumps(skill_trace) + "\n")

if __name__ == "__main__":

    dataloader = SFTDatasetCreator()
    output_jsonl_file = r"datasets\sft_dataset.jsonl"
    successful_output_file = r"datasets\sft_successful_traces.jsonl"
    failed_output_file = r"datasets\sft_failed_traces.jsonl"
    #dataloader.create_jsonl_dataset_from_db_skills(output_jsonl_file)
    #dataloader.create_game_traces(output_jsonl_file, successful_output_file, failed_output_file)