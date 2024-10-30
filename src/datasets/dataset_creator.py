import ast
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

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
    
    def get_skills_for_sft(self) -> List[Dict]:
        all_skills = self.skills_db.get_all_skills()
        # remove all skills where implementation starts with def test
        all_skills = [skill for skill in all_skills if not skill["implementation"].startswith("def test")]
        return all_skills

    def skills_db_to_jsonl(self, skills: List[Dict], output_file: str) -> None:
        with open(output_file, "w") as f:
            for skill in skills:
                f.write(json.dumps(skill) + "\n")

    def create_jsonl_dataset_from_db_skills(self, output_file: str) -> None:
            all_skills = self.get_skills_for_sft()
            self.skills_db_to_jsonl(all_skills, output_file)


if __name__ == "__main__":

    dataloader = SFTDatasetCreator()
    output_jsonl_file = r"datasets\sft_dataset.jsonl"
    dataloader.create_jsonl_dataset_from_db_skills(output_jsonl_file)