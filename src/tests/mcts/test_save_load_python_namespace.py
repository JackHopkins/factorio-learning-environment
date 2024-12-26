import unittest

from search.mcts.model.game_state import GameState
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
                           inventory={'boiler': 1})

    def test_save_load_simple_variable_namespace(self):
        self.instance.eval('x=2')
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(address='localhost',
                                         bounding_box=200,
                                         tcp_port=27015,
                                         fast=True,
                                         inventory={})

        self.instance.reset(game_state)
        self.instance.eval('assert x == 2')

    def test_save_load_simple_variable_namespace(self):
        resp = self.instance.eval('boiler = place_entity(Prototype.Boiler, Direction.UP, Position(x=0, y=0))')
        game_state = GameState.from_instance(self.instance)

        self.instance = FactorioInstance(address='localhost',
                                         bounding_box=200,
                                         tcp_port=27015,
                                         fast=True,
                                         inventory={})
        self.instance.reset()
        self.instance.reset(game_state)
        self.instance.eval('assert boiler')
        resp2 = self.instance.eval('print(boiler)')
        assert 'error' not in resp2


if __name__ == '__main__':
    unittest.main()