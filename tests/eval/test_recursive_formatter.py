import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch

from fle.agents.formatters.recursive_formatter import RecursiveFormatter
from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.agents.llm.api_factory import APIFactory


class TestRecursiveFormatter(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.mock_llm = Mock(spec=APIFactory)
        self.formatter = RecursiveFormatter(
            chunk_size=4,  # Smaller chunk size for testing
            api_factory=self.mock_llm,
            cache_dir=self.temp_dir,
        )

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)

    def create_test_conversation(self, length: int) -> Conversation:
        """Helper to create a test conversation of specified length."""
        messages = [Message(role="system", content="You are a helpful assistant.")]

        for i in range(length):
            messages.extend(
                [
                    Message(role="user", content=f"Message {i}"),
                    Message(role="assistant", content=f"Response {i}"),
                ]
            )

        return Conversation(messages=messages)

    def test_chunk_hash_deterministic(self):
        """Test that the same messages produce the same hash."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]

        hash1 = self.formatter._get_chunk_hash(messages)
        hash2 = self.formatter._get_chunk_hash(messages)

        self.assertEqual(hash1, hash2)

    def test_cache_operations(self):
        """Test cache save and load operations."""
        messages = [
            Message(role="user", content="Test message"),
            Message(role="assistant", content="Test response"),
        ]

        chunk_hash = self.formatter._get_chunk_hash(messages)
        summary = Message(
            role="assistant", content="Summary content", metadata={"summarized": True}
        )

        # Save to cache
        self.formatter._save_summary_cache(chunk_hash, summary, 1, 2)

        # Load from cache
        loaded_summary = self.formatter._load_cached_summary(chunk_hash)

        self.assertIsNotNone(loaded_summary)
        self.assertEqual(loaded_summary.content, "Summary content")
        self.assertEqual(loaded_summary.metadata["summarized"], True)

    async def test_basic_summarization(self):
        """Test basic summarization of a conversation chunk."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Summarized content"
        self.mock_llm.acall.return_value = mock_response

        messages = [Message(role="user", content=f"Message {i}") for i in range(5)]

        summary = await self.formatter._summarize_chunk(messages, 1, 5)

        self.assertEqual(summary.content, "Summarized content")
        self.assertTrue(summary.metadata["summarized"])
        self.assertEqual(summary.metadata["summary_range"], "[1-5]")

    async def test_recursive_summarization(self):
        """Test recursive summarization of a longer conversation."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Summarized chunk"
        self.mock_llm.acall.return_value = mock_response

        # Create conversation with 9 messages (system + 4 exchanges)
        conversation = self.create_test_conversation(4)

        formatted = await self.formatter.format_conversation(conversation)

        # With chunk_size=4, we expect:
        # - System message
        # - One summary for first 4 messages
        # - Remaining 4 messages
        self.assertGreater(len(formatted), 1)
        self.assertEqual(formatted[0].role, "system")
        self.assertTrue(any(msg.metadata.get("summarized") for msg in formatted))

    async def test_very_long_conversation(self):
        """Test handling of a conversation requiring multiple levels of recursion."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Summarized content"
        self.mock_llm.acall.return_value = mock_response

        # Create conversation with 33 messages (system + 16 exchanges)
        conversation = self.create_test_conversation(16)

        formatted = await self.formatter.format_conversation(conversation)

        # Verify the conversation was compressed
        self.assertLess(len(formatted), len(conversation.messages))

        # Check that we have appropriate metadata
        summaries = [msg for msg in formatted if msg.metadata.get("summarized")]
        self.assertGreater(len(summaries), 0)

    def test_error_handling(self):
        """Test error handling in cache operations."""
        with patch("builtins.open", side_effect=IOError):
            # Should handle cache write failure gracefully
            messages = [Message(role="user", content="Test")]
            chunk_hash = self.formatter._get_chunk_hash(messages)
            summary = Message(role="assistant", content="Summary")

            # Should not raise exception
            self.formatter._save_summary_cache(chunk_hash, summary, 1, 1)

            # Should return None on cache read failure
            loaded = self.formatter._load_cached_summary(chunk_hash)
            self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
