import unittest
from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message

from fle.agents.formatters import StructurePreservingFormatter, CodeProcessor


class TestStructurePreservingFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = StructurePreservingFormatter(planning=False)
        self.conversation = Conversation(
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Inventory: {}"),
                Message(
                    role="assistant",
                    content="# Gather iron ore\nprint(0)\nprint(1)\n# Construct stone furnace",
                ),
                Message(role="user", content="Execution result: 1: 0\n2: 1"),
                Message(
                    role="assistant",
                    content="# Gather more iron ore\nprint(2)\nprint(3)\n# Construct stone furnace",
                ),
                Message(role="user", content="Execution result: 3: 0\n4: 1"),
            ]
        )

    def test_code_extractor(self):
        code_snippets = CodeProcessor.extract_code_blocks(
            self.conversation.messages[2].content
        )

        # Should produce one code snippet
        self.assertEqual(len(code_snippets), 1)

    def test_code_extractor_2(self):
        code_snippets = CodeProcessor.extract_code_blocks(
            self.conversation.messages[2].content
        )

        self.assertIn("print(0)\nprint(1)", code_snippets[0])

    def test_code_summariser(self):
        code_block = "# Gather iron ore\nprint(0)\nprint(1)\n# Construct stone furnace"
        CodeProcessor.extract_code_blocks(code_block)

        summarized = CodeProcessor.summarize_code_block(
            code_block, preserve_comments=True
        )

        self.assertEqual(
            "# Gather iron ore\n<LINES 2-3 CUT/>\n# Construct stone furnace", summarized
        )

        summarized2 = CodeProcessor.summarize_code_block(
            "# Gather iron ore\n# Gather more iron ore\nprint(0)\nprint(1)\n# Construct stone furnace",
            preserve_comments=True,
        )

        self.assertEqual(
            summarized2,
            "# Gather iron ore\n# Gather more iron ore\n<LINES 3-4 CUT/>\n# Construct stone furnace",
        )

    def test_format_conversation(self):
        formatted = self.formatter.format_conversation(self.conversation)

        # Should produce 6 messages: system, user, assistant1, user1, assistant2, user2
        self.assertEqual(len(formatted), 6)

        # Check system message is preserved exactly
        self.assertEqual(formatted[0].role, "system")
        self.assertEqual(formatted[0].content, "You are a helpful assistant.")

        # Check first assistant message (not the last program, should be summarized)
        assistant1 = formatted[2]
        self.assertEqual(assistant1.role, "assistant")
        expected_summary = (
            "# Gather iron ore\n<LINES 2-3 CUT/>\n# Construct stone furnace"
        )
        self.assertEqual(assistant1.content, expected_summary)

        # Check last assistant message (should be preserved in full)
        assistant2 = formatted[4]
        self.assertEqual(assistant2.role, "assistant")
        expected_full = (
            "# Gather more iron ore\nprint(2)\nprint(3)\n# Construct stone furnace"
        )
        self.assertEqual(assistant2.content, expected_full)
        self.assertEqual(assistant2.metadata, {"summarized": False})

        # Check user execution results are formatted correctly
        user1 = formatted[3]
        self.assertEqual(user1.role, "user")
        self.assertEqual(user1.content, "Execution result:\n1: 0\n2: 1")

        user2 = formatted[5]
        self.assertEqual(user2.role, "user")
        self.assertEqual(user2.content, "Execution result:\n3: 0\n4: 1")

    def test_format_single_message(self):
        # Test formatting of a non-last assistant message
        message = Message(
            role="assistant",
            content="# First task\nprint(1)\n# Second task\nprint(2)\n",
        )
        formatted = self.formatter.format_message(message, should_format=True)
        expected = "# First task\n<LINE 2 CUT/>\n# Second task\n<LINE 4 CUT/>"
        self.assertEqual(formatted.content, expected)
        self.assertEqual(formatted.metadata, {"summarized": True})

        # Test formatting of a last assistant message (should preserve everything)
        formatted_last = self.formatter.format_message(message, should_format=False)
        self.assertEqual(
            formatted_last.content, "# First task\nprint(1)\n# Second task\nprint(2)\n"
        )
        self.assertEqual(formatted_last.metadata, {"summarized": False})

    def test_empty_code_blocks(self):
        # Test handling of empty code blocks or blocks without comments
        message = Message(role="assistant", content="print(1)\nprint(2)\n")
        formatted = self.formatter.format_message(message, should_format=True)
        self.assertEqual(formatted.content, "<LINES 1-2 CUT/>")

    def test_docstring_code_summariser(self):
        code_block = '''from factorio_instance import *

    """
    Objective: We need to get 20 copper plates

    Planning:
    1. Print the recipe for copper plates
    2. Analyze the current game state
    """

    """
    Step 1: Print recipe for copper plates
    """
    print("Copper Plate Recipe:")
    print("Crafting requires smelting")

    """
    Step 2: Analyze current game state
    """
    inventory = inspect_inventory()
    print(f"Current inventory: {inventory}")'''

        self.formatter.code_processor.summarize_code_block(
            code_block, preserve_comments=True
        )

        pass


if __name__ == "__main__":
    unittest.main()
