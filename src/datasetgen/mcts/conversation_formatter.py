from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any

from datasetgen.mcts.conversation import Message, Conversation

PLANNING_ADDITION_PROMPT = \
"""
First bring out a thorough step-by-step plan how you can achieve this task and then create the python script to achieve the task.
For your plan, follow this structure:
1) What entities are needed for the task
2) What entities do we have on the map, in different entity inventories or in our inventory
3) What entities are we missing for the task
4) Execution -- Taking into account 1,2 and 3, what steps do we need to take to successfully carry out the task
"""

class ConversationFormatter(ABC):
    """Abstract base class for conversation formatting strategies"""

    @abstractmethod
    def format_conversation(self, conversation: Conversation) -> List[Message]:
        """
        Format a conversation according to the specific strategy.
        Returns a list of formatted messages ready for LLM consumption.
        """
        pass

    @abstractmethod
    def format_message(self, message: Message) -> Message:
        """Format a single message according to the strategy"""
        pass

    def to_llm_messages(self, formatted_msgs: List[Message]) -> List[Dict[str, str]]:
        """Convert formatted messages to LLM-compatible format"""
        return [{"role": msg.role, "content": msg.content} for msg in formatted_msgs]

class DefaultFormatter(ConversationFormatter):
    def format_conversation(self, conversation: Conversation) -> List[Message]:
        return conversation.messages

    def format_message(self, message: Message) -> Message:
        return message

class OutputOnlyFormatter(ConversationFormatter):
    """
    Concrete formatter that preserves program outputs but omits program code.
    Only includes the results/printed output from program execution.
    """

    def __init__(self, planning = False):
        self.planning = planning

    def format_conversation(self, conversation: Conversation) -> List[Message]:
        formatted = []

        # Keep system message unchanged
        if conversation.messages and conversation.messages[0].role == "system":
            formatted.append(self.format_message(conversation.messages[0]))
            messages = conversation.messages[1:]
        else:
            messages = conversation.messages

        # Process message pairs (assistant's program + user's result)
        for i in range(0, len(messages), 2):
            if i + 1 >= len(messages):
                break

            assistant_msg = messages[i]
            user_msg = messages[i + 1]

            # Skip the assistant's program code
            if assistant_msg.role != "assistant":
                continue

            # Extract and format only the program output
            formatted_result = self.format_message(user_msg)
            if formatted_result:
                formatted.append(formatted_result)

        return formatted

    def format_message(self, message: Message) -> Message:
        if message.role == "system":
            # Preserve system messages unchanged
            return Message(role="system", content=message.content)

        elif message.role == "user":
            # Extract only the program output/results
            content = message.content
            try:
                # Split on common result markers
                if "Execution result" in content:
                    content = content.split("Execution result")[1]

                # Remove state information but keep reward
                if "Updated state:" in content:
                    content = content.split("Updated state:")[0]

                # Clean up and format
                content = content.strip()
                if content:
                    return Message(
                        role="user",
                        content=f"{PLANNING_ADDITION_PROMPT if self.planning else ''} Previous attempt result: {content}".strip()
                    )
            except Exception as e:
                print(f"Error formatting user message: {str(e)}")
                return None

        # Skip assistant messages (programs)
        return None