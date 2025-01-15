import asyncio
import tempfile
from unittest.mock import Mock

from llm_factory import LLMFactory
from search.mcts.formatters.recursive_formatter import RecursiveFormatter
from search.model.conversation import Conversation, Message

temp_dir = tempfile.mkdtemp()
mock_llm = Mock(spec=LLMFactory)
formatter = RecursiveFormatter(
            chunk_size=16,  # Smaller chunk size for testing
            llm_factory=mock_llm,
            cache_dir=temp_dir
)


def create_test_conversation(length: int) -> Conversation:
    """Helper to create a test conversation of specified length."""
    messages = [
        Message(
            role="system",
            content="You are a helpful assistant."
        )
    ]

    for i in range(length):
        messages.extend([
            Message(role="user", content=f"Message {i}"),
            Message(role="assistant", content=f"Response {i}")
        ])

    return Conversation(messages=messages)

async def main():
    mock_response = Mock()
    mock_response.content = "Summarized content"
    mock_llm.acall.return_value = mock_response

    # Create conversation with 33 messages (system + 16 exchanges)
    conversation = create_test_conversation(33)

    formatted = await formatter.format_conversation(conversation)
    pass


if __name__ == '__main__':
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(main())
