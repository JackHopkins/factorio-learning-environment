import unittest
import ast
from dataclasses import dataclass
from typing import List, Optional

from datasetgen.mcts.chunked_mcts import ChunkedMCTS
from datasetgen.mcts.game_state import GameState
from factorio_instance import FactorioInstance


class TestSaveLoadPythonNamespace(unittest.TestCase):
    """
    FactorioInstance exposes a Python namespace for the agent to persist variables.
    These tests verify that the namespace can be saved and loaded correctly into new instances.
    """
    def setUp(self):
        self.instance = FactorioInstance(address='localhost',
                           bounding_box=200,
                           tcp_port=27015,
                           fast=True,
                           inventory={})

    def test_save_load_namespace(self):
        self.instance.eval('x=2')
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(address='localhost',
                                         bounding_box=200,
                                         tcp_port=27015,
                                         fast=True,
                                         inventory={})

        self.instance.reset(game_state)
        self.instance.eval('assert x == 2')


if __name__ == '__main__':
    unittest.main()