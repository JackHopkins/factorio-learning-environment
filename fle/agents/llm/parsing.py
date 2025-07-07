import ast
import re
from typing import Optional, Tuple

from pydantic import BaseModel

from fle.commons.models.conversation import Conversation


class Python(str):
    """A custom type that only accepts syntactically valid Python code."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, values=None, config=None, field=None) -> str:
        if not isinstance(value, str):
            raise TypeError("string required")

        try:
            # Try to parse the string as Python code
            ast.parse(value)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing Python code: {str(e)}")

        return value


class PolicyMeta(BaseModel):
    output_tokens: int
    input_tokens: int
    total_tokens: int
    text_response: str


class Policy(BaseModel):
    code: Python
    input_conversation: Conversation = None
    meta: PolicyMeta


class PythonParser:
    """Parser that breaks code into chunks and validates each independently."""

    @staticmethod
    def is_valid_python(code: str) -> bool:
        """Check if a string is valid Python syntax.

        This version supports checking indented code blocks by dedenting
        the code before parsing.
        """
        try:
            # Import the textwrap module for dedent functionality
            import textwrap

            # Dedent the code before attempting to parse
            dedented_code = textwrap.dedent(code)

            # Parse the dedented code
            ast.parse(dedented_code)
            return True
        except:
            return False

    @staticmethod
    def wrap_in_docstring(text: str) -> str:
        """Wrap text in docstring delimiters."""
        # Clean the text first
        text = text.strip()
        if text:
            return f'"""\n{text}\n"""'
        return ""

    @staticmethod
    def process_chunk(chunk: str) -> str:
        """Process a single chunk of text."""
        # Skip empty chunks
        if not chunk.strip():
            return ""

        # Remove markdown code block markers if present
        chunk = re.sub(r"^```python\s*", "", chunk)
        chunk = re.sub(r"^```\s*", "", chunk)
        chunk = re.sub(r"\s*```$", "", chunk)

        # If it's valid Python, return as is
        if PythonParser.is_valid_python(chunk):
            return chunk

        # Otherwise wrap in docstring
        return PythonParser.wrap_in_docstring(chunk)

    @staticmethod
    def extract_markdown_code_blocks(content: str) -> Optional[str]:
        """
        Attempt to extract all Python code blocks marked with ```python.

        Args:
            content: The full text content to parse

        Returns:
            Combined valid Python code from all blocks, or None if no valid blocks found
        """
        # Find all code blocks marked with ```python
        pattern = r"```python\s*(.*?)\s*```"
        matches = re.finditer(pattern, content, re.DOTALL)

        code_blocks = []
        for match in matches:
            code = match.group(1).strip()
            if code and PythonParser.is_valid_python(code):
                code_blocks.append(code)

        if code_blocks:
            combined_code = "\n\n".join(code_blocks)
            if PythonParser.is_valid_python(combined_code):
                return combined_code

        return None

    @staticmethod
    def clean_chunk(chunk: str) -> str:
        """Clean a chunk of text by removing extra whitespace while preserving indentation."""
        # Remove any leading/trailing whitespace while preserving internal indentation
        lines = chunk.splitlines()
        # Remove empty lines at start and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines) if lines else ""

    @staticmethod
    def wrap_as_comment(text: str) -> str:
        """Wrap text as either a single-line comment or multi-line docstring."""
        if not text.strip():
            return ""

        # If single line, use #
        if len(text.splitlines()) == 1:
            return f"# {text.strip()}"

        # For multiple lines, use docstring
        return f'"""\n{text}\n"""'

    @staticmethod
    def extract_all_valid_python_chunks(content: str) -> Optional[str]:
        # Split content into chunks by double newline
        chunks = content.split("\n\n")
        processed_chunks = []

        for chunk in chunks:
            cleaned_chunk = PythonParser.clean_chunk(chunk)
            if not cleaned_chunk:
                continue

            # If chunk is valid Python, add it directly
            if PythonParser.is_valid_python(cleaned_chunk):
                processed_chunks.append(cleaned_chunk)
            else:
                # Wrap non-Python text as comment
                processed_chunks.append(PythonParser.wrap_as_comment(cleaned_chunk))

        # Combine processed chunks
        if processed_chunks:
            final_code = "\n\n".join(processed_chunks)
            if PythonParser.is_valid_python(final_code):
                return final_code

    @staticmethod
    def extract_all_backtick_blocks(content: str) -> Optional[str]:
        """
        Attempt to extract all code blocks between backticks, regardless of language marker.

        Args:
            content: The full text content to parse

        Returns:
            Combined valid Python code from all blocks, or None if no valid blocks found
        """
        # Find all code blocks between backticks, with or without language marker
        pattern = r"```(?:\w+)?\s*(.*?)\s*```"
        matches = re.finditer(pattern, content, re.DOTALL)

        code_blocks = []
        for match in matches:
            code = match.group(1).strip()
            if code and PythonParser.is_valid_python(code):
                code_blocks.append(code)

        if code_blocks:
            combined_code = "\n\n".join(code_blocks)
            if PythonParser.is_valid_python(combined_code):
                return combined_code

        return None

    @staticmethod
    def extract_code(choice) -> Optional[Tuple[str, str]]:
        """
        Extract code from LLM response, first trying markdown blocks then falling back to chunk processing.

        Args:
            choice: LLM response object with message.content or text attribute

        Returns:
            Tuple of (processed_code, original_content) or None if no content
        """
        # Get content from response object
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            content = choice.message.content
        elif hasattr(choice, "text"):
            content = choice.text
        else:
            raise RuntimeError("Incorrect message format")

        if PythonParser.is_valid_python(content):
            return content, content

        # First try to extract all backtick blocks
        backtick_code = PythonParser.extract_all_backtick_blocks(content)
        if backtick_code:
            return backtick_code, content

        content = content.replace("```python", "").replace("```", "")
        code = PythonParser.extract_all_valid_python_chunks(content)
        if code:
            return code, content
        # First try to extract markdown code blocks
        # markdown_code = PythonParser.extract_markdown_code_blocks(content)
        # if markdown_code:
        #     return markdown_code, content
        #
        # # Fall back to chunk-based processing
        # chunks = content.split('\n\n')
        # processed_chunks = []
        # for chunk in chunks:
        #     processed = PythonParser.process_chunk(chunk)
        #     if processed:
        #         processed_chunks.append(processed)
        #
        # # Combine processed chunks
        # if processed_chunks:
        #     final_code = '\n\n'.join(processed_chunks)
        #     if PythonParser.is_valid_python(final_code):
        #         return final_code, content
        #     else:
        #         raise Exception("Not valid python code")

        return None, None


def parse_response(response) -> Optional[Policy]:
    if hasattr(response, "choices"):
        choice = response.choices[0]
        input_tokens = response.usage.prompt_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.completion_tokens if hasattr(response, "usage") else 0
        )
    else:
        choice = response.content[0]
        input_tokens = response.usage.input_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.output_tokens if hasattr(response, "usage") else 0
        )

    total_tokens = input_tokens + output_tokens
    try:
        code, text_response = PythonParser.extract_code(choice)
    except Exception as e:
        print(f"Failed to extract code from choice: {str(e)}")
        return None

    if not code:
        return None

    policy = Policy(
        code=code,
        meta=PolicyMeta(
            output_tokens=output_tokens,
            input_tokens=input_tokens,
            total_tokens=total_tokens,
            text_response=text_response,
        ),
    )
    return policy
