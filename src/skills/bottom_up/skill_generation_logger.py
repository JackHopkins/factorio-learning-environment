import ast
import os
import random
import textwrap
from datetime import datetime
from typing import List, Dict, Tuple

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from utilities.controller_loader import load_schema, load_definitions, load_controller_names


class SkillGenerationLogger:
    def __init__(self, log_dir="skill_generation_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"skill_generation_{timestamp}.txt")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")

    def log_separator(self):
        with open(self.log_file, 'a') as f:
            f.write("\n" + "=" * 80 + "\n\n")