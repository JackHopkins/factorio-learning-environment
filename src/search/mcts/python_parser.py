import re
from typing import Optional, Tuple
import ast


class PythonParser:
    """Parser that breaks code into chunks and validates each independently."""

    def _is_valid_python(self, code: str) -> bool:
        """Check if a string is valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except:
            return False

    def _wrap_in_docstring(self, text: str) -> str:
        """Wrap text in docstring delimiters."""
        # Clean the text first
        text = text.strip()
        if text:
            return f'"""\n{text}\n"""'
        return ""

    def _process_chunk(self, chunk: str) -> str:
        """Process a single chunk of text."""
        # Skip empty chunks
        if not chunk.strip():
            return ""

        # Remove markdown code block markers if present
        chunk = re.sub(r'^```python\s*', '', chunk)
        chunk = re.sub(r'^```\s*', '', chunk)
        chunk = re.sub(r'\s*```$', '', chunk)

        # If it's valid Python, return as is
        if self._is_valid_python(chunk):
            return chunk

        # Otherwise wrap in docstring
        return self._wrap_in_docstring(chunk)

    def _extract_markdown_code_blocks(self, content: str) -> Optional[str]:
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
            if code and self._is_valid_python(code):
                code_blocks.append(code)

        if code_blocks:
            combined_code = '\n\n'.join(code_blocks)
            if self._is_valid_python(combined_code):
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

        # First try to extract markdown code blocks
        markdown_code = self._extract_markdown_code_blocks(content)
        if markdown_code:
            return markdown_code, content

        # Fall back to chunk-based processing
        chunks = content.split('\n\n')
        processed_chunks = []
        for chunk in chunks:
            processed = self._process_chunk(chunk)
            if processed:
                processed_chunks.append(processed)

        # Combine processed chunks
        if processed_chunks:
            final_code = '\n\n'.join(processed_chunks)
            if self._is_valid_python(final_code):
                return final_code, content
            else:
                raise Exception("Not valid python code")

        return None