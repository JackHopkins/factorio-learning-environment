from typing import Tuple

import numpy as np


def get_position() -> Tuple[int, int]:
    """
    :return: The position of the agent
    """
    pass

def get_mini_map(distance=500):
    """
    Retrieve and downsample broader map
    :param distance: Distance from the player to retrieve the map.
    :return:
    """
    pass


def get_local_map(distance=100):
    """

    :param distance: Distance from the player to retrieve the map.
    :return:
    """
    pass

def get_inventory() -> np.array:
    """
    :return: The set of items in the inventory
    """
    pass

def get_resources(local=True) -> np.array:
    """

    :param local: Whether to include all extracted resources on the map,
    or only include those in the inventory
    :return:
    """
    pass

