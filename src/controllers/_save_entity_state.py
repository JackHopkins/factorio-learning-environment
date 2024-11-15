import base64
import json
import zlib
from typing import Dict, List, Union

from controllers.__action import Action
from factorio_instance import PLAYER


class SaveEntityState(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 distance=100,
                 player_entities=True,
                 resource_entities=False,
                 encode=False,
                 compress=False,
                 ) -> Union[List[Dict], str]:
        """
        Saves the current player entities on the map into a blueprint string
        :arg: distance: Distance around the player to search for entities. Default is 100 tiles.
        :arg: player_entities: Whether or not to include player entities in the blueprint. Default is True.
        :arg: resource_entities: Whether or not to include resource entities in the blueprint. Default is False.
            Note: This is enormously expensive!
        :arg: encode: Whether or not to encode the blueprint string. Default is False.
        :arg: compress: Whether or not to compress the blueprint string before encoding it. Default is False.
            Note: Perform encoding and compression if we are sending this over a network.
        :return: Blueprint and offset to blueprint from the origin.
        """
        entities, _ = self.execute(PLAYER, distance, player_entities, resource_entities)

        if encode:
            encoded_string = json.dumps(entities).encode()
            if compress:
                encoded_string = zlib.compress(encoded_string)

            return base64.b64encode(encoded_string).decode()

        return entities
