import base64
import json
import zlib
from typing import Union, List, Dict

from fle.env.tools import Tool


class LoadEntityState(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, entities: Union[str, List[Dict]], decompress=False) -> bool:
        """
        Loads the entity state back into the game.
        :param entities: Either a list of un-serialized dictionaries or a string containing Base64 encoded JSON data representing the entities to load.
        :return: True if successful, False otherwise
        """

        if isinstance(entities, str):
            entities = base64.b64decode(entities)
            if decompress:
                entities = zlib.decompress(entities)
        else:
            entities = json.dumps(entities)

        result, _ = self.execute(self.player_index, entities)

        return result
