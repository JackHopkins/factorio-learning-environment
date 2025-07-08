import copy
import hashlib
import json
import os
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypedDict

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.env.namespace import FactorioNamespace

from fle.agents.formatters.conversation_formatter_abc import ConversationFormatter

DEFAULT_INSTRUCTIONS = """
You are a report generating model for the game factorio. You are given a number of steps and logs an agent has executed in the game. You are also given the previous historical report. Using the previous historical report and the latest step execution logs you must generate a new report. The report must have 2 sections: EXISTING STRUCTURES and ERROR TIPS. Below are instructions for both of them

EXISTING STRUCTURES
In this section you must summarise what structures the agent has created on the map and what are the use-cases of those structures. You must also bring out the entities and positions of entities of each of those structures.

Focus on the structures themselves. Do not bring out entities separately, create sections like 
###Electricity generator at position(x)
Consists of steam engine(position x), boiler(position y) and offshore pump (position z)

###Copper plate mine at position(x)
Consists of following entities
-  Burner mining drill (position x1) and a furnace at position(y1)
-  Burner mining drill (position x2) and a furnace at position(y2)
-  Burner mining drill (position x3) and a furnace at position(y3)

###Copper cable factory
Consists of following entities
-  Burner mining drill (position x1) and a furnace at position(y1)
-  Assembling machine at position(z1) and inserter at position(a) that puts into assembling machine
-  Beltgroup (position ) that connects the furnace at position y1 to assembling machine at position(z1)

- If multiple sections are connected, summarise them as one structure
- Do not include any mention of harvesting or crafting activities. That is not the aim of this report and is self-evident as the agent can see its own inventory
- All structures from the previous report that did not have any updates, include them in the new report unchanged

ERROR TIPS
In this section you must analyse the errors that the agent has made and bring out tips how to mitigate these errors. 
Usually error messages tell you what the agent did wrong. The errors can be incorrect use of API, misplaced objects etc. 
Make this a succinct detailed list, group common similar error patterns and solutions how to avoid these errors. 
Group similar mistakes, if the agent made the same mistake multiple times but at many places, bring it out as one section/bulletpoint. 
Include new mistakes and all mistake tips from the previous report

Make the sections accurate and thorough. Do not mention things like "The error message suggests" etc, this is self evident.
Some examples

### Errors when using extracting but being too far
 -  Make sure to move to the target entity where you want to extract from before extracting items
### Errors when placing into a tile which is occupied by another entity
- Ensure you can place a entity to a tile before attempting placing

NAMESPACE
In this section you should build up a list of type-annotated utility functions that have be defined by the agent.
Only include the function signature (function name, input-output variables and typehints) and a brief description of what the function does.
If they have been invoked, you should include a summary of the failure and success modes, with reasons.
Include a bullet point list of important variables that have been assigned, with their types.

Only include functions that have been defined by the agent, not any of the built-in functions.
Do not include any of the code of the functions, only the signature
If the agent has not defined any functions, do not include this section

Only output the report, nothing else
Make the report concise, accurate and informative
    """


class LLMParams(TypedDict):
    messages: List[Dict[str, str]]
    max_tokens: int
    temperature: float


class RecursiveReportFormatter(ConversationFormatter):
    """
    Formatter that maintains a fixed context window through hierarchical summarization.
    Recursively summarizes from left to right, incorporating newer messages into the summary.
    """

    def __init__(
        self,
        chunk_size: int = 16,
        llm_call: Callable[[LLMParams], Awaitable[Any]] = None,
        cache_dir: str = ".conversation_cache",
        truncate_entity_data: bool = True,
        summarize_history: bool = True,
        max_chars: int = 200000,
    ):
        """
        @param chunk_size:
        @param api_factory:
        @param cache_dir:
        @param summary_instructions:
        @param truncate_entity_data: Whether we should truncate historical (stale) entity observations when summarizing.
        """
        self.llm_call = llm_call
        self.chunk_size = chunk_size
        self.cache_dir = cache_dir
        self.summary_instructions = DEFAULT_INSTRUCTIONS
        self.truncate_entity_data = truncate_entity_data
        self.entity_data_pattern = re.compile(r"\[([\n\t\\\t\n].+)+[\"\]]")
        self.summarize_history = summarize_history
        self.max_chars = max_chars

        # Ensure cache directory exists.
        os.makedirs(cache_dir, exist_ok=True)

    def _get_conversation_length(self, messages: List[Message]) -> int:
        """Calculate total character length of all messages in conversation."""
        return sum(len(msg.content) for msg in messages)

    def _trim_conversation_to_limit(self, messages: List[Message]) -> List[Message]:
        """
        Trim conversation to stay within character limit while preserving system message.
        Removes oldest messages first (after system message).
        """
        if not messages:
            return messages

        # Separate system message if present
        system_message = None
        working_messages = messages.copy()
        if working_messages[0].role == "system":
            system_message = working_messages.pop(0)

        # Calculate current length
        current_length = self._get_conversation_length(working_messages)
        if system_message:
            current_length += len(system_message.content)

        # If we're already under limit, return original messages
        if current_length <= self.max_chars:
            return messages

        # Remove oldest messages until we're under the limit
        while working_messages and current_length > self.max_chars:
            removed_message = working_messages.pop(0)
            current_length -= len(removed_message.content)

        # Reassemble messages with system message if present
        final_messages = working_messages
        if system_message:
            final_messages.insert(0, system_message)

        return final_messages

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

    def _load_cached_summary(self, chunk_hash: str) -> Optional[str]:
        """Load a cached summary if it exists."""
        cache_path = self._get_cache_path(chunk_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                return data["content"]
            except Exception as e:
                print(f"Error loading cached summary: {e}")
                return None
        return None

    def _save_summary_cache(self, chunk_hash: str, summary: str):
        """Save a generated summary to the cache."""
        cache_path = self._get_cache_path(chunk_hash)
        try:
            with open(cache_path, "w") as f:
                json.dump({"content": summary}, f)
        except Exception as e:
            print(f"Error saving summary cache: {e}")

    def _truncate_entity_data(
        self, message: Message, is_recent: bool = False, message_index=0
    ) -> Message:
        """
        Truncate entity data in message content if enabled and message is not recent.
        Returns a new Message instance with modified content if truncation occurred.
        """
        if not self.truncate_entity_data or message.role in ("assistant", "system"):
            return message
        if isinstance(message.content, str):
            if is_recent:
                new_content = message.content
            else:
                new_content = self.entity_data_pattern.sub(
                    ": <STALE_ENTITY_DATA_OMITTED/>", message.content
                )

            if new_content != message.content:
                pass
            new_content = f"Step {message_index} execution log\n{new_content}"
            return Message(
                role=message.role, content=new_content, metadata=message.metadata
            )

        return message

    async def _generate_summary(
        self, messages: List[Message], previous_report: str, last_summary_step: int
    ) -> Message:
        """Generate a summary of messages using the LLM."""
        if not self.llm_call:
            raise ValueError("LLM factory required for summary generation")

        summary_prompt = [{"role": "system", "content": self.summary_instructions}]
        if last_summary_step == 0:
            steps = "These are the first steps so there is no historical report to summarize.\n\n"
            steps += f"Here are the first {int(self.chunk_size / 2)} execution steps of the agent:\n\n"
        else:
            steps = f"Here is the report from step 0 until step {int(last_summary_step / 2) - 1}\n\n{previous_report}\n\n"
            steps += f"Here are the next {int(self.chunk_size / 2)} execution steps of the agent:\n\n"
        for msg in messages:
            if msg.role == "user":
                steps += msg.content + "\n\n"
        summary_prompt.append({"role": "user", "content": steps})
        response = await self.llm_call(
            messages=summary_prompt, max_tokens=1024, temperature=0.3
        )

        if hasattr(response, "choices"):
            content = response.choices[0].message.content
        else:
            content = response.content[0].text

        return content

    def _get_chunk_hash(self, messages: List[Message]) -> str:
        """Generate a deterministic hash for a chunk of messages."""
        chunk_content = json.dumps(
            [
                {
                    "content": msg.content,
                }
                for msg in messages
                if msg.role == "user"
            ],
            sort_keys=True,
        )
        return hashlib.sha256(chunk_content.encode()).hexdigest()

    async def format_conversation(
        self, conversation: Conversation, namespace: Optional[FactorioNamespace] = None
    ) -> Conversation:
        """
        Format conversation by recursively summarizing historical messages from left to right.
        Returns [system_message (if present), historical_summary, recent_messages].
        """
        messages = conversation.messages

        total_length = len(messages)

        # Handle base cases
        if len(messages) <= self.chunk_size:  # account for system message
            messages = [
                self._truncate_entity_data(
                    msg,
                    is_recent=(i >= len(messages) - 1),
                    message_index=int((total_length - len(messages)) / 2) + int(i / 2),
                )
                for i, msg in enumerate(messages)
            ]
            messages = self._trim_conversation_to_limit(messages)
            return Conversation(messages=messages)

        # Keep system message separate if present
        system_message = None
        if messages[0].role == "system":
            system_message = messages[0]
            messages = messages[1:]

        function_definitions = namespace.get_functions() if namespace else []

        # Add function definitions to system prompt
        if function_definitions:
            system_message.content += "# Your utility functions:\n\n" + "\n\n".join(
                [str(f) for f in function_definitions]
            )

        new_messages = copy.deepcopy(messages[-self.chunk_size :])
        new_formatted_messages = [
            self._truncate_entity_data(
                msg,
                is_recent=(i >= len(new_messages) - 1),
                message_index=int((total_length - len(new_messages)) / 2) + int(i / 2),
            )
            for i, msg in enumerate(new_messages)
        ]

        # We turn this off
        if self.summarize_history:
            nr_of_messages = total_length - 1
            if nr_of_messages % self.chunk_size == 0:
                nr_of_messages_in_report = nr_of_messages - self.chunk_size
                messages_in_report = messages[:nr_of_messages_in_report]
                if nr_of_messages_in_report > 0:
                    messages_hash = self._get_chunk_hash(messages_in_report)
                    report = self._load_cached_summary(messages_hash)
                else:
                    report = ""
                historical_report = await self._generate_summary(
                    new_formatted_messages,
                    previous_report=report,
                    last_summary_step=nr_of_messages_in_report,
                )
                new_hash = self._get_chunk_hash(messages)
                self._save_summary_cache(new_hash, historical_report)
                nr_of_messages_in_report = nr_of_messages
            else:
                nr_of_messages_in_report = (
                    len(messages) // self.chunk_size
                ) * self.chunk_size
                messages_in_report = messages[:nr_of_messages_in_report]
                messages_hash = self._get_chunk_hash(messages_in_report)
                historical_report = self._load_cached_summary(messages_hash)

            # Historical report of actions and observations
            if system_message:
                sys = system_message.content.split(
                    "Historical report of actions, observations, variables and functions until step"
                )[0].strip()
                system_message.content = (
                    sys
                    + f"\n\nHistorical report of actions, observations, variables and functions until step {int(nr_of_messages_in_report / 2) - 1}\n\n{historical_report}\n\n"
                )
                new_formatted_messages = [system_message] + new_formatted_messages
        else:
            if system_message:
                new_formatted_messages = [system_message] + new_formatted_messages

        # First trim conversation to character limit
        new_formatted_messages = self._trim_conversation_to_limit(
            new_formatted_messages
        )
        return Conversation(messages=new_formatted_messages)

    def format_message(self, message: Message) -> Message:
        """Format a single message - apply entity data truncation if enabled."""
        return self._truncate_entity_data(message, is_recent=True)
