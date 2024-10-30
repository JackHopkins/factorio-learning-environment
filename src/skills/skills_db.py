import psycopg2
from openai import OpenAI
from psycopg2.extras import Json
import openai
from typing import List, Dict, Union, Tuple
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
client = OpenAI()



class SkillsDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD")
        )
        
    def get_all_skills(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, implementation, description, signature FROM public.skills")

        return [{"name": row[0], "implementation": row[1], "description": row[2], "signature": row[3]} for row in cursor.fetchall()] 
    
    def delete_all_skills(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM public.skills")
        self.conn.commit()

    def save_function(self, name: str, implementation: str, description: str, dependencies: List[str], signature: str, implementation_model: str):
        cursor = self.conn.cursor()
        embedding = self.get_embedding(signature)
        cursor.execute("""
            INSERT INTO public.skills (name, implementation, description, embedding, dependencies, version, embedding_model, implementation_model, signature)
            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s)
        """, (name, implementation, description, embedding, dependencies, "v1.0", "text-embedding-3-small",
              implementation_model, signature))
        self.conn.commit()

    
    def get_embedding(self, text: str) -> List[float]:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    def find_similar_functions(self, query: str, n: int = 5) -> List[Dict]:
        cursor = self.conn.cursor()
        query_embedding = self.get_embedding(query)
        cursor.execute("""
            SELECT name, implementation, description, signature
            FROM public.skills
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (query_embedding, n))
        return [{"name": row[0], "implementation": row[1], "description": row[2], "signature": row[3]} for row in
                cursor.fetchall()]