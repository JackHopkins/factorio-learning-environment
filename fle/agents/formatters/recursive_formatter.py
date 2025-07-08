import hashlib
import json
import os
import re
from typing import List, Optional

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message

from fle.agents.llm.api_factory import APIFactory
from fle.agents.formatters.conversation_formatter_abc import ConversationFormatter

DEFAULT_INSTRUCTIONS = "Summarize the following conversation chunk maintaining key information and context. Focus on decisions made, actions taken, and important outcomes."


class RecursiveFormatter(ConversationFormatter):
    """
    Formatter that maintains a fixed context window through hierarchical summarization.
    Recursively summarizes from left to right, incorporating newer messages into the summary.
    """

    def __init__(
        self,
        chunk_size: int = 16,
        api_factory: Optional[APIFactory] = None,
        cache_dir: str = ".conversation_cache",
        summary_instructions: str = DEFAULT_INSTRUCTIONS,
        truncate_entity_data: bool = True,
        summarize_history: bool = True,
    ):
        """

        @param chunk_size:
        @param api_factory:
        @param cache_dir:
        @param summary_instructions:
        @param truncate_entity_data: Whether we should truncate historical (stale) entity observations when summarizing.
        """
        self.chunk_size = chunk_size
        self.api_factory = api_factory
        self.cache_dir = cache_dir
        self.summary_instructions = summary_instructions
        self.truncate_entity_data = truncate_entity_data
        self.entity_data_pattern = re.compile(
            r"(?:,|:) \[((.|[\n])+)\]\)"
        )  # re.compile(r': \[((.|[\n])+)]",\)')
        self.summarize_history = summarize_history

        # Ensure cache directory exists.
        os.makedirs(cache_dir, exist_ok=True)

    def _get_chunk_hash(self, messages: List[Message]) -> str:
        """Generate a deterministic hash for a chunk of messages."""
        chunk_content = json.dumps(
            [
                {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
                for msg in messages
            ],
            sort_keys=True,
        )
        return hashlib.sha256(chunk_content.encode()).hexdigest()

    def _get_cache_path(self, chunk_hash: str) -> str:
        """Get the file path for a cached summary."""
        return os.path.join(self.cache_dir, f"{chunk_hash}.json")

    def _load_cached_summary(self, chunk_hash: str) -> Optional[Message]:
        """Load a cached summary if it exists."""
        cache_path = self._get_cache_path(chunk_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                return Message(
                    role="assistant",
                    content=data["content"],
                    metadata={
                        "summarized": True,
                        "summary_range": data["summary_range"],
                    },
                )
            except Exception as e:
                print(f"Error loading cached summary: {e}")
                return None
        return None

    def _save_summary_cache(self, chunk_hash: str, summary: Message):
        """Save a generated summary to the cache."""
        cache_path = self._get_cache_path(chunk_hash)
        try:
            with open(cache_path, "w") as f:
                json.dump(
                    {
                        "content": summary.content,
                        "summary_range": summary.metadata["summary_range"],
                    },
                    f,
                )
        except Exception as e:
            print(f"Error saving summary cache: {e}")

    def _truncate_entity_data(
        self, message: Message, is_recent: bool = False
    ) -> Message:
        """
        Truncate entity data in message content if enabled and message is not recent.
        Returns a new Message instance with modified content if truncation occurred.
        """
        if (
            not self.truncate_entity_data
            or is_recent
            or message.role in ("assistant", "system")
        ):
            return message

        if isinstance(message.content, str):
            new_content = self.entity_data_pattern.sub(
                ": <STALE_ENTITY_DATA_OMITTED/>", message.content
            )
            if new_content != message.content:
                return Message(
                    role=message.role, content=new_content, metadata=message.metadata
                )

        return message

    async def _generate_summary(
        self,
        messages: List[Message],
        start_idx: int,
        end_idx: int,
        system_message: Message,
    ) -> Message:
        """Generate a summary of messages using the LLM."""
        if not self.api_factory:
            raise ValueError("LLM factory required for summary generation")

        summary_prompt = [{"role": "system", "content": self.summary_instructions}]

        for msg in messages:
            summary_prompt.append({"role": msg.role, "content": msg.content})

        response = await self.api_factory.acall(
            messages=summary_prompt, max_tokens=1024, temperature=0.3
        )

        if hasattr(response, "choices"):
            content = response.choices[0].message.content
        else:
            content = response.content[0].text

        return Message(
            role="user",
            content=content,
            metadata={"summarized": True, "summary_range": f"[{start_idx}-{end_idx}]"},
        )

    async def _summarize_chunk(
        self,
        messages: List[Message],
        start_idx: int,
        end_idx: int,
        system_message: Message,
    ) -> Message:
        """Summarize a chunk of messages, using cache if available."""
        # Truncate entity data before generating cache hash
        # truncated_messages = [self._truncate_entity_data(msg) for msg in messages]
        chunk_hash = self._get_chunk_hash(messages)

        cached_summary = self._load_cached_summary(chunk_hash)
        if cached_summary:
            return cached_summary

        summary = await self._generate_summary(
            messages, start_idx, end_idx, system_message
        )
        self._save_summary_cache(chunk_hash, summary)
        return summary

    async def _recursive_summarize_left(
        self, messages: List[Message], system_message: Message
    ) -> Message:
        """
        Recursively summarize messages from left to right:
        1. Take first chunk_size messages and summarize
        2. Take that summary and next chunk of messages, summarize together
        3. Continue until all messages are incorporated
        """
        if len(messages) <= self.chunk_size:
            return await self._summarize_chunk(
                messages, 1, len(messages), system_message
            )

        # First summarize the leftmost chunk
        left_chunk = messages[: self.chunk_size]
        current_summary = await self._summarize_chunk(
            left_chunk, 1, self.chunk_size, system_message
        )

        # Process remaining messages in chunks
        remaining = messages[self.chunk_size :]
        current_end = self.chunk_size

        while remaining:
            # Take next chunk of messages
            next_chunk_size = min(len(remaining), self.chunk_size)
            next_chunk = remaining[:next_chunk_size]

            # Combine current summary with next chunk and summarize
            messages_to_summarize = [current_summary] + next_chunk
            current_summary = await self._summarize_chunk(
                messages_to_summarize,
                1,  # Always start from 1
                current_end + next_chunk_size,
                system_message,
            )

            # Update remaining messages and current end position
            remaining = remaining[next_chunk_size:]
            current_end += next_chunk_size

        return current_summary

    async def format_conversation(self, conversation: Conversation) -> List[Message]:
        """
        Format conversation by recursively summarizing historical messages from left to right.
        Returns [system_message (if present), historical_summary, recent_messages].
        """
        messages = conversation.messages

        # Handle base cases
        if len(messages) <= self.chunk_size:
            return [
                self._truncate_entity_data(msg, is_recent=(i >= len(messages) - 1))
                for i, msg in enumerate(messages)
            ]

        # Keep system message separate if present
        system_message = None
        if messages[0].role == "system":
            system_message = messages[0]
            messages = messages[1:]

        # Keep the most recent chunk as-is
        recent_messages = messages[-self.chunk_size :]

        # We turn this off
        if self.summarize_history:
            historical_messages = messages[: -self.chunk_size]
        else:
            historical_messages = []

        if historical_messages:
            # Recursively summarize historical messages from left to right
            historical_summary = await self._recursive_summarize_left(
                historical_messages, system_message
            )
            formatted = [historical_summary] + [
                self._truncate_entity_data(
                    msg, is_recent=(i >= len(recent_messages) - 1)
                )
                for i, msg in enumerate(recent_messages)
            ]
        else:
            formatted = [
                self._truncate_entity_data(
                    msg, is_recent=(i >= len(recent_messages) - 1)
                )
                for i, msg in enumerate(recent_messages)
            ]

        # Add back system message if present
        if system_message:
            formatted = [system_message] + formatted

        return formatted

    def format_message(self, message: Message) -> Message:
        """Format a single message - apply entity data truncation if enabled."""
        return self._truncate_entity_data(message, is_recent=True)
