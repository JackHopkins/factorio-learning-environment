"""Tests that print() statements inside agent-defined functions are captured in STDOUT.

These tests verify that when an agent defines a function and calls it, any print()
calls within that function appear in the result output returned by instance.eval().
"""


class TestPrintInTopLevelFunction:
    """Print inside a simple function defined and called at top level."""

    def test_print_in_simple_function(self, instance):
        """Basic case: def foo(): print('hello') then foo()"""
        _, _, result = instance.eval('def foo():\n    print("hello from foo")\n\nfoo()')
        assert "hello from foo" in result

    def test_print_in_function_with_loop(self, instance):
        """Print inside a for loop inside a function."""
        _, _, result = instance.eval(
            'def count():\n    for i in range(3):\n        print(f"item {i}")\n\ncount()'
        )
        assert "item 0" in result
        assert "item 1" in result
        assert "item 2" in result

    def test_print_in_function_with_conditional(self, instance):
        """Print inside if/else inside a function."""
        _, _, result = instance.eval(
            'def check():\n    x = 5\n    if x > 3:\n        print("big")\n    else:\n        print("small")\n\ncheck()'
        )
        assert "big" in result

    def test_multiple_prints_in_function(self, instance):
        """Multiple print statements in sequence inside a function."""
        _, _, result = instance.eval(
            'def steps():\n    print("step 1")\n    print("step 2")\n    print("step 3")\n\nsteps()'
        )
        assert "step 1" in result
        assert "step 2" in result
        assert "step 3" in result


class TestPrintInNestedFunctions:
    """Print inside nested function definitions (function defined inside function)."""

    def test_print_in_inner_function(self, instance):
        """Inner function with print, called by outer function."""
        code = (
            "def outer():\n"
            "    def inner():\n"
            '        print("from inner")\n'
            "    inner()\n"
            '    print("from outer")\n'
            "\n"
            "outer()"
        )
        _, _, result = instance.eval(code)
        assert "from inner" in result
        assert "from outer" in result

    def test_print_in_helper_wrapper(self, instance):
        """Pattern commonly used by agents: define a log/safe wrapper with print."""
        code = (
            "def my_task():\n"
            "    def log(msg):\n"
            "        print(str(msg))\n"
            '    log("starting task")\n'
            '    log("task complete")\n'
            "\n"
            "my_task()"
        )
        _, _, result = instance.eval(code)
        assert "starting task" in result
        assert "task complete" in result


class TestPrintInTryExcept:
    """Print inside try/except blocks inside functions."""

    def test_print_in_try_block(self, instance):
        """Print inside a try block inside a function."""
        code = (
            "def safe_op():\n"
            "    try:\n"
            '        print("in try")\n'
            "    except Exception as e:\n"
            '        print(f"error: {e}")\n'
            "\n"
            "safe_op()"
        )
        _, _, result = instance.eval(code)
        assert "in try" in result

    def test_print_in_except_block(self, instance):
        """Print inside an except block inside a function."""
        code = (
            "def safe_op():\n"
            "    try:\n"
            "        x = 1 / 0\n"
            "    except Exception as e:\n"
            '        print(f"caught: {e}")\n'
            "\n"
            "safe_op()"
        )
        _, _, result = instance.eval(code)
        assert "caught:" in result


class TestPrintInSafeWrapper:
    """Reproduction of the real agent pattern: safe() wrapper with print-based logging."""

    def test_agent_safe_pattern(self, instance):
        """Real-world pattern: agent defines safe() and log() wrappers, calls tools."""
        code = (
            "def do_work():\n"
            "    def log(msg):\n"
            "        print(str(msg))\n"
            "\n"
            "    def safe(fn, *args, name=None, default=None, **kwargs):\n"
            "        try:\n"
            "            return fn(*args, **kwargs)\n"
            "        except Exception as e:\n"
            '            log(f"ERROR {name}: {e}")\n'
            "            return default\n"
            "\n"
            '    log("=== START ===")\n'
            '    inv = safe(inspect_inventory, name="inspect_inventory", default={})\n'
            '    log(f"Inventory: {inv}")\n'
            '    log("=== DONE ===")\n'
            "\n"
            "do_work()"
        )
        _, _, result = instance.eval(code)
        assert "=== START ===" in result
        assert "Inventory:" in result
        assert "=== DONE ===" in result

    def test_agent_safe_pattern_with_error(self, instance):
        """Agent's safe() wrapper catches error and prints it."""
        code = (
            "def do_work():\n"
            "    def log(msg):\n"
            "        print(str(msg))\n"
            "\n"
            "    def safe(fn, *args, name=None, default=None, **kwargs):\n"
            "        try:\n"
            "            return fn(*args, **kwargs)\n"
            "        except Exception as e:\n"
            '            log(f"ERROR calling {name}: {e}")\n'
            "            return default\n"
            "\n"
            '    log("start")\n'
            '    result = safe(lambda: 1/0, name="divide", default=None)\n'
            '    log(f"result={result}")\n'
            "\n"
            "do_work()"
        )
        _, _, result = instance.eval(code)
        assert "start" in result
        assert "ERROR calling divide" in result
        assert "result=None" in result


class TestPrintInFunctionCalledMultipleTimes:
    """Functions called multiple times should capture prints each time."""

    def test_function_called_twice(self, instance):
        """Prints from both invocations should appear."""
        code = (
            "def greet(name):\n"
            '    print(f"hello {name}")\n'
            "\n"
            'greet("alice")\n'
            'greet("bob")'
        )
        _, _, result = instance.eval(code)
        assert "hello alice" in result
        assert "hello bob" in result

    def test_persistent_function_across_evals(self, instance):
        """Function defined in one eval, called in the next, should still capture prints."""
        instance.eval('def say(x):\n    print(f"saying: {x}")')
        _, _, result = instance.eval('say("works")')
        assert "saying: works" in result
