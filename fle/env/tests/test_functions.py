import pytest
from time import sleep
from env.src.entities import Position, ResourcePatch
from env.src.instance import Direction
from env.src.game_types import Prototype, Resource


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
    _, _, result = game.instance.eval(functions)

    assert result == 'Error: invalid syntax (<unknown>, line 4):     assert 1 = 2'

def test_assertion_exception(game):
    functions = \
"""
def func_1(arg1: Dict) -> str:
    \"\"\"this is a func\"\"\"
    print("a")
    assert 1 == 2

def func_2():
    func_1({})

func_2()
"""
    _, _, result = game.instance.eval(functions)

    funcs = game.get_functions()

    description = "# Your utility functions" + "\n\n".join([str(f) for f in funcs])

    assert result == '0: mart'

def test_function_with_entity_annotation(game):
    functions = \
"""
def func_1(arg1: Entity) -> str:
    \"\"\"this is a func\"\"\"
    print("a")
    assert 1 == 2

def func_2():
    func_1({})

func_2()
"""
    _, _, result = game.instance.eval(functions)

    assert result == '0: mart'