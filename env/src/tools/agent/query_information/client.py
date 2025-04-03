from time import sleep
from tools.tool import Tool
import os
# import PATH to construct dynamic paths
import sys
from pathlib import Path
import json
import numpy as np

from openai import OpenAI

class QueryInformation(Tool):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        # get the location of this file
        root_directory = os.path.dirname(os.path.abspath(__file__))
        self.pages_path = Path(root_directory, 'pages')
        # get all md files in the pages directory
        self.pages = [page.replace(".md", "") for page in os.listdir(self.pages_path) if page.endswith('.md')]
        # read inthe embeddings.json file
        self.embeddings_path = Path(root_directory, 'embeddings.json')
        with open(self.embeddings_path, 'r') as file:
            self.embeddings = json.load(file)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        for page in self.pages:
            if page not in self.embeddings:
                # get the embeddings for the page
                with open(Path(self.pages_path, page + ".md"), 'r') as file:
                    content = file.read()
                self.embeddings[page] = self.get_embeddings(content)
        try:
            # overwrite the embeddings file
            with open(self.embeddings_path, 'w') as file:
                json.dump(self.embeddings, file, indent=4)
        except Exception as e:
            print(f"Error writing to embeddings file: {e}")


    def cosine_similarity(self, a: list, b: list) -> float:
        """
        Calculate the cosine similarity between two vectors
        :param a: The first vector
        :param b: The second vector
        :return: The cosine similarity between the two vectors
        """
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def __call__(self,
                 query: str,
                 nr_of_results: int = 2,
                 ) -> str:
        """
        retrieve closest pages to the query and return their content
        :param query: The query to search for
        :param nr_of_results: The number of results to return
        :return: The content of the pages
        """
        
        # get the embeddings for the query
        query_embedding = self.get_embeddings(query)
        # get the closest pages to the query
        closest_pages = []
        for page, embedding in self.embeddings.items():
            similarity = self.cosine_similarity(query_embedding, embedding)
            closest_pages.append((page, similarity))
        # sort the pages by similarity
        closest_pages = sorted(closest_pages, key=lambda x: x[1], reverse=True)
        # get the content of the closest pages
        content = f"QUERY RESULTS FOR - {query}:\n\n"
        for page, _ in closest_pages[:nr_of_results]:
            with open(Path(self.pages_path, page + ".md"), 'r') as file:
                content += file.read() + "\n\n"
        
        return content.strip()
    
    def get_embeddings(self, text: str) -> list:
        """
        Get the embeddings of a text
        :param text: The text to get the embeddings for
        :return: The embeddings of the text
        """
        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_model
        )
        return response.data[0].embedding