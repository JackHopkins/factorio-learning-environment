import unittest

from fle.agents.llm.parsing import PythonParser


class TestChunkBasedPythonParser(unittest.TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_valid_python_chunks(self):
        """Test handling of valid Python code chunks."""
        test_content = """print("Hello")

x = 5
y = 10
print(x + y)

def test_func():
    return 42"""

        class MockResponse:
            def __init__(self, content):
                self.message = type("Message", (), {"content": content})

        result = self.parser.extract_code(MockResponse(test_content))
        self.assertIsNotNone(result)
        code, original = result

        # Should preserve valid Python chunks as-is
        self.assertIn('print("Hello")', code)
        self.assertIn("x = 5", code)
        self.assertIn("def test_func():", code)

        # Verify the result is valid Python
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            self.fail("Resulting code is not valid Python")

    def test_markdown_chunks(self):
        """Test handling of markdown-style documentation chunks."""
        test_content = """# Step 1: Initialize variables

x = 5
y = 10

## Processing steps:
1. Add numbers
2. Print result

result = x + y
print(result)"""

        class MockResponse:
            def __init__(self, content):
                self.message = type("Message", (), {"content": content})

        result = self.parser.extract_code(MockResponse(test_content))
        self.assertIsNotNone(result)
        code, original = result

        # Verify markdown sections are wrapped in docstrings
        self.assertIn('"""', code)
        self.assertIn("# Step 1:", code)

        # Verify code sections remain unwrapped
        self.assertIn("x = 5", code)
        self.assertIn("result = x + y", code)

        # Check overall validity
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            self.fail("Resulting code is not valid Python")

    def test_mixed_content(self):
        """Test handling of mixed markdown and code content."""
        test_content = """# First we need to check inventory

current_inventory = inspect_inventory()
required_stone = 5

## Next steps:
* Get more resources
* Build furnace

if current_inventory["stone"] < required_stone:
    gather_stone()"""

        class MockResponse:
            def __init__(self, content):
                self.message = type("Message", (), {"content": content})

        result = self.parser.extract_code(MockResponse(test_content))
        self.assertIsNotNone(result)
        code, original = result

        # Verify structure
        code_lines = code.split("\n")
        docstring_count = sum(1 for line in code_lines if '"""' in line)
        self.assertEqual(docstring_count % 2, 0, "Unmatched docstring delimiters")

        # Verify code validity
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            self.fail("Resulting code is not valid Python")

    def test_empty_chunks(self):
        """Test handling of empty chunks and whitespace."""
        test_content = """

print("First")


print("Second")

"""

        class MockResponse:
            def __init__(self, content):
                self.message = type("Message", (), {"content": content})

        result = self.parser.extract_code(MockResponse(test_content))
        self.assertIsNotNone(result)
        code, original = result

        # Verify empty chunks are handled correctly
        self.assertIn('print("First")', code)
        self.assertIn('print("Second")', code)

        # Verify no empty docstrings
        self.assertNotIn('"""\n"""', code)

        # Check overall validity
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            self.fail("Resulting code is not valid Python")

    def test_code_block_markers(self):
        """Test handling of markdown code block markers."""
        test_content = """Some explanation here

```python
def test_func():
    return 42
```

More explanation

```
x = 5
print(x)
```"""

        class MockResponse:
            def __init__(self, content):
                self.message = type("Message", (), {"content": content})

        result = self.parser.extract_code(MockResponse(test_content))
        self.assertIsNotNone(result)
        code, original = result

        # Verify code blocks are extracted without markers
        self.assertIn("def test_func():", code)
        self.assertIn("x = 5", code)
        self.assertNotIn("```", code)

        # Verify explanatory text is wrapped in docstrings
        self.assertIn('"""Some explanation here"""', code.replace("\n", ""))

        # Check overall validity
        import ast

        try:
            ast.parse(code)
        except SyntaxError:
            self.fail("Resulting code is not valid Python")


if __name__ == "__main__":
    unittest.main()
