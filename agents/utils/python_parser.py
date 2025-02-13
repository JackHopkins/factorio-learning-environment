import re
from typing import Optional, Tuple
import ast


class PythonParser:
    """Parser that breaks code into chunks and validates each independently."""

    @staticmethod
    def is_valid_python(code: str) -> bool:
        """Check if a string is valid Python syntax."""
        try:
            ast.parse(code)
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
        chunk = re.sub(r'^```python\s*', '', chunk)
        chunk = re.sub(r'^```\s*', '', chunk)
        chunk = re.sub(r'\s*```$', '', chunk)

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
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.finditer(pattern, content, re.DOTALL)

        code_blocks = []
        for match in matches:
            code = match.group(1).strip()
            if code and PythonParser.is_valid_python(code):
                code_blocks.append(code)

        if code_blocks:
            combined_code = '\n\n'.join(code_blocks)
            if PythonParser.is_valid_python(combined_code):
                return combined_code

        return None

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
        pattern = r'```(?:\w+)?\s*(.*?)\s*```'
        matches = re.finditer(pattern, content, re.DOTALL)

        code_blocks = []
        for match in matches:
            code = match.group(1).strip()
            if code and PythonParser.is_valid_python(code):
                code_blocks.append(code)

        if code_blocks:
            combined_code = '\n\n'.join(code_blocks)
            if PythonParser.is_valid_python(combined_code):
                return combined_code

        return None

    def extract_code(self, choice) -> Optional[Tuple[str, str]]:
        """
        Extract code from LLM response, first trying markdown blocks then falling back to chunk processing.

        Args:
            choice: LLM response object with message.content or text attribute

        Returns:
            Tuple of (processed_code, original_content) or None if no content
        """
        # Get content from response object
        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
            content = choice.message.content
        elif hasattr(choice, 'text'):
            content = choice.text
        else:
            raise RuntimeError('Incorrect message format')

        if PythonParser.is_valid_python(content):
            return content, content

        # First try to extract all backtick blocks
        backtick_code = PythonParser.extract_all_backtick_blocks(content)
        if backtick_code:
            return backtick_code, content

        # First try to extract markdown code blocks
        markdown_code = PythonParser.extract_markdown_code_blocks(content)
        if markdown_code:
            return markdown_code, content

        # Fall back to chunk-based processing
        chunks = content.split('\n\n')
        processed_chunks = []
        for chunk in chunks:
            processed = PythonParser.process_chunk(chunk)
            if processed:
                processed_chunks.append(processed)

        # Combine processed chunks
        if processed_chunks:
            final_code = '\n\n'.join(processed_chunks)
            if PythonParser.is_valid_python(final_code):
                return final_code, content
            else:
                raise Exception("Not valid python code")

        return None, None