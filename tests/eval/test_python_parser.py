import pytest
from typing import NamedTuple
from fle.agents.llm.parsing import PythonParser


class MockMessage(NamedTuple):
    content: str


class MockLLMResponse(NamedTuple):
    """Mock LLM response object for testing"""

    message: MockMessage


class TestPythonParser:
    def test_single_valid_python_block(self):
        """Test that a single block of valid Python code is returned unchanged"""
        code = """
x = 1
y = 2
print(x + y)
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(code)))
        assert result.strip() == code.strip()

    def test_mixed_content_with_explanation(self):
        """Test handling of mixed content with explanation and code"""
        content = """
Let's create a loop to process items

for i in range(10):
    print(i)

This will print numbers 0-9
"""
        expected = """# Let's create a loop to process items

for i in range(10):
    print(i)

# This will print numbers 0-9"""

        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert result.strip() == expected.strip()

    def test_complex_pipe_example_1(self):
        """Test the first complex pipe placement example"""
        content = """The repeated attempts to place pipes indicate that the terrain or path chosen is not suitable for pipe placement. Let's try a different approach by moving further away from the current path and using a combination of underground and regular pipes to bypass any potential obstacles.

# Define positions for offshore pump and boiler
offshore_pump_position = Position(x=-11.5, y=26.5)
boiler_position = Position(x=-3.5, y=26.0)

# Move to offshore pump position
move_to(offshore_pump_position)

# Inspect and clear obstructions manually along a new path, slightly above the previous attempt
pipe_path_positions = [Position(x=i, y=28.5) for i in range(-11, -3)]
for pos in pipe_path_positions:
    move_to(pos)
    entities = get_entities(position=pos, radius=0.5)
    print(f"Entities at {pos}: {entities}")
    for entity in entities:
        if not isinstance(entity, Pipe):
            pickup_entity(entity)
            print(f"Cleared obstruction at {entity.position}.")"""

        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "# The repeated attempts" in result
        assert "offshore_pump_position = Position(x=-11.5, y=26.5)" in result
        assert (
            "pipe_path_positions = [Position(x=i, y=28.5) for i in range(-11, -3)]"
            in result
        )

    def test_complex_pipe_example_2(self):
        """Test the second complex pipe placement example"""
        content = """The current approach of trying to place pipes at various y-coordinates has not been successful. Let's try a different strategy by placing the pipes directly from the offshore pump to the boiler without skipping positions, ensuring that we use both underground and regular pipes where necessary.

# Define positions for offshore pump and boiler
offshore_pump_position = Position(x=-11.5, y=26.5)
boiler_position = Position(x=-3.5, y=26.0)

# Move to offshore pump position
move_to(offshore_pump_position)"""

        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "# The current approach" in result
        assert "offshore_pump_position = Position(x=-11.5, y=26.5)" in result
        assert "move_to(offshore_pump_position)" in result

    def test_empty_content(self):
        """Test handling of empty content"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage("")))
        assert not result

    def test_only_comments(self):
        """Test handling of content that contains only comments"""
        content = """
This is just some text
with multiple lines
but no actual code
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert result.startswith('"""') or result.startswith("#")

    def test_invalid_python(self):
        """Test handling of invalid Python syntax"""
        content = """
for i in range(10)    # Missing colon
    print(i)
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert result.startswith('"""') or result.startswith("#")

    def test_markdown_code_blocks(self):
        """Test handling of markdown code blocks"""
        content = """
Here's some explanation

```python
x = 1
y = 2
print(x + y)
```

More explanation here
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "x = 1" in result

    def test_mixed_valid_invalid_blocks(self):
        """Test handling of mixed valid and invalid Python blocks"""
        content = """
def valid_function():
    return 42

This is some invalid content

x = 1
y = 2
print(x + y)
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "def valid_function():" in result
        assert "return 42" in result
        assert "# This is some invalid content" in result
        assert "x = 1" in result

    def test_indentation_preservation(self):
        """Test that indentation is preserved in valid Python blocks"""
        content = """
def nested_function():
    if True:
        for i in range(10):
            print(i)
            if i % 2 == 0:
                print('even')
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "            print(i)" in result
        assert "                print('even')" in result

    def test_multiline_string_preservation(self):
        """Test that multiline strings in valid Python are preserved"""
        content = '''
text = """
This is a
multiline string
in valid Python
"""
print(text)
'''
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert 'text = """' in result
        assert "multiline string" in result

    def test_mixed_comments_and_code(self):
        """Test handling of mixed inline comments and code"""
        content = """
# This is a comment
x = 1  # Inline comment
# Another comment
y = 2
"""
        result, _ = PythonParser.extract_code(MockLLMResponse(MockMessage(content)))
        assert "# This is a comment" in result
        assert "x = 1  # Inline comment" in result
        assert "# Another comment" in result
        assert "y = 2" in result


if __name__ == "__main__":
    pytest.main([__file__])
