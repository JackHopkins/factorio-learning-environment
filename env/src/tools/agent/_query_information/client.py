from time import sleep
from tools.tool import Tool
import os
# import PATH to construct dynamic paths
import sys
from pathlib import Path
class QueryInformation(Tool):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        # get the location of this file
        root_directory = os.path.dirname(os.path.abspath(__file__))
        self.pages_path = Path(root_directory, 'pages')
        # get all md files in the pages directory
        self.pages = [page.replace(".md", "") for page in os.listdir(self.pages_path) if page.endswith('.md')]
    def __call__(self,
                 page_id: str
                 ) -> str:
        """
        Get the information of a page from the database
        :param page_id: The id of the page
        :return: The content of the page
        """
        assert isinstance(page_id, str), f"First argument must be a Position object"
        assert page_id in self.pages, f"Page {page_id} not found. Existing pages are {self.pages}"

        # read the content of the page
        with open(Path(self.pages_path, page_id + ".md"), 'r') as file:
            content = file.read()
        return content.strip()