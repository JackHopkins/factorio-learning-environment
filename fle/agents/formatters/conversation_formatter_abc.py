from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.env.namespace import FactorioNamespace

PLANNING_ADDITION_PROMPT = """
Your goal is to automate an increasingly complex factory process.
Identify an appropriate next task given the recent history and environment feedback to achieve this goal.
Develop thorough step-by-step plans for how you can achieve the next task and then create the python script to achieve the task.
For your plan, follow this structure:
1) What entities are needed for the task
2) What entities do we have on the map, in different entity inventories or in our inventory
3) What entities are we missing for the task
4) Execution -- Taking into account 1,2 and 3, what are the steps we need to take to successfully carry out the task.
"""


class CodeProcessor:
    """Handles code block processing and summarization"""

    @staticmethod
    def is_comment_start(line: str) -> bool:
        """Check if line starts a comment (either # or \"\"\")"""
        stripped = line.strip()
        return stripped.startswith("#") or stripped.startswith('"""')

    @staticmethod
    def is_comment_end(line: str) -> bool:
        """Check if line ends a comment block"""
        stripped = line.strip()
        return not stripped.startswith('"""') and stripped.endswith('"""')

    @staticmethod
    def extract_code_blocks(content: str) -> List[Tuple[str, int, int]]:
        """
        Extract code blocks that are between comments.
        Returns list of (code, start_line, end_line) tuples.
        """
        lines = content.splitlines()
        blocks = []
        current_block = []
        block_start = None

        for i, line in enumerate(lines, 1):  # Start line counting from 1
            stripped = line.strip()

            if stripped.startswith("#"):
                # If we have an active block, end it
                if current_block:
                    blocks.append(("\n".join(current_block), block_start, i - 1))
                    current_block = []
                    block_start = None
            else:
                # If this is first code line after comment
                if stripped and block_start is None:
                    block_start = i
                # Add non-empty lines to current block
                if stripped:
                    current_block.append(line)

        # Handle any remaining block
        if current_block:
            blocks.append(("\n".join(current_block), block_start, len(lines)))

        # If no blocks found, treat entire content as one block
        if not blocks:
            return [(content, 1, len(lines))]

        return blocks

    @staticmethod
    def summarize_code_block(
        code: str,
        start_line: int = None,
        end_line: int = None,
        preserve_comments: bool = True,
    ) -> str:
        """
        Summarize a code block by replacing code sections with line count indicators.
        Handles both inline (#) and block (\"\"\") comments.
        """
        lines = code.splitlines()

        if not lines:
            return ""

        result = []
        code_start = None
        code_lines = 0
        in_docstring = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Handle docstring boundaries
            if stripped.startswith('"""'):
                if not in_docstring:  # Start of docstring
                    if code_start is not None:
                        if code_lines == 1:
                            result.append(f"<LINE {code_start} CUT/>")
                        else:
                            result.append(
                                f"<LINES {code_start}-{code_start + code_lines - 1} CUT/>"
                            )
                        code_start = None
                        code_lines = 0
                    in_docstring = True
                    result.append(line)
                    continue

            if in_docstring:
                result.append(line)
                if stripped.endswith('"""'):
                    in_docstring = False
                continue

            # Handle regular comments and code
            if stripped.startswith("#"):
                if code_start is not None:
                    if code_lines == 1:
                        result.append(f"<LINE {code_start} CUT/>")
                    else:
                        result.append(
                            f"<LINES {code_start}-{code_start + code_lines - 1} CUT/>"
                        )
                    code_start = None
                    code_lines = 0
                result.append(line)
            else:
                if stripped:
                    if code_start is None:
                        code_start = i
                    code_lines += 1

        # Handle any remaining code section
        if code_start is not None:
            if code_lines == 1:
                result.append(f"<LINE {code_start} CUT/>")
            else:
                result.append(
                    f"<LINES {code_start}-{code_start + code_lines - 1} CUT/>"
                )

        return "\n".join(result)


class ConversationFormatter(ABC):
    """Abstract base class for conversation formatting strategies"""

    @abstractmethod
    def format_conversation(
        self, conversation: Conversation, namespace: FactorioNamespace
    ) -> List[Message]:
        """
        Format a conversation according to the specific strategy.
        Returns a list of formatted messages ready for LLM consumption.
        """
        pass

    @abstractmethod
    def format_message(self, message: Message) -> Message:
        """Format a single message according to the strategy"""
        pass

    def to_llm_messages(
        self, formatted_conversation: Conversation
    ) -> List[Dict[str, str]]:
        """Convert formatted messages to LLM-compatible format"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in formatted_conversation.messages
        ]


class DefaultFormatter(ConversationFormatter):
    def format_conversation(
        self, conversation: Conversation, namespace: FactorioNamespace
    ) -> List[Message]:
        return conversation.messages

    def format_message(self, message: Message) -> Message:
        return message


class StructurePreservingFormatter(ConversationFormatter):
    """
    Formatter that preserves program structure through comments while reducing token usage.
    It replaces all code not in the most recent history with `<LINE X CUT/>` tags.
    """

    def __init__(self, planning=True):
        self.code_processor = CodeProcessor()
        self.planning = planning

    def format_message(
        self, message: Message, should_format: bool = True
    ) -> Optional[Message]:
        if message.role == "system":
            return Message(role="system", content=message.content)

        elif message.role == "assistant":
            if should_format:  # Summarize all but the last program
                content = self.code_processor.summarize_code_block(message.content)
                return Message(
                    role="assistant", content=content, metadata={"summarized": True}
                )
            else:
                return Message(
                    role="assistant",
                    content=message.content,
                    metadata={"summarized": False},
                )

        elif message.role == "user":
            content = message.content
            try:
                if "Execution result:" in content:
                    result = content.split("Execution result:")[1].split(
                        "Updated state:"
                    )[0]
                    # content = f"Execution result:\n{result.strip()}"
                    # if self.planning:
                    #    content = PLANNING_ADDITION_PROMPT + '\n' + content
                    return Message(role="user", content=result.strip())
                else:
                    return Message(role="user", content=content.strip())
            except Exception as e:
                print(f"Error formatting user message: {str(e)}")
                return None

        return None

    def format_conversation(
        self, conversation: Conversation, namespace: FactorioNamespace
    ) -> List[Message]:
        formatted = []

        # Handle system message if present
        if conversation.messages and conversation.messages[0].role == "system":
            formatted.append(self.format_message(conversation.messages[0]))
            messages = conversation.messages[1:]
        else:
            messages = conversation.messages

        last_message_role = messages[-1].role

        # Format each message
        for i, msg in enumerate(messages):
            if last_message_role == "assistant":
                formatted_msg = self.format_message(
                    msg, should_format=(i != len(messages) - 1)
                )
            elif last_message_role == "user":
                formatted_msg = self.format_message(
                    msg, should_format=(i != len(messages) - 2)
                )
            if formatted_msg:
                formatted.append(formatted_msg)

        return formatted
