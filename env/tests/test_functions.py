import pytest
from time import sleep
from entities import Position, ResourcePatch
from instance import Direction
from game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace

def test_syntax_error(game):
    functions = \
"""
def func_1(arg):
    print("a")
    assert 1 = 2

func_1(6)
"""
    _, _, result = game.eval(functions)

    assert result == 'Error: invalid syntax (<unknown>, line 4):     assert 1 = 2'

def test_assertion_exception(game):
    functions = \
"""
def func_1():
    print("a")
    assert 1 == 2

def func_2():
    func_1()

func_2()
"""
    _, _, result = game.eval(functions)

    assert result == '0: mart'
